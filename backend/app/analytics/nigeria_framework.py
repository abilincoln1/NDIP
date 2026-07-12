"""
Nigeria Intelligence Framework
Config-driven narrative mapping — no hardcoded values.
Future Nigerian media connectors map automatically into these categories.
Add new categories by updating NIGERIA_NARRATIVE_CONFIG only.
"""
from typing import Optional

# ─── Config-driven narrative definitions ─────────────────────────────────────
# Each category defines: keywords, weight, monitoring threshold, description
# Connectors map to these by keyword matching — no hardcoding required

NIGERIA_NARRATIVE_CONFIG = {
    "Economy": {
        "description": "Economic conditions, financial markets, business, employment",
        "keywords": ["economy", "inflation", "naira", "forex", "gdp", "unemployment", "investment",
                     "business", "market", "budget", "revenue", "tax", "debt", "trade", "oil", "petroleum"],
        "weight": 1.3, "monitoring_threshold": 0.15,
        "connector_tags": ["nairametrics", "businessday", "punch_economy"],
    },
    "Governance": {
        "description": "Government, policy, legislation, administration, accountability",
        "keywords": ["government", "policy", "legislation", "reform", "corruption", "accountability",
                     "senate", "assembly", "minister", "president", "tinubu", "cabinet", "court"],
        "weight": 1.2, "monitoring_threshold": 0.10,
        "connector_tags": ["punch_politics", "vanguard_politics", "thisday_politics"],
    },
    "Security": {
        "description": "Public safety, crime, terrorism, military, civil unrest",
        "keywords": ["security", "terrorism", "kidnap", "bandit", "military", "police", "attack",
                     "conflict", "boko", "insurgency", "violence", "crime"],
        "weight": 1.2, "monitoring_threshold": 0.10,
        "connector_tags": ["punch_crime", "vanguard_crime"],
    },
    "Elections & Democracy": {
        "description": "Elections, voting, democratic institutions, political participation",
        "keywords": ["election", "vote", "inec", "ballot", "campaign", "democracy", "party",
                     "tribunal", "petition", "rigging", "result"],
        "weight": 1.1, "monitoring_threshold": 0.05,
        "connector_tags": ["punch_politics", "premium_times"],
    },
    "Energy": {
        "description": "Power supply, electricity, fuel, gas, energy policy",
        "keywords": ["energy", "electricity", "power", "fuel", "gas", "solar", "generation",
                     "outage", "blackout", "subsidy", "petroleum", "pipeline", "nepa"],
        "weight": 1.0, "monitoring_threshold": 0.05,
        "connector_tags": ["nairametrics", "energy_mix"],
    },
    "Infrastructure": {
        "description": "Roads, bridges, housing, transport, water, public works",
        "keywords": ["infrastructure", "road", "bridge", "railway", "airport", "construction",
                     "housing", "water", "sanitation", "transport", "broadband"],
        "weight": 0.9, "monitoring_threshold": 0.05,
        "connector_tags": ["punch_metro", "vanguard_metro"],
    },
    "Education": {
        "description": "Schools, universities, academic policy, training",
        "keywords": ["education", "school", "university", "student", "asuu", "scholarship",
                     "academic", "teacher", "curriculum", "examination", "graduate"],
        "weight": 0.9, "monitoring_threshold": 0.05,
        "connector_tags": ["punch_education", "vanguard_education"],
    },
    "Health": {
        "description": "Healthcare, disease, medical services, public health",
        "keywords": ["health", "hospital", "doctor", "medicine", "disease", "malaria",
                     "vaccine", "maternal", "mental health", "epidemic"],
        "weight": 1.0, "monitoring_threshold": 0.05,
        "connector_tags": ["punch_health", "vanguard_health"],
    },
    "Diaspora": {
        "description": "Overseas community, migration, identity, engagement, remittances",
        "keywords": ["diaspora", "migration", "immigrant", "abroad", "overseas", "community",
                     "identity", "heritage", "remittance", "citizenship", "nigeria", "nigerian", "african"],
        "weight": 1.4, "monitoring_threshold": 0.15,
        "connector_tags": ["rtifn_feed", "bbc_africa", "voa_africa"],
    },
    "Investment": {
        "description": "Business investment, startups, technology, economic development",
        "keywords": ["investment", "investor", "startup", "fintech", "technology", "innovation",
                     "venture", "funding", "manufacturing", "partnership"],
        "weight": 1.1, "monitoring_threshold": 0.05,
        "connector_tags": ["nairametrics", "techcabal"],
    },
    "Media Representation": {
        "description": "How Nigerians and diaspora are portrayed in media",
        "keywords": ["media", "journalism", "narrative", "coverage", "reporting", "image",
                     "portrayal", "representation", "stereotype", "perception"],
        "weight": 1.0, "monitoring_threshold": 0.05,
        "connector_tags": ["bbc_africa", "cnn_africa", "guardian_africa"],
    },
}


def get_narrative_for_text(text: str) -> Optional[str]:
    """Returns the best matching narrative category for a text, or None."""
    if not text:
        return None
    text_lower = text.lower()
    best_narrative = None
    best_score = 0
    for narrative, config in NIGERIA_NARRATIVE_CONFIG.items():
        score = sum(1 for kw in config["keywords"] if kw in text_lower) * config["weight"]
        if score > best_score:
            best_score = score
            best_narrative = narrative
    return best_narrative if best_score >= 2 else None


def get_narrative_config(narrative: str) -> Optional[dict]:
    """Get config for a named narrative."""
    return NIGERIA_NARRATIVE_CONFIG.get(narrative)


def register_connector_mapping(connector_tag: str, text: str) -> str:
    """Auto-map a connector's content to a narrative category."""
    # Check connector_tags first (source-level mapping)
    for narrative, config in NIGERIA_NARRATIVE_CONFIG.items():
        if connector_tag in config.get("connector_tags", []):
            return narrative
    # Fall back to text analysis
    return get_narrative_for_text(text) or "Other"


def get_all_categories() -> list[dict]:
    """Return all narrative categories — for UI and API consumption."""
    return [
        {
            "name": narrative,
            "description": config["description"],
            "keyword_count": len(config["keywords"]),
            "weight": config["weight"],
            "monitoring_threshold": config["monitoring_threshold"],
            "connector_count": len(config.get("connector_tags", [])),
        }
        for narrative, config in NIGERIA_NARRATIVE_CONFIG.items()
    ]
