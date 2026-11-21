# AI Cenzor Studio v1.5 — szybkie wdrożenie do pustego repozytorium

1. Pobierz i **rozpakuj** paczkę ZIP. Do repozytorium wgrywa się **pliki i foldery**, nie pojedynczy plik ZIP.
2. Otwórz na GitHubie repozytorium z gałęzią `main` i użyj **Add file → Upload files**.
3. Przeciągnij zawartość rozpakowanego katalogu. Główne pliki muszą znajdować się bezpośrednio w głównym katalogu repozytorium, a nie np. w `AI_Cenzor_Studio_v1_5_GitHub/app.py`.
4. Sprawdź, czy w głównym katalogu są `app.py`, `requirements.txt`, `packages.txt`, `style.css`, `speech.py`, `detectors.py`, `audio_engine.py`, `quality_checks.py`. Do prawdziwie czarnego wyglądu wymagany jest też `.streamlit/config.toml`; GitHub może ukrywać foldery rozpoczynające się kropką w niektórych oknach wyboru plików. Jeśli nie został wgrany, utwórz `.streamlit/config.toml` na GitHubie z treścią z paczki.
5. Kliknij **Commit changes**. Potwierdź, że plik `BUILD_VERSION.txt` zawiera `1.5.0`.
6. Otwórz **https://share.streamlit.io** i utwórz aplikację: repozytorium, `main`, plik startowy `app.py`.
7. W Advanced settings wybierz **Python 3.12**. `.python-version` ma wartość 3.12, ale wybór w Cloud może wymagać osobnej konfiguracji.
8. Po wdrożeniu sprawdź wersję **1.5.0** i dostępność FFmpeg/Whisper w panelu Diagnostyka.
9. Przetestuj na krótkim fikcyjnym nagraniu, a potem włącz `small` + `Dokładny`. `medium` i `large-v3` są oferowane, lecz mogą przekroczyć RAM Community Cloud.

## Jeśli widzisz starą wersję

Sprawdź repozytorium, gałąź i ścieżkę `app.py` w Streamlit Cloud. Wybierz **Reboot app** lub wymuś przebudowę. Jeśli wciąż jest Python 3.14 i biblioteki się nie instalują, utwórz wdrożenie od nowa z Pythonem 3.12.

## Jeśli AI działa słabo

Sprawdź w Diagnostyce liczbę słów. Porównaj `base` i `small` na *tym samym* nagraniu. Zostaw VAD wyłączony do dyktowanych numerów. Popraw pojedyncze słowa lub oznacz ręcznie zakresy. Model GLiNER2 nie jest automatycznie instalowany na darmowej chmurze.

## Bezpieczeństwo

**Nie wgrywaj na GitHub prawdziwych nagrań ani plików z danymi osobowymi.** Na Streamlit Cloud pliki trafiają na serwer zewnętrzny. Dla wrażliwych rozmów uruchom program na własnym komputerze lub zabezpieczonym serwerze i dokonaj kontroli całego wyniku.
