# AI Cenzor Studio v1.4 — wgranie na pusty GitHub

1. Rozpakuj ZIP na komputerze. **Nie wgrywaj ZIP-a jako pojedynczego pliku.**
2. Wejdź do pustego repozytorium GitHub na gałęzi `main` i wybierz **Add file → Upload files**.
3. Przenieś do okna GitHub całą **zawartość** rozpakowanego folderu (bez dodatkowego folderu nadrzędnego).
4. Upewnij się, że w głównym katalogu widać obok siebie: `app.py`, `speech.py`, `audio_engine.py`, `detectors.py`, `quality_checks.py`, `requirements.txt`, `packages.txt`, `style.css`.
5. Zapisz **Commit changes**. Z GitHub Desktop można wygodniej wgrać również ukryte foldery `.github` i `.streamlit` (testy i motyw), ale nie są one wymagane do uruchomienia.
6. Przejdź na https://share.streamlit.io — **Create app**. Repository: Twoje repo; branch: `main`; main file path: `app.py`.
7. W **Advanced settings** wybierz Python **3.12** (plik `.python-version` na GitHub może nie wymuszać wersji w Cloud). Wdróż.
8. Otwórz panel „Diagnostyka AI / serwera” i potwierdź: **Wersja aplikacji 1.4.0**, **Whisper dostępny**, **FFmpeg dostępny**, **PyAV 18.1.0**.
9. Wgraj krótki **fikcyjny** plik testowy, wybierz model `tiny` i uruchom analizę. Po przetestowaniu przełącz na `base`.

## Jeśli Streamlit nadal wyświetla starszą wersję

Sprawdź, czy aplikacja jest połączona z właściwym repozytorium, gałęzią `main` i plikiem `app.py`. W panelu Streamlit Cloud wybierz **Reboot app**. Jeśli zmieniasz wersję Pythona, może być konieczne utworzenie wdrożenia na nowo.

## Ważne ograniczenia

Wersja podstawowa używa Whisper do rozpoznawania mowy i reguł wykrywania. Pełne rozpoznawanie imion/nazwisk nie jest gwarantowane. Dodatkowy polski model PII jest **opcjonalny** i wymaga zależności z `requirements-ner.txt`; na darmowym Cloud może nie zmieścić się w RAM. Zweryfikuj każdy wrażliwy fragment i odsłuchaj wynik.

Streamlit Community Cloud to **zewnętrzny serwer** — wrażliwe rozmowy najlepiej anonimizować lokalnie lub na własnej zabezpieczonej instancji. Repozytorium nie powinno zawierać żadnych nagrań, tokenów ani danych klientów.
