# AI Cenzor Studio 1.7.1 — poprawka przesuwających się cięć

## Diagnoza przyczyny

W v1.7 graficzny edytor odtwarzał **niezapisane zmiany w przeglądarce**, a eksport w Streamlit używał **ostatniego zapisanego planu**. Kliknięcie `Wygeneruj` bez wcześniejszego `Zapisz wszystkie zmiany` tworzyło plik ze starymi czasami. Jednocześnie szybki odsłuch MP3 i eksport FFmpeg były realizowane dwiema odrębnymi ścieżkami — nie należy oczekiwać tożsamości próbek w odtwarzaczu przeglądarkowym.

## Poprawki

1. Oznaczanie edytora jako `dirty` / `clean` po zakończeniu edycji, z przekazaniem stanu do Streamlit.
2. Zablokowanie eksportu, dopóki zmienione przedziały nie zostaną zapisane; to samo dotyczy edycji w tabeli.
3. Precyzyjne `atrim` oparte na numerach próbek 48 kHz zamiast surowych znaczników czasu kontenera; zegar wejścia jest zerowany.
4. Domyślny margines edycji = 0.00 s (wcześniej 0.12 s po **każdej** stronie). Margines nadal można ustawić świadomie.
5. Pliki wynikowe otrzymują indywidualny identyfikator ustawień cięcia w nazwie zamiast jednego stałego pliku.
6. Nowe testy regresyjne z kilkoma cięciami i wstawieniami ciszy: porównanie sygnału po eksporcie z oczekiwanymi fragmentami oryginału (nie tylko długości pliku).

## Weryfikacja

- 67 testów automatycznych: 66 zaliczonych, 1 pominięty z powodu braku biblioteki `faster-whisper` w środowisku testowym.
- Dodatkowo test Chromium: przeciągnięcie zaznaczenia → zdarzenie niezapisanych zmian → zapis nowych czasów; bez błędów JS.
- Nie przetestowano pełnego wdrożenia w Streamlit Cloud ani rzeczywistego prywatnego nagrania użytkownika. Dla poufnych rozmów odsłuch końcowego pliku jest konieczny.
