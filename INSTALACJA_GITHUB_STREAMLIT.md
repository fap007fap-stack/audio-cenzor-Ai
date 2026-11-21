# AI Cenzor Studio 1.7.1 — instalacja na GitHub i Streamlit

1. **Rozpakuj ZIP.** Nie przesyłaj samego archiwum.
2. Otwórz repozytorium na GitHubie, wybierz `main`, kliknij **Add file → Upload files**.
3. Wgraj całą zawartość rozpakowanego katalogu, w tym:
   - w głównym katalogu: `app.py`, `timeline_editor.py`, `audio_engine.py`, `speech.py`, `detectors.py`, `quality_checks.py`, `requirements.txt`, `packages.txt`, `style.css`, `BUILD_VERSION.txt`;
   - w podfolderze `components/waveform/`: **`index.html`**, bez którego nie będzie nowego edytora;
   - ukryte podfoldery `.streamlit/` (ciemny motyw) i `.github/` (testy automatyczne).
4. Kliknij **Commit changes**.
5. Wejdź do [Streamlit Community Cloud](https://share.streamlit.io) i jako plik wejściowy wybierz **`app.py`**, gałąź `main` i Python **3.12** (Advanced settings).
6. Po wdrożeniu sprawdź napis **Wersja 1.7.1**, wgraj próbne nagranie **bez prawdziwych danych osobowych**, uruchom analizę AI, a w kroku 3 sprawdź nową falę dźwiękową.
7. Przesuń jedno zaznaczenie, odtwórz „po cięciach” i sprawdź, czy **eksport jest zablokowany**, dopóki nie klikniesz **Zapisz wszystkie zmiany**. Następnie wygeneruj testowy eksport MP3.
8. **Nie trzeba usuwać repozytorium**, wystarczy zastąpić pliki nową zawartością. Jeżeli poprzednio były wgrane starsze pliki, wgraj pełną paczkę, w tym `app.py`, `audio_engine.py`, `components/waveform/index.html` i testy.

## Jeśli widać stary edytor

Sprawdź: `BUILD_VERSION.txt` powinien mieć `1.7.1`, `app.py` powinien importować `timeline_editor`, a na GitHubie musi istnieć ścieżka **`components/waveform/index.html`**. Sprawdź również gałąź i plik uruchomieniowy wskazany w Streamlit Cloud; w razie potrzeby uruchom ponownie wdrożenie.

## Jeśli pełny edytor fali nie działa

Aplikacja pokaże komunikat i zapasową tabelę czasów, jeśli nie może wygenerować lekkiego MP3 lub przebiegu fali. Upewnij się, że pakiet systemowy FFmpeg jest instalowany przez `packages.txt`. Upewnij się, że przeglądarka pozwala odtwarzać dźwięk; wymagane jest świadome kliknięcie Play.

## Jeśli transkrypcja działa słabo

Na początek użyj `small` + `Dokładny`; `medium` i `large-v3` potrzebują więcej pamięci. Zostaw VAD wyłączony dla numerów dyktowanych cyframi. Sprawdź tekst i popraw rozpoznane słowa ręcznie. Dodatkowy model rozpoznawania nazwisk (NER) nie jest instalowany automatycznie.

## Bezpieczeństwo

Nie przesyłaj prawdziwych nagrań ani tokenów na publicznego GitHuba. W Streamlit Cloud nagrania znajdują się na zewnętrznym serwerze hostingowym. Przy poufnych rozmowach uruchom aplikację lokalnie. Automatycznie wykryte fragmenty zawsze wymagają ręcznego sprawdzenia.
