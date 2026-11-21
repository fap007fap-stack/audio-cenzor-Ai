# AI Cenzor Studio 1.7.2 — wspólna oś czasu, naprawa eksportu AAC/M4A

**Streamlit · polskie nagrania głosowe · faster-whisper · FFmpeg · prywatność z kontrolą człowieka**

Aplikacja odczytuje MP4 (audio-only lub z obrazem), MP3, M4A, WAV, AAC, OGG, FLAC i WebM. Rozpoznaje polską mowę, proponuje wycięcia wulgaryzmów i potencjalnych danych osobowych, a następnie eksportuje MP3, M4A, WAV lub MP4 z samą ścieżką audio. AI *nie gwarantuje* usunięcia wszystkich danych.

## Krytyczna naprawa v1.7.2: niepoprawne znaczniki czasu M4A/AAC

Niektóre nagrania mają **czas kontenera wyraźnie dłuższy niż liczba próbek audio**. W starszym kodzie FFmpeg zerował prezentacyjne znaczniki czasu (`asetpts=N/SR/TB`) przed kompensacją ubytków — stąd wyeksportowane nagranie bywało o kilka sekund krótsze niż plan i kolejne zaznaczenia przesuwały się w czasie. To **nie** jest błąd suwaków ani samego modelu AI.

**Jak działa poprawka:** po wgraniu pliku aplikacja raz przygotowuje lokalny, **bezstratny roboczy plik FLAC 48 kHz**, na którym za pomocą `aresample=async=1000:first_pts=0` zachowuje oś prezentacji AAC, a następnie dopasowuje liczbę próbek do długości nagrania. Ten **sam plik** trafia do transkrypcji, waveform, odsłuchu w edytorze, odsłuchu fragmentów i eksportu. Oryginał M4A/MP4/MP3 pozostaje nietknięty. Roboczy FLAC leży wyłącznie w katalogu tymczasowym sesji i zostaje usunięty po ręcznym wyczyszczeniu sesji lub zmianie pliku.

**Testy na nagraniu wykazującym błąd:** źródło M4A pokazywało `38,227 s`, a prosty dekoder dostarczał `35,136 s` próbek; w starym eksporcie ten brak `3,091 s` przekładał się wprost na `27,86 s` zamiast planowanych `30,95 s`. Po normalizacji testowe wielokrotne cięcia dawały **30,950 s** w WAV; wyniki MP3/M4A przechodziły kontrolę czasu, a WAV odpowiadał próbkom planu dokładnie. Do repozytorium **nie** dołączono żadnego nagrania użytkownika ani danych z niego. Testy automatyczne używają wyłącznie syntetycznego dźwięku z sztucznie zmodyfikowanymi znacznikami AAC.

**Po instalacji koniecznie wgraj nagranie ponownie, ponownie uruchom AI i popraw zaznaczenia.** Stare numery sekund mogły odnosić się do wadliwie odczytanego nagrania z wersji 1.7.1. Nawet w v1.7.2 przed udostępnieniem pliku trzeba odsłuchać cały wynik i upewnić się, że nie zawiera danych wrażliwych. Zapis i edycja M4A na Streamlit Cloud nadal odbywają się na zdalnym serwerze; poufne pliki przetwarzaj na własnym komputerze.

## Poprzednia naprawa v1.7.1 — eksport zgodny z ZAPISANYMI zaznaczeniami

**Zdiagnozowany błąd v1.7:** w edytorze można było przesuwać zaznaczenia i odsłuchiwać wynik przed zapisaniem. Przycisk eksportu był mimo to aktywny i korzystał ze **starych, wcześniej zapisanych czasów**. W efekcie wyciszenia/cięcia w pobranym pliku mogły wypaść w innym miejscu niż w odsłuchu. To błąd synchronizacji stanu, nie błąd AI ani zwykle kodeka.

- Edytor informuje Streamlit po każdej **zakończonej** zmianie o niezapisanych danych. Gdy cokolwiek jest niezapisane, **eksport zostaje zablokowany**, a aplikacja pokazuje komunikat.
- Po kliknięciu **„Zapisz wszystkie zmiany do eksportu”** wszystkie granice trafiają do serwera w jednym zestawie i dopiero wtedy można generować wynik. Tabela edycji jest objęta podobną kontrolą.
- FFmpeg przycina na podstawie **numerów próbek PCM 48 kHz**, z czasem wejściowym wyzerowanym przed rozdzielaniem ścieżek; ogranicza to rozbieżności wynikające ze znaczników czasu kodeków.
- **Domyślny margines cięcia zmieniono z 0,12 s na 0,00 s**, żeby nie rozszerzać niejawnie zaznaczeń. W razie potrzeby można ustawić dowolny margines ręcznie; zalecamy bezwzględnie sprawdzić, czy wrażliwy fragment został usunięty w całości.
- Nazwa każdego eksportu zawiera odcisk konfiguracji cięć, co zapobiega przypadkowemu odsłuchowi starego pliku z pamięci przeglądarki.

**UWAGA:** szybki odsłuch w edytorze symuluje wycięcia poprzez przeskakiwanie w skompresowanym MP3. Nie jest równoważny próbka-po-próbce z końcowym montażem. **Odsłuch pod krokiem 4 po wygenerowaniu pliku jest odsłuchem rzeczywistego eksportu FFmpeg** i powinien zostać sprawdzony przed udostępnieniem.

## Edytor podobny do Audacity

W kroku 3 znajduje się **jedna wspólna fala dźwiękowa z WSZYSTKIMI zaznaczeniami naraz**. To **nie jest** panel kolejnych suwaków dla pojedynczych fragmentów.

1. Uruchom analizę AI. Wszystkie wykrycia pojawią się na przebiegu fali: czerwone obszary = **Wytnij**, turkusowe = **Wstaw ciszę**.
2. **Przeciągnij całe zaznaczenie**, aby przesunąć je w czasie. Złap **lewą lub prawą krawędź**, aby skrócić albo wydłużyć przedział.
3. Kliknij przycisk **Odtwarzaj po cięciach**: odtwarzacz w przeglądarce przeskakuje wszystkie aktualnie wycięte fragmenty lub pauzuje na czas wstawianej ciszy. **Oryginał** odtwarza bez cenzury. Przyciskiem **Odsłuchaj od zaznaczenia** można rozpocząć blisko konkretnego cięcia.
4. Użyj **Zoom** do dokładniejszej korekty, np. przy pojedynczych słowach. W polach poniżej można też wpisać czasy do **0,01 s** oraz metodę i długość ciszy (**0–30 s**).
5. Możesz **dodać**, **usunąć**, **wyłączyć**, **cofnąć** zaznaczenie. Po dowolnej liczbie zmian kliknij **Zapisz wszystkie zmiany do eksportu** — wszystkie korekty trafiają do projektu jednocześnie.
6. W kroku 4 kliknij **Wygeneruj oczyszczony plik** i **odsłuchaj cały wynik przed pobraniem**.

**Ważne rozróżnienie:** odtwarzanie wewnątrz edytora jest **szybkim podglądem przeglądarkowym** opartym na skompresowanym MP3 i przeskokach w czasie; może mieć małą zwłokę (nie jest montażem z dokładnością do pojedynczej próbki). **Dopiero FFmpeg** składa właściwy wynik z bezstratnego pliku roboczego FLAC i precyzyjnych zapisanych zakresów. Niezapisane zmiany na osi blokują przycisk eksportu — należy je najpierw zatwierdzić. Przy eksporcie brany jest też pod uwagę margines bezpieczeństwa ustawiony w panelu bocznym. Nakładające się fragmenty są scalane, a „Wytnij” ma pierwszeństwo nad „Wstaw ciszę”.

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
4. Potwierdź numer **1.7.2** w aplikacji. Po przeanalizowaniu pliku sprawdź krok 3: ma być widoczna cała fala z kolorowymi zaznaczeniami.

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

Testy automatyczne sprawdzają m.in. poprawne zapisywanie wielu regionów, blokowanie eksportu przy niezapisanym planie oraz fizyczne położenie treści w MP3/M4A/WAV po kilku cięciach i wstawieniach ciszy. Samo sprawdzanie długości pliku nie wystarcza. Dodatkowo komponent weryfikowano w Chromium na generowanym audio (przeciągnięcie obszaru, odtworzenie i zapis) bez błędów JavaScript. **Pełne uruchomienie Streamlit Cloud i jakość ASR na rzeczywistych polskich nagraniach wymagają niezależnej weryfikacji.**
