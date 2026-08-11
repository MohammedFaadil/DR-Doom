"""
Adaptive Question Engine (§13, §15).

Each question set is keyed by the symptom's `question_set` (see
symptom_lexicon.py) and is a small ordered list of typed Question dicts.
`clinical_priority` follows the spec's global ordering (§13): emergency
screening always happens first via the EmergencyRiskEngine, not here; this
module handles priorities 5-13 (main symptom onward).

Every question carries a `reason` so the conversation stays explainable —
"why is Dr Doom asking this" is always answerable.
"""
from __future__ import annotations

from typing import Literal, TypedDict


class QuestionOption(TypedDict):
    label: str
    value: str


class Question(TypedDict, total=False):
    id: str
    question: str
    type: Literal["single_select", "multi_select", "numeric", "date", "text", "yes_no", "slider"]
    options: list[QuestionOption]
    reason: str
    clinical_priority: int
    field: str  # where the answer is stored in patient_state


PROFILE_QUESTIONS: list[Question] = [
    {
        "id": "age",
        "question": "How old are you (or the patient, if you're asking on someone else's behalf)?",
        "type": "numeric",
        "reason": "Age changes which conditions are likely and how urgently symptoms should be evaluated.",
        "clinical_priority": 2,
        "field": "age",
    },
    {
        "id": "sex",
        "question": "What was the sex recorded at birth?",
        "type": "single_select",
        "options": [
            {"label": "Female", "value": "female"},
            {"label": "Male", "value": "male"},
            {"label": "Intersex", "value": "intersex"},
            {"label": "Prefer not to say", "value": "prefer_not_to_say"},
        ],
        "reason": "Some conditions and questions differ by sex.",
        "clinical_priority": 3,
        "field": "sex",
    },
    {
        "id": "pregnancy_status",
        "question": "Is there any chance you could be pregnant right now?",
        "type": "single_select",
        "options": [
            {"label": "Yes", "value": "pregnant"},
            {"label": "No", "value": "not_pregnant"},
            {"label": "Not sure", "value": "unknown"},
            {"label": "Not applicable", "value": "na"},
        ],
        "reason": "Pregnancy changes which explanations and medications are safe to discuss.",
        "clinical_priority": 4,
        "field": "pregnancy_status",
    },
]

DURATION_OPTIONS: list[QuestionOption] = [
    {"label": "Less than 1 hour", "value": "<1h"},
    {"label": "1–6 hours", "value": "1-6h"},
    {"label": "6–24 hours", "value": "6-24h"},
    {"label": "1–3 days", "value": "1-3d"},
    {"label": "More than 3 days", "value": ">3d"},
    {"label": "I'm not sure", "value": "unsure"},
]

SEVERITY_QUESTION: Question = {
    "id": "severity",
    "question": "How severe is it, on a scale of 1 (barely noticeable) to 10 (worst pain imaginable)?",
    "type": "slider",
    "reason": "Severity helps judge urgency and which self-care advice is appropriate.",
    "clinical_priority": 8,
    "field": "severity",
}


def _duration_question(id_suffix: str, label: str, priority: int = 7) -> Question:
    return {
        "id": f"duration_{id_suffix}",
        "question": f"When did the {label} begin?",
        "type": "single_select",
        "options": DURATION_OPTIONS,
        "reason": "Onset and duration narrow down likely causes and urgency.",
        "clinical_priority": priority,
        "field": "duration",
    }


QUESTION_SETS: dict[str, list[Question]] = {
    "chest_pain": [
        {
            "id": "chest_pain_location",
            "question": "Where exactly is the pain?",
            "type": "single_select",
            "options": [
                {"label": "Center of chest", "value": "center"},
                {"label": "Left side", "value": "left"},
                {"label": "Right side", "value": "right"},
                {"label": "Upper chest", "value": "upper"},
                {"label": "Other", "value": "other"},
            ],
            "reason": "Location helps distinguish possible causes of chest pain.",
            "clinical_priority": 6,
            "field": "location",
        },
        _duration_question("chest_pain", "chest pain"),
        SEVERITY_QUESTION,
        {
            "id": "chest_pain_associated",
            "question": "Are you currently experiencing any of these?",
            "type": "multi_select",
            "options": [
                {"label": "Difficulty breathing", "value": "dyspnea"},
                {"label": "Fainting or near-fainting", "value": "syncope"},
                {"label": "Cold sweat", "value": "cold_sweat"},
                {"label": "Nausea", "value": "nausea"},
                {"label": "Pain spreading to arm/jaw/back", "value": "radiation"},
                {"label": "None of these", "value": "none"},
            ],
            "reason": "These associated symptoms are the classic warning signs checked before anything else.",
            "clinical_priority": 1,
            "field": "associated_symptoms",
        },
    ],
    "palpitations": [
        _duration_question("palpitations", "palpitations"),
        {
            "id": "palpitations_trigger",
            "question": "Did anything seem to trigger it?",
            "type": "single_select",
            "options": [
                {"label": "Exercise/exertion", "value": "exertion"},
                {"label": "Caffeine or stimulants", "value": "stimulants"},
                {"label": "Stress or anxiety", "value": "stress"},
                {"label": "Nothing noticeable", "value": "none"},
                {"label": "Not sure", "value": "unsure"},
            ],
            "reason": "Triggers help distinguish benign from concerning causes.",
            "clinical_priority": 9,
            "field": "trigger",
        },
        {
            "id": "palpitations_associated",
            "question": "Are you also experiencing any of these?",
            "type": "multi_select",
            "options": [
                {"label": "Chest pain", "value": "chest_pain"},
                {"label": "Shortness of breath", "value": "dyspnea"},
                {"label": "Dizziness or fainting", "value": "syncope"},
                {"label": "None of these", "value": "none"},
            ],
            "reason": "These combinations change how urgently palpitations should be evaluated.",
            "clinical_priority": 1,
            "field": "associated_symptoms",
        },
    ],
    "headache": [
        _duration_question("headache", "headache"),
        SEVERITY_QUESTION,
        {
            "id": "headache_pattern",
            "question": "How did it start?",
            "type": "single_select",
            "options": [
                {"label": "Suddenly / like a thunderclap", "value": "sudden"},
                {"label": "Gradually", "value": "gradual"},
                {"label": "After an injury", "value": "post_injury"},
                {"label": "Comes and goes (recurring)", "value": "recurring"},
            ],
            "reason": "A sudden 'thunderclap' onset is treated very differently from a gradual headache.",
            "clinical_priority": 5,
            "field": "onset_pattern",
        },
        {
            "id": "headache_associated",
            "question": "Are you experiencing any of these along with the headache?",
            "type": "multi_select",
            "options": [
                {"label": "Vision changes", "value": "vision_changes"},
                {"label": "Confusion or trouble speaking", "value": "confusion"},
                {"label": "Weakness on one side", "value": "weakness"},
                {"label": "Neck stiffness", "value": "neck_stiffness"},
                {"label": "Nausea or vomiting", "value": "nausea"},
                {"label": "Sensitivity to light/sound", "value": "photophobia"},
                {"label": "None of these", "value": "none"},
            ],
            "reason": "These are the warning signs checked before discussing common headache causes.",
            "clinical_priority": 1,
            "field": "associated_symptoms",
        },
    ],
    "fever": [
        _duration_question("fever", "fever"),
        {
            "id": "fever_temperature",
            "question": "Do you know your temperature reading?",
            "type": "text",
            "reason": "An exact reading (if available) helps gauge severity; it's fine to skip if unknown.",
            "clinical_priority": 8,
            "field": "temperature",
        },
        {
            "id": "fever_associated",
            "question": "Are you also experiencing any of these?",
            "type": "multi_select",
            "options": [
                {"label": "Stiff neck", "value": "neck_stiffness"},
                {"label": "Rash", "value": "rash"},
                {"label": "Confusion", "value": "confusion"},
                {"label": "Difficulty breathing", "value": "dyspnea"},
                {"label": "Severe headache", "value": "severe_headache"},
                {"label": "None of these", "value": "none"},
            ],
            "reason": "These combinations with fever can indicate a more serious infection.",
            "clinical_priority": 1,
            "field": "associated_symptoms",
        },
    ],
    "abdominal_pain": [
        {
            "id": "abdominal_pain_location",
            "question": "Where is the pain?",
            "type": "single_select",
            "options": [
                {"label": "Upper abdomen", "value": "upper"},
                {"label": "Lower abdomen", "value": "lower"},
                {"label": "Right side", "value": "right"},
                {"label": "Left side", "value": "left"},
                {"label": "Around the belly button", "value": "periumbilical"},
                {"label": "I'm not sure", "value": "unsure"},
            ],
            "reason": "Location narrows down which organs may be involved.",
            "clinical_priority": 6,
            "field": "location",
        },
        _duration_question("abdominal_pain", "pain"),
        SEVERITY_QUESTION,
        {
            "id": "abdominal_pain_vomiting",
            "question": "Have you experienced vomiting?",
            "type": "yes_no",
            "reason": "Vomiting alongside abdominal pain changes the likely explanations.",
            "clinical_priority": 9,
            "field": "vomiting",
        },
        {
            "id": "abdominal_pain_fever",
            "question": "Do you have a fever?",
            "type": "single_select",
            "options": [
                {"label": "Yes", "value": "yes"},
                {"label": "No", "value": "no"},
                {"label": "Not sure", "value": "unsure"},
            ],
            "reason": "Fever with abdominal pain can indicate infection or inflammation.",
            "clinical_priority": 9,
            "field": "fever",
        },
        {
            "id": "abdominal_pain_progression",
            "question": "Is the pain getting worse?",
            "type": "single_select",
            "options": [
                {"label": "Yes", "value": "worsening"},
                {"label": "No", "value": "improving"},
                {"label": "About the same", "value": "stable"},
            ],
            "reason": "Worsening pain is one factor that raises urgency.",
            "clinical_priority": 10,
            "field": "progression",
        },
    ],
    "cough": [
        _duration_question("cough", "cough"),
        {
            "id": "cough_type",
            "question": "Is the cough producing anything?",
            "type": "single_select",
            "options": [
                {"label": "Dry (nothing coming up)", "value": "dry"},
                {"label": "Mucus/phlegm", "value": "productive"},
                {"label": "Blood", "value": "blood"},
            ],
            "reason": "Coughing up blood is evaluated very differently from a dry or mucus-producing cough.",
            "clinical_priority": 6,
            "field": "cough_type",
        },
        {
            "id": "cough_associated",
            "question": "Are you also experiencing any of these?",
            "type": "multi_select",
            "options": [
                {"label": "Fever", "value": "fever"},
                {"label": "Shortness of breath", "value": "dyspnea"},
                {"label": "Chest pain", "value": "chest_pain"},
                {"label": "Wheezing", "value": "wheezing"},
                {"label": "None of these", "value": "none"},
            ],
            "reason": "These combinations affect how the cough should be evaluated.",
            "clinical_priority": 1,
            "field": "associated_symptoms",
        },
    ],
    "dizziness": [
        _duration_question("dizziness", "dizziness"),
        {
            "id": "dizziness_character",
            "question": "How would you describe it?",
            "type": "single_select",
            "options": [
                {"label": "The room feels like it's spinning", "value": "vertigo"},
                {"label": "Lightheaded, like I might faint", "value": "presyncope"},
                {"label": "Off-balance/unsteady", "value": "imbalance"},
            ],
            "reason": "The character of dizziness points toward different causes.",
            "clinical_priority": 6,
            "field": "character",
        },
        {
            "id": "dizziness_associated",
            "question": "Are you also experiencing any of these?",
            "type": "multi_select",
            "options": [
                {"label": "Chest pain or palpitations", "value": "cardiac"},
                {"label": "Weakness on one side", "value": "weakness"},
                {"label": "Slurred speech", "value": "slurred_speech"},
                {"label": "Fainting", "value": "syncope"},
                {"label": "None of these", "value": "none"},
            ],
            "reason": "These combinations change how urgently dizziness should be evaluated.",
            "clinical_priority": 1,
            "field": "associated_symptoms",
        },
    ],
    "rash": [
        _duration_question("rash", "rash"),
        {
            "id": "rash_spreading",
            "question": "Is it spreading or getting worse?",
            "type": "yes_no",
            "reason": "A rapidly spreading rash, especially with other symptoms, may need urgent attention.",
            "clinical_priority": 8,
            "field": "spreading",
        },
        {
            "id": "rash_associated",
            "question": "Are you also experiencing any of these?",
            "type": "multi_select",
            "options": [
                {"label": "Fever", "value": "fever"},
                {"label": "Difficulty breathing or swallowing", "value": "airway"},
                {"label": "Facial/lip swelling", "value": "swelling"},
                {"label": "None of these", "value": "none"},
            ],
            "reason": "These combinations can indicate a severe allergic reaction.",
            "clinical_priority": 1,
            "field": "associated_symptoms",
        },
    ],
}

GENERIC_FOLLOW_UP: list[Question] = [
    {
        "id": "existing_conditions",
        "question": "Do you have any existing medical conditions I should know about?",
        "type": "text",
        "reason": "Existing conditions can change what these symptoms might mean.",
        "clinical_priority": 11,
        "field": "medical_history",
    },
    {
        "id": "current_medications",
        "question": "Are you currently taking any medications?",
        "type": "text",
        "reason": "Some medications can cause or worsen these symptoms, or interact with self-care options.",
        "clinical_priority": 12,
        "field": "medications",
    },
    {
        "id": "allergies",
        "question": "Do you have any known drug allergies?",
        "type": "text",
        "reason": "This is checked before any medication information is discussed.",
        "clinical_priority": 13,
        "field": "allergies",
    },
]


def get_question_set(question_set_key: str) -> list[Question]:
    return QUESTION_SETS.get(question_set_key, [])
