# AI Cenzor Studio v1.3 — diagnostyka AI i poprawki Streamlit Cloud

**Dopracowany prototyp Streamlit do redakcji NAGRAŃ GŁOSOWYCH (także audio zapisanych w MP4).**

Wgraj nagranie → analizuj polską mowę → sprawdź propozycje cięć → zmień metodę i długość ciszy → odsłuchaj → pobierz wynik. Bez płatnego klucza API.


## Co zmieniło się w v1.3?

- Widoczny numer **1.3.0** w nagłówku i panelu bocznym, żeby odróżnić stare wdrożenie od nowego.
- **Diagnostyka AI** pokazuje obecność Whispera, FFmpeg, opcjonalnego GLiNER2, Python i konfigurację tokenu Hugging Face.
- **Test detektora bez nagrania** sprawdza na fikcyjnej próbce nazwisko, telefon i wulgaryzm. Nie pobiera modelu i nie testuje rozpoznawania mowy.
- Analiza pokazuje **4 etapy** i raportuje liczbę rozpoznanych słów oraz liczbę wykryć. Dzięki temu wiadomo, czy problem dotyczy pobierania modelu, transkrypcji czy reguł.
- Poprawione ostrzeżenia, gdy detektory nie znajdą żadnych danych.
- Usunięte przestarzałe `use_container_width`; interfejs korzysta z `width="stretch"`.
- Opcjonalny `HF_TOKEN` może być podany w **Streamlit Secrets**; publiczne modele nie wymagają go do działania.

**To diagnostyczna poprawka, nie dowód, że każdy model działa na Streamlit Cloud.** Dodatkowy GLiNER2 nie jest częścią domyślnego `requirements.txt`, bo model może przekroczyć limity darmowej chmury. Whisper pozostaje silnikiem rozpoznawania mowy, a reguły wyszukują dane w jego wynikach.

## Pierwsze kroki, gdy „AI nie działa”

1. **Sprawdź wersję.** Po otwarciu aplikacji nagłówek musi pokazywać `Wersja 1.3.0`, a panel boczny `AI Cenzor Studio · 1.3.0`. Jeśli widzisz starszą, sprawdź gałąź GitHub, ścieżkę `app.py` w Streamlit oraz to, czy nowe pliki zostały zatwierdzone (**Commit**).
2. W bocznym panelu otwórz **Diagnostyka AI / serwera**. Kliknij **Przetestuj detektor danych (bez pobierania AI)**. Test ma wykryć 3 kategorie na fikcyjnych danych.
3. Dodaj krótki testowy MP3/MP4 z wyraźną polską mową i wybierz model `tiny` lub `base`; kliknij **Uruchom analizę nagrania**. Etapy pokażą, czy problem jest przy pobieraniu Whispera, transkrypcji czy detekcji danych.
4. Jeśli transkrypcja ma słowa, ale wykryć jest 0, sprawdź *Sprawdź transkrypcję* oraz dodatkowe kategorie. Wersja bez GLiNER2 bazuje na regułach i nie rozpoznaje wszystkich form nazwisk.
5. Jeśli pierwszy etap pobierania modelu kończy się błędem limitu Hugging Face, opcjonalnie dodaj token: Streamlit Cloud → **Settings → Secrets**, a następnie wpisz `HF_TOKEN = "hf_TUTAJ_WLASNY_TOKEN"`. Nie umieszczaj prawdziwego tokenu w GitHubie ani logach.
6. Gdy aplikacja działa na Pythonie 3.14, usuń wdrożenie **w Streamlit Cloud** i wdroż repozytorium ponownie, wybierając **Python 3.12** w Advanced settings. Nie usuwaj repozytorium GitHub.
7. Jeśli nadal jest problem, skopiuj **błąd z ekranu aplikacji po kliknięciu analizy** oraz późniejsze linie logów. Nie przesyłaj poufnych nagrań.

**Uwaga:** status `Uvicorn server started` dowodzi tylko startu serwera, nie końca transkrypcji. Ostrzeżenie `HF Hub unauthenticated` samo nie blokuje dostępu do publicznego modelu.

> **Ważne:** to narzędzie wspomaga usuwanie danych osobowych, ale nie gwarantuje anonimizacji. Transkrypcja i detektory mogą przeoczyć dane albo wskazać fałszywe alarmy. Obowiązkowo odsłuchaj wynik i przeprowadź ręczną kontrolę przed udostępnieniem. W przypadku poufnych nagrań używaj wdrożenia lokalnego lub własnego zabezpieczonego serwera.

## Naprawa błędu `ModuleNotFoundError: No module named 'cenzor'`

Ta wersja **nie korzysta z folderu `cenzor/`**. Wszystkie wymagane do uruchomienia moduły znajdują się w głównym katalogu repozytorium. Po wgraniu nowej paczki na GitHub upewnij się, że:

- `app.py` i `audio_engine.py`, `detectors.py`, `quality_checks.py`, `speech.py`, `style.css` znajdują się **na tym samym poziomie**;
- `requirements.txt` i `packages.txt` są w katalogu głównym;
- logi uruchomienia pokazują **Python 3.12**, a nie 3.14; samo `.python-version` nie zmienia wersji w Streamlit Cloud;
- usunięcie starego folderu `cenzor/` jest opcjonalne, ale nie pozostawiaj starego `app.py`.

Szybki test po pobraniu: `python -m unittest discover -s . -p "test_*.py" -v`.

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
2. **Wgraj zawartość rozpakowanego folderu**, nie sam ZIP: w katalogu głównym repozytorium powinny znajdować się `app.py`, `audio_engine.py`, `detectors.py`, `quality_checks.py`, `speech.py`, `style.css`, `requirements.txt` i `packages.txt` **obok siebie w katalogu głównym**. Nie ma już folderu `cenzor/`.
3. Otwórz https://share.streamlit.io → Create app → wybierz repozytorium i gałąź `main` → Main file: **`app.py`**.
4. W **Advanced settings** wybierz **Python 3.12**. **Plik `.python-version` nie zmienia wersji w Streamlit Community Cloud**; jeśli na logach widzisz 3.14, usuń istniejące wdrożenie w Streamlit Cloud i wdróż aplikację ponownie z wybraną 3.12. Kliknij **Deploy**.
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
python -m unittest discover -s . -p "test_*.py" -v
python -m compileall -q app.py audio_engine.py detectors.py quality_checks.py speech.py
```

W repozytorium jest także GitHub Actions `ci.yml`, który na Linuxie i Pythonie 3.12 instaluje zależności i uruchamia testy bez potrzeby Twojej interwencji. Status CI jest obiektywną kontrolą powtarzalności wykonania kodu, **nie certyfikatem jakości anonimizacji**.

Dodatkowa checklista ręczna i wymagania niezależnej oceny: [`KONTROLA_JAKOSCI.md`](KONTROLA_JAKOSCI.md). Opis architektury i model zagrożeń: [`ARCHITEKTURA.md`](ARCHITEKTURA.md).

## 5. Ograniczenia i ważne informacje

- Rozpoznawanie tekstu z audio może przeoczyć słowo, zwłaszcza w hałasie, gwarze lub przy nakładających się głosach.
- Reguły nie rozpoznają wszystkich nazw własnych ani liczb mówionych np. „pięćset jeden”; w razie potrzeby użyj własnej listy i ręcznych cięć.
- Opcjonalny model PII może wykrywać odmienne formy nazwisk niekompletnie; należy sprawdzić całą transkrypcję oraz wynik.
- Gdy plik jest usuwany z bieżącej sesji, katalog roboczy jest czyszczony. Nie zapewnia to gwarancji usunięcia wszystkich kopii w RAM, buforach usługi ani backupach dostawcy. To nie jest certyfikowany system retencji danych.
- Dźwięk wynikowy jest ponownie kodowany (48 kHz, mono), a więc mogą się pojawić niewielkie różnice jakości. Przy stykach cięć mogą być słyszalne przeskoki.
- Wersja nie zawiera logowania, izolowanej bazy klientów ani zgodności prawnej potwierdzonej audytem. Nie używaj jej produkcyjnie w organizacji bez oceny bezpieczeństwa.
- Długie nagrania mogą nie mieścić się w zasobach bezpłatnego Streamlit Cloud; kod wprowadza granicę 120 min i 150 MB, lecz nie jest to gwarancja ich obsługi w chmurze.

## Struktura plików (wszystkie kluczowe pliki w jednym folderze)

```text
repozytorium/
├── app.py                 # Streamlit, plik startowy
├── audio_engine.py        # FFmpeg: cięcia i cisza
├── detectors.py           # wykrywanie wrażliwych fraz
├── quality_checks.py      # podsumowanie i raport
├── speech.py              # rozpoznawanie mowy
├── style.css              # wygląd aplikacji
├── requirements.txt       # zależności Python
├── packages.txt           # FFmpeg na Streamlit Cloud
├── test_core.py           # testy wykryć i eksportu
├── test_studio.py         # testy integracyjne
├── test_deployment.py     # kontrola poprawnego wgrania plików
├── .github/workflows/     # opcjonalna automatyczna CI
└── .streamlit/config.toml # opcjonalne ustawienia motywu
```

**Najczęstszy błąd `No module named 'cenzor'`:** oznacza uruchomienie starego `app.py` lub niekompletnego repozytorium. Wersja 1.3 nie używa pakietu `cenzor`. **Wgraj i zastąp razem** `app.py`, `audio_engine.py`, `detectors.py`, `quality_checks.py`, `speech.py`, `style.css`, `requirements.txt` i `packages.txt`. Nie mieszaj modułów z wersji 1.1, 1.2 i 1.3.

**Nie trzeba** kopiować do GitHuba nagrań, danych klientów ani plików `.env`. Nie publikuj plików MP3/MP4 w repozytorium.

Licencja MIT. Osoba przetwarzająca dane odpowiada za zgodność ich użycia z prawem i zasadami prywatności.
