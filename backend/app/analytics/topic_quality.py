"""
Topic Quality Control Layer
Validates, filters, and categorises topics for executive intelligence.
Only meaningful subjects pass — no HTML, CSS, UI, or metadata terms.
"""
import re
from typing import Optional

# ─── Comprehensive exclusion lists ───────────────────────────────────────────

HTML_TERMS = {
    "href", "src", "div", "span", "class", "classname", "style", "width", "height",
    "margin", "padding", "color", "font", "border", "display", "flex", "grid",
    "button", "input", "form", "label", "table", "tbody", "thead", "tr", "td", "th",
    "header", "footer", "section", "article", "aside", "nav", "main", "html", "body",
    "head", "meta", "link", "script", "iframe", "image", "video", "audio", "canvas",
    "container", "wrapper", "modal", "popup", "dropdown", "navbar", "sidebar",
    "onclick", "onchange", "onload", "onsubmit", "eventlistener", "addeventlistener",
    "innerhtml", "innertext", "textcontent", "queryselector", "getelementbyid",
    "classlist", "dataset", "attribute", "property", "value", "default", "null",
    "undefined", "boolean", "string", "integer", "float", "array", "object",
    "function", "return", "const", "async", "await", "import", "export",
    "react", "nextjs", "tailwind", "typescript", "javascript", "python",
    "rgba", "opacity", "rounded", "shadow", "hover", "focus", "active",
}

UI_TERMS = {
    "click", "button", "read", "more", "load", "loading", "close", "open",
    "save", "delete", "cancel", "confirm", "submit", "reset", "back", "next",
    "previous", "page", "pages", "post", "posts", "item", "items", "list",
    "card", "cards", "view", "views", "show", "hide", "toggle", "menu",
    "search", "filter", "sort", "order", "select", "option", "check",
    "uncheck", "enable", "disable", "active", "inactive", "status", "type",
    "title", "name", "email", "phone", "address", "date", "time", "number",
    "text", "content", "data", "info", "information", "details", "detail",
    "share", "follow", "like", "comment", "reply", "send", "receive",
    "upload", "download", "export", "import", "print", "copy", "paste",
    "edit", "update", "create", "remove", "login", "logout", "signup",
    "password", "username", "profile", "account", "settings", "help",
    "about", "contact", "home", "news", "latest", "recent", "popular",
    "featured", "trending", "related", "similar", "recommended",
    "newsap", "newsa", "articl", "appeared", "continue", "reading",
    "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december",
}

GENERIC_TERMS = {
    "the", "and", "that", "this", "with", "from", "have", "been", "will",
    "would", "could", "should", "might", "must", "shall", "were", "there",
    "their", "they", "them", "then", "than", "when", "where", "what", "which",
    "who", "how", "why", "also", "just", "even", "only", "very", "much",
    "many", "some", "such", "each", "both", "into", "over", "under", "after",
    "before", "between", "through", "during", "against", "without", "within",
    "across", "around", "along", "among", "upon", "about", "said", "says",
    "told", "says", "according", "reported", "noted", "stated", "added",
    "year", "years", "month", "months", "week", "weeks", "day", "days",
    "time", "times", "people", "person", "man", "woman", "men", "women",
    "world", "country", "countries", "city", "state", "states", "government",
    "report", "reports", "study", "studies", "research", "analysis",
    "percent", "million", "billion", "thousand", "hundred", "first", "second",
    "third", "last", "next", "new", "old", "good", "great", "large", "small",
    "high", "low", "long", "short", "major", "minor", "number", "part",
    "place", "way", "thing", "things", "make", "made", "take", "taken",
    "come", "came", "gone", "going", "getting", "having", "being", "doing",
    "following", "including", "using", "used", "based", "called", "known",
    "given", "said", "made", "seen", "found", "want", "need", "look",
    "know", "think", "feel", "believe", "hope", "seem", "appear",
}

ALL_EXCLUSIONS = HTML_TERMS | UI_TERMS | GENERIC_TERMS

# ─── Topic category mapping ───────────────────────────────────────────────────

TOPIC_CATEGORIES = {
    "Economy": [
        "economy", "economic", "inflation", "gdp", "growth", "recession", "trade",
        "investment", "market", "finance", "financial", "fiscal", "monetary",
        "revenue", "budget", "debt", "deficit", "surplus", "naira", "dollar",
        "currency", "exchange", "bank", "banking", "credit", "loan", "interest",
        "poverty", "unemployment", "employment", "jobs", "wage", "salary",
        "business", "enterprise", "entrepreneur", "startup", "industry", "sector",
        "oil", "petroleum", "commodity", "export", "import", "tariff", "tax",
        "remittance", "forex", "stock", "shares", "capital", "wealth",
    ],
    "Governance": [
        "government", "governance", "policy", "policies", "legislation", "law",
        "regulation", "reform", "corruption", "transparency", "accountability",
        "democracy", "election", "vote", "voting", "president", "minister",
        "parliament", "senate", "congress", "assembly", "council", "committee",
        "tinubu", "obi", "atiku", "buhari", "president", "governor", "senator",
        "representative", "official", "authority", "administration", "cabinet",
        "judiciary", "court", "justice", "rights", "constitution", "federal",
        "state", "local", "municipal", "civic", "political", "party",
    ],
    "Infrastructure": [
        "infrastructure", "road", "roads", "highway", "bridge", "railway",
        "transport", "transportation", "airport", "seaport", "port",
        "construction", "building", "housing", "urban", "rural", "development",
        "water", "sanitation", "sewage", "waste", "electricity", "grid",
        "broadband", "internet", "connectivity", "network", "telecommunications",
    ],
    "Energy": [
        "energy", "power", "electricity", "fuel", "gas", "solar", "renewable",
        "generation", "transmission", "distribution", "outage", "blackout",
        "nepa", "discos", "genco", "petroleum", "refinery", "pipeline",
        "subsidy", "kerosene", "diesel", "coal", "hydro", "nuclear",
    ],
    "Security": [
        "security", "safety", "crime", "violence", "terrorism", "insurgency",
        "boko", "bandit", "kidnap", "abduction", "conflict", "war", "military",
        "police", "army", "navy", "airforce", "defence", "attack", "threat",
        "protest", "unrest", "tension", "crisis", "emergency", "disaster",
    ],
    "Health": [
        "health", "healthcare", "hospital", "doctor", "nurse", "medicine",
        "disease", "illness", "epidemic", "pandemic", "vaccine", "vaccination",
        "treatment", "surgery", "mental", "wellbeing", "nutrition", "malaria",
        "hiv", "aids", "cancer", "maternal", "child", "mortality", "mortality",
    ],
    "Education": [
        "education", "school", "university", "college", "student", "teacher",
        "learning", "academic", "curriculum", "scholarship", "research",
        "literacy", "skill", "training", "graduate", "undergraduate",
        "asuu", "strike", "tuition", "examination", "certificate", "degree",
    ],
    "Diaspora": [
        "diaspora", "migration", "migrant", "immigrant", "emigrant", "abroad",
        "overseas", "foreign", "international", "global", "community",
        "identity", "culture", "heritage", "origin", "homeland", "return",
        "citizenship", "passport", "visa", "dual", "british", "american",
        "canada", "europe", "engagement", "representation", "advocacy",
    ],
    "Investment": [
        "investment", "investor", "fund", "funding", "venture", "equity",
        "startup", "fintech", "technology", "innovation", "digital",
        "agtech", "agriculture", "manufacturing", "production", "supply",
        "logistics", "retail", "commerce", "partnership", "collaboration",
    ],
    "Media": [
        "media", "journalism", "journalist", "newspaper", "television",
        "radio", "broadcast", "social media", "twitter", "facebook",
        "narrative", "story", "coverage", "reporting", "press", "freedom",
        "censorship", "propaganda", "misinformation", "fake", "truth",
    ],
}

# Build reverse lookup: keyword → category
KEYWORD_TO_CATEGORY: dict[str, str] = {}
for category, keywords in TOPIC_CATEGORIES.items():
    for kw in keywords:
        KEYWORD_TO_CATEGORY[kw] = category


# ─── Validation functions ─────────────────────────────────────────────────────

def is_valid_topic(word: str) -> bool:
    """Return True if a word/phrase is a meaningful intelligence topic."""
    w = word.lower().strip()

    # Too short
    if len(w) < 4:
        return False

    # In exclusion list
    if w in ALL_EXCLUSIONS:
        return False

    # Contains URL patterns
    if any(p in w for p in ["http", "www.", ".com", ".org", ".net", "://", "html"]):
        return False

    # Purely numeric
    if w.replace(",", "").replace(".", "").isdigit():
        return False

    # Contains special chars (except hyphen for compound words)
    if re.search(r'[^a-z0-9\-\s]', w):
        return False

    # Single-char repetition (e.g. "aaaa")
    if len(set(w)) < 3 and len(w) > 3:
        return False

    return True


def categorise_topic(topic: str) -> str:
    """Return the category for a topic."""
    t = topic.lower()
    for keyword, category in KEYWORD_TO_CATEGORY.items():
        if keyword in t:
            return category
    return "Other"


def calculate_confidence(count: int, source_count: int, total_posts: int) -> tuple[float, str]:
    """
    Calculate confidence score and label for an intelligence finding.
    Returns (score 0.0-1.0, label)
    """
    # Base confidence from mention frequency
    freq_score = min(count / max(total_posts * 0.1, 1), 1.0)
    # Boost for multi-source corroboration
    source_score = min(source_count / 3, 1.0)
    score = round((freq_score * 0.6 + source_score * 0.4), 2)

    if score >= 0.7:
        label = "High"
    elif score >= 0.4:
        label = "Medium"
    else:
        label = "Low"

    return score, label


def filter_and_enrich_topics(
    raw_topics: list[tuple[str, int]],
    source_count: int = 1,
    total_posts: int = 100,
) -> list[dict]:
    """
    Filter raw topics through quality controls and enrich with metadata.
    Returns list of validated, categorised, scored topic dicts.
    """
    results = []
    rejected = 0

    for topic, count in raw_topics:
        if not is_valid_topic(topic):
            rejected += 1
            continue

        category = categorise_topic(topic)
        confidence, confidence_label = calculate_confidence(count, source_count, total_posts)

        results.append({
            "topic": topic,
            "count": count,
            "category": category,
            "confidence": confidence,
            "confidence_label": confidence_label,
            "source_count": source_count,
        })

    return results, rejected


# ─── Entity alias map ─────────────────────────────────────────────────────────
# Maps variant names to canonical form for deduplication
# Add new aliases here as they are discovered

ENTITY_ALIASES = {
    # Nigerian President - all variants map to full name
    "bola": "Bola Tinubu",
    "tinubu": "Bola Tinubu",
    "bola tinubu": "Bola Tinubu",
    "president tinubu": "Bola Tinubu",
    "president bola": "Bola Tinubu",
    "asiwaju": "Bola Tinubu",
    # Other common variants
    "buhari": "Muhammadu Buhari",
    "peter obi": "Peter Obi",
    "atiku": "Atiku Abubakar",
    "atiku abubakar": "Atiku Abubakar",
    "shettima": "Kashim Shettima",
    "wike": "Nyesom Wike",
    "tinubu administration": "Bola Tinubu",
}


def resolve_entity_alias(name: str) -> str:
    """Resolve an entity name to its canonical form."""
    key = name.lower().strip()
    return ENTITY_ALIASES.get(key, name)


def deduplicate_topics(topics: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """
    Merge topic variants that refer to the same subject.
    e.g. 'tinubu' and 'bola' both become 'Bola Tinubu'
    """
    merged: dict[str, int] = {}
    for topic, count in topics:
        canonical = resolve_entity_alias(topic)
        merged[canonical] = merged.get(canonical, 0) + count
    return sorted(merged.items(), key=lambda x: x[1], reverse=True)
