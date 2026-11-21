# Architektura AI Cenzor Studio v1.7

1. **Streamlit** (`app.py`) zarządza importem nagrania, detekcją, stanem sesji oraz żądaniami zapisu i eksportu.
2. **Transkrypcja** (`speech.py` + `faster-whisper`): FFmpeg przygotowuje WAV, model rozpoznaje mowę i przybliżone znaczniki słów.
3. **Detekcja** (`detectors.py`): polskie reguły, słowniki i opcjonalny GLiNER2 proponują zakresy wrażliwe.
4. **Waveform** (`timeline_editor.py` + `components/waveform/index.html`): Python oblicza amplitudy z oryginalnego pliku oraz przeglądarkowy MP3 32 kb/s mono. Komponent dwukierunkowy rysuje falę na Canvas, wszystkie regiony na jednej osi, umożliwia przeciąganie, zoom, edytowanie metod i czasu ciszy. Zmiany przechowywane są po stronie przeglądarki aż do przycisku „Zapisz wszystkie zmiany”.
5. **Walidacja** (`valid_timeline_rows`): backend weryfikuje wersję edycji, liczby, zakresy, metody, limit 250 pozycji oraz odzyskuje metadane z poprzednich sprawdzonych wierszy; nie ufa polom opisowym od przeglądarki.
6. **Montaż finalny** (`audio_engine.py` + FFmpeg): po zapisaniu wszystkich zmian z oryginalnego pliku wycina fragmenty lub wstawia ciszę; nakładanie łączy zgodnie z regułami backendu. Podgląd przeglądarkowy (przeskoki elementu Audio) ma charakter orientacyjny i nie zastępuje odsłuchu całego eksportu.
7. **Kontrola jakości** (`quality_checks.py`): raport z zakresów bez transkrypcji i ręczne potwierdzenie przed pobraniem.

## Działanie komponentu Streamlit

Własny komponent HTML/JS jest spakowany w repozytorium. Nie potrzebuje zewnętrznych skryptów CDN ani osobnej kompilacji `npm`. Łączność Python ↔ JS odbywa się przez mechanizm `streamlit.components.v1.declare_component` i wiadomości Streamlit. Zmiany podczas przeciągania nie powodują ponownego uruchomienia całego skryptu Pythona. Po naciśnięciu „Zapisz” komponent wysyła całą listę regionów w jednej wiadomości i Streamlit wykonuje ponowny przebieg.

## Ograniczenia wydajności

Przeglądarka używa zmniejszonej jakości MP3 tylko do odsłuchu; maksimum 25 MB danych audio w podglądzie. Obliczanie amplitud wykorzystuje niską częstotliwość próbkowania i nie przesyła pełnego PCM. Bardzo długie pliki mogą nie uzyskać fali interaktywnej, ale nadal mają tryb tabelaryczny. Finalny eksport zachowuje jakość odpowiedniego kodeka wyjściowego i pochodzi z oryginału.

## Prywatność

Dane audio są przechowywane tymczasowo na serwerze Streamlit, w przypadku Cloud — na zewnętrznej infrastrukturze. Komponent nie wysyła próbek do usług zewnętrznych. Model może przeoczyć dane osobowe — wymagany jest końcowy odsłuch przed publikacją.
