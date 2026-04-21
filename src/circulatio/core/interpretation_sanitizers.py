from __future__ import annotations


def truncate_text(value: object, limit: int) -> str:
    text = str(value or "").strip()
    return text[:limit]


def clamp_float(value: object, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def sanitize_confidence(value: object) -> str:
    confidence = str(value).strip()
    return confidence if confidence in {"low", "medium", "high"} else "low"


def sanitize_phrasing_policy(value: object) -> str:
    phrasing_policy = str(value).strip()
    return (
        phrasing_policy if phrasing_policy in {"tentative", "very_tentative"} else "very_tentative"
    )


def sanitize_symbol_category(value: object) -> str:
    category = str(value).strip()
    return (
        category
        if category
        in {
            "animal",
            "element",
            "place",
            "object",
            "figure",
            "body",
            "movement",
            "color",
            "threshold",
            "unknown",
        }
        else "unknown"
    )


def sanitize_figure_role(value: object) -> str:
    role = str(value).strip()
    return (
        role
        if role in {"family", "authority", "child", "stranger", "elder", "shadow_like", "unknown"}
        else "unknown"
    )


def sanitize_motif_type(value: object) -> str:
    motif_type = str(value).strip()
    return (
        motif_type
        if motif_type
        in {
            "threshold",
            "descent",
            "containment",
            "flooding",
            "pursuit",
            "authority_pressure",
            "body_sensation",
        }
        else "threshold"
    )


def sanitize_hypothesis_type(value: object) -> str | None:
    hypothesis_type = str(value).strip()
    return (
        hypothesis_type
        if hypothesis_type
        in {"compensation", "complex_candidate", "symbol_meaning", "practice_need", "theme"}
        else None
    )


def sanitize_practice_type(value: object) -> str:
    allowed = {
        "grounding",
        "journaling",
        "passive_imagination",
        "brief_meditation",
        "none",
        "active_imagination",
        "somatic_tracking",
        "shadow_dialogue",
        "image_dialogue",
        "body_checkin",
        "amplification_journaling",
    }
    practice_type = str(value).strip()
    return practice_type if practice_type in allowed else "journaling"


def sanitize_duration(value: object) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return 8
    return max(1, min(duration, 30))


def locate_text_span(text: str, surface_text: str) -> dict[str, int]:
    index = text.lower().find(surface_text.lower())
    if index < 0:
        index = 0
        return {"start": index, "end": min(len(text), max(len(surface_text), 1))}
    return {"start": index, "end": index + len(surface_text)}
