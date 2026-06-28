import re

STOP_WORDS = {
    'the','a','an','and','or','but','in','on','at','to','for',
    'of','with','by','from','is','was','are','were','has','have',
    'had','be','been','being','patient','presents','history',
    'no','not','without','evidence','denies','possible',
    'acute','bilateral','unilateral','left','right','upper','lower',
    'disease','disorder','syndrome','condition','injury','currently',
    'stable','follow','following','presented','presenting'
}

NEGATION_TRIGGERS = [
    "no ","no evidence of","without","denies","denied",
    "negative for","not ","absence of","ruled out","rule out",
    "unremarkable for","free of","never had","does not have",
    "did not have"
]

UNCERTAINTY_TRIGGERS = [
    "possible","possibly","probable","probably","suspected",
    "suspect","query","cannot exclude","may have","might have",
    "history of"
]


def extract_medical_phrases(text, max_phrases=6):
    words = re.sub(r'[^\w\s]', '', text.lower()).split()
    phrases = []
    used_indices = set()

    for i in range(len(words) - 2):
        if all(words[i+j] not in STOP_WORDS for j in range(3)):
            phrase = ' '.join(words[i:i+3])
            if not phrase[0].isdigit():
                phrases.append(phrase)
                used_indices.update([i, i+1, i+2])

    for i in range(len(words) - 1):
        if all(words[i+j] not in STOP_WORDS for j in range(2)) and i not in used_indices:
            phrase = ' '.join(words[i:i+2])
            if not phrase[0].isdigit():
                phrases.append(phrase)
                used_indices.update([i, i+1])

    for i, w in enumerate(words):
        if i not in used_indices and w not in STOP_WORDS and len(w) > 5:
            phrases.append(w)

    multi = [p for p in phrases if len(p.split()) > 1]
    covered = set(w for p in multi for w in p.split())
    singles = [p for p in phrases if len(p.split()) == 1 and p not in covered]

    return (multi + singles)[:max_phrases]


def detect_negation(text, entity, window=8):
    text_lower = text.lower()
    entity_lower = entity.lower()

    sentences = re.split(r'[.!?]', text_lower)
    for sent in sentences:
        if entity_lower in sent:
            for t in NEGATION_TRIGGERS:
                if t in sent:
                    return 'negated'
            for t in UNCERTAINTY_TRIGGERS:
                if t in sent:
                    return 'uncertain'
            entity_pos = sent.find(entity_lower)
            before_text = ' '.join(sent[:entity_pos].split()[-window:])
            for t in NEGATION_TRIGGERS:
                if t in before_text:
                    return 'negated'
    return 'affirmed'