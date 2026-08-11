"""Summary Agent (§22, §52.8): builds a structured consultation summary
from the conversation's accumulated patient_state + evidence used."""
from __future__ import annotations

DISCLAIMER = (
    "Dr Doom provides AI-generated health information and educational guidance based on its "
    "available medical knowledge sources. It is not a substitute for an examination, diagnosis, "
    "or treatment from a qualified healthcare professional. If symptoms are severe, sudden, or "
    "concerning, seek appropriate medical care."
)


def build_summary(state: dict, evidence_consulted: list[dict], guidance_provided: str | None) -> dict:
    symptoms = state.get("symptoms", [])
    primary = symptoms[0] if symptoms else {}
    associated: list[str] = []
    for s in symptoms[1:]:
        associated.append(s.get("name", ""))
    for s in symptoms:
        assoc = s.get("associated_symptoms") or []
        if isinstance(assoc, str):
            assoc = [assoc]
        associated.extend(assoc)

    missing = []
    if state.get("age") is None:
        missing.append("age")
    if state.get("sex") is None:
        missing.append("sex")
    if primary and primary.get("severity") is None:
        missing.append(f"{primary.get('name')}_severity")
    if primary and primary.get("duration") is None:
        missing.append(f"{primary.get('name')}_duration")

    return {
        "patient_profile": {
            "age": state.get("age"),
            "sex": state.get("sex"),
            "pregnancy_status": state.get("pregnancy_status"),
        },
        "primary_concern": state.get("primary_complaint"),
        "symptoms": [s.get("name") for s in symptoms],
        "duration": primary.get("duration"),
        "severity": primary.get("severity"),
        "associated_symptoms": [a for a in associated if a],
        "relevant_history": state.get("medical_history", []),
        "medications": state.get("medications", []),
        "allergies": state.get("allergies", []),
        "red_flags": state.get("red_flags", []),
        "risk_level": state.get("risk_level", "unknown"),
        "evidence_consulted": evidence_consulted,
        "guidance_provided": guidance_provided,
        "recommended_next_step": _recommended_next_step(state.get("risk_level", "unknown")),
        "unanswered_questions": missing,
        "disclaimer": DISCLAIMER,
    }


def _recommended_next_step(risk_level: str) -> str:
    return {
        "emergency": "Seek emergency medical care immediately.",
        "urgent": "Seek prompt medical evaluation, ideally within 24 hours.",
        "moderate": "Consider scheduling an appointment with a clinician if symptoms persist or worsen.",
        "low": "Monitor symptoms and use general self-care guidance; seek care if things change.",
        "unknown": "Consult a clinician if you remain concerned or symptoms persist.",
    }.get(risk_level, "Consult a clinician if you remain concerned or symptoms persist.")
