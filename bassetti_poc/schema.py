"""Fixed review schema and validation helpers."""

from __future__ import annotations

from copy import deepcopy


FIELD_ORDER = [
    "contact.name",
    "contact.email",
    "contact.phone",
    "location",
    "education",
    "work_experience",
    "skills",
    "languages",
]

FIELD_LABELS = {
    "contact.name": "Full name",
    "contact.email": "Email",
    "contact.phone": "Phone",
    "location": "Location",
    "education": "Education",
    "work_experience": "Work experience",
    "skills": "Skills",
    "languages": "Languages",
}

# For this POC, every schema group is required to be explicitly reviewed. A missing
# value can still be confirmed as "Not found"; confirmation means a human saw it.
REQUIRED_FIELDS = tuple(FIELD_ORDER)


def empty_result() -> dict:
    fields = {}
    for path in FIELD_ORDER:
        fields[path] = {
            "label": FIELD_LABELS[path],
            "value": [] if path in {"education", "work_experience", "skills", "languages"} else None,
            "display": "Not found",
            "evidence": [],
            "confidence": "low",
            "ambiguity": None,
            "review_status": "unreviewed",
        }
    return {
        "schema_version": "1.0",
        "fields": fields,
        "warnings": [],
        "source": {},
        "processing_ms": 0,
    }


def clone_result(result: dict) -> dict:
    return deepcopy(result)


def value_to_display(value) -> str:
    if value is None or value == "" or value == []:
        return "Not found"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        if all(isinstance(v, str) for v in value):
            return ", ".join(value) if value else "Not found"
        return f"{len(value)} item" + ("" if len(value) == 1 else "s")
    return str(value)


def export_payload(session: dict) -> dict:
    fields = session["result"]["fields"]
    return {
        "schema_version": session["result"]["schema_version"],
        "candidate": {
            "name": fields["contact.name"]["value"],
            "email": fields["contact.email"]["value"],
            "phone": fields["contact.phone"]["value"],
            "location": fields["location"]["value"],
        },
        "education": fields["education"]["value"],
        "work_experience": fields["work_experience"]["value"],
        "skills": fields["skills"]["value"],
        "languages": fields["languages"]["value"],
        "review": {
            "status": "human_approved",
            "approved_at": session.get("approved_at"),
            "session_id": session["id"],
            "disclaimer": "Human-reviewed information extraction only; no scoring, ranking, matching or rejection decision.",
        },
    }

