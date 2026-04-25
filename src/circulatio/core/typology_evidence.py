from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Literal, cast

from ..domain.ids import now_iso
from ..domain.types import (
    AnalysisPacketSection,
    Id,
    MethodContextSnapshot,
    PacketFunctionDynamicsSummary,
    PsychologicalFunction,
    TypologyEvidenceDigest,
    TypologyLensSummary,
    TypologyMethodStateSummary,
    TypologyRoleEvidenceBucket,
)

_ROLE_BUCKETS = {
    "foreground": {"dominant", "auxiliary"},
    "compensation": {"inferior", "compensation_link"},
    "background": {"tertiary"},
}
_ALLOWED_FUNCTIONS = {"thinking", "feeling", "sensation", "intuition"}
_PROMPT_BIAS_MAP = {
    "sensation": "body_first",
    "intuition": "image_first",
    "feeling": "relational_first",
    "thinking": "reflection_first",
}
_PRACTICE_BIAS_MAP = {
    "sensation": "sensation_grounding",
    "intuition": "image_tracking",
    "feeling": "value_discernment",
    "thinking": "pattern_noting",
}


def build_typology_evidence_digest(
    *,
    payload: dict[str, object],
    method_context: MethodContextSnapshot | None,
) -> TypologyEvidenceDigest | None:
    memory = (
        payload.get("hermesMemoryContext")
        if isinstance(payload.get("hermesMemoryContext"), dict)
        else {}
    )
    raw_lens_summaries = memory.get("typologyLensSummaries") if isinstance(memory, dict) else []
    lens_summaries = [
        cast(TypologyLensSummary, deepcopy(item))
        for item in raw_lens_summaries or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    if not lens_summaries:
        return None

    active_lenses = [
        item for item in lens_summaries if str(item.get("status") or "") != "disconfirmed"
    ]
    buckets: dict[str, TypologyRoleEvidenceBucket] = {
        "foreground": {"functions": [], "lensIds": [], "evidenceIds": [], "linkedMaterialIds": []},
        "compensation": {
            "functions": [],
            "lensIds": [],
            "evidenceIds": [],
            "linkedMaterialIds": [],
        },
        "background": {"functions": [], "lensIds": [], "evidenceIds": [], "linkedMaterialIds": []},
    }

    for lens in active_lenses:
        bucket_name = _bucket_name(str(lens.get("role") or "").strip())
        bucket = buckets[bucket_name]
        lens_id = str(lens["id"])
        function = str(lens.get("function") or "").strip()
        bucket["lensIds"] = _merge_ids(bucket["lensIds"], [lens_id])
        if function in _ALLOWED_FUNCTIONS:
            bucket["functions"] = _merge_functions(
                bucket["functions"], [cast(PsychologicalFunction, function)]
            )
        bucket["evidenceIds"] = _merge_ids(
            bucket["evidenceIds"],
            [str(item) for item in lens.get("evidenceIds", []) if str(item).strip()],
        )
        bucket["linkedMaterialIds"] = _merge_ids(
            bucket["linkedMaterialIds"],
            [str(item) for item in lens.get("linkedMaterialIds", []) if str(item).strip()],
        )

    feedback_signal_count = sum(
        1
        for item in lens_summaries
        if str(item.get("status") or "").strip() in {"user_refined", "disconfirmed"}
    )
    evidenced_lens_count = sum(
        1
        for item in active_lenses
        if any(str(evidence_id).strip() for evidence_id in item.get("evidenceIds", []))
    )
    if evidenced_lens_count > 0 and active_lenses:
        status = "hypotheses_available"
    elif active_lenses or feedback_signal_count > 0:
        status = "signals_only"
    else:
        status = "insufficient_evidence"

    body_state_ids = _collect_ids(method_context, "recentBodyStates")
    practice_outcome_ids = _collect_ids(method_context, "recentPracticeSessions")
    individuation_context = (
        method_context.get("individuationContext") if isinstance(method_context, dict) else {}
    )
    relational_scene_ids = (
        _collect_nested_ids(individuation_context, "relationalScenes")
        if isinstance(individuation_context, dict)
        else []
    )
    counterevidence_ids = _merge_ids(
        [],
        [
            str(item)
            for lens in lens_summaries
            for item in lens.get("counterevidenceIds", [])
            if str(item).strip()
        ],
    )
    supporting_refs = _merge_ids(
        [],
        [lens_id for bucket in buckets.values() for lens_id in bucket.get("lensIds", [])],
    )
    supporting_refs = _merge_ids(supporting_refs, body_state_ids)
    supporting_refs = _merge_ids(supporting_refs, relational_scene_ids)
    supporting_refs = _merge_ids(supporting_refs, practice_outcome_ids)
    supporting_refs = _merge_ids(
        supporting_refs,
        [
            material_id
            for bucket in buckets.values()
            for material_id in bucket.get("linkedMaterialIds", [])
        ],
    )
    ambiguity_notes = _ambiguity_notes(lens_summaries, buckets, evidenced_lens_count)
    updated_at = max(
        str(item.get("lastUpdated") or item.get("updatedAt") or now_iso())
        for item in lens_summaries
    )
    return cast(
        TypologyEvidenceDigest,
        {
            "status": cast(object, status),
            "lensSummaries": lens_summaries,
            "foreground": buckets["foreground"],
            "compensation": buckets["compensation"],
            "background": buckets["background"],
            "supportingRefs": supporting_refs,
            "counterevidenceIds": counterevidence_ids,
            "bodyStateIds": body_state_ids,
            "relationalSceneIds": relational_scene_ids,
            "practiceOutcomeIds": practice_outcome_ids,
            "ambiguityNotes": ambiguity_notes,
            "evidencedLensCount": evidenced_lens_count,
            "feedbackSignalCount": feedback_signal_count,
            "updatedAt": updated_at,
        },
    )


def overlay_typology_method_state(
    current: TypologyMethodStateSummary | None,
    digest: TypologyEvidenceDigest | None,
) -> TypologyMethodStateSummary | None:
    if digest is None:
        return current
    summary: TypologyMethodStateSummary = cast(TypologyMethodStateSummary, deepcopy(current or {}))
    foreground = list(digest["foreground"].get("functions", []))
    compensation = list(digest["compensation"].get("functions", []))
    background = list(digest["background"].get("functions", []))
    active_functions = _merge_functions(_merge_functions(foreground, compensation), background)
    status_map = {
        "hypotheses_available": "candidate_available",
        "signals_only": "signals_only",
        "insufficient_evidence": "insufficient_evidence",
    }
    mapped_status: Literal["insufficient_evidence", "signals_only", "candidate_available"] = cast(
        Literal["insufficient_evidence", "signals_only", "candidate_available"],
        status_map[str(digest["status"])],
    )
    summary["status"] = mapped_status
    summary["activeLensIds"] = [
        str(item["id"])
        for item in digest["lensSummaries"]
        if str(item.get("status") or "").strip() != "disconfirmed"
    ][:5]
    summary["feedbackSignalCount"] = int(digest["feedbackSignalCount"])
    summary["activeFunctions"] = active_functions
    summary["foregroundFunctions"] = foreground
    summary["compensatoryFunctions"] = compensation
    summary["backgroundFunctions"] = background
    summary["supportingEvidenceIds"] = _merge_ids(
        [],
        [
            evidence_id
            for bucket in (
                digest["foreground"],
                digest["compensation"],
                digest["background"],
            )
            for evidence_id in bucket.get("evidenceIds", [])
        ],
    )
    summary["counterevidenceIds"] = list(digest["counterevidenceIds"])
    summary["ambiguityNotes"] = list(digest["ambiguityNotes"])
    summary["evidencedLensCount"] = int(digest["evidencedLensCount"])
    if "promptBias" not in summary:
        summary["promptBias"] = cast(
            object,
            _PROMPT_BIAS_MAP.get((compensation or foreground or [""])[0], "neutral"),
        )
    if "practiceBias" not in summary:
        summary["practiceBias"] = cast(
            object,
            _PRACTICE_BIAS_MAP.get((compensation or foreground or [""])[0], "neutral"),
        )
    if compensation and "balancingFunction" not in summary:
        summary["balancingFunction"] = compensation[0]
    if "confidence" not in summary:
        summary["confidence"] = "medium" if digest["evidencedLensCount"] > 0 else "low"
    if "caution" not in summary:
        summary["caution"] = "Typology remains tentative and should stay evidence-backed."
    summary["updatedAt"] = str(digest["updatedAt"])
    return summary


def render_typology_discovery_summary(digest: TypologyEvidenceDigest | None) -> str | None:
    if digest is None or str(digest["status"]) == "insufficient_evidence":
        return None
    fragments: list[str] = []
    foreground = _format_functions("Foreground", digest["foreground"].get("functions", []))
    compensation = _format_functions("Compensation", digest["compensation"].get("functions", []))
    background = _format_functions("Background", digest["background"].get("functions", []))
    for fragment in (foreground, compensation, background):
        if fragment:
            fragments.append(fragment)
    if digest["evidencedLensCount"] <= 0:
        fragments.append("These remain tentative signals rather than evidence-backed hypotheses.")
    if digest["ambiguityNotes"]:
        fragments.append(digest["ambiguityNotes"][0])
    return " ".join(fragments) or None


def build_typology_packet_fallback(
    digest: TypologyEvidenceDigest | None,
) -> tuple[AnalysisPacketSection | None, PacketFunctionDynamicsSummary | None]:
    if digest is None:
        return None, None
    foreground = list(digest["foreground"].get("functions", []))
    compensation = list(digest["compensation"].get("functions", []))
    background = list(digest["background"].get("functions", []))
    if str(digest["status"]) == "hypotheses_available" and (foreground or compensation):
        status = "readable"
    elif str(digest["status"]) == "signals_only" and (foreground or compensation or background):
        status = "signals_only"
    else:
        status = "insufficient_evidence"
    summary = _function_dynamics_summary(
        foreground=foreground,
        compensation=compensation,
        background=background,
        status=status,
        ambiguity_notes=list(digest["ambiguityNotes"]),
    )
    packet_status: Literal["insufficient_evidence", "signals_only", "readable"] = cast(
        Literal["insufficient_evidence", "signals_only", "readable"], status
    )
    packet_summary: PacketFunctionDynamicsSummary = {
        "status": packet_status,
        "summary": summary,
        "foregroundFunctions": foreground,
        "compensatoryFunctions": compensation,
        "backgroundFunctions": background,
        "ambiguityNotes": list(digest["ambiguityNotes"]),
        "supportingRefs": list(digest["supportingRefs"]),
    }
    if status == "insufficient_evidence":
        return None, packet_summary
    related_record_refs = [
        {"recordType": "TypologyLens", "recordId": lens_id}
        for lens_id in (
            digest["foreground"].get("lensIds", [])
            + digest["compensation"].get("lensIds", [])
            + digest["background"].get("lensIds", [])
        )
    ]
    items = []
    if foreground:
        items.append(
            {
                "label": "Foreground",
                "summary": (
                    f"Foreground pressure currently clusters around {', '.join(foreground)}."
                ),
                "evidenceIds": list(digest["foreground"].get("evidenceIds", [])),
                "relatedRecordRefs": related_record_refs,
            }
        )
    if compensation:
        items.append(
            {
                "label": "Compensation",
                "summary": (
                    f"Compensatory pressure currently clusters around {', '.join(compensation)}."
                ),
                "evidenceIds": list(digest["compensation"].get("evidenceIds", [])),
                "relatedRecordRefs": related_record_refs,
            }
        )
    if background:
        items.append(
            {
                "label": "Background",
                "summary": f"Background tone remains visible around {', '.join(background)}.",
                "evidenceIds": list(digest["background"].get("evidenceIds", [])),
                "relatedRecordRefs": related_record_refs,
            }
        )
    if digest["ambiguityNotes"]:
        items.append(
            {
                "label": "Ambiguity",
                "summary": digest["ambiguityNotes"][0],
                "evidenceIds": [],
                "relatedRecordRefs": related_record_refs,
            }
        )
    section = cast(
        AnalysisPacketSection,
        {
            "title": "Function dynamics",
            "purpose": "Hold typology function-dynamics in bounded, evidence-aware language.",
            "items": items,
        },
    )
    return section, packet_summary


def _bucket_name(role: str) -> str:
    for bucket_name, roles in _ROLE_BUCKETS.items():
        if role in roles:
            return bucket_name
    return "background"


def _collect_ids(method_context: MethodContextSnapshot | None, field_name: str) -> list[Id]:
    if not isinstance(method_context, dict):
        return []
    values = method_context.get(field_name)
    if not isinstance(values, list):
        return []
    return _merge_ids(
        [],
        [
            str(item.get("id"))
            for item in values
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        ],
    )


def _collect_nested_ids(container: Mapping[str, object], field_name: str) -> list[Id]:
    values = container.get(field_name)
    if not isinstance(values, list):
        return []
    return _merge_ids(
        [],
        [
            str(item.get("id"))
            for item in values
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        ],
    )


def _ambiguity_notes(
    lens_summaries: list[TypologyLensSummary],
    buckets: dict[str, TypologyRoleEvidenceBucket],
    evidenced_lens_count: int,
) -> list[str]:
    notes: list[str] = []
    for bucket_name, bucket in buckets.items():
        functions = bucket.get("functions", [])
        if len(functions) > 1:
            notes.append(f"Multiple {bucket_name} functions remain active in this window.")
    active_pairs = {
        (str(item.get("role") or "").strip(), str(item.get("function") or "").strip())
        for item in lens_summaries
        if str(item.get("status") or "").strip() != "disconfirmed"
    }
    if any(
        str(item.get("status") or "").strip() == "disconfirmed"
        and (
            str(item.get("role") or "").strip(),
            str(item.get("function") or "").strip(),
        )
        in active_pairs
        for item in lens_summaries
    ):
        notes.append("Active and disconfirmed typology signals are both present.")
    if evidenced_lens_count <= 0 and active_pairs:
        notes.append(
            "Existing typology lenses currently read more as user-confirmed "
            "signals than direct evidence."
        )
    return notes[:4]


def _format_functions(label: str, functions: list[PsychologicalFunction]) -> str:
    if not functions:
        return ""
    return f"{label}: {', '.join(functions)}."


def _function_dynamics_summary(
    *,
    foreground: list[PsychologicalFunction],
    compensation: list[PsychologicalFunction],
    background: list[PsychologicalFunction],
    status: str,
    ambiguity_notes: list[str],
) -> str:
    if status == "insufficient_evidence":
        return "Current window does not support a function-dynamics answer yet."
    fragments: list[str] = []
    if foreground:
        fragments.append(f"Foreground pressure leans toward {', '.join(foreground)}.")
    if compensation:
        fragments.append(f"Compensatory pressure leans toward {', '.join(compensation)}.")
    if background:
        fragments.append(f"Background support remains around {', '.join(background)}.")
    if status == "signals_only":
        fragments.append(
            "These remain provisional signals rather than settled evidence-backed hypotheses."
        )
    if ambiguity_notes:
        fragments.append(ambiguity_notes[0])
    return " ".join(fragments) or "Current function-dynamics signals remain tentative."


def _merge_ids(existing: list[Id], incoming: list[Id]) -> list[Id]:
    merged = list(existing)
    for item in incoming:
        if item and item not in merged:
            merged.append(item)
    return merged


def _merge_functions(
    existing: list[PsychologicalFunction],
    incoming: list[PsychologicalFunction],
) -> list[PsychologicalFunction]:
    merged = list(existing)
    for item in incoming:
        if item not in merged:
            merged.append(item)
    return merged
