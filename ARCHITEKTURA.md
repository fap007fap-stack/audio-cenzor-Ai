# AI Cenzor Studio v1.5 — architektura

| Element | Odpowiedzialność |
|---|---|
| `app.py` | UI Streamlit, sesja, edytor, diagnostyka, kontrola przed pobraniem |
| `speech.py` | model Whisper (CPU int8), WAV→NumPy bez używania `av.open`, PL, 3 profile jakości, znaczniki czasowe |
| `detectors.py` | reguły wulgaryzmów, telefonów cyfrowych/dyktowanych, e-maili, adresów, imion z kontekstu oraz własnych fraz; opcjonalnie GLiNER2 |
| `audio_engine.py` | FFprobe/FFmpeg, przygotowanie audio, fizyczne wycinanie, cisza, eksport 4 formatów |
| `quality_checks.py` | fingerprint, ostrzeżenia konfliktów, raport JSON bez tekstu |
| `style.css`, `.streamlit/config.toml` | motyw ciemny oraz dostosowanie wyglądu |

## Przepływ danych

Przesłany plik → katalog tymczasowy sesji → FFmpeg/WAV 16k mono → faster-whisper → słowa z czasami → reguły (+ opcjonalne GLiNER2) → tabela propozycji → ręczna korekta → cięcie oryginału FFmpeg → kontrola długości → odsłuch i eksport.

**Poprawki transkrypcji** zmieniają tekst słowa przy zachowaniu znacznika czasowego z oryginału; po poprawieniu detektory uruchamiane są ponownie. Nie gwarantuje to, że granice czasowe będą idealne.

**Brak zewnętrznego API mowy:** model Hugging Face jest pobierany na serwer i działa lokalnie względem tego serwera. Streamlit Cloud nadal jest hostingiem zewnętrznym. Nie używamy ani nie zapisujemy rozmów w GitHubie.

## Ograniczenia świadome

- Bez instalacji GLiNER2 imiona i nazwiska pochodzą z reguł; nie jest to pełne NER.
- Modele `medium`/`large-v3` mogą przekroczyć limity RAM w Community Cloud i nie muszą poprawić każdego pliku.
- Polskie dyktowane liczby typu „pięćset jeden, dwieście...” wymagają dodatkowej pracy; aplikacja rozpoznaje pojedyncze cyfry oraz wiele bloków zapisanych cyfrowo.
- Łączenie fragmentów używa priorytetu `Wytnij` przy konfliktach; użytkownik powinien przejrzeć zakresy i wynik.
- Użytkownik nie powinien uważać ostrzeżeń o powodzeniu analizy za gwarancję usunięcia wszystkich danych.
