"""Sensitive Topic Classifier: Policy-Driven Content Routing.

Categorizes queries against high-risk policy domains (CBRN/Weapons, Malware/Exploits,
Self-Harm/Crisis, Hate Speech, and Fraud). Distinguishes between hard-blocking attacks
and routing vulnerable users to supportive crisis helplines.
"""

from __future__ import annotations

import re

from guardrails.models import SensitiveCategory, SensitiveTopicFinding, SensitiveTopicResult

# Structured policy taxonomy
TAXONOMY_RULES: dict[SensitiveCategory, dict] = {
    SensitiveCategory.WEAPONS_CBRN: {
        "route": "hard_block",
        "terms": [
            "how to make a bomb", "synthesize explosives", "build a nuclear",
            "chemical weapon", "biological weapon", "ricin", "anthrax",
            "mustard gas", "sarin", "cbrn", "dirty bomb", "weaponize anthrax",
            "toxic compounds", "prohibited toxic compounds",
        ],
        "patterns": [
            r"(?i)\b(make|build|construct|create|synthesize)\b.*\b(bomb|explosive|chemical\s+weapon|bioweapon|detonator|toxic\s+compounds?)\b",
            r"(?i)\b(how\s+to\s+(manufacture|produce|weaponize|synthesize))\b.*\b(ricin|anthrax|sarin|nerve\s+agent|toxic\s+compounds?)\b",
        ],
    },
    SensitiveCategory.CYBERWEAPONS_MALWARE: {
        "route": "hard_block",
        "terms": [
            "write ransomware", "create malware", "build a botnet",
            "ddos attack script", "how to hack into", "exploit zero-day",
            "phishing kit", "keylogger source", "credential harvester",
            "rootkit generator", "reverse shell payload", "denial of service",
        ],
        "patterns": [
            r"(?i)\b(write|create|build|generate|develop|launch|conduct)\b.*\b(ransomware|malware|keylogger|rootkit|botnet|exploit\s+script|denial\s+of\s+service|ddos|cyber\s+attack)\b",
            r"(?i)\b(how\s+(can\s+i|to)\s+(hack|breach|infiltrate|launch|attack))\b.*\b(database|server|network|bank\s+account|servers?)\b",
        ],
    },
    SensitiveCategory.SELF_HARM_CRISIS: {
        "route": "safe_response",
        "terms": [
            "want to kill myself", "end my life", "suicide method",
            "how to commit suicide", "i want to die", "no reason to live",
            "cutting myself", "overdose on pills", "hang myself", "ending my life",
        ],
        "patterns": [
            r"(?i)\b((thoughts\s+of\s+)?ending\s+my\s+life|kill\s+myself|commit\s+suicide|want\s+to\s+die)\b",
            r"(?i)\b(i\s+(want|need|plan|am\s+going|feel\s+like)\s+to\s+(die|kill\s+myself|end\s+my\s+life|commit\s+suicide|harm\s+myself))\b",
            r"(?i)\b(suicide|self[\s-]?harm|self[\s-]?injury)\b.*\b(how|method|way|best)\b",
        ],
    },
    SensitiveCategory.HATE_SPEECH: {
        "route": "hard_block",
        "terms": [
            "ethnic cleansing", "kill all minorities", "exterminate race",
            "white supremacy doctrine", "subhuman race", "harassment and discrimination",
        ],
        "patterns": [
            r"(?i)\b(ethnic\s+cleansing|genocide|exterminate)\b.*\b(race|minority|immigrants|group)\b",
            r"(?i)\b(promoting|spread|advocate)\b.*\b(harassment|discrimination|hate)\b.*\b(ethnic|racial|religious|group)\b",
        ],
    },
    SensitiveCategory.FRAUD: {
        "route": "hard_block",
        "terms": [
            "steal credit card numbers", "fake identity generator",
            "forge passport template", "bank fraud tutorial",
        ],
        "patterns": [
            r"(?i)\b(how\s+to\s+(steal|clone|forge))\b.*\b(credit\s+card|passport|identity|ssn)\b",
        ],
    },
}


class SensitiveTopicClassifier:
    """Classifies user prompts into safety risk categories."""

    CRISIS_HELPLINE_MESSAGE = (
        "It sounds like you may be going through a difficult time. "
        "Support is available 24/7. Please reach out to someone who can help:\n"
        "• Nepal Suicide Helpline: 1166\n"
        "• US National Crisis Line: 988\n"
        "• International Crisis Lifeline: https://findahelpline.com/\n"
        "You are not alone, and there are compassionate professionals ready to listen."
    )

    def __init__(self) -> None:
        self._compiled_rules: list[tuple[str, str, re.Pattern]] = []
        for cat, rule in TAXONOMY_RULES.items():
            route = rule["route"]
            # Compile regex patterns
            for pat in rule.get("patterns", []):
                self._compiled_rules.append((cat.value, route, re.compile(pat)))
            # Compile keyword terms as whole-phrase boundary matches
            for term in rule.get("terms", []):
                escaped = re.escape(term)
                self._compiled_rules.append((cat.value, route, re.compile(rf"(?i)\b{escaped}\b")))

    def classify(self, text: str) -> SensitiveTopicResult:
        """Classify input text against safety policies and determine strictness."""
        findings: list[SensitiveTopicFinding] = []
        actions: set[str] = set()

        for category, action, pattern in self._compiled_rules:
            match = pattern.search(text)
            if match:
                actions.add(action)
                findings.append(
                    SensitiveTopicFinding(
                        category=category,
                        matched_term=match.group(),
                        route_action=action,  # type: ignore[arg-type]
                        confidence=1.0,
                    )
                )

        if not findings:
            return SensitiveTopicResult(
                topics_detected=False,
                findings=[],
                strictest_action="allowed",
                crisis_response_needed=False,
            )

        # Strictest action resolution: hard_block takes precedence over safe_response
        strictest = "hard_block" if "hard_block" in actions else "safe_response"
        is_crisis = any(f.category == SensitiveCategory.SELF_HARM_CRISIS.value for f in findings)

        return SensitiveTopicResult(
            topics_detected=True,
            findings=findings,
            strictest_action=strictest,
            crisis_response_needed=is_crisis,
        )
