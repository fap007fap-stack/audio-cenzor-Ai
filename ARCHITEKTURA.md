# Architektura i kontrola bezpieczeństwa

## Przepływ danych

```text
Streamlit file_uploader
   │ (plik trzymany w katalogu roboczym bieżącej sesji)
   ├── FFprobe: kontrola faktycznej obecności audio i długości
   ├── FFmpeg: roboczy WAV mono 16 kHz
   │       └── faster-whisper CPU: transkrypcja + czasy słów
   │               ├── reguły: telefon, cyfry słownie, mail, adres, PESEL/IBAN, wulgaryzmy
   │               ├── własne frazy użytkownika
   │               └── opcjonalny GLiNER2 PII: krótkie nakładające się bloki
   │                       └── lista sugerowanych przedziałów
   └── Streamlit data_editor: ręczna korekta i akceptacja
           └── walidacja, margines i scalenie przedziałów
                   └── FFmpeg filter_complex: zachowane odcinki + anullsrc(cisza)
                          └── wynik MP3/M4A/WAV/MP4 audio-only
                                 └── odsłuch, potwierdzenie przez człowieka i download
```

## Mechanika montażu

Obróbka jest na osi czasu oryginału. Zaznaczone przedziały są ucinane bez pozostawiania ścieżki oryginalnej wypowiedzi. W `Wstaw ciszę` zastępujący sygnał to cyfrowa cisza `anullsrc`, a nie redukcja głośności oryginału. Opcje działają niezależnie dla każdego wiersza. Wynik jest ponownie kodowany przez FFmpeg do wybranego formatu.

**Nakładanie zakresów:** w MVP przedziały zachodzące na siebie po dodaniu marginesu są scalane. Jeśli choć jedna część ma operację `Wytnij`, połączony zakres jest wycinany; to nie jest kompozycja odcinkowych operacji. UI ostrzega o konflikcie. W razie potrzeby zmień granice.

**Pliki robocze:** osobne katalogi tworzone przez `tempfile.mkdtemp` dla każdej sesji. Kasowanie przez przycisk czyści pliki katalogu. Bez osobnego procesu sprzątającego osierocone katalogi po awarii mogą pozostać w systemowym katalogu tymczasowym do czasu resetu instancji; administrator instalacji produkcyjnej powinien dodać retencję.

## Ryzyka i mitigacje

| Ryzyko | Aktualne zabezpieczenie | Czego nadal brak |
|---|---|---|
| Wycieki wskutek błędów ASR i NER | Lista wykryć, manualne zakresy, odsłuch, potwierdzenie użytkownika | Audyt skuteczności na realnych rozmowach i wyliczona czułość |
| PII poza transkrypcją | Dodatkowe wzorce, własna lista nazwisk | Zaawansowana kontrola fonetyczna i wielomodelowa |
| Nakładanie zakresów | Scalenie i ostrzeżenie | Indywidualne rozstrzyganie konfliktów na osi |
| Złośliwy/uszkodzony plik | FFprobe, wymuszony audio, limit długości/rozmiaru, timeout | Piaskownica FFmpeg i antivirus na serwerze |
| Publiczny dostęp do danych | Izolacja katalogów według sesji, brak bazowania na nazwie pliku | Logowanie, SSO, polityka IAM, własne zabezpieczone wdrożenie |
| Utrzymywanie danych po sesji | Ręczny przycisk czyszczenia | Automatyczna retencja i usunięcie z kopii zapasowych |
| Nagrania wysłane na Cloud | Dokumentacja i ostrzeżenia | Ocena prawna/DPA zależna od dostawcy i przetwarzanych danych |

## Wydajność

Domyślny `base` Whisper działa CPU INT8, opcja `tiny` jest najlżejsza. GLiNER2 jest opcjonalny i działa porcjami po ~105 słów z nakładką. Nie są używane płatne zewnętrzne API mowy; modele pobierane są z oficjalnych repozytoriów przez serwer podczas pierwszego uruchomienia.
