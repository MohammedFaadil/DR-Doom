"""
PDF consultation summary export (§39).

Explicitly NOT styled or titled to resemble an official prescription —
plain "Health Assessment Summary" document with clear disclaimer, per the
spec's instruction not to visually impersonate a physician's prescription.
"""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

BRAND_TEAL = colors.HexColor("#0F766E")
MUTED = colors.HexColor("#475569")

_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _clean_guidance_text(guidance: str) -> str:
    """Strip markdown formatting for plain-text PDF rendering, and drop the
    guidance's own appended "**Sources**" block — the PDF already renders a
    dedicated Sources section from evidence_consulted, so keeping both would
    just duplicate the citation list."""
    guidance = guidance.split("**Sources**")[0].split("Sources**")[0]
    guidance = _MD_LINK_RE.sub(r"\1", guidance)
    return guidance.replace("#", "").replace("*", "").strip()


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("BrandTitle", parent=styles["Title"], textColor=BRAND_TEAL, fontSize=20))
    styles.add(ParagraphStyle("SectionHeading", parent=styles["Heading2"], textColor=BRAND_TEAL, spaceBefore=14))
    styles.add(ParagraphStyle("Body", parent=styles["BodyText"], leading=15))
    styles.add(ParagraphStyle("Muted", parent=styles["BodyText"], textColor=MUTED, fontSize=9))
    return styles


def render_summary_pdf(summary: dict, conversation_title: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER, topMargin=0.75 * inch, bottomMargin=0.75 * inch, leftMargin=0.75 * inch, rightMargin=0.75 * inch
    )
    styles = _styles()
    story = []

    story.append(Paragraph("🩺 DR DOOM", styles["BrandTitle"]))
    story.append(Paragraph("Evidence-grounded health intelligence — Health Assessment Summary", styles["Muted"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", color=BRAND_TEAL, thickness=1))
    story.append(Spacer(1, 10))

    story.append(Paragraph(conversation_title, styles["Heading1"]))
    story.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Muted"],
        )
    )

    profile = summary.get("patient_profile", {})
    story.append(Paragraph("Patient Profile", styles["SectionHeading"]))
    story.append(
        Paragraph(
            f"Age: {profile.get('age') or 'Not provided'} &nbsp;&nbsp; "
            f"Sex: {profile.get('sex') or 'Not provided'} &nbsp;&nbsp; "
            f"Pregnancy status: {profile.get('pregnancy_status') or 'Not provided'}",
            styles["Body"],
        )
    )

    story.append(Paragraph("Primary Concern", styles["SectionHeading"]))
    story.append(Paragraph(summary.get("primary_concern") or "Not specified", styles["Body"]))

    story.append(Paragraph("Reported Symptoms", styles["SectionHeading"]))
    symptoms = summary.get("symptoms") or []
    story.append(Paragraph(", ".join(symptoms) if symptoms else "None recorded", styles["Body"]))
    story.append(
        Paragraph(
            f"Duration: {summary.get('duration') or 'Not provided'} &nbsp;&nbsp; "
            f"Severity: {summary.get('severity') or 'Not provided'}",
            styles["Body"],
        )
    )
    associated = summary.get("associated_symptoms") or []
    if associated:
        story.append(Paragraph(f"Associated symptoms: {', '.join(associated)}", styles["Body"]))

    for label, key in (("Relevant History", "relevant_history"), ("Medications", "medications"), ("Allergies", "allergies")):
        items = summary.get(key) or []
        story.append(Paragraph(label, styles["SectionHeading"]))
        story.append(Paragraph(", ".join(items) if items else "None recorded", styles["Body"]))

    story.append(Paragraph("Red Flags / Risk Level", styles["SectionHeading"]))
    red_flags = summary.get("red_flags") or []
    story.append(
        Paragraph(
            f"Risk level: <b>{(summary.get('risk_level') or 'unknown').upper()}</b> &nbsp;&nbsp; "
            f"Red flags noted: {', '.join(red_flags) if red_flags else 'None'}",
            styles["Body"],
        )
    )

    story.append(Paragraph("Evidence-Grounded Guidance", styles["SectionHeading"]))
    guidance = _clean_guidance_text(summary.get("guidance_provided") or "Not available")
    for para in guidance.split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), styles["Body"]))

    story.append(Paragraph("Recommended Next Step", styles["SectionHeading"]))
    story.append(Paragraph(summary.get("recommended_next_step") or "Consult a clinician.", styles["Body"]))

    evidence = summary.get("evidence_consulted") or []
    if evidence:
        story.append(Paragraph("Sources", styles["SectionHeading"]))
        for i, e in enumerate(evidence, 1):
            story.append(Paragraph(f"{i}. {e.get('organization')} — {e.get('title')} ({e.get('url')})", styles["Body"]))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", color=MUTED, thickness=0.5))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Disclaimer", styles["SectionHeading"]))
    story.append(Paragraph(summary.get("disclaimer", ""), styles["Muted"]))

    doc.build(story)
    return buffer.getvalue()
