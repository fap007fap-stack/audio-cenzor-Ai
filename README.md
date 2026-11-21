# AI Cenzor Studio

**Dopracowany prototyp Streamlit do redakcji NAGRAŃ GŁOSOWYCH (także audio zapisanych w MP4).**

Wgraj nagranie → analizuj polską mowę → sprawdź propozycje cięć → zmień metodę i długość ciszy → odsłuchaj → pobierz wynik. Bez płatnego klucza API.

> **Ważne:** to narzędzie wspomaga usuwanie danych osobowych, ale nie gwarantuje anonimizacji. Transkrypcja i detektory mogą przeoczyć dane albo wskazać fałszywe alarmy. Obowiązkowo odsłuchaj wynik i przeprowadź ręczną kontrolę przed udostępnieniem. W przypadku poufnych nagrań używaj wdrożenia lokalnego lub własnego zabezpieczonego serwera.

## Co potrafi

- Import: **MP4 z audio**, M4A, MP3, WAV, OGG, AAC, FLAC, WebM; do 150 MB. Jeśli MP4 zawiera także obraz, eksport świadomie zapisuje tylko dźwięk.
- Polski Whisper na CPU; automatyczne znaczniki czasowe słów.
- Wykrywanie: **wulgaryzmy, imiona/nazwiska, telefony, adresy i e-maile, inne dane osobowe**, w tym PESEL i IBAN (identyfikatory są kandydatami na podstawie wzorca).
- Dodatkowe reguły dla **numerów wypowiadanych pojedynczymi cyframi** i własnych słów/nazwisk dodanych w panelu.
- Opcjonalny polski GLiNER2 PII dla dokładniejszej detekcji kontekstowej (wymaga więcej RAM).
- Tabela z edycją granic przedziałów, odznaczaniem wykryć i wyborem **„Wytnij” / „Wstaw ciszę”** osobno dla każdego wiersza.
- Cisza od **0 do 30 sekund**; zastępuje cały wskazany fragment. Możliwa jest też pełna redukcja czasu przez wycięcie.
- Ręczne dodawanie zakresów i odsłuch ±2 sekund wokół dowolnego wykrycia.
- Kolorowa oś cięć, statystyki zmiany czasu i ostrzeżenia o nachodzących na siebie przedziałach.
- Eksport: **MP3 / M4A / WAV / MP4 audio-only**; po eksporcie odsłuch pliku oraz raport JSON bez fragmentów transkrypcji.
- Kontrola jakości: wynik należy odsłuchać i potwierdzić ręcznie przed pobraniem.

## 1. Start na Streamlit Community Cloud (GitHub)

1. Rozpakuj plik ZIP. Utwórz repozytorium na https://github.com/new (dla publicznej aplikacji kod może być publiczny, **nie umieszczaj tam nagrań**).
2. **Wgraj zawartość rozpakowanego folderu**, nie sam ZIP: w katalogu głównym repozytorium powinny znajdować się `app.py`, `requirements.txt`, `packages.txt`, `.streamlit/`, `assets/`, `cenzor/` i `tests/`.
3. Otwórz https://share.streamlit.io → Create app → wybierz repozytorium i gałąź `main` → Main file: **`app.py`**.
4. W opcjach zaawansowanych wybierz **Python 3.12**, jeśli usługa udostępnia wybór wersji; kod i zależności zaprojektowano pod 3.12. Kliknij **Deploy**.
5. Pierwszą analizę przetestuj na **krótkim, niesekretnym pliku**. Model `base` jest domyślny, `tiny` działa z mniejszym zużyciem zasobów. Przy pierwszej analizie model zostanie pobrany przez środowisko aplikacji.

`requirements.txt` wskazuje biblioteki Python, a `packages.txt` instaluje systemowy `ffmpeg` i `ffprobe`. Nie trzeba dodawać tokenu OpenAI ani klucza API. Streamlit Cloud może mieć ograniczenia pamięci i przestrzeni dyskowej; dla długich nagrań użyj komputera lokalnego.

**Uwaga o prywatności:** Streamlit Community Cloud nie jest lokalny. Plik trafia do zdalnej instancji, a publicznie dostępna aplikacja bez logowania nie nadaje się do wrażliwych nagrań bez osobnej oceny bezpieczeństwa i zgodności z przepisami. Własne repozytorium nie przechowuje nagrań, ale wgrane audio jest tymczasowo zapisywane na serwerze Streamlit w trakcie sesji.

## 2. Uruchomienie lokalne (zalecane dla rozmów z danymi)

Wymagane: **Python 3.12**, **FFmpeg i FFprobe** dostępne w `PATH`.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Aplikacja pojawi się zwykle pod `http://localhost:8501`. Na Windows FFmpeg możesz zainstalować przez `winget install Gyan.FFmpeg`; uruchom nowy terminal, by odświeżyć `PATH`.

### Mocniejszy model PII — opcjonalnie

```bash
python -m pip install -r requirements-ner.txt
streamlit run app.py
```

W panelu bocznym aktywuj „Polski model PII (dodatkowy)”. Pobierany model: [`piotrmaciejbednarski/gliner2-polish-pii`](https://huggingface.co/piotrmaciejbednarski/gliner2-polish-pii). Wykrywanie działa na transkrypcji i jest wykonywane porcjami; może nadal pomijać polskie odmiany imion i nazwisk. **Pakiet opcjonalny nie jest domyślnie instalowany na Community Cloud**, gdyż potrafi zużyć znaczną pamięć RAM.

## 3. Dokładnie co robią dwie metody?

Przykładowe oryginalne nagranie trwa 10 sekund, a wrażliwy fragment ma od 3,0 do 4,5 s.

| Tryb | Działanie | Długość wyniku (bez marginesu) |
|---|---|---|
| Wytnij | Usuwa 1,5 s oryginalnej mowy i skleja zachowane fragmenty | 8,5 s |
| Wstaw ciszę — 1 s | Usuwa 1,5 s mowy i **wstawia 1 s rzeczywistej ciszy** | 9,5 s |
| Wstaw ciszę — 3 s | Usuwa 1,5 s mowy i wstawia 3 s ciszy | 11,5 s |

Margines powiększa usuwane przedziały z obu stron (domyślnie po 0,12 s). Nakładające się zakresy są **scalane**. Przy konflikcie „Wytnij” ma pierwszeństwo nad „Wstaw ciszę”; ostrzeżenie wyświetlane jest w interfejsie. FFmpeg tworzy nowy plik i usuwa oryginalną treść zakresów, zamiast tylko modyfikować znaczniki odtwarzania.

## 4. Jak sprawdzić, czy wszystko działa?

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py cenzor tests
```

W repozytorium jest także GitHub Actions `ci.yml`, który na Linuxie i Pythonie 3.12 instaluje zależności i uruchamia testy bez potrzeby Twojej interwencji. Status CI jest obiektywną kontrolą powtarzalności wykonania kodu, **nie certyfikatem jakości anonimizacji**.

Dodatkowa checklista ręczna i wymagania niezależnej oceny: [`docs/KONTROLA_JAKOSCI.md`](docs/KONTROLA_JAKOSCI.md). Opis architektury i model zagrożeń: [`docs/ARCHITEKTURA.md`](docs/ARCHITEKTURA.md).

## 5. Ograniczenia i ważne informacje

- Rozpoznawanie tekstu z audio może przeoczyć słowo, zwłaszcza w hałasie, gwarze lub przy nakładających się głosach.
- Reguły nie rozpoznają wszystkich nazw własnych ani liczb mówionych np. „pięćset jeden”; w razie potrzeby użyj własnej listy i ręcznych cięć.
- Opcjonalny model PII może wykrywać odmienne formy nazwisk niekompletnie; należy sprawdzić całą transkrypcję oraz wynik.
- Gdy plik jest usuwany z bieżącej sesji, katalog roboczy jest czyszczony. Nie zapewnia to gwarancji usunięcia wszystkich kopii w RAM, buforach usługi ani backupach dostawcy. To nie jest certyfikowany system retencji danych.
- Dźwięk wynikowy jest ponownie kodowany (48 kHz, mono), a więc mogą się pojawić niewielkie różnice jakości. Przy stykach cięć mogą być słyszalne przeskoki.
- Wersja nie zawiera logowania, izolowanej bazy klientów ani zgodności prawnej potwierdzonej audytem. Nie używaj jej produkcyjnie w organizacji bez oceny bezpieczeństwa.
- Długie nagrania mogą nie mieścić się w zasobach bezpłatnego Streamlit Cloud; kod wprowadza granicę 120 min i 150 MB, lecz nie jest to gwarancja ich obsługi w chmurze.

## Struktura

```text
AI_Cenzor_Studio/
├── app.py                   # nowoczesny interfejs Streamlit
├── assets/style.css         # styl, układ responsywny
├── cenzor/audio.py          # FFmpeg: cięcie, cisza, walidacja, preview
├── cenzor/detect.py         # reguły PII, imiona, telefony, własne frazy, NER
├── cenzor/transcribe.py     # faster-whisper PL
├── cenzor/quality.py        # raport, fingerprint, ostrzeżenia
├── tests/                   # testy jednostkowe + integracyjne FFmpeg
├── .github/workflows/ci.yml # automatyczna kontrola na GitHubie
├── docs/                    # architektura, QA i ograniczenia
├── .streamlit/config.toml
├── .python-version          # 3.12
├── requirements.txt
├── requirements-ner.txt     # opcjonalny AI PII
└── packages.txt             # ffmpeg dla Cloud
```

Licencja MIT. Autor lub odbiorca przetwarzający dane jest odpowiedzialny za zgodność ich użycia z prawem i zasadami prywatności.
