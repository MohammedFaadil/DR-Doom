"""
EmergencyRiskEngine (§16, §51, §52.3).

Deterministic, rule-based red-flag detection that runs BEFORE any response
generation, on every user turn, regardless of conversation state. This is
intentionally NOT delegated to the LLM/template generator — safety-critical
detection must not depend on a language model's judgment (§52: "Do not rely
exclusively on an LLM to detect emergencies").

Each rule is plain Python (regex + structured patient_state checks), so it
is auditable and testable in isolation (see backend/tests/test_emergency_engine.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

PatientState = dict


@dataclass(frozen=True)
class EmergencyMatch:
    rule_id: str
    category: str
    reason: str


@dataclass(frozen=True)
class EmergencyRule:
    rule_id: str
    category: str
    reason: str
    patterns: tuple[str, ...] = ()
    predicate: Callable[[str, PatientState], bool] | None = None

    def matches(self, text_lower: str, state: PatientState) -> bool:
        if any(re.search(p, text_lower) for p in self.patterns):
            return True
        if self.predicate is not None:
            return self.predicate(text_lower, state)
        return False


def _has_symptom(state: PatientState, name: str) -> bool:
    return any(s.get("name") == name for s in state.get("symptoms", []))


def _severity_at_least(state: PatientState, name: str, threshold: int) -> bool:
    for s in state.get("symptoms", []):
        if s.get("name") == name and isinstance(s.get("severity"), (int, float)):
            return s["severity"] >= threshold
    return False


def _age_under_months(state: PatientState, months: int) -> bool:
    age = state.get("age")
    age_unit = state.get("age_unit", "years")
    if age is None:
        return False
    age_in_months = age if age_unit == "months" else age * 12
    return age_in_months < months


RULES: list[EmergencyRule] = [
    EmergencyRule(
        "severe_breathing_difficulty",
        "respiratory",
        "Severe difficulty breathing can indicate a life-threatening respiratory or cardiac emergency.",
        patterns=(
            r"can'?t breathe", r"cannot breathe", r"severe (shortness of breath|difficulty breathing)",
            r"gasping for (air|breath)", r"turning blue", r"lips? (are |is )?blue",
        ),
    ),
    EmergencyRule(
        "loss_of_consciousness",
        "neurological",
        "Loss of consciousness or fainting can indicate a serious underlying condition requiring urgent evaluation.",
        patterns=(r"passed out", r"blacked out", r"lost consciousness", r"fainted", r"unresponsive", r"won'?t wake up"),
    ),
    EmergencyRule(
        "stroke_like_symptoms",
        "neurological",
        "These symptoms are consistent with possible stroke warning signs, where speed of treatment matters greatly.",
        patterns=(
            r"face (is |looks )?droop", r"slurred speech", r"can'?t speak (properly|clearly)",
            r"sudden weakness (on )?one side", r"can'?t move (my|one) (arm|leg|side)",
            r"worst headache of my life", r"sudden severe headache", r"thunderclap headache",
            r"sudden vision loss", r"sudden confusion",
        ),
    ),
    EmergencyRule(
        "severe_chest_pain",
        "cardiovascular",
        "Chest pain with these features can indicate a possible heart attack and needs urgent evaluation.",
        predicate=lambda text, state: (
            bool(re.search(r"chest pain|chest pressure|chest tightness", text))
            and (
                bool(re.search(r"radiat|spreading to (my )?(arm|jaw|back|neck)|cold sweat|sweating|shortness of breath|can'?t breathe|nausea|light ?headed|fainting", text))
                or _severity_at_least(state, "chest pain", 7)
            )
        ),
    ),
    EmergencyRule(
        "uncontrolled_bleeding",
        "trauma",
        "Bleeding that will not stop is a medical emergency.",
        patterns=(r"bleeding (won'?t|will not|wont) stop", r"heavy bleeding", r"bleeding a lot", r"blood (is )?spurting"),
    ),
    EmergencyRule(
        "severe_allergic_reaction",
        "allergy",
        "These symptoms can indicate anaphylaxis, a life-threatening allergic reaction.",
        patterns=(
            r"throat (is )?(closing|swelling|tightening)", r"swollen (throat|tongue|lips)",
            r"difficulty breathing after (eating|a sting|a bite|taking)", r"anaphyla",
        ),
    ),
    EmergencyRule(
        "seizure",
        "neurological",
        "An active or recent seizure requires urgent medical assessment, especially if it is new, prolonged, or repeated.",
        patterns=(r"\bseizure\b", r"\bconvulsion", r"having a fit\b"),
    ),
    EmergencyRule(
        "suicidal_crisis",
        "mental_health_crisis",
        "You mentioned thoughts of suicide or self-harm. Your safety matters and immediate support is available.",
        patterns=(
            r"kill myself", r"end my life", r"suicid", r"want to die", r"self[- ]?harm",
            r"hurt myself on purpose",
        ),
    ),
    EmergencyRule(
        "severe_poisoning",
        "toxicology",
        "Possible poisoning or overdose is a medical emergency.",
        patterns=(r"swallowed (poison|chemical|bleach|pills)", r"overdose", r"ingested (poison|chemical)"),
    ),
    EmergencyRule(
        "testicular_torsion",
        "urological",
        "Sudden, severe testicular pain can indicate testicular torsion, a time-critical emergency.",
        patterns=(r"sudden (severe )?testicular pain", r"testicle.*(sudden|severe).*pain"),
    ),
    EmergencyRule(
        "pediatric_infant_fever",
        "pediatric",
        "Fever in a very young infant needs urgent medical evaluation regardless of how the baby otherwise looks.",
        # Checked against the raw text (not state.symptoms) because this rule
        # runs before symptom-extraction (intake) happens for this turn —
        # relying on already-extracted state would silently never fire on a
        # message's first mention of fever.
        predicate=lambda text, state: (
            bool(re.search(r"fever|temperature|hot to (the )?touch|running a temp", text)) or _has_symptom(state, "fever")
        )
        and _age_under_months(state, 3),
    ),
    EmergencyRule(
        "febrile_seizure",
        "pediatric",
        "A seizure associated with fever in a child needs urgent medical evaluation.",
        patterns=(r"febrile seizure", r"seizure.*(fever|hot)", r"fit.*(fever|hot)"),
    ),
]


def screen_for_emergency(text: str, patient_state: PatientState | None = None) -> list[EmergencyMatch]:
    """Run every red-flag rule against the latest user text + accumulated
    structured patient state. Returns all matches (usually 0 or 1)."""
    state = patient_state or {}
    lowered = text.lower()
    matches = [
        EmergencyMatch(rule.rule_id, rule.category, rule.reason)
        for rule in RULES
        if rule.matches(lowered, state)
    ]
    return matches


EMERGENCY_NUMBER_BY_COUNTRY = {
    "US": "911",
    "IN": "112",
    "GB": "999",
    "EU": "112",
}

CRISIS_LINE_BY_COUNTRY = {
    "US": "988 Suicide & Crisis Lifeline (call or text 988)",
    "IN": "iCall (+91 9152987821) or Tele-MANAS (14416)",
    "GB": "Samaritans (116 123)",
}


def emergency_guidance_text(matches: list[EmergencyMatch], country: str = "US") -> str:
    number = EMERGENCY_NUMBER_BY_COUNTRY.get(country, EMERGENCY_NUMBER_BY_COUNTRY["US"])
    categories = {m.category for m in matches}
    lines = ["**Your symptoms may require urgent medical evaluation.**", ""]
    for m in matches:
        lines.append(f"- {m.reason}")
    lines.append("")
    if "mental_health_crisis" in categories:
        crisis = CRISIS_LINE_BY_COUNTRY.get(country, CRISIS_LINE_BY_COUNTRY["US"])
        lines.append(
            f"Please reach out right now: call {number} (emergency services) or contact {crisis}. "
            "You do not have to go through this alone, and immediate help is available."
        )
    else:
        lines.append(
            f"Please call {number} (or your local emergency number) or go to the nearest emergency department now. "
            "This assessment cannot safely continue until you are evaluated by emergency medical professionals."
        )
    lines.append("")
    lines.append(
        "This guidance is based on general emergency-recognition information and is educational only — "
        "it is not a substitute for emergency medical care."
    )
    return "\n".join(lines)
