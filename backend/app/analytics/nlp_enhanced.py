# NDIP spaCy/pydantic v1 compatibility patch
import typing as _t
_orig_eval = _t.ForwardRef._evaluate
def _patched_eval(self, globalns, localns, *args, **kwargs):
    for _call in [
        lambda: _orig_eval(self, globalns, localns, recursive_guard=frozenset()),
        lambda: _orig_eval(self, globalns, localns, frozenset()),
        lambda: _orig_eval(self, globalns, localns),
    ]:
        try: return _call()
        except TypeError: continue
_t.ForwardRef._evaluate = _patched_eval
del _t, _orig_eval, _patched_eval
# End patch

"""
NDIP Enhanced NLP Pipeline v5.1
Uses spaCy for entity recognition when available.
Falls back to capitalised phrase extraction gracefully.
"""
import re
from typing import Optional

# Try to load spaCy - graceful fallback
_nlp = None
_spacy_available = False

def _load_spacy():
    global _nlp, _spacy_available
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_md")
            _spacy_available = True
            print("[NLP] spaCy en_core_web_md loaded")
        except OSError:
            try:
                _nlp = spacy.load("en_core_web_sm")
                _spacy_available = True
                print("[NLP] spaCy en_core_web_sm loaded (fallback)")
            except OSError:
                print("[NLP] spaCy models not found — using fallback NER")
    except (ImportError, ValueError, TypeError, Exception) as e:
        print(f"[NLP] spaCy unavailable ({type(e).__name__}) — using enhanced fallback NER")
        _spacy_available = False
    return _nlp


# ─── Entity alias resolution ──────────────────────────────────────────────────
ENTITY_ALIASES = {
    # People
    "bola": "Bola Tinubu",
    "tinubu": "Bola Tinubu",
    "president tinubu": "Bola Tinubu",
    "bola tinubu": "Bola Tinubu",
    "asiwaju": "Bola Tinubu",
    "bola ahmed tinubu": "Bola Tinubu",
    "buhari": "Muhammadu Buhari",
    "muhammadu buhari": "Muhammadu Buhari",
    "atiku": "Atiku Abubakar",
    "atiku abubakar": "Atiku Abubakar",
    "peter obi": "Peter Obi",
    "obi": "Peter Obi",
    "ngozi okonjo": "Ngozi Okonjo-Iweala",
    "okonjo-iweala": "Ngozi Okonjo-Iweala",
    "okonjo iweala": "Ngozi Okonjo-Iweala",
    "wto director": "Ngozi Okonjo-Iweala",
    # Organisations
    "all progressives congress": "APC",
    "peoples democratic party": "PDP",
    "independent national electoral commission": "INEC",
    "nigerian senate": "Nigerian Senate",
    "national assembly": "National Assembly",
    "economic community": "ECOWAS",
    # Locations
    "eko": "Lagos",
    "fct": "Abuja",
    "federal capital territory": "Abuja",
    "port harcourt": "Port Harcourt",
    "ph": "Port Harcourt",
}

SUPPRESS_ENTITIES = {
    "president", "minister", "governor", "senator", "congressman",
    "director", "chief", "sir", "dr", "mr", "mrs", "ms", "prof",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "nigeria", "nigerian", "nigerians",  # too generic
    "africa", "african",
}

ENTITY_TYPE_MAP = {
    "PERSON": "PERSON",
    "ORG": "ORGANISATION",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "EVENT": "EVENT",
    "FAC": "LOCATION",
    "NORP": "GROUP",
    "PRODUCT": "PRODUCT",
    "WORK_OF_ART": "OTHER",
    "LAW": "POLICY",
    "LANGUAGE": "OTHER",
}


def resolve_entity(text: str) -> Optional[str]:
    """Resolve entity to canonical form."""
    lower = text.lower().strip()
    if lower in SUPPRESS_ENTITIES:
        return None
    if lower in ENTITY_ALIASES:
        return ENTITY_ALIASES[lower]
    # Check partial matches
    for alias, canonical in ENTITY_ALIASES.items():
        if alias in lower and len(alias) > 4:
            return canonical
    return text.strip() if len(text.strip()) > 2 else None


def extract_entities_spacy(text: str) -> list[dict]:
    """Extract entities using spaCy NER."""
    nlp = _load_spacy()
    if not nlp or not text:
        return []
    try:
        doc = nlp(text[:5000])  # limit for performance
        entities = []
        seen = set()
        for ent in doc.ents:
            entity_type = ENTITY_TYPE_MAP.get(ent.label_, "OTHER")
            if entity_type == "OTHER":
                continue
            resolved = resolve_entity(ent.text)
            if not resolved or resolved.lower() in SUPPRESS_ENTITIES:
                continue
            key = f"{resolved}:{entity_type}"
            if key not in seen:
                seen.add(key)
                entities.append({
                    "name": resolved,
                    "entity_type": entity_type,
                    "original_text": ent.text,
                    "confidence": 0.85,
                })
        return entities
    except Exception as e:
        return []


def extract_entities_fallback(text: str) -> list[dict]:
    """Fallback: extract capitalised phrases."""
    if not text:
        return []
    # Match capitalised phrases (2+ words or known single entities)
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    matches = re.findall(pattern, text)
    entities = []
    seen = set()
    for match in matches:
        resolved = resolve_entity(match)
        if not resolved or resolved in seen:
            continue
        if len(resolved) < 3:
            continue
        seen.add(resolved)
        entities.append({
            "name": resolved,
            "entity_type": "PERSON",  # default for fallback
            "original_text": match,
            "confidence": 0.5,
        })
    return entities[:20]


def extract_entities(text: str) -> list[dict]:
    """Main entity extraction — uses spaCy if available, fallback otherwise."""
    nlp = _load_spacy()
    if nlp and _spacy_available:
        entities = extract_entities_spacy(text)
        if entities:
            return entities
    return extract_entities_fallback(text)


def get_nlp_status() -> dict:
    """Return current NLP pipeline status."""
    try:
        nlp = _load_spacy()
    except Exception:
        nlp = None
    return {
        "spacy_available": _spacy_available,
        "model": nlp.meta.get("name", "unknown") if nlp else "enhanced-fallback",
        "entity_extraction": "spaCy NER" if _spacy_available else "Enhanced alias-aware NER fallback",
    }
