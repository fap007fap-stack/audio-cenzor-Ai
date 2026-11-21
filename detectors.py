"""Reguły do polskich rozmów + mapowanie tekstu na znaczniki czasu słów."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable


CATEGORIES = ("Wulgaryzmy", "Imiona i nazwiska", "Numery telefonów", "Adresy i e-maile", "Inne dane osobowe")


@dataclass(frozen=True)
class Token:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Finding:
    start: float
    end: float
    category: str
    text: str
    source: str
    confidence: float = 0.0


BAD_WORDS = re.compile(r"(?iu)\b(?:kurw\w*|skurw\w*|chuj\w*|pierd\w*|jeb\w*|zajeb\w*|spierdal\w*|pizd\w*|wypierdal\w*|dup[aieęy]\w*)\b")
EMAIL = re.compile(r"(?i)\b[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"(?<!\d)(?:\+?48[\s,;.-]*)?(?:\d[\s,;.-]*){9}(?!\d)")
PESEL = re.compile(r"(?<!\d)\d{11}(?!\d)")
POSTCODE = re.compile(r"\b\d{2}-\d{3}\b")
IBAN = re.compile(r"(?i)\bPL[\s]?\d{2}(?:[\s]?\d{4}){6}\b")
ADDRESS = re.compile(r"(?iu)\b(?:ul\.?|ulica|ulicy|ulicę|ulicą|aleja|alei|al\.?|plac|osiedle)\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż.\-]*(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż.\-]*){0,2}(?:\s+\d+[a-zA-Z]?(?:/\d+)?)?")
NAME_PAIR = re.compile(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\-]{2,}\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\-]{2,}\b")
NAME_CONTEXT = re.compile(r"(?iu)\b(?:nazywam\s+się|mam\s+na\s+imię|imię|nazwisko|panem|panią|pana|pani|pan|panem|do\s+pana|od\s+pani)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\-]{2,}(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\-]{2,})?)")
SPOKEN_EMAIL = re.compile(r"(?iu)\b[\w.\-]+\s+małpa\s+[\w.\-]+(?:\s+kropka\s+[a-ząćęłńóśźż]{2,})+\b")

# Pozwala odrzucić popularne początki zdań mylone z imionami.
NOT_NAMES = {"dzień dobry", "dobry wieczór", "bardzo dobrze", "tak naprawdę", "witam serdecznie", "dzień dzisiejszy", "numer telefonu", "proszę pana", "w związku"}


def text_with_offsets(tokens: Iterable[Token]) -> tuple[str, list[tuple[int, int, Token]]]:
    pieces: list[str] = []
    offsets: list[tuple[int, int, Token]] = []
    position = 0
    for w in tokens:
        word = w.text.strip()
        if not word:
            continue
        if pieces:
            position += 1
        begin = position
        position += len(word)
        offsets.append((begin, position, w))
        pieces.append(word)
    return " ".join(pieces), offsets


def mapped_findings(text: str, offsets: list[tuple[int, int, Token]],
                    pattern: re.Pattern, category: str, source: str, confidence: float = 0.9,
                    only_group: int | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for m in pattern.finditer(text):
        s, e = m.span(only_group) if only_group is not None else m.span()
        value = text[s:e]
        if category == "Imiona i nazwiska" and (value.lower() in NOT_NAMES or value.split()[0].casefold() in TITLES):
            continue
        touched = [t for left, right, t in offsets if left < e and right > s]
        if touched:
            findings.append(Finding(min(t.start for t in touched), max(t.end for t in touched), category,
                                    value, source, confidence))
    return findings


def detect_patterns(tokens: list[Token], enabled: set[str]) -> tuple[str, list[Finding]]:
    text, offsets = text_with_offsets(tokens)
    found: list[Finding] = []
    specs = [
        (BAD_WORDS, "Wulgaryzmy", "Słownik", 0.95, None),
        (PHONE, "Numery telefonów", "Wzorzec cyfr", 0.82, None),
        (EMAIL, "Adresy i e-maile", "Wzorzec e-mail", 0.98, None),
        (SPOKEN_EMAIL, "Adresy i e-maile", "E-mail wypowiedziany", 0.6, None),
        (ADDRESS, "Adresy i e-maile", "Wzorzec adresu", 0.65, None),
        (POSTCODE, "Adresy i e-maile", "Kod pocztowy", 0.75, None),
        (PESEL, "Inne dane osobowe", "11 cyfr — sprawdź PESEL", 0.65, None),
        (IBAN, "Inne dane osobowe", "Wzorzec IBAN", 0.85, None),
        (NAME_PAIR, "Imiona i nazwiska", "Dwa słowa z wielkiej litery", 0.4, None),
        (NAME_CONTEXT, "Imiona i nazwiska", "Kontekst imienia", 0.62, 1),
    ]
    for pattern, category, source, confidence, group in specs:
        if category in enabled:
            found.extend(mapped_findings(text, offsets, pattern, category, source, confidence, group))
    # Wykrycia nakładające się z tej samej kategorii redukujemy do szerszego.
    return text, deduplicate(found)


def deduplicate(found: list[Finding]) -> list[Finding]:
    found = sorted(found, key=lambda f: (f.start, -(f.end-f.start), -f.confidence))
    kept: list[Finding] = []
    for f in found:
        duplicate = next((j for j, old in enumerate(kept)
                          if old.category == f.category and f.start >= old.start - 0.02 and f.end <= old.end + 0.02), None)
        if duplicate is None:
            kept.append(f)
    return kept


def gliner2_findings(text: str, offsets: list[tuple[int, int, Token]], model: Any,
                     enabled: set[str]) -> list[Finding]:
    """Opcjonalny polski NER: GLiNER2; zwraca span'y znakowe w transkrypcji."""
    mapping = {
        "person": "Imiona i nazwiska", "first_name": "Imiona i nazwiska", "last_name": "Imiona i nazwiska",
        "phone_number": "Numery telefonów", "email": "Adresy i e-maile", "address": "Adresy i e-maile",
        "street_address": "Adresy i e-maile", "postal_code": "Adresy i e-maile",
        "pesel": "Inne dane osobowe", "bank_account": "Inne dane osobowe", "iban": "Inne dane osobowe",
        "date_of_birth": "Inne dane osobowe", "id_card_number": "Inne dane osobowe",
    }
    descriptions = {
        "person": "pełne imię i nazwisko albo nazwa konkretnej osoby",
        "first_name": "imię osoby", "last_name": "nazwisko osoby",
        "phone_number": "numer telefonu", "email": "adres e-mail",
        "address": "pełny adres zamieszkania", "street_address": "ulica i numer budynku",
        "postal_code": "kod pocztowy", "pesel": "polski numer PESEL",
        "bank_account": "numer konta bankowego", "iban": "numer rachunku w formacie IBAN",
        "date_of_birth": "data urodzenia", "id_card_number": "numer dowodu osobistego",
    }
    schema = {key: description for key, description in descriptions.items() if mapping[key] in enabled}
    if not schema:
        return []
    result = model.extract_entities(text, schema, threshold=0.35, include_confidence=True, include_spans=True)
    entities = result.get("entities", result) if isinstance(result, dict) else {}
    findings: list[Finding] = []
    if not isinstance(entities, dict):
        return findings
    for label, matches in entities.items():
        category = mapping.get(label)
        if not category:
            continue
        if isinstance(matches, dict):
            matches = [matches]
        for match in matches or []:
            if not isinstance(match, dict):
                continue
            s, e = match.get("start"), match.get("end")
            if s is None or e is None:
                # Starsze wersje API: ostrożny fallback, bez dopasowywania pierwszego przypadkowego wystąpienia.
                continue
            touched = [t for left, right, t in offsets if left < int(e) and right > int(s)]
            if touched:
                findings.append(Finding(min(t.start for t in touched), max(t.end for t in touched),
                                        category, str(match.get("text", text[int(s):int(e)])),
                                        "AI / GLiNER2", float(match.get("confidence", 0.5))))
    return deduplicate(findings)

# Dodatkowe detektory dopasowane do polskich rozmów.
DIGITS_PL = {
    'zero': '0', 'jeden': '1', 'jedna': '1', 'jedno': '1', 'dwa': '2', 'dwie': '2',
    'trzy': '3', 'cztery': '4', 'pięć': '5', 'piec': '5', 'sześć': '6', 'szesc': '6',
    'siedem': '7', 'osiem': '8', 'dziewięć': '9', 'dziewiec': '9',
}


def _digit_group(raw: str) -> str | None:
    """Extract numeric phone grouping from comma-separated digits/words.

    Examples: '3,4,5' -> '345', '501' -> '501', 'osiem,' -> '8'.
    Mixed words and digits are rejected, rather than guessed.
    """
    stripped = raw.strip().casefold()
    if not stripped or not re.fullmatch(r"[0-9a-ząćęłńóśźż\s,.;:+-]+", stripped):
        return None
    pieces = re.findall(r"\d+|[a-ząćęłńóśźż]+", stripped)
    if not pieces:
        return None
    if len(pieces) > 14:
        return None
    digits = []
    for part in pieces:
        if part.isdecimal():
            if len(part) > 11:
                return None
            digits.append(part)
        elif part in DIGITS_PL:
            digits.append(DIGITS_PL[part])
        else:
            return None
    return "".join(digits)


def detect_spoken_phones(tokens: list[Token]) -> list[Finding]:
    """9-digit Polish numbers spoken or ASR formatted with commas and spacing.

    Keeps actual original start/end timestamps, not inferred character offsets.
    Formats that cannot safely be parsed remain for manual review.
    """
    result: list[Finding] = []
    sequence: list[Token] = []
    digits = ""

    def flush() -> None:
        nonlocal sequence, digits
        if len(digits) in (9, 11) and (len(digits) == 9 or digits.startswith("48")) and sequence:
            result.append(Finding(sequence[0].start, sequence[-1].end,
                                  "Numery telefonów", " ".join(t.text for t in sequence),
                                  "Cyfry / liczby wypowiedziane", 0.82))
        sequence = []
        digits = ""

    for token in tokens:
        number = _digit_group(token.text)
        if (not number or len(digits) + len(number) > 11 or
                (sequence and token.start - sequence[-1].end > 1.3)):
            flush()
        if number:
            sequence.append(token)
            digits += number
            if len(digits) == 11 and digits.startswith("48"):
                flush()
            elif len(digits) == 9:
                flush()
    flush()
    return result


# Common Polish first names, including frequent case-inflected spoken forms.
# Heuristic, not a substitute for Polish NER. Add domain-specific names in sidebar.
FIRST_NAMES = set("""
jan jana janem janowi janie anna anny annę annie anną adam adama adamem
maria marii marię marią marysia marysi marek marka markiem mareczek
piotr piotra piotrem piotrze paweł pawła pawłem pawle krzysztof krzysztofa
krzysztofem tomasz tomasza tomaszem tomek tomka magdalena magdaleny
magdaleną magda magdy magdą agnieszka agnieszki agnieszkę agnieszką
joanna joanny joannę joanną asia asią kasia kasią katarzyna katarzyny
katarzynę katarzyną dorota doroty dorotę dorotą martyna martyny martynę
martyną marzena marzeny marzenę marzeną marzyna marzyny marzynę marzyną
kazimierz kazimierza kazimierzem kazimierzu robert roberta robertem
michał michała michałem maciej macieja maciejem jakub jakuba jakubem
kuba kubę kubie bartosz bartosza bartoszem wojciech wojciecha wojciechem
artur artura arturem kamil kamila kamilem dawid dawida dawidem
karol karola karolem szymon szymona szymonem dawid julia julii julię
julią natalia natalii natalię natalią monika moniki monikę moniką
ewa ewy ewę ewą ewelina eweliny ewelinę eweliną aleksandra aleksandry
aleksandrą ola oli olę olą aleksander aleksandra aleksandrem
wiktoria wiktorii wiktorię wiktorią paulina pauliny paulinę pauliną
patrycja patrycji patrycję patrycją łukasz łukasza łukaszem
sebastian sebastiana sebastianem przemysław przemysława przemysławem
filip filipa filipem iga igi igę igą olga olgi olgę olgą
zbigniew zbigniewa zbigniewem halina haliny halinę haliną
barbara barbary barbarę barbarą basia basi basię basią jerzy jerzego jerzym
andrzej andrzeja andrzejem grzegorz grzegorza grzegorzem
""".split())
TITLES = {"pan", "pani", "pana", "panu", "panem", "panią", "panowie", "panny"}
NAME_PREPOSITIONS = {"z", "ze", "od", "do", "dla", "u", "przez", "koło", "przy"}


def _word(raw: str) -> str:
    return re.sub(r"^[^\w]+|[^\w]+$", "", raw, flags=re.UNICODE)


def _proper(raw: str) -> bool:
    word = _word(raw)
    return len(word) >= 3 and word[0].isupper() and word[1:].islower() and word.isalpha()


def detect_name_context(tokens: list[Token]) -> list[Finding]:
    """Review suggestions for names following titles/prepositions in Polish."""
    result: list[Finding] = []
    for index, token in enumerate(tokens):
        cleaned = _word(token.text)
        if not cleaned:
            continue
        lowered = cleaned.casefold()
        prev = _word(tokens[index - 1].text).casefold() if index else ""
        # Names after honorifics even if ASR fails to capitalize.
        explicit = prev in TITLES
        contextual = prev in NAME_PREPOSITIONS and lowered in FIRST_NAMES
        if not (explicit or contextual):
            continue
        if not (lowered in FIRST_NAMES or _proper(token.text)):
            continue
        last = index
        if index + 1 < len(tokens):
            following = _word(tokens[index + 1].text)
            if (_proper(following) and following.casefold() not in TITLES
                    and tokens[index + 1].start - token.end <= 0.9):
                last += 1
        phrase = " ".join(t.text for t in tokens[index:last + 1])
        result.append(Finding(token.start, tokens[last].end,
                              "Imiona i nazwiska", phrase,
                              "Kontekst osoby (sprawdź)", 0.66 if last > index else 0.48))
    return deduplicate(result)


def detect_custom_phrases(tokens: list[Token], phrases: Iterable[str]) -> list[Finding]:
    """Dodatkowe nazwy, imiona i frazy podane przez użytkownika, bez wysyłania do API."""
    text, offsets = text_with_offsets(tokens)
    found: list[Finding] = []
    for phrase in phrases:
        phrase = ' '.join(str(phrase).strip().split())[:130]
        if len(phrase) < 2:
            continue
        pattern = re.compile(r'(?iu)(?<!\w)' + r'\s+'.join(re.escape(w) for w in phrase.split()) + r'(?!\w)')
        found.extend(mapped_findings(text, offsets, pattern, 'Własne frazy', 'Lista użytkownika', 1.0))
    return deduplicate(found)


def detect_all(tokens: list[Token], enabled: set[str], phrases: Iterable[str] = ()) -> tuple[str, list[Finding]]:
    text, found = detect_patterns(tokens, enabled)
    if 'Numery telefonów' in enabled:
        found.extend(detect_spoken_phones(tokens))
    if "Imiona i nazwiska" in enabled:
        found.extend(detect_name_context(tokens))
    found.extend(detect_custom_phrases(tokens, phrases))
    return text, deduplicate(sorted(found, key=lambda f: (f.start, f.end)))


def gliner2_for_tokens(tokens: list[Token], model: Any, enabled: set[str],
                       chunk_size: int = 105, overlap: int = 12) -> list[Finding]:
    """Run expensive NER in small overlapping chunks; word timings stay in original audio."""
    if not 0 < overlap < chunk_size:
        raise ValueError('Overlap musi być mniejszy niż chunk_size.')
    findings: list[Finding] = []
    step = chunk_size - overlap
    for i in range(0, len(tokens), step):
        slice_tokens = tokens[i:i + chunk_size]
        if not slice_tokens:
            break
        chunk_text, chunk_offsets = text_with_offsets(slice_tokens)
        findings.extend(gliner2_findings(chunk_text, chunk_offsets, model, enabled))
        if i + chunk_size >= len(tokens):
            break
    return deduplicate(findings)
