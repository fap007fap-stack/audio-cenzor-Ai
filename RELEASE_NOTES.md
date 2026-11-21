# Informacje o wydaniu — AI Cenzor Studio v1.5.0

## Status weryfikacji

- Automatyczne testy wykonane w środowisku tworzenia: **44 testy, 43 zaliczone, 1 pominięty** (brak biblioteki faster-whisper/PyAV w środowisku wykonawczym testów); testy rzeczywistego montażu i eksportu FFmpeg zaliczone.
- Kod Python: kompilacja składni wszystkich modułów i testów zakończona pomyślnie.
- Sprawdzenie ZIP-a: weryfikacja po utworzeniu, łącznie z `.streamlit/config.toml` i `.github/workflows/ci.yml`.
- Nie wykonano pełnej analizy na rzeczywistych polskich rozmowach ani zewnętrznego wdrożenia Streamlit Cloud w tym środowisku. Te kroki trzeba potwierdzić po wdrożeniu.

## Świadome ograniczenia

- Żaden model nie gwarantuje znalezienia wszystkich danych osobowych. Użytkownik musi sprawdzić transkrypcję, oznaczenia i plik wynikowy.
- Streamlit Community Cloud ma ograniczenia zasobów. `medium` i `large-v3` mogą przekroczyć limit pamięci; `small` jest ustawiony domyślnie.
- Dodatkowy GLiNER2 nie jest instalowany automatycznie. Włączysz go lokalnie instalacją z `requirements-ner.txt`.
- Nie przeprowadzono audytu bezpieczeństwa ani certyfikacji ochrony danych.

## Co zmieniono względem v1.4.0

Czarny motyw, poprawiony selektor modeli, profile jakości, opcjonalny preprocessing, lepsze reguły numerów i polskich nazw, poprawianie transkrypcji bez ponownej pracy Whispera oraz obsługa niepowodzenia dodatkowego modelu bez utraty detekcji podstawowych.
