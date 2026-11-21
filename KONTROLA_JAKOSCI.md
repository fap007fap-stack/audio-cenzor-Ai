# Kontrola jakości AI Cenzor Studio 1.7

## Co sprawdzono automatycznie

- 63 testy uruchomione w środowisku budowania: **62 zaliczone, 1 pominięty**, bo nie było tam zainstalowanego `faster-whisper`.
- Testy walidacji przesuwania/wydłużania zakresów i jednoczesnego zapisywania wielu regionów.
- Testy odrzucania nieprawidłowych zakresów, powtórzonych ID, niedozwolonych metod, zbyt długiej ciszy i nieaktualnej wersji edycji.
- Testy rzeczywistego FFmpeg: eksport po zmianach, odtwarzalne formaty, prawdziwa cisza, obliczenie czasu końcowego.
- Test w **Chromium (headless)** na generowanym 12-sekundowym audio: załadowanie przebiegu fali, pokazanie dwóch regionów, przeciągnięcie regionu myszką, aktualizacja początku/końca, uruchomienie odtwarzania, wysłanie obu regionów do Pythona. Brak błędów JavaScript w konsoli testu.
- Kontrola składni JavaScript poleceniem Node `--check`.

## Czego te testy nie dowodzą

- Nie był możliwy pełny test aplikacji Streamlit Cloud w środowisku budowania, ponieważ nie ma tam biblioteki Streamlit ani dostępu do jej instalacji.
- Nie potwierdzono jakości rozpoznawania każdego polskiego nazwiska i numeru telefonu przez Whisper/NER; to ograniczenie modelu, nie montażu.
- Podgląd przeglądarkowy nie jest dokładny do pojedynczych próbek i może pokazać krótką zwłokę na granicy przeskoku. Wymagana jest ocena **finalnego eksportu**.
- W długich plikach może zabraknąć pamięci na przetwarzanie AI w Streamlit Community Cloud.

## Test akceptacyjny dla osoby wdrażającej

1. Wgraj **syntetyczne**, niepoufne nagranie głosowe 15–30 s.
2. Zaznacz ręcznie trzy fragmenty; ustaw „Wytnij”, „Wstaw ciszę 1,50 s”, „Wytnij”.
3. Zmień myszką granice wszystkich trzech regionów, przybliż falę, odsłuchaj od wybranego punktu i włącz odtwarzanie po cięciach.
4. Kliknij „Zapisz wszystkie zmiany” i upewnij się, że tabela odzwierciedla czasy.
5. Wygeneruj MP3 i zweryfikuj początek, środek, koniec, długość ciszy i brak usuwanych wypowiedzi.
6. Sprawdź export dla zakresów na początku i końcu, a następnie dla nakładających się zaznaczeń.
7. Potwierdź, że w aplikacji widać wersję `1.7.0` i nie widać wcześniejszego edytora suwakowego v1.6.
