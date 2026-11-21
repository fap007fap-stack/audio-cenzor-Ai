# AI Cenzor Studio — wersja 1.7.0

## Główna zmiana

Wprowadzono niezależny, dwukierunkowy komponent Streamlit z graficzną osią czasu audio: wszystkie zaznaczenia widoczne równocześnie, przeciąganie całych regionów i końcówek, skala zoom, podgląd całej rozmowy z uwzględnieniem bieżącego planu usunięć/wstawień ciszy, dodawanie/usuwanie/wyłączanie regionów oraz jednorazowe zapisanie wszystkich korekt do eksportu.

To zastępuje wcześniejszy schemat v1.6, w którym można było odsłuchiwać i poprawiać tylko jeden fragment na raz. Pozostawiono edycję tabelaryczną jako opcję awaryjną i do precyzyjnego wpisywania liczb.

## Technika

- `components/waveform/index.html`: komponent frontend z Canvas + HTML Audio, bez bibliotek z CDN.
- `timeline_editor.py`: konwersja oryginału na lekkie MP3 do przeglądarki, wyliczanie amplitud fali, walidacja całego planu z przeglądarki.
- Komponent przekazuje dane do Pythona **dopiero po zapisie**. Jedna akcja może przenieść 250 zaznaczeń naraz.
- Eksport z oryginalnego audio, a nie z podglądu MP3, realizuje nadal `audio_engine.py` / FFmpeg.
- Odtwarzanie w przeglądarce jest przybliżonym, szybkim odsłuchem, a nie gwarancją bezprzerwowego montażu z dokładnością do próbki.

## Sprawdzenie

- Testy jednostkowe i integracyjne edytora/FFmpeg wykonywane na syntetycznym audio.
- Test w przeglądarce Chromium: widoczność dwóch zakresów, drag, aktualizacja czasów, uruchomienie odtwarzacza, przesłanie wszystkich zaznaczeń do backendu, brak błędów JS.
- Test pełnego wdrożenia Streamlit Cloud nie był możliwy w środowisku budowania.

## Bezpieczeństwo i prywatność

W chmurze Streamlit nagrania trafiają na serwer hostingowy. Transkrypcja i detektory mogą pomijać dane. Obowiązkowy odsłuch gotowego eksportu przed pobraniem pozostaje w aplikacji.
