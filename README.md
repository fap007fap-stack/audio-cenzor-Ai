# AI Cenzor Studio v1.4.0

Aplikacja Streamlit do pracy z **nagraną mową** (także w kontenerze MP4). Transkrybuje polskie audio przez `faster-whisper`, podpowiada fragmenty zawierające wulgaryzmy, imiona, nazwiska, telefony, adresy oraz inne potencjalne dane osobowe. Pozwala **przyciąć fragment** lub **zastąpić go ciszą o dowolnej długości 0–30 sekund**. Eksport MP3, M4A, WAV i MP4 audio-only.

## Szybkie wdrożenie na GitHub / Streamlit

**Otwórz [INSTALACJA_GITHUB_STREAMLIT.md](INSTALACJA_GITHUB_STREAMLIT.md)** i wykonaj kroki. Kod nie wymaga osobnego katalogu `cenzor/`.

## Naprawione w v1.4

- `speech.py` przekazuje Whisperowi próbki `numpy.float32` z pliku WAV przygotowanego przez FFmpeg, zamiast ścieżki otwieranej przez PyAV. Omija w ten sposób `TypeError: open() got an unexpected keyword argument 'metadata_errors'`.
- `requirements.txt` przypina dodatkowo `av==18.1.0` dla zgodności z `faster-whisper==1.2.1`. Konfiguracja docelowa: Python 3.12.
- Dodatkowy test sprawdza, czy transkrypcja naprawdę otrzymuje tablicę NumPy, a nie ścieżkę audio.
- Wszystkie główne moduły znajdują się **obok** `app.py`, bez pozostałości starego `cenzor/`.
- Aplikacja zachowuje edytor tabelaryczny, odsłuch fragmentów, margines cięć, skalę czasu, raport JSON bez transkrypcji oraz diagnostykę środowiska.

## Uruchom lokalnie (zalecane przy poufnych danych)

Wymagania: **Python 3.12**, FFmpeg / ffprobe. Terminal w katalogu aplikacji:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## Działanie w praktyce

1. Wgrywasz MP4 / MP3 / M4A / WAV / FLAC / OGG / WebM / AAC (do 150 MB).
2. Whisper rozpoznaje polską mowę i czasy słów; reguły szukają danych i wulgaryzmów. Opcjonalny GLiNER2 (`requirements-ner.txt`) może rozszerzyć wykrywanie osób i innych danych.
3. W tabeli włączasz/wyłączasz wykrycia, poprawiasz czasy i wybierasz `Wytnij` lub `Wstaw ciszę` oraz długość ciszy.
4. Możesz dodać dowolny przedział ręcznie i odsłuchać oryginalny fragment.
5. FFmpeg tworzy nowy plik audio. Odsłuchujesz całość i pobierasz wynik wraz z opcjonalnym raportem JSON.

**Uwaga:** samo rozpoznawanie mowy nie zapewnia pełnego wykrycia danych. Ta wersja nie jest certyfikowanym narzędziem anonimizacji; zawsze konieczna jest kontrola człowieka. Streamlit Cloud przesyła nagrania na serwer dostawcy — do poufnych rozmów użyj wdrożenia lokalnego.

## Testy i kontrola

```bash
python -m unittest discover -s . -p 'test_*.py' -v
python -m compileall -q app.py speech.py audio_engine.py detectors.py quality_checks.py
```

Testy obejmują wykrywanie przykładowych danych, logikę cięć i ciszy, fizyczny eksport FFmpeg, integralność struktury repozytorium, regresję dekodera PyAV i przekazanie NumPy do Whispera. Test modelu Whisper na realnym polskim nagraniu wymaga pobrania wag i nie jest zastąpiony testami automatycznymi.

Zobacz też `ARCHITEKTURA.md`, `KONTROLA_JAKOSCI.md` i `INSTALACJA_GITHUB_STREAMLIT.md`.
