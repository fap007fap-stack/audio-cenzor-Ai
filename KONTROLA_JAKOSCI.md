# Wyniki kontroli jakości v1.7.2 — poprawka zegara AAC

Zestaw testów automatycznych: 69 testów, 68 zaliczonych, 1 pominięty (brak modelu faster-whisper w lokalnym środowisku). Testy obejmują syntetyczny plik z zaburzonym PTS oraz rzeczywisty odczyt i eksport formatów audio. Zewnętrzne wdrożenie Streamlit Cloud nie zostało uruchomione w środowisku testowym.

Dodatkowe próby na dostarczonym nagraniu (wyłącznie lokalnie, **nie jest częścią ZIP**):
- czas oryginału M4A: 38,227 s; dekodowane PCM bez korekty: 35,136 s;
- bezstratna oś robocza: 38,227 s;
- kilka przykładowych planów cięć o oczekiwanym czasie 30,950 s: po naprawie 30,950 s;
- plan z wycięciami i ciszą: WAV 28,950 s, MP3 i M4A zgodne z tolerancją kontenerów;
- porównanie planowanych i rzeczywistych próbek WAV: dokładne, maksymalna różnica wartości = 0.

Ograniczenie: nie ma tu odtworzonej pełnej interakcji z hostowanym Streamlit i nie odtworzono prywatnej listy cięć z sesji użytkownika. To test przyczyny i poprawki, a nie gwarancja wychwycenia wszystkich danych przez AI. Obowiązkowy ręczny odsłuch wyniku.

---

# Kontrola jakości AI Cenzor Studio 1.7.1

## Potwierdzone testami

- **67 testów uruchomionych, 66 zaliczonych, 1 pominięty** (`faster-whisper` nie był dostępny w środowisku testowym).
- Testy oryginalnego silnika montażu FFmpeg oraz rozpoznawania danych regułowego.
- Nowe testy numerycznej zgodności **próbek** z oryginalnym plikiem dla WAV, AAC/M4A i MP3 po wielu wycięciach i wstawieniach ciszy.
- Sprawdzenie opóźnień i przesunięcia treści w **wynikowym MP3 oraz M4A**, również przy cięciach późno w pliku; tolerancja testu 8 ms.
- Weryfikacja, że przy niezapisanych zmianach edytora/tabeli eksport jest blokowany, a zapis przekazuje komplet czasów do serwera.
- Test interakcji w **Chromium** na nowym komponencie: drag regionu → zgłoszenie statusu `dirty` → `save` z nowymi czasami; błędy JS: 0.
- `node --check` dla JavaScriptu oraz `py_compile` dla Pythona.

## Test odbiorczy po aktualizacji na Streamlit Cloud

1. Wgraj neutralne, fikcyjne nagranie z 3–4 rozpoznawalnymi dźwiękami lub słowami, bez prawdziwych danych osób.
2. Zaznacz na fali kilka fragmentów, w tym co najmniej jeden `Wstaw ciszę 1.50 s`.
3. **Przesuń jeden region, NIE klikaj „Zapisz”**. W kroku 4 eksport powinien być zablokowany.
4. Kliknij **„Zapisz wszystkie zmiany do eksportu”**. Zweryfikuj czasy w tabeli, następnie wygeneruj WAV.
5. Odsłuchaj z kroku 4 i sprawdź wstawioną ciszę oraz kolejne cięcia, szczególnie te pod koniec.
6. Powtórz jako MP3/M4A, wyłącz margines (0.00 s), sprawdź brak przesunięć. Możesz potem włączyć świadomy margines i ponownie wykonać kontrolę.
7. Potwierdź widoczny numer **1.7.1** i nową nazwę pliku eksportu z identyfikatorem wersji cięć.

## Ograniczenia

- Podgląd odtwarzany przez przeglądarkę jest **przybliżeniem**. Potwierdzeniem wyniku jest odtwarzacz **po wygenerowaniu pliku**.
- Nie uruchomiono całej aplikacji na Streamlit Community Cloud w środowisku budowania; nie potwierdzono wyniku na prywatnych nagraniach użytkownika.
- AI może przeoczyć dane osobowe. Przed publikacją należy odsłuchać cały eksport.
