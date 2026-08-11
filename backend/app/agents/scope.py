"""
Scope Agent — decides how to respond to input that isn't a symptom
assessment or a retrievable medical question.

Dr Doom is deliberately a *health* assistant grounded in a medical
knowledge base, so it must not answer arbitrary general-knowledge or
task requests by improvising — that's exactly the failure mode §90 forbids.
But flatly replying "I don't have enough evidence in my verified medical
knowledge base" to "hello" or "what can you do?" is a poor experience and
tells the user nothing.

So instead of one blunt refusal, input that retrieval can't serve is
triaged into intents that each get a genuinely useful, honest reply:
  greeting / smalltalk  -> friendly orientation + what to try next
  capability question   -> concrete description of what Dr Doom can do
  gratitude / closing   -> brief acknowledgement
  out_of_scope          -> clear statement of what it is and isn't, plus
                            a redirect, rather than pretending the medical
                            knowledge base was consulted and came up empty
  unknown medical topic -> the honest "not in my knowledge base" answer,
                            with concrete examples of covered topics
"""
from __future__ import annotations

import re

# Allows a short trailing address ("hello there", "hi doc") without
# swallowing an actual complaint ("hi I have a fever") — the trailing part
# is capped at a couple of words and must not contain clinical content.
GREETING_RE = re.compile(
    r"^\s*(hi+|hey+|hello+|yo|good\s+(morning|afternoon|evening)|greetings|namaste|salaam)"
    r"(\s+(there|doc|doctor|dr|dr\.?\s*doom|everyone|team))?\b[\s!.,]*$",
    re.I,
)
GRATITUDE_RE = re.compile(r"^\s*(thanks?|thank you|thx|ty|ok(ay)?|got it|cool|great|bye|goodbye)\b[\s!.,]*$", re.I)
CAPABILITY_RE = re.compile(
    r"\b(what can you do|who are you|what are you|how do you work|what do you do|help me|"
    r"your capabilities|can you help|how can you help|what is this)\b",
    re.I,
)
# Clearly non-medical task requests — answering these would mean operating
# entirely outside the knowledge base this product is built on.
OUT_OF_SCOPE_RE = re.compile(
    # `\w+\s+` repeats allow modifiers between the verb and the noun
    # ("write me a python script", "write a short funny poem").
    r"\b(write|code|build|debug)\s+(me\s+)?(a|an|some)?\s*(\w+\s+){0,3}"
    r"(code|program|script|app|essay|poem|story|email|song|blog|letter)\b"
    r"|\b(translate|calculate|solve for|stock price|who won|capital of|"
    r"recipe for|book a|flight|movie|tell me a joke|latest news)\b"
    r"|\bweather\b",
    re.I,
)

COVERED_TOPICS_HINT = (
    "fever, headache and migraine, cough and cold, sore throat, chest pain, breathing problems, "
    "stomach and digestive issues, back and joint pain, skin rashes, sleep and stress, "
    "and common medications"
)


def classify_scope(text: str) -> str:
    """Return one of: greeting | gratitude | capability | out_of_scope | medical."""
    stripped = (text or "").strip()
    if not stripped:
        return "greeting"
    if GREETING_RE.match(stripped):
        return "greeting"
    if GRATITUDE_RE.match(stripped):
        return "gratitude"
    if CAPABILITY_RE.search(stripped):
        return "capability"
    if OUT_OF_SCOPE_RE.search(stripped):
        return "out_of_scope"
    return "medical"


GREETING_MESSAGE = (
    "Hello — I'm Dr Doom, an evidence-grounded health assistant.\n\n"
    "Tell me what you're experiencing in your own words (for example, *\"I've had a sore throat "
    "for two days\"*), and I'll ask a few focused questions before giving you guidance backed by "
    "verified medical sources.\n\n"
    "You can also ask me a direct health question, like *\"what causes migraines?\"*"
)

CAPABILITY_MESSAGE = (
    "I'm Dr Doom — an evidence-grounded health information and triage assistant. Here's what I can do:\n\n"
    "- **Assess symptoms** — describe what you're feeling and I'll ask focused clinical questions "
    "one at a time, then give you a structured, cited assessment.\n"
    "- **Answer health questions** — every factual answer comes from my verified medical knowledge "
    "base, with clickable sources.\n"
    "- **Flag urgent situations** — I screen every message for emergency warning signs before "
    "anything else.\n"
    "- **Explain medications** — general information on common medicines, checked against your "
    "profile for allergies and other cautions.\n"
    "- **Save your consultations** — each one is summarised and stored so you can revisit or "
    "export it as a PDF.\n\n"
    f"My knowledge base currently covers {COVERED_TOPICS_HINT}.\n\n"
    "**What I can't do:** diagnose you, prescribe medication, or replace an examination by a "
    "qualified clinician."
)

GRATITUDE_MESSAGE = (
    "You're welcome. If anything changes or you'd like to look at another concern, just tell me "
    "what you're experiencing.\n\n"
    "Remember: if symptoms are severe, sudden, or getting worse, seek medical care rather than "
    "waiting."
)

OUT_OF_SCOPE_MESSAGE = (
    "That's outside what I can help with — I'm a health assistant, and I only answer from a "
    "verified medical knowledge base rather than improvising on general topics.\n\n"
    f"What I *can* help with: symptoms and health concerns ({COVERED_TOPICS_HINT}), and general "
    "information about common medications.\n\n"
    "What's going on with your health?"
)


def scope_message(scope: str) -> str:
    return {
        "greeting": GREETING_MESSAGE,
        "capability": CAPABILITY_MESSAGE,
        "gratitude": GRATITUDE_MESSAGE,
        "out_of_scope": OUT_OF_SCOPE_MESSAGE,
    }[scope]


def no_evidence_message(_query: str = "") -> str:
    """Honest 'not in my knowledge base' reply (§48) — but actionable,
    telling the user what IS covered instead of dead-ending."""
    return (
        "I don't have enough evidence in my verified medical knowledge base to answer that safely, "
        "and I won't guess on a health question.\n\n"
        f"My sources currently cover {COVERED_TOPICS_HINT}.\n\n"
        "You could try rephrasing it, ask about one of those areas, or describe the symptoms you're "
        "actually experiencing and I'll work through them with you."
    )
