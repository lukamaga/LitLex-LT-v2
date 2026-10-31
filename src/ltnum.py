import re

UNITS = {
    "vienas": 1, "vieno": 1, "vieną": 1, "vienam": 1, "viena": 1, "vienos": 1,
    "du": 2, "dvi": 2, "dviejų": 2, "dviem": 2,
    "trys": 3, "trijų": 3, "tris": 3, "trims": 3,
    "keturi": 4, "keturių": 4, "keturis": 4, "keturiems": 4,
    "penki": 5, "penkių": 5, "penkis": 5, "penkiems": 5,
    "šeši": 6, "šešių": 6, "šešis": 6, "šešiems": 6,
    "septyni": 7, "septynių": 7, "septynis": 7, "septyniems": 7,
    "aštuoni": 8, "aštuonių": 8, "aštuonis": 8, "aštuoniems": 8,
    "devyni": 9, "devynių": 9, "devynis": 9, "devyniems": 9,
}
TEENS = {
    "dešimt": 10, "vienuolik": 11, "dvylik": 12, "trylik": 13, "keturiolik": 14, "penkiolik": 15,
    "šešiolik": 16, "septyniolik": 17, "aštuoniolik": 18, "devyniolik": 19,
}
TENS = {
    "dvidešimt": 20, "trisdešimt": 30, "keturiasdešimt": 40, "penkiasdešimt": 50,
    "šešiasdešimt": 60, "septyniasdešimt": 70, "aštuoniasdešimt": 80, "devyniasdešimt": 90,
}
HUNDRED = ("šimtas", "šimto", "šimtą", "šimtai", "šimtų", "šimtui", "šimtus")
THOUSAND = ("tūkstantis", "tūkstančio", "tūkstantį", "tūkstančiai", "tūkstančių", "tūkstančiui", "tūkstančius")

UNIT_WORDS = (r"vien(?:as|o|ą|am|a|os)|dv(?:i|iejų|iem|u)|du|tr(?:ys|ijų|is|ims)|ketur(?:i|ių|is|iems)|"
              r"penk(?:i|ių|is|iems)|šeš(?:i|ių|is|iems)|septyn(?:i|ių|is|iems)|aštuon(?:i|ių|is|iems)|"
              r"devyn(?:i|ių|is|iems)")
TEEN_WORDS = r"dešimt(?:ies)?|(?:vienuo|dvy|try|keturio|penkio|šešio|septynio|aštuonio|devynio)lik(?:a|os|ai)"
TEN_WORDS = (r"(?:keturi|penki|šeši|septyni|aštuoni|devyni)asdešimt(?:ies)?|dvidešimt(?:ies)?|"
             r"trisdešimt(?:ies)?")
BIG_WORDS = r"šimt(?:as|o|ą|ai|ų|ui|us)|tūkstan(?:tis|čio|tį|čiai|čių|čiui|čius)"
WORD = "(?:" + UNIT_WORDS + "|" + TEEN_WORDS + "|" + TEN_WORDS + "|" + BIG_WORDS + ")"
PHRASE = rf"(?:{WORD}\s+)*{WORD}"
EUR = r"eur(?:ų|us|ai|ams|ui|o)\b"
UPPER = r"ir\s+ne\s+didesn\w*\s+negu\s+"

FROM_TO_WORDS = rf"(?:\bnuo\s+)?\b({PHRASE})(?:\s+{EUR})?\s+iki\s+({PHRASE})\s+{EUR}"
NOT_LESS_WORDS = rf"\bne\s+mažesn\w*\s+negu\s+({PHRASE})\s+{UPPER}({PHRASE})\s+{EUR}"
RANGE = re.compile(FROM_TO_WORDS + "|" + NOT_LESS_WORDS, re.I)
UP_TO = re.compile(rf"\biki\s+({PHRASE})\s+{EUR}", re.I)
AFTER_AMOUNT = rf"(?:{EUR}|iki\s+{PHRASE}\s+{EUR}|{UPPER}{PHRASE}\s+{EUR})"
AMOUNT = re.compile(rf"\b({PHRASE})(?=\s+{AFTER_AMOUNT})", re.I)

DIGITS = r"(?:\d{1,3}(?:[ .]\d{3})+(?!\d)|\d+)(?:,\d{1,2}(?!\d))?"
NUMBER = rf"\b(?:{DIGITS}|{PHRASE})"
FIRST = rf"(?<![\d.,\-\u2013]){NUMBER}"
MONEY = r"(?:eur(?:ų|us|ai|ams|ui|o|as|ą)?\b|€)"

LOWER_LIMIT = r"\bne\s+(?:mažesn\w*\s+negu|mažiau\s+kaip)\s+"
UPPER_LIMIT = r"ne\s+(?:didesn\w*\s+negu|daugiau\s+kaip)\s+"
STATED_LIMITS = rf"{LOWER_LIMIT}({FIRST})\s*(?:{MONEY}\s*)?,?\s*(?:ir|bet)\s+{UPPER_LIMIT}({NUMBER})\s*{MONEY}"
STATED_FROM_TO = rf"(?:\bnuo\s+)?({FIRST})\s*(?:{MONEY}\s*)?(?:iki|-|\u2013)\s*({NUMBER})\s*{MONEY}"
STATED_UP_TO = rf"\biki\s+()({FIRST})\s*{MONEY}"
STATED = [
    re.compile(STATED_LIMITS, re.I),
    re.compile(STATED_FROM_TO, re.I),
    re.compile(STATED_UP_TO, re.I),
]
STATED_AMOUNT = re.compile(rf"({FIRST})\s*{MONEY}", re.I)


def word_value(word):
    word = word.lower()
    if word in UNITS:
        return UNITS[word]
    stem = re.sub(r"(ies)$", "", word)
    if stem in TENS:
        return TENS[stem]
    if stem == "dešimt":
        return 10
    teen = re.sub(r"(a|os|ai)$", "", word)
    if teen in TEENS:
        return TEENS[teen]
    return None


def to_int(phrase):
    total = 0
    current = 0
    words = phrase.lower().split()
    for word in words:
        if word in HUNDRED:
            if current == 0:
                current = 1
            current = current * 100
        elif word in THOUSAND:
            if current == 0:
                current = 1
            total += current * 1000
            current = 0
        else:
            value = word_value(word)
            if value is None:
                raise ValueError(f"not a number word: {word!r} in {phrase!r}")
            current += value
    return total + current


def norm(text):
    if not text:
        text = ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def ranges(text):
    text = norm(text)
    found = []
    spans = []

    for m in RANGE.finditer(text):
        if m.group(1):
            low = m.group(1)
            high = m.group(2)
        else:
            low = m.group(3)
            high = m.group(4)
        fine = (to_int(low), to_int(high))
        found.append((m.start(), fine))
        spans.append(m.span())

    for m in UP_TO.finditer(text):
        inside_range = False
        for start, end in spans:
            if start <= m.start() < end:
                inside_range = True
                break
        if not inside_range:
            fine = (0, to_int(m.group(1)))
            found.append((m.start(), fine))

    result = []
    for position, fine in sorted(found):
        result.append(fine)
    return result


def amounts(text):
    text = norm(text)
    phrases = AMOUNT.findall(text)
    return [to_int(phrase) for phrase in phrases]


def value(token):
    token = token.strip()
    if not token:
        return 0
    if token[0].isdigit():
        whole, comma, cents = token.partition(",")
        whole = re.sub(r"[ .]", "", whole)
        number = int(whole)
        if cents and int(cents):
            return number + int(cents) / 10 ** len(cents)
        return number
    try:
        return to_int(token)
    except ValueError:
        return None


def thousands(text):
    def k(number):
        number = number.replace(",", ".")
        return str(round(float(number) * 1000))

    def replace_range(m):
        low = k(m.group(1))
        high = k(m.group(3))
        return f"{low} {m.group(2)} {high}"

    def replace_single(m):
        return k(m.group(1))

    euro_first = r"(?:\bEUR|€)\s*(\d+(?:[ .]\d{3})*(?:,\d{1,2})?)"
    range_in_thousands = r"(\d+(?:,\d+)?)\s*(iki|-|\u2013)\s*(\d+(?:,\d+)?)\s*tūkst\.?"
    single_in_thousands = r"(\d+(?:,\d+)?)\s*tūkst\.?"

    text = re.sub(euro_first, r"\1 eurų", text, flags=re.I)
    text = re.sub(range_in_thousands, replace_range, text, flags=re.I)
    text = re.sub(single_in_thousands, replace_single, text, flags=re.I)
    return text


def stated(text):
    text = norm(text)
    text = text.replace("\u00a0", " ")
    text = thousands(text)
    found = []
    spans = []

    def free(m):
        for start, end in spans:
            if m.start() < end and m.end() > start:
                return False
        return True

    for pattern in STATED:
        for m in pattern.finditer(text):
            low = value(m.group(1))
            high = value(m.group(2))
            if free(m) and low is not None and high is not None:
                found.append((m.start(), (low, high)))
                spans.append(m.span())

    singles = []
    for m in STATED_AMOUNT.finditer(text):
        if not free(m):
            continue
        amount = value(m.group(1))
        if amount is not None:
            singles.append(amount)

    result = []
    for position, fine in sorted(found):
        result.append(fine)
    return result, singles
