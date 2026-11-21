"""AI Cenzor Studio — privacy-aware Streamlit voice redaction tool.

Run with: streamlit run app.py
The default pipeline never calls an external transcription API; on cloud hosting
all uploaded files are still transferred to the remote Streamlit server.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import tempfile
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

# The processing modules live next to app.py. Explicitly include that folder so
# Streamlit can load them consistently when deployed from GitHub.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
REQUIRED_LOCAL_FILES = ("audio_engine.py", "detectors.py", "quality_checks.py", "speech.py")
missing_local_files = [name for name in REQUIRED_LOCAL_FILES if not (APP_DIR / name).is_file()]
if missing_local_files:
    st.set_page_config(page_title="AI Cenzor Studio — naprawa instalacji", layout="centered")
    st.error("Niekompletne repozytorium: brakuje plików silnika aplikacji.")
    st.code("\n".join(missing_local_files))
    st.info("Wgraj do głównego katalogu repozytorium wszystkie pliki z paczki ZIP \n" 
            "(obok app.py), zatwierdź zmiany w GitHub i uruchom aplikację ponownie.")
    st.stop()

from audio_engine import (
    Edit, audio_info, export_audio, export_excerpt, extract_audio, make_timeline,
    normalize_edits, result_duration,
)
from detectors import CATEGORIES, deduplicate, detect_all, gliner2_for_tokens
from quality_checks import fingerprint, overlapping_pairs, redaction_report
from speech import load_model, transcribe

APP_VERSION = "1.3.0"
ROOT = Path(__file__).resolve().parent
MAX_UPLOAD_BYTES = 150 * 1024 * 1024
EDIT_COLS = ["ID", "Zastosuj", "Od (s)", "Do (s)", "Kategoria", "Wykryty fragment",
             "Metoda", "Cisza (s)", "Źródło", "Pewność"]
FORMATS = {"MP3": (".mp3", "audio/mpeg"), "M4A": (".m4a", "audio/mp4"),
           "WAV": (".wav", "audio/wav"), "MP4 · tylko audio": (".mp4", "audio/mp4")}
INPUT_MIMES = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".mp4": "audio/mp4",
               ".wav": "audio/wav", ".flac": "audio/flac", ".webm": "audio/webm",
               ".ogg": "audio/ogg", ".aac": "audio/aac"}

st.set_page_config(page_title="AI Cenzor Studio — prywatność w nagraniach", page_icon="🎙️",
                   layout="wide", initial_sidebar_state="expanded")
# Public HF models do not require a token. A token stored in Streamlit Secrets
# can optionally increase download rate limits; never display or log its value.
if not os.environ.get("HF_TOKEN"):
    try:
        hf_token = st.secrets.get("HF_TOKEN")
    except Exception:
        hf_token = None
    if hf_token:
        os.environ["HF_TOKEN"] = str(hf_token)

style_path = ROOT / "style.css"
if style_path.is_file():
    st.markdown(f"<style>{style_path.read_text(encoding='utf-8')}</style>",
                unsafe_allow_html=True)
else:
    st.warning("Brakuje style.css — interfejs działa, ale bez dodatkowego stylu. Wgraj ten plik obok app.py.")


@st.cache_resource(show_spinner="Ładowanie modelu rozpoznawania mowy…")
def whisper_cached(size: str):
    return load_model(size)


@st.cache_resource(show_spinner="Uruchamianie dodatkowego polskiego modelu PII…")
def pii_model_cached():
    from gliner2 import GLiNER2
    return GLiNER2.from_pretrained("piotrmaciejbednarski/gliner2-polish-pii")


def fmt_time(t: float) -> str:
    secs = max(0.0, float(t))
    minutes, seconds = divmod(secs, 60.0)
    return f"{int(minutes):02}:{seconds:05.2f}"


def step(number: int, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="ai-section"><div class="ai-step">{number:02}</div>'
                f'<div><h2>{escape(title)}</h2><p>{escape(subtitle)}</p></div></div>',
                unsafe_allow_html=True)


def reset_file_state() -> None:
    old = st.session_state.get("workdir")
    if old:
        shutil.rmtree(old, ignore_errors=True)
    for key in ["workdir", "source", "file_id", "info", "rows", "tokens", "transcript",
                "analysis_key", "revision", "output", "export_key", "preview_path", "preview_key",
                "preview_number", "last_analysis_warnings", "verified_download", "analysis_diag"]:
        st.session_state.pop(key, None)


def upload_file(upload) -> None:
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValueError("Plik przekracza limit 150 MB.")
    suffix = Path(upload.name).suffix.lower()
    if suffix not in INPUT_MIMES:
        raise ValueError("Nieobsługiwane rozszerzenie pliku.")
    raw = upload.getbuffer()
    signature = hashlib.sha256(raw).hexdigest()
    if st.session_state.get("file_id") == signature:
        return
    reset_file_state()
    folder = Path(tempfile.mkdtemp(prefix="ai_cenzor_studio_"))
    src = folder / ("oryginal" + suffix)
    try:
        with src.open("wb") as handle:
            handle.write(raw)
        info = audio_info(src)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    st.session_state.update({"workdir": str(folder), "source": str(src), "file_id": signature,
                             "info": info, "rows": [], "revision": 0})


def editor_frame() -> pd.DataFrame:
    return pd.DataFrame(st.session_state.get("rows", []), columns=EDIT_COLS)


def validate_edits(table: pd.DataFrame, duration: float) -> list[Edit]:
    selected: list[Edit] = []
    for number, (_, row) in enumerate(table.iterrows(), 1):
        if not bool(row["Zastosuj"]):
            continue
        try:
            start = float(row["Od (s)"])
            end = float(row["Do (s)"])
            silence = float(row["Cisza (s)"])
            action = str(row["Metoda"])
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Wiersz {number}: uzupełnij poprawnie czasy i metodę.") from exc
        if not all(math.isfinite(v) for v in (start, end, silence)):
            raise ValueError(f"Wiersz {number}: czasy muszą być liczbami.")
        if not (0 <= start < end <= duration + 0.02):
            raise ValueError(f"Wiersz {number}: początek i koniec muszą mieścić się w nagraniu.")
        if action not in ("Wytnij", "Wstaw ciszę") or not (0 <= silence <= 30):
            raise ValueError(f"Wiersz {number}: wybierz metodę i ciszę 0–30 sekund.")
        selected.append(Edit(start, min(end, duration), action, silence))
    if len(selected) > 250:
        raise ValueError("Limit 250 zaznaczonych fragmentów na eksport. Podziel nagranie na części.")
    return selected


def timeline_html(edits: list[Edit], duration: float, padding: float) -> str:
    intervals = normalize_edits(edits, duration, padding)
    tags: list[str] = []
    cursor = 0.0
    for item in intervals:
        if item.start > cursor:
            tags.append(f'<span title="Zachowane" style="width:{100*(item.start-cursor)/duration:.6f}%;background:#9cc6f5"></span>')
        color = '#fc8c83' if item.action == 'Wytnij' else '#4acabb'
        label = 'Wycięcie' if item.action == 'Wytnij' else 'Zastąpienie ciszą'
        tags.append(f'<span title="{label}" style="width:{100*(item.end-item.start)/duration:.6f}%;background:{color}"></span>')
        cursor = item.end
    if cursor < duration:
        tags.append(f'<span title="Zachowane" style="width:{100*(duration-cursor)/duration:.6f}%;background:#9cc6f5"></span>')
    if not tags:
        tags.append('<span style="width:100%;background:#9cc6f5"></span>')
    return ('<div class="ai-timeline">' + ''.join(tags) + '</div>'
            '<div class="ai-key">'
            '<span class="ai-dot" style="background:#9cc6f5"></span>Zachowane &nbsp;&nbsp; '
            '<span class="ai-dot" style="background:#fc8c83"></span>Wycięte &nbsp;&nbsp; '
            '<span class="ai-dot" style="background:#4acabb"></span>Zastąpione ciszą'
            '</div>')


def export_reset() -> None:
    st.session_state.pop("output", None)
    st.session_state.pop("export_key", None)
    st.session_state.pop("verified_download", None)


# ──────────────────────── BRAND / APPLICATION SHELL ────────────────────────
st.markdown('''<div class="ai-hero"><div class="ai-kicker">AUDIO PRIVACY WORKSPACE</div>
<h1>AI Cenzor <span style="color:#7de6d4">Studio</span></h1>
<p>Zamień surową rozmowę w nagranie gotowe do nauki. Znajdź dane osobowe i wulgaryzmy,
zatwierdź precyzyjne cięcia i wybierz własną długość ciszy.</p>
<span class="ai-pill">🎙 Tylko nagrania głosowe</span>
<span class="ai-pill">✂ Precyzyjny montaż</span>
<span class="ai-pill">🔒 Bez zewnętrznego API mowy</span>
<span class="ai-pill">🛠 Wersja 1.3.0 · diagnostyka AI</span></div>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Ustawienia projektu")
    st.caption("AI Cenzor Studio · " + APP_VERSION)
    st.markdown("**Szukaj w nagraniu:**")
    enabled: set[str] = set()
    for category in CATEGORIES:
        if st.checkbox(category, value=True, key="category_" + category):
            enabled.add(category)
    st.divider()
    model_size = st.selectbox("Model rozpoznawania mowy", ["tiny", "base", "small"], index=1,
                              help="Base jest rozsądnym kompromisem; small wymaga więcej zasobów.")
    ner_installed = importlib.util.find_spec("gliner2") is not None
    use_ner = st.checkbox("Polski model PII (dodatkowy)", disabled=not ner_installed,
                          help="Wymaga instalacji requirements-ner.txt; na darmowej chmurze może zabraknąć pamięci.")
    if not ner_installed:
        st.warning("Dodatkowy model rozpoznawania osób (GLiNER2) NIE jest zainstalowany. "
                   "Whisper rozpoznaje mowę, a wykrywanie danych odbywa się przede wszystkim "
                   "według reguł. Pełne rozpoznawanie nazwisk wymaga osobnego modelu.")
    additional = st.text_area("Własna lista słów i nazwisk", height=95,
                              placeholder="Jan Kowalski\nNazwa firmy\nPseudonim",
                              help="Jedna fraza w wierszu; wyszukiwane będą jej wystąpienia w transkrypcji.")
    custom_phrases = [w.strip() for w in additional.splitlines() if 1 < len(w.strip()) <= 130][:70]
    st.divider()
    default_action = st.radio("Domyślny sposób redakcji", ["Wytnij", "Wstaw ciszę"], horizontal=False)
    default_silence = st.number_input("Domyślna cisza (s)", 0.0, 30.0, 1.0, 0.25, format="%.2f")
    padding = st.slider("Margines bezpieczeństwa (s)", 0.0, 0.5, 0.12, 0.01,
                        help="Margines zostanie dodany do obu końców każdego zaznaczonego fragmentu.")
    st.divider()
    with st.expander("Diagnostyka AI / serwera", expanded=True):
        st.caption("Testowanie środowiska bez wysyłania nagrania do zewnętrznego API.")
        st.write("Wersja aplikacji:", APP_VERSION)
        st.write("Python:", sys.version.split()[0])
        st.write("Whisper (biblioteka):", "Dostępna" if importlib.util.find_spec("faster_whisper") else "BRAK — sprawdź requirements.txt")
        st.write("FFmpeg:", "Dostępny" if shutil.which('ffmpeg') else "BRAK")
        st.write("FFprobe:", "Dostępny" if shutil.which('ffprobe') else "BRAK")
        st.write("Dodatkowy model PII:", "Zainstalowany" if ner_installed else "NIEZAINSTALOWANY")
        st.write("Token HF:", "Ustawiony" if os.environ.get("HF_TOKEN") else "Brak (opcjonalny)")
        if sys.version_info[:2] != (3, 12):
            st.warning("Zalecany Python 3.12. Obecny interpreter może mieć inne wersje lub zgodność bibliotek.")
        if st.button("Przetestuj detektor danych (bez pobierania AI)"):
            demo = ["Nazywam", "się", "Jan", "Kowalski", "telefon", "501", "234", "567", "kurwa"]
            from detectors import Token
            synthetic = [Token(w, i * 0.4, (i + 1) * 0.4) for i, w in enumerate(demo)]
            _, checks = detect_all(synthetic, set(CATEGORIES))
            categories = sorted(set(f.category for f in checks))
            if {"Imiona i nazwiska", "Numery telefonów", "Wulgaryzmy"}.issubset(categories):
                st.success("Detektor reguł działa: nazwisko, telefon i wulgaryzm wykryte na próbce.")
            else:
                st.error("Test detektora nie przeszedł. Sprawdź zgodność plików z wersją 1.3.0.")
            st.caption("Ten test NIE sprawdza Whispera ani modelu GLiNER2 i nie potwierdza skuteczności anonimizacji.")
    if st.button("Usuń pliki tej sesji", width="stretch", key="reset"):
        reset_file_state()
        # Changing the uploader key also clears browser-side uploader state.
        st.session_state["upload_revision"] = st.session_state.get("upload_revision", 0) + 1
        st.rerun()

step(1, "Dodaj nagranie", "Obsługiwane: MP4 (audio), MP3, M4A, WAV, OGG, FLAC, AAC, WebM · maks. 150 MB")
with st.container(border=True):
    upload = st.file_uploader("Przeciągnij plik lub wybierz z dysku",
                              key=f"audio_upload_{st.session_state.get('upload_revision', 0)}",
                              type=["mp4", "m4a", "mp3", "wav", "aac", "ogg", "flac", "webm"],
                              help="Aplikacja zawsze pracuje na ścieżce audio, nie na obrazie.")
    if upload is None:
        st.markdown('<div class="ai-note">Wgraj krótką próbkę, aby przetestować cały proces. '
                    'Rozpoznawanie mowy pobiera model przy pierwszym uruchomieniu. '
                    'Możesz też wykonać cięcia ręcznie, bez uruchamiania AI.</div>', unsafe_allow_html=True)
        st.stop()
    try:
        upload_file(upload)
    except Exception as exc:
        st.error(f"Nie udało się odczytać pliku: {exc}")
        st.stop()
    info = st.session_state["info"]
    duration = float(info["duration"])
    source = Path(st.session_state["source"])
    a, b, c = st.columns(3)
    a.metric("Długość", fmt_time(duration))
    b.metric("Format dźwięku", str(info["codec"]).upper())
    c.metric("Kanały", str(info["channels"]))
    if info["has_video"]:
        st.info("Plik zawiera także obraz. Eksport będzie zawierał wyłącznie dźwięk, zgodnie z założeniem projektu.")
    with st.expander("Odsłuch oryginalnego nagrania", expanded=False):
        st.audio(str(source), format=INPUT_MIMES[source.suffix])

# Fingerprint prevents applying decisions based on out-of-date detection settings.
current_analysis_key = fingerprint([st.session_state["file_id"], sorted(enabled), model_size,
                                    use_ner, sorted(custom_phrases)])
step(2, "Wykrywanie AI", "Transkrypcja polskiej mowy + rozpoznawanie wrażliwych informacji")
with st.container(border=True):
    l, r = st.columns([3, 2], vertical_alignment="center")
    with l:
        st.markdown("**Wykrywanie w dwóch warstwach**")
        st.caption("Whisper lokalnie na serwerze aplikacji, następnie reguły i opcjonalny polski model NER. Wyniki są propozycjami.")
    with r:
        run_analysis = st.button("Uruchom analizę nagrania", type="primary", width="stretch", disabled=not bool(enabled or custom_phrases))
    if not use_ner:
        st.info("Tryb podstawowy: Whisper + detektory regułowe. "
                "Polski model NER jest wyłączony, więc część imion i nazwisk może nie zostać wykryta.")
    if run_analysis:
        try:
            with st.status("Uruchamianie analizy…", expanded=True) as status:
                st.write("Etap 1/4: przygotowanie ścieżki audio")
                transcribed_wav = Path(st.session_state["workdir"]) / "do_rozpoznawania.wav"
                extract_audio(source, transcribed_wav)
                st.write("Etap 2/4: uruchomienie Whispera. Pierwszy raz może wymagać pobrania modelu z Hugging Face")
                model = whisper_cached(model_size)
                st.write("Etap 3/4: rozpoznawanie polskich słów — ten etap wykonuje się na serwerze Streamlit")
                tokens = transcribe(transcribed_wav, model)
                st.write(f"Rozpoznano {len(tokens)} elementów tekstu. Wyszukiwanie danych…")
                text, found = detect_all(tokens, enabled, custom_phrases)
                rules_count = len(found)
                if use_ner and tokens:
                    st.write("Etap 4/4: weryfikacja nazwisk i danych przez model GLiNER2")
                    found = deduplicate(found + gliner2_for_tokens(tokens, pii_model_cached(), enabled))
                else:
                    st.write("Etap 4/4: dodatkowy model GLiNER2 wyłączony lub brak tekstu")
                status.update(label="Analiza zakończona", state="complete")
            found.sort(key=lambda f: (f.start, f.end))
            st.session_state["rows"] = [{
                "ID": i+1, "Zastosuj": True,
                "Od (s)": round(max(0.0, f.start), 3),
                "Do (s)": round(min(duration, f.end), 3),
                "Kategoria": f.category, "Wykryty fragment": f.text,
                "Metoda": default_action, "Cisza (s)": float(default_silence),
                "Źródło": f.source, "Pewność": round(float(f.confidence), 2),
            } for i, f in enumerate(found) if f.end > f.start and f.start < duration]
            st.session_state["tokens"] = tokens
            st.session_state["transcript"] = text
            st.session_state["analysis_key"] = current_analysis_key
            st.session_state["analysis_diag"] = {"tokens": len(tokens), "rules_count": rules_count,
                                                  "total_count": len(found), "ner": bool(use_ner),
                                                  "model": model_size}
            st.session_state["revision"] = st.session_state.get("revision", 0) + 1
            export_reset()
            st.success(f"Analiza zakończona. Wykryto {len(st.session_state['rows'])} potencjalnych fragmentów.")
            if not tokens:
                st.warning("Whisper nie odczytał żadnych słów. Sprawdź, czy nagranie zawiera zrozumiałą "
                           "polską mowę; spróbuj modelu 'base' lub 'small' albo dodaj zakresy ręcznie.")
            elif not found:
                st.warning("Whisper rozpoznał słowa, ale detektory nie znalazły zaznaczonych kategorii. "
                           "Sprawdź tekst poniżej. Model GLiNER2 może być niezainstalowany; "
                           "imiona zapisane małymi literami mogą umknąć regułom.")
        except Exception as exc:
            st.error(f"Analiza się nie powiodła ({type(exc).__name__}): {exc}")
            st.info("Jeśli błąd dotyczy pobierania: sprawdź internet/Hugging Face i opcjonalny "
                    "HF_TOKEN w Secrets Streamlit. Jeśli brakuje RAM, wybierz model 'tiny'. "
                    "Do wycinania możesz użyć ręcznych zakresów.")
    if st.session_state.get("analysis_key") != current_analysis_key and st.session_state.get("analysis_key") is not None:
        st.warning("Zmieniono kategorię, model lub własne frazy. Uruchom analizę ponownie, aby odświeżyć wykrycia.")
    if st.session_state.get("analysis_diag"):
        diag = st.session_state["analysis_diag"]
        st.caption(f"Diagnostyka ostatniej analizy: model Whisper {diag['model']} · "
                   f"rozpoznane słowa: {diag['tokens']} · detektor regułowy: {diag['rules_count']} · "
                   f"łącznie propozycji: {diag['total_count']} · model PII: "
                   f"{'użyty' if diag['ner'] else 'nieużyty'}")
    if "transcript" in st.session_state:
        with st.expander("Sprawdź transkrypcję (oryginalny tekst zawiera dane z rozmowy)"):
            st.text_area("Rozpoznany tekst", st.session_state["transcript"], height=175,
                         disabled=True, help="Czasy cięć zmieniasz w edytorze, nie tutaj.")
            st.caption("Uwaga: AI może pominąć słowa. Najpierw sprawdź pełną transkrypcję, potem odsłuchaj wynik.")

step(3, "Edytor fragmentów", "Każde wykrycie możesz poprawić, odznaczyć lub zastąpić ciszą o innej długości")
frame = editor_frame()
with st.container(border=True):
    if frame.empty:
        st.info("Nie ma jeszcze wykryć. Uruchom analizę lub dodaj fragment ręcznie.")
        edited = frame
    else:
        edited = st.data_editor(
            frame, hide_index=True, width="stretch", num_rows="fixed",
            key=f"editor_{st.session_state.get('revision', 0)}",
            disabled=["ID", "Kategoria", "Wykryty fragment", "Źródło", "Pewność"],
            column_config={
                "Zastosuj": st.column_config.CheckboxColumn("Usuń / zastąp", required=True),
                "Od (s)": st.column_config.NumberColumn("Od (s)", min_value=0, max_value=duration, step=0.05, format="%.2f", required=True),
                "Do (s)": st.column_config.NumberColumn("Do (s)", min_value=0, max_value=duration, step=0.05, format="%.2f", required=True),
                "Wykryty fragment": st.column_config.TextColumn("Fraza", width="medium"),
                "Metoda": st.column_config.SelectboxColumn("Sposób", options=["Wytnij", "Wstaw ciszę"], required=True),
                "Cisza (s)": st.column_config.NumberColumn("Wstaw ciszę (s)", min_value=0, max_value=30, step=0.25, format="%.2f", required=True),
                "Pewność": st.column_config.NumberColumn("Ocena metody", format="%.2f",
                               help="Orientacyjna ocena detektora, NIE pewność anonimizacji"),
            },
        )

    with st.expander("Dodaj brakujący fragment ręcznie", expanded=frame.empty):
        with st.form("add_manual", clear_on_submit=False):
            p1, p2, p3 = st.columns(3)
            with p1:
                add_start = st.number_input("Od sekundy", min_value=0.0, max_value=duration,
                                            value=0.0, step=0.1, format="%.2f")
            with p2:
                add_end = st.number_input("Do sekundy", min_value=0.0, max_value=duration,
                                          value=min(1.0, duration), step=0.1, format="%.2f")
            with p3:
                add_action = st.selectbox("Metoda", ["Wytnij", "Wstaw ciszę"], index=0 if default_action == "Wytnij" else 1)
            p4, p5 = st.columns([1, 2])
            with p4:
                add_silence = st.number_input("Cisza (s)", 0.0, 30.0, float(default_silence), 0.25, format="%.2f")
            with p5:
                add_label = st.text_input("Opis (opcjonalnie)", placeholder="np. nazwisko klienta")
            if st.form_submit_button("Dodaj do edytora", width="stretch"):
                if not (0 <= add_start < add_end <= duration + 0.02):
                    st.error("Podaj przedział wewnątrz nagrania z końcem większym od początku.")
                else:
                    current = edited.to_dict("records")
                    st.session_state["rows"] = current + [{
                        "ID": max([int(row['ID']) for row in current], default=0) + 1,
                        "Zastosuj": True, "Od (s)": add_start, "Do (s)": add_end,
                        "Kategoria": "Ręczne", "Wykryty fragment": add_label,
                        "Metoda": add_action, "Cisza (s)": add_silence,
                        "Źródło": "Użytkownik", "Pewność": 1.0,
                    }]
                    st.session_state["revision"] = st.session_state.get("revision", 0) + 1
                    export_reset()
                    st.rerun()

    valid = True
    try:
        edits = validate_edits(edited, duration)
        plan = make_timeline(edits, duration, padding)
        estimated_duration = result_duration(plan)
    except (ValueError, TypeError, OverflowError) as exc:
        valid = False
        edits, estimated_duration = [], duration
        st.error(f"Popraw dane przed eksportem: {exc}")

    if valid:
        st.markdown(timeline_html(edits, duration, padding), unsafe_allow_html=True)
        x, y, z = st.columns(3)
        x.metric("Aktywne wykrycia", len(edits))
        y.metric("Szacowany wynik", fmt_time(estimated_duration))
        z.metric("Zmiana długości", f"{estimated_duration-duration:+.2f} s")
        overlaps = overlapping_pairs(edits, duration, padding)
        if overlaps:
            st.warning(f"Wykryto {overlaps} nakładających się zakresów (z marginesem). "
                       "Takie zakresy zostaną scalone; jeśli chociaż jeden ma tryb 'Wytnij', "
                       "cały wspólny obszar zostanie wycięty. Sprawdź granice.")

    if not edited.empty:
        with st.expander("Odsłuchaj konkretny fragment przed cięciem"):
            labels = [f"{i+1:02}. {fmt_time(float(row['Od (s)']))} – {fmt_time(float(row['Do (s)']))} · {str(row['Kategoria'])}"
                      for i, (_, row) in enumerate(edited.iterrows())]
            selection = st.selectbox("Fragment do odsłuchu", list(range(len(labels))), format_func=lambda i: labels[i])
            chosen = edited.iloc[selection]
            start_at = max(0.0, float(chosen["Od (s)"]) - 2)
            end_at = min(duration, float(chosen["Do (s)"]) + 2)
            if end_at - start_at > 45:
                end_at = start_at + 45
                st.caption("Podgląd ograniczony do 45 sekund.")
            sample_key = fingerprint([st.session_state["file_id"], start_at, end_at])
            if st.button("Odsłuchaj ±2 s wokół wykrycia", width="stretch"):
                try:
                    sample_path = Path(st.session_state["workdir"]) / "odsluch_fragmentu.mp3"
                    export_excerpt(source, sample_path, start_at, end_at, duration)
                    st.session_state["preview_path"] = str(sample_path)
                    st.session_state["preview_key"] = sample_key
                except Exception as exc:
                    st.error(f"Nie można przygotować odsłuchu: {exc}")
            if st.session_state.get("preview_key") == sample_key:
                preview = Path(st.session_state.get("preview_path", ""))
                if preview.is_file():
                    st.audio(str(preview), format="audio/mpeg")

step(4, "Eksport i kontrola jakości", "Wygeneruj, odsłuchaj w całości, następnie pobierz oczyszczony dźwięk")
with st.container(border=True):
    f1, f2 = st.columns([2, 1], vertical_alignment="bottom")
    with f1:
        format_name = st.selectbox("Format pliku wynikowego", list(FORMATS), index=0)
    with f2:
        st.caption("MP4 zawiera wyłącznie ścieżkę audio — bez obrazu.")
    suffix, mime = FORMATS[format_name]
    key = fingerprint([st.session_state.get('file_id'), edited.to_dict('records'), padding, format_name])
    if st.session_state.get("export_key") != key:
        export_reset()
    disabled = not valid or not edits or (st.session_state.get("analysis_key") not in (None, current_analysis_key))
    if not edits and valid:
        st.info("Zaznacz co najmniej jeden przedział, aby przygotować oczyszczone nagranie.")
    if st.button("Wygeneruj oczyszczony plik", type="primary", width="stretch", disabled=disabled):
        try:
            dest = Path(st.session_state["workdir"]) / ("AI_Cenzor_Studio_wynik" + suffix)
            with st.spinner("FFmpeg wycina fragmenty i składa nowy plik audio…"):
                produced = export_audio(source, dest, edits, duration, padding)
            st.session_state.update({"output": str(dest), "export_key": key, "produced": produced})
            st.session_state["verified_download"] = False
            st.success("Plik gotowy. Odsłuchaj go przed pobraniem.")
        except Exception as exc:
            export_reset()
            st.error(f"Eksport nie powiódł się: {exc}")
    if st.session_state.get("export_key") == key:
        path = Path(st.session_state.get("output", ""))
        if path.is_file():
            st.markdown("**Odsłuch pliku wynikowego**")
            st.audio(str(path), format=mime)
            st.markdown('<div class="ai-note ai-note-amber">Automatyczna redakcja nie jest gwarancją anonimizacji. '
                        'Sprawdź odsłuchem całe nagranie: początek, koniec, okolice cięć i dane wypowiedziane słownie.</div>',
                        unsafe_allow_html=True)
            accept = st.checkbox("Odsłuchałem/am wynik i samodzielnie sprawdziłem/am, czy dane zostały usunięte.",
                                 key="verified_download")
            d1, d2 = st.columns([2, 1])
            with d1:
                st.download_button("Pobierz gotowe nagranie", data=path.read_bytes(),
                                   file_name=path.name, mime=mime, disabled=not accept,
                                   type="primary", width="stretch")
            with d2:
                report = redaction_report(edits, duration, padding, output_duration=estimated_duration, format_name=format_name)
                st.download_button("Pobierz raport JSON", data=report,
                                   file_name="AI_Cenzor_raport.json", mime="application/json", width="stretch")

st.markdown('<div class="ai-footer">AI Cenzor Studio · Twój dźwięk, Twoja decyzja · '
            'Bez automatycznego publikowania nagrań · 2026</div>', unsafe_allow_html=True)
st.caption("Prywatność: w Streamlit Community Cloud pliki są przesyłane na zewnętrzny serwer; "
           "przy poufnych rozmowach uruchom aplikację lokalnie albo na własnym zabezpieczonym serwerze. "
           "Wyczyść sesję po zakończeniu pracy.")
