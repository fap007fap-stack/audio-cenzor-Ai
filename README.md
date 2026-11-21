# AI Cenzor Studio 1.7.0 — wspólny edytor fali dźwiękowej

**Streamlit · polskie nagrania głosowe · faster-whisper · FFmpeg · prywatność z kontrolą człowieka**

Aplikacja odczytuje MP4 (audio-only lub z obrazem), MP3, M4A, WAV, AAC, OGG, FLAC i WebM. Rozpoznaje polską mowę, proponuje wycięcia wulgaryzmów i potencjalnych danych osobowych, a następnie eksportuje MP3, M4A, WAV lub MP4 z samą ścieżką audio. AI *nie gwarantuje* usunięcia wszystkich danych.

## Nowość v1.7: edytor podobny do Audacity

W kroku 3 znajduje się **jedna wspólna fala dźwiękowa z WSZYSTKIMI zaznaczeniami naraz**. To **nie jest** panel kolejnych suwaków dla pojedynczych fragmentów.

1. Uruchom analizę AI. Wszystkie wykrycia pojawią się na przebiegu fali: czerwone obszary = **Wytnij**, turkusowe = **Wstaw ciszę**.
2. **Przeciągnij całe zaznaczenie**, aby przesunąć je w czasie. Złap **lewą lub prawą krawędź**, aby skrócić albo wydłużyć przedział.
3. Kliknij przycisk **Odtwarzaj po cięciach**: odtwarzacz w przeglądarce przeskakuje wszystkie aktualnie wycięte fragmenty lub pauzuje na czas wstawianej ciszy. **Oryginał** odtwarza bez cenzury. Przyciskiem **Odsłuchaj od zaznaczenia** można rozpocząć blisko konkretnego cięcia.
4. Użyj **Zoom** do dokładniejszej korekty, np. przy pojedynczych słowach. W polach poniżej można też wpisać czasy do **0,01 s** oraz metodę i długość ciszy (**0–30 s**).
5. Możesz **dodać**, **usunąć**, **wyłączyć**, **cofnąć** zaznaczenie. Po dowolnej liczbie zmian kliknij **Zapisz wszystkie zmiany do eksportu** — wszystkie korekty trafiają do projektu jednocześnie.
6. W kroku 4 kliknij **Wygeneruj oczyszczony plik** i **odsłuchaj cały wynik przed pobraniem**.

**Ważne rozróżnienie:** odtwarzanie wewnątrz edytora jest **szybkim podglądem przeglądarkowym** opartym na skompresowanym MP3 i przeskokach w czasie; może mieć małą zwłokę (nie jest montażem z dokładnością do pojedynczej próbki). **Dopiero FFmpeg** składa właściwy wynik z oryginalnego pliku i precyzyjnych zapisanych zakresów. Niezapisane zmiany na osi nie trafiają do pliku wyjściowego. Przy eksporcie brany jest też pod uwagę margines bezpieczeństwa ustawiony w panelu bocznym. Nakładające się fragmenty są scalane, a „Wytnij” ma pierwszeństwo nad „Wstaw ciszę”.

### Skróty

- **Spacja:** odtwarzaj / pauza; **Delete:** usuń wybrane zaznaczenie; **Ctrl+Z:** cofnij ostatnią operację; **strzałki:** przesuwaj zaznaczenie o 0,01 s (Shift = 0,1 s).
- **Kliknięcie niezaznaczonej części fali:** zmienia miejsce odtwarzania.
- **Kliknięcie regionu:** wybiera region i pokazuje jego szczegóły.

### Gdy fala nie chce się załadować

Podgląd przeglądarkowy jest generowany z mono MP3 o przepływności 32 kb/s. Przy bardzo długich nagraniach albo przy błędzie FFmpeg wyświetla się informacja i **nadal działa awaryjny edytor tabelaryczny oraz właściwy eksport**. Komponent nie pobiera JavaScriptu z zewnętrznego CDN.

## Jak wgrać na GitHub + Streamlit Cloud

1. Pobierz ZIP i **rozpakuj**. Wgraj **całą zawartość** do katalogu głównego repozytorium: `app.py`, `timeline_editor.py`, `audio_engine.py`, `detectors.py`, `speech.py`, `quality_checks.py`, `requirements.txt`, `packages.txt`, `style.css` i folder **`components/waveform/index.html`**. Zachowaj również ukryte foldery **`.streamlit`** i **`.github`**.
2. W GitHub kliknij **Commit changes**.
3. W Streamlit Cloud jako main file wskaż `app.py`, gałąź `main`, Python **3.12** (najlepiej podczas tworzenia wdrożenia) i kliknij Deploy.
4. Potwierdź numer **1.7.0** w aplikacji. Po przeanalizowaniu pliku sprawdź krok 3: ma być widoczna cała fala z kolorowymi zaznaczeniami.

Instrukcja krok po kroku: [INSTALACJA_GITHUB_STREAMLIT.md](INSTALACJA_GITHUB_STREAMLIT.md).

## Uruchomienie lokalne

Wymagania: Python 3.12, systemowe `ffmpeg` i `ffprobe` w PATH.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

`small` jest domyślnym modelem ASR; `medium` i `large-v3` są dostępne w ustawieniach, ale mogą przekraczać RAM darmowego Streamlit Cloud. Zaawansowany polski NER jest opcjonalny i wymaga instalacji z `requirements-ner.txt` oraz pamięci. Domyślna wersja działa bez niego z wykrywaniem regułowym.

## Prywatność

**Oryginalny plik jest przesyłany na serwer, na którym działa Streamlit.** To nie jest automatycznie prywatna instalacja tylko dlatego, że Whisper działa lokalnie na serwerze. Nagrania poufne przetwarzaj lokalnie lub w kontrolowanym środowisku. Modele mowy są pobierane z Hugging Face, ale program nie wysyła nagrań do zewnętrznego API transkrypcji. Projekt nie publikuje nagrań w repozytorium GitHub. Nie zamieszczaj tam tokenów ani plików klientów.

## Testy i ograniczenia

```bash
python -m unittest discover -s . -p 'test_*.py' -v
python -m compileall -q app.py audio_engine.py detectors.py speech.py quality_checks.py timeline_editor.py
```

Testy automatyczne sprawdzają m.in. poprawne zapisywanie wielu regionów jednocześnie i fizyczny eksport po takich zmianach. Dodatkowo komponent weryfikowano w Chromium na generowanym audio (przeciągnięcie obszaru, odtworzenie i zapis) bez błędów JavaScript. **Pełne uruchomienie Streamlit Cloud i jakość ASR na rzeczywistych polskich nagraniach wymagają niezależnej weryfikacji.**
