# AI Cenzor Studio v1.5.0

**Streamlit · polskie nagrania głosowe · lokalny Whisper · ręczna kontrola · FFmpeg**

Aplikacja przyjmuje MP4 z dźwiękiem, MP3, M4A, WAV, AAC, OGG, FLAC i WebM. Proponuje wycięcia wulgaryzmów i potencjalnych danych osobowych. Użytkownik decyduje, czy dany przedział **wyciąć** czy **zastąpić ciszą 0–30 sekund**. Eksport: MP3, M4A, WAV, MP4 audio-only.

**Ważne:** narzędzie wspomaga anonimizację, nie certyfikuje jej. Model może błędnie zapisać nazwisko, pomylić cyfry lub pominąć całą wypowiedź. Odsłuchaj wynik w całości przed użyciem.

## Co nowego w wersji 1.5

- **Pełny ciemny motyw** (`.streamlit/config.toml` + `style.css`): czarne tło, kontrastowy tekst, granatowe panele.
- **Modele ASR:** `small` (domyślnie), `base`, `medium`, `large-v3` i `tiny`. `medium` i `large-v3` wymagają znacznie więcej pamięci oraz czasu, na darmowej chmurze mogą nie działać.
- Profile transkrypcji `Szybki`, `Dokładny`, `Bardzo dokładny` (beam search 3 / 5 / 7); wymuszony polski; opcjonalne przygotowanie dźwięku (filtr pasmowy i wyrównanie głośności), przełączany VAD.
- Poprawianie **słów transkrypcji** (do 500 pozycji) i ponowne wykrywanie bez ponownego uruchamiania Whispera. Zachowujemy czasy, więc poprawne granice cięć trzeba potwierdzić odsłuchem.
- Lepsze wykrywanie **telefonów dyktowanych jako pojedyncze cyfry** także w zapisie `1,2,3,4,5,6,7,8,9` oraz typowych bloków `123 456 789`; polskie imiona w kontekście `Pani Alicja ...`, `z Janem` i część odmian adresów `ulicę ...`.
- Rozpoznane imiona i nazwiska to wciąż tylko kandydaci. Dodatkowy polski model GLiNER2 pozostaje opcjonalny, aby nie blokować startu na Streamlit Cloud. Jeśli się nie uruchomi, aplikacja nie traci wyników podstawowych.
- Eksport nie używa modelu AI; oryginalny dźwięk edytuje FFmpeg. Wstawiona cisza zawiera fizycznie wyciszony sygnał. Raport JSON **nie zawiera transkrypcji**.
- Dekodowanie transkrypcji omija problem `metadata_errors` dzięki `WAV 16 kHz` + `NumPy`; zależności `faster-whisper==1.2.1` / `av==18.1.0` przypięte z myślą o Pythonie 3.12.

## Wdrożenie GitHub → Streamlit Cloud

Szczegóły: **[INSTALACJA_GITHUB_STREAMLIT.md](INSTALACJA_GITHUB_STREAMLIT.md)**.

1. Rozpakuj ZIP. Wgraj **zawartość** paczki do katalogu głównego repozytorium GitHub (obok siebie: `app.py`, `audio_engine.py`, `speech.py`, `detectors.py`, `style.css`, `requirements.txt`, `packages.txt`). Wgraj również ukryty folder `.streamlit` z `config.toml` i `.github` z testami.
2. W Streamlit Community Cloud wskaż repozytorium, gałąź `main`, plik `app.py` i ustaw **Python 3.12** w Advanced settings.
3. Po wdrożeniu sprawdź napis **1.5.0** w aplikacji i wykonaj test na nagraniu z fikcyjnymi danymi. Na chmurze zacznij od `small`; jeśli wystąpi błąd RAM, użyj `base`.
4. *Przy wrażliwych rozmowach nie używaj publicznej chmury bez oceny przetwarzania danych.* Lokalna instalacja jest bezpieczniejszym punktem wyjścia.

### Lokalnie (zalecane do rzeczywistych poufnych rozmów)

Wymagania: Python 3.12, zainstalowane `ffmpeg` i `ffprobe` w PATH.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

### Opcjonalny model PII (GLiNER2)

Bazowy projekt **nie pobiera** GLiNER2. Aby włączyć NER w środowisku lokalnym z odpowiednią pamięcią:

```bash
python -m pip install -r requirements-ner.txt
```

Po instalacji uruchom ponownie Streamlit i zaznacz **Polski model PII (dodatkowy)**. Na Streamlit Cloud wymagałoby to dodania samej linii `gliner2[local]==1.3.2` do głównego `requirements.txt` i przebudowania środowiska; może przekroczyć limity pamięci. Model: [piotrmaciejbednarski/gliner2-polish-pii](https://huggingface.co/piotrmaciejbednarski/gliner2-polish-pii).

### Jak poprawić rozpoznawanie

- `small` + profil `Dokładny` na początek. `medium` wybieraj tylko gdy serwer ma zapas RAM; nie ma automatycznej gwarancji poprawy na każdym nagraniu.
- Gdy nagranie jest ciche, włącz opcjonalne wyrównanie głośności. Sprawdź transkrypcję z filtrem i bez niego; silny filtr potrafi pogorszyć mowę.
- Jeśli Whisper pomija krótkie liczby, zostaw VAD wyłączony (wartość domyślna).
- Dopisz znane nazwiska do listy własnych fraz. Wskazówka do modelu mowy jest osobnym checkboxem i domyślnie wyłączona, bo może powodować halucynacje.
- Skoryguj pomylone słowa w edytorze transkrypcji lub dodaj zakresy ręcznie. **Czasy z Whispera są przybliżone**, szczególnie na początku i końcu słowa.

### Testy

```bash
python -m unittest discover -s . -p 'test_*.py' -v
python -m compileall -q app.py audio_engine.py detectors.py speech.py quality_checks.py
```

Testy sprawdzają reguły, integralność eksportu audio, ciszę, formaty, numery dyktowane i zgodność konfiguracji. **Nie stanowią pomiaru rzeczywistej skuteczności rozpoznawania na polskich nagraniach.** Zobacz także `KONTROLA_JAKOSCI.md`, `ARCHITEKTURA.md`.

## Prywatność

Aplikacja nie używa płatnego API mowy, ale wdrożenie w Streamlit Cloud oznacza przesłanie pliku na zdalny serwer. Modele są pobierane z Hugging Face. Po zakończeniu kliknij **Usuń pliki tej sesji**. Własne nagrania, dane klientów, pliki `.env` i tokeny nie powinny trafić do repozytorium. Nie zakładaj, że automatyczna cenzura usuwa 100% PII.
