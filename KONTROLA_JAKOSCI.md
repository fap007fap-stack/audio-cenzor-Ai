# Protokół kontroli jakości

## Automatyczna kontrola

Uruchom `python -m unittest discover -s . -p "test_*.py" -v` oraz `python -m compileall -q app.py audio_engine.py detectors.py quality_checks.py speech.py`. Dołączony workflow GitHub Actions ponawia te kontrole na czystej maszynie z Pythonem 3.12 i FFmpeg. Testy sprawdzają działanie logiki i FFmpeg, **nie mierzą recall/precision ASR/PII na prawdziwych rozmowach**.

## Ręczne UAT — najlepiej przeprowadzone przez drugą osobę

- [ ] Program uruchamia się na czystym Pythonie 3.12 przez `streamlit run app.py`.
- [ ] Na Streamlit Community Cloud działa instalacja zależności z GitHub bez zmian w kodzie.
- [ ] Przykładowy plik MP3 oraz audio w MP4 daje się wczytać i odsłuchać.
- [ ] `small` Whisper rozpoznaje polską mowę i generuje znaczniki czasu.
- [ ] Wykrywanie: przekleństwo, imię/nazwisko, telefon cyfrowy i słownie, adres oraz e-mail (własne nagrania syntetyczne, bez cudzych danych).
- [ ] Ręczne dodanie przedziału oraz odznaczenie propozycji AI rzeczywiście wpływają na eksport.
- [ ] Dwa różne wiersze można ustawić odpowiednio na `Wytnij` i `Wstaw ciszę = 2.75 s`.
- [ ] Długość wynikowa i rzeczywisty odsłuch zgadzają się z przyjętymi cięciami.
- [ ] Miejsca zaznaczone jako wycięte nie są słyszalne, w tym początek i koniec słowa.
- [ ] Wprowadzenie błędnego czasu nie powoduje niejawnego uszkodzenia pliku.
- [ ] Eksport MP3, M4A, MP4 (tylko audio) i WAV działa na urządzeniu docelowym.
- [ ] Po zmianie tabeli stary wyeksportowany plik nie jest oferowany do pobrania.
- [ ] Plik wynikowy można pobrać dopiero po potwierdzeniu odsłuchu.
- [ ] Przycisk `Usuń pliki tej sesji` usuwa katalog roboczy.
- [ ] Test responsywności przy szerokościach ekranu desktop/tablet/telefon.

## Niezależna ewaluacja wykrywania AI (przed użyciem produkcyjnym)

1. Przygotuj reprezentatywny i prawnie dopuszczalny zestaw testowy 30–100 rozmów z ręcznie oznaczonymi wrażliwymi fragmentami. Uwzględnij odmiany imion, przerwy, gwarę, długie liczby wypowiedziane słownie, hałas, nakładające się głosy i słowa z wieloma znaczeniami.
2. Oddzielnie oznacz poprawne wykrycia, fałszywe alarmy i pominięcia. Oblicz **recall**, **precision** oraz liczbę wycieków PII po eksporcie (liczoną przez odsłuch człowieka).
3. Zaakceptuj projekt tylko przy jawnie ustalonych przez Ciebie progach jakości (dla danych osobowych potrzebny bardzo wysoki recall). Jeśli progów nie osiąga, wprowadź kolejne warstwy detekcji lub wymagaj ręcznej edycji przed udostępnieniem.
4. Przeprowadź przegląd ochrony danych, retencji, dostępu i logów przez uprawnioną osobę przed uruchomieniem dla rzeczywistych klientów.

**Nikt z zewnątrz nie certyfikował w tej chwili tego repozytorium.** Status zielony na GitHub Actions oznacza jedynie, że testy automatyczne przeszły.

## Regresje v1.5

- [ ] Ciemny motyw na desktopie i telefonie (sprawdź ukryty `.streamlit/config.toml`).
- [ ] `small`, `medium`, `large-v3` są widoczne, a większe modele ostrzegają o RAM.
- [ ] Test `1,2,3,4,5,6,7,8,9` i `123 456 789` daje zakres telefonu.
- [ ] `Pani Alicja Testowa` oznacza nazwisko, nie sam tytuł `Pani`.
- [ ] Edycja jednego źle zapisanego słowa i ponowna detekcja nie uruchamia Whispera.
- [ ] Przetestuj opcjonalne filtrowanie audio na cichym i na czystym nagraniu; nie zakładaj poprawy bez porównania.
- [ ] Jeśli GLiNER2 nie działa, wynik regułowy nadal pozostaje dostępny.

Przed rzeczywistą produkcją przeprowadź ręczną ocenę na wielu legalnie używanych nagraniach, z ekspercką oceną pominięć PII, w tym mową szybką, dyktowanymi numerami i nazwiskami w odmianach. Nie ma niezależnego certyfikatu skuteczności.
