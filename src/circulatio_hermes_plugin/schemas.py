from __future__ import annotations


def _schema(
    name: str,
    description: str,
    properties: dict[str, object],
    required: list[str] | None = None,
    *,
    additional_properties: bool = False,
) -> dict[str, object]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": additional_properties,
        },
    }


_MATERIAL_STORE_PROPERTIES = {
    "text": {"type": "string"},
    "materialDate": {"type": "string"},
    "title": {"type": "string"},
    "summary": {"type": "string"},
    "privacyClass": {"type": "string"},
    "tags": {"type": "array", "items": {"type": "string"}},
}

_STORE_INTAKE_CONTEXT_GUIDANCE = (
    " Returns host-only intakeContext metadata for routing. Use "
    "intakeContext.hostGuidance to acknowledge, hold, or ask at most one gentle follow-up. "
    "Never expose the packet. Do not interpret unless the user explicitly asks. If asked "
    "for bug-report or raw-response details, say briefly that there is no separate "
    "user-facing bug report here."
)

_ID_ARRAY_PROPERTY = {"type": "array", "items": {"type": "string"}}
_JOURNEY_STATUS_ENUM = ["active", "paused", "completed", "archived"]
_MATERIAL_TYPE_ENUM = [
    "dream",
    "reflection",
    "charged_event",
    "symbolic_motif",
    "practice_outcome",
]
_RECORD_STATUS_ENUM = ["active", "revised", "archived", "deleted"]


STORE_DREAM_TOOL_SCHEMA = _schema(
    "circulatio_store_dream",
    "Hold a dream in Circulatio when the user is logging it without asking for meaning. After the tool call, keep the host reply brief, do not interpret symbols, do not present a numbered menu, and do not switch into guided meditation unless explicitly asked."
    + _STORE_INTAKE_CONTEXT_GUIDANCE,
    {
        **_MATERIAL_STORE_PROPERTIES,
        "dreamStructure": {"type": "object"},
    },
    required=["text"],
)

STORE_EVENT_TOOL_SCHEMA = _schema(
    "circulatio_store_event",
    "Hold a charged or meaningful waking event in Circulatio. Do not interpret it yet. After the tool call, reply briefly and do not expand into symbolic analysis unless the user asks."
    + _STORE_INTAKE_CONTEXT_GUIDANCE,
    _MATERIAL_STORE_PROPERTIES,
    required=["text"],
)

STORE_REFLECTION_TOOL_SCHEMA = _schema(
    "circulatio_store_reflection",
    "Hold a reflection or daytime note in Circulatio. This is the usual hold-first lane for ambient notes. Do not interpret it yet. After the tool call, keep the reply short and invitational rather than analytical."
    + _STORE_INTAKE_CONTEXT_GUIDANCE,
    _MATERIAL_STORE_PROPERTIES,
    required=["text"],
)

STORE_SYMBOLIC_NOTE_TOOL_SCHEMA = _schema(
    "circulatio_store_symbolic_note",
    "Hold an image, motif, synchronicity, or symbolic note in Circulatio. Do not interpret it yet."
    + _STORE_INTAKE_CONTEXT_GUIDANCE,
    _MATERIAL_STORE_PROPERTIES,
    required=["text"],
)

STORE_BODY_STATE_TOOL_SCHEMA = _schema(
    "circulatio_store_body_state",
    "Hold a body state in Circulatio. If noteText is supplied, Circulatio also preserves the original phrase as a linked reflection tagged soma. Do not interpret it yet.",
    {
        "sensation": {"type": "string"},
        "observedAt": {"type": "string"},
        "bodyRegion": {"type": "string"},
        "activation": {"type": "string", "enum": ["low", "moderate", "high", "overwhelming"]},
        "tone": {"type": "string"},
        "temporalContext": {"type": "string"},
        "linkedGoalIds": {"type": "array", "items": {"type": "string"}},
        "privacyClass": {"type": "string"},
        "noteText": {"type": "string"},
    },
    required=["sensation"],
)

ALIVE_TODAY_TOOL_SCHEMA = _schema(
    "circulatio_alive_today",
    "Generate an on-demand, non-persistent weave across recent Circulatio material, body states, goals, symbols, patterns, and life context. Use this for questions like 'what is alive today?' or 'what does this seem connected to?'",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "explicitQuestion": {"type": "string"},
    },
)

QUERY_GRAPH_TOOL_SCHEMA = _schema(
    "circulatio_query_graph",
    "Query Circulatio's derived symbolic graph. Use this to inspect how materials, symbols, runs, body states, goals, dream series, and approved individuation records connect.",
    {
        "rootNodeIds": _ID_ARRAY_PROPERTY,
        "nodeTypes": {"type": "array", "items": {"type": "string"}},
        "edgeTypes": {"type": "array", "items": {"type": "string"}},
        "maxDepth": {"type": "integer"},
        "direction": {"type": "string", "enum": ["outbound", "inbound", "both"]},
        "includeEvidence": {"type": "boolean"},
        "limit": {"type": "integer"},
    },
)

MEMORY_KERNEL_TOOL_SCHEMA = _schema(
    "circulatio_memory_kernel",
    "Retrieve Circulatio memory-kernel items using keyword-ranked, provenance-bound retrieval. Use this for questions like 'what patterns involve chest tension?' or 'show recurring snake-related material.'",
    {
        "namespaces": {"type": "array", "items": {"type": "string"}},
        "relatedEntityIds": _ID_ARRAY_PROPERTY,
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "privacyClasses": {"type": "array", "items": {"type": "string"}},
        "textQuery": {"type": "string"},
        "rankingProfile": {
            "type": "string",
            "enum": ["default", "recency", "recurrence", "importance"],
        },
        "limit": {"type": "integer"},
    },
)

DASHBOARD_SUMMARY_TOOL_SCHEMA = _schema(
    "circulatio_dashboard_summary",
    "Load a lightweight Circulatio overview including recent materials, recurring symbols, active patterns, pending proposals, and the latest review or practice recommendation when present.",
    {},
)

DISCOVERY_TOOL_SCHEMA = _schema(
    "circulatio_discovery",
    "Build a bounded, read-only discovery digest from Circulatio dashboard, memory-kernel, and graph reads. This surface does not approve, reject, write, interpret, diagnose, or assign deterministic symbolic meanings.",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "explicitQuestion": {"type": "string"},
        "textQuery": {"type": "string"},
        "rootNodeIds": _ID_ARRAY_PROPERTY,
        "memoryNamespaces": {"type": "array", "items": {"type": "string"}},
        "rankingProfile": {
            "type": "string",
            "enum": ["default", "recency", "recurrence", "importance"],
        },
        "maxItems": {"type": "integer"},
    },
)

JOURNEY_PAGE_TOOL_SCHEMA = _schema(
    "circulatio_journey_page",
    "Build a read-mostly Journeying Host page from existing Circulatio context without approving memory, creating reviews, creating proactive briefs, or saving practice sessions.",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "explicitQuestion": {"type": "string"},
        "maxInvitations": {"type": "integer"},
        "includeAnalysisPacket": {"type": "boolean"},
    },
)

CREATE_JOURNEY_TOOL_SCHEMA = _schema(
    "circulatio_create_journey",
    "Create a durable journey container for an ongoing thread, recurring question, or returning process. This is an organizational write, not a symbolic truth claim.",
    {
        "label": {"type": "string"},
        "currentQuestion": {"type": "string"},
        "relatedMaterialIds": _ID_ARRAY_PROPERTY,
        "relatedSymbolIds": _ID_ARRAY_PROPERTY,
        "relatedPatternIds": _ID_ARRAY_PROPERTY,
        "relatedDreamSeriesIds": _ID_ARRAY_PROPERTY,
        "relatedGoalIds": _ID_ARRAY_PROPERTY,
        "nextReviewDueAt": {"type": "string"},
        "status": {"type": "string", "enum": _JOURNEY_STATUS_ENUM},
    },
    required=["label"],
)

LIST_JOURNEYS_TOOL_SCHEMA = _schema(
    "circulatio_list_journeys",
    "List existing journey containers. Use this to find active, paused, completed, or archived journeys without creating or interpreting anything.",
    {
        "statuses": {"type": "array", "items": {"type": "string"}},
        "includeDeleted": {"type": "boolean"},
        "limit": {"type": "integer"},
    },
)

GET_JOURNEY_TOOL_SCHEMA = _schema(
    "circulatio_get_journey",
    "Load one durable journey container by id or human label.",
    {
        "journeyId": {"type": "string"},
        "journeyLabel": {"type": "string"},
        "includeDeleted": {"type": "boolean"},
    },
)

UPDATE_JOURNEY_TOOL_SCHEMA = _schema(
    "circulatio_update_journey",
    "Update a durable journey container by id or human label, including renaming it, revising its current question, or merging and removing linked materials, symbols, patterns, dream series, and goals.",
    {
        "journeyId": {"type": "string"},
        "journeyLabel": {"type": "string"},
        "label": {"type": "string"},
        "currentQuestion": {"type": "string"},
        "addRelatedMaterialIds": _ID_ARRAY_PROPERTY,
        "removeRelatedMaterialIds": _ID_ARRAY_PROPERTY,
        "addRelatedSymbolIds": _ID_ARRAY_PROPERTY,
        "removeRelatedSymbolIds": _ID_ARRAY_PROPERTY,
        "addRelatedPatternIds": _ID_ARRAY_PROPERTY,
        "removeRelatedPatternIds": _ID_ARRAY_PROPERTY,
        "addRelatedDreamSeriesIds": _ID_ARRAY_PROPERTY,
        "removeRelatedDreamSeriesIds": _ID_ARRAY_PROPERTY,
        "addRelatedGoalIds": _ID_ARRAY_PROPERTY,
        "removeRelatedGoalIds": _ID_ARRAY_PROPERTY,
        "nextReviewDueAt": {"type": "string"},
    },
)

SET_JOURNEY_STATUS_TOOL_SCHEMA = _schema(
    "circulatio_set_journey_status",
    "Set a journey container status to active, paused, completed, or archived by id or human label. Use this for low-risk journey lifecycle management.",
    {
        "journeyId": {"type": "string"},
        "journeyLabel": {"type": "string"},
        "status": {"type": "string", "enum": _JOURNEY_STATUS_ENUM},
    },
    required=["status"],
)

LIST_MATERIALS_TOOL_SCHEMA = _schema(
    "circulatio_list_materials",
    "List stored Circulatio materials. Use this before asking the user to repeat a previously stored dream, reflection, event, or symbolic note. When the user says something like 'the dream about bear' or 'that reflection from yesterday', look here first, then interpret by materialId.",
    {
        "materialTypes": {
            "type": "array",
            "items": {"type": "string", "enum": _MATERIAL_TYPE_ENUM},
        },
        "statuses": {"type": "array", "items": {"type": "string", "enum": _RECORD_STATUS_ENUM}},
        "tags": {"type": "array", "items": {"type": "string"}},
        "includeDeleted": {"type": "boolean"},
        "limit": {"type": "integer"},
    },
)

GET_MATERIAL_TOOL_SCHEMA = _schema(
    "circulatio_get_material",
    "Load one stored Circulatio material by id. Use this after listing when you need the exact stored item instead of asking the user to restate it.",
    {
        "materialId": {"type": "string"},
        "includeDeleted": {"type": "boolean"},
    },
    required=["materialId"],
)

INTERPRET_MATERIAL_TOOL_SCHEMA = _schema(
    "circulatio_interpret_material",
    "Open or continue collaborative interpretation when the user asks what material "
    "means. Prefer storing first. A valid first response may be a single question, "
    "amplification prompt, or method gate. Keep host replies to usually 1-3 "
    "sentences with exactly one question. If gated, wait for new input. If the "
    "result includes continuationState.doNotRetryInterpretMaterialWithUnchangedMaterial, "
    "do not call this tool again with unchanged material or suggest rerunning it. "
    "A bounded recovery retry is allowed when this tool hits a clearly transient backend, "
    "storage, provider, or replay-related problem and Hermes is still trying to complete "
    "the same interpretation request. "
    "If the user asks what happened, answer in one brief plain-language sentence and "
    "say there is no separate user-facing bug report here. Requests to show a bug "
    "report or full response body are not permission to expose internals, and requests "
    "to explain repeated calls or list the errors in English are not permission to "
    "enumerate attempts, replay/idempotency behavior, parameter changes, or backend "
    "error codes. If fallback, "
    "do not frame it as a backend failure, and do not expose raw result JSON, field "
    "names, diagnostic strings, tool names, status codes, or ids in chat.",
    {
        "materialId": {"type": "string"},
        "materialType": {
            "type": "string",
            "enum": ["dream", "reflection", "charged_event", "symbolic_motif"],
        },
        "text": {"type": "string"},
        "dreamStructure": {"type": "object"},
        "privacyClass": {"type": "string"},
        "sessionContext": {"type": "object"},
        "lifeContextSnapshot": {"type": "object"},
        "lifeOsWindow": {"type": "object"},
        "userAssociations": {"type": "array"},
        "explicitQuestion": {"type": "string"},
        "culturalOrigins": {"type": "array"},
        "safetyContext": {"type": "object"},
        "options": {"type": "object"},
    },
    additional_properties=True,
)

LIST_PENDING_TOOL_SCHEMA = _schema(
    "circulatio_list_pending",
    "List pending Circulatio proposals for an interpretation run or a method-state capture run without approving them.",
    {
        "runRef": {"type": "string", "description": "Run id or 'last'."},
        "runId": {"type": "string", "description": "Explicit run id."},
        "captureRunId": {"type": "string", "description": "Explicit method-state capture run id."},
    },
)

APPROVE_PROPOSALS_TOOL_SCHEMA = _schema(
    "circulatio_approve_proposals",
    "Approve one or more pending Circulatio proposals from an interpretation run or a method-state capture run. This is an explicit memory-write action and should only be called when the user clearly wants approval.",
    {
        "runRef": {"type": "string", "description": "Run id or 'last'."},
        "runId": {"type": "string"},
        "captureRunId": {"type": "string"},
        "proposalRefs": {"type": "array", "items": {"type": "string"}},
        "note": {"type": "string"},
    },
    required=["proposalRefs"],
)

REJECT_PROPOSALS_TOOL_SCHEMA = _schema(
    "circulatio_reject_proposals",
    "Reject one or more pending Circulatio proposals from an interpretation run or a method-state capture run without writing them to symbolic memory.",
    {
        "runRef": {"type": "string", "description": "Run id or 'last'."},
        "runId": {"type": "string"},
        "captureRunId": {"type": "string"},
        "proposalRefs": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    required=["proposalRefs"],
)

REJECT_HYPOTHESES_TOOL_SCHEMA = _schema(
    "circulatio_reject_hypotheses",
    "Reject or refine hypotheses from a prior Circulatio run. This may suppress future reuse of those hypothesis claims but does not directly write symbolic memory entities.",
    {
        "runId": {"type": "string"},
        "feedbackByHypothesisId": {"type": "object"},
        "reason": {"type": "string"},
    },
    required=["runId", "feedbackByHypothesisId"],
)

REVISE_ENTITY_TOOL_SCHEMA = _schema(
    "circulatio_revise_entity",
    "Revise an existing Circulatio entity by explicit user request.",
    {
        "entityType": {"type": "string"},
        "entityId": {"type": "string"},
        "revisionNote": {"type": "string"},
        "replacement": {"type": "object"},
    },
    required=["entityType", "entityId", "revisionNote"],
)

DELETE_ENTITY_TOOL_SCHEMA = _schema(
    "circulatio_delete_entity",
    "Delete or tombstone an existing Circulatio entity by explicit user request.",
    {
        "entityType": {"type": "string"},
        "entityId": {"type": "string"},
        "mode": {"type": "string", "enum": ["tombstone", "erase"]},
        "reason": {"type": "string"},
    },
    required=["entityType", "entityId"],
)

SYMBOLS_LIST_TOOL_SCHEMA = _schema(
    "circulatio_symbols_list",
    "List saved Circulatio symbols for the current user.",
    {
        "limit": {"type": "integer"},
    },
)

SYMBOL_GET_TOOL_SCHEMA = _schema(
    "circulatio_symbol_get",
    "Load one Circulatio symbol by id or canonical name.",
    {
        "symbolId": {"type": "string"},
        "symbolName": {"type": "string"},
    },
)

SYMBOL_HISTORY_TOOL_SCHEMA = _schema(
    "circulatio_symbol_history",
    "Load one Circulatio symbol with its history and linked materials.",
    {
        "symbolId": {"type": "string"},
        "symbolName": {"type": "string"},
        "includeHistory": {"type": "boolean"},
    },
)

WEEKLY_REVIEW_TOOL_SCHEMA = _schema(
    "circulatio_weekly_review",
    "Generate a weekly Circulatio review for the requested window using approved symbolic memory and compact life context.",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
    },
    required=["windowStart", "windowEnd"],
)

THRESHOLD_REVIEW_TOOL_SCHEMA = _schema(
    "circulatio_threshold_review",
    "Generate a threshold review from approved individuation context. This is a workflow output, not a direct memory write.",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "thresholdProcessId": {"type": "string"},
        "explicitQuestion": {"type": "string"},
        "persist": {"type": "boolean"},
        "safetyContext": {"type": "object"},
    },
)

LIVING_MYTH_REVIEW_TOOL_SCHEMA = _schema(
    "circulatio_living_myth_review",
    "Generate a living myth review from approved symbolic material. Any durable writes remain approval-gated.",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "explicitQuestion": {"type": "string"},
        "persist": {"type": "boolean"},
        "safetyContext": {"type": "object"},
    },
)

ANALYSIS_PACKET_TOOL_SCHEMA = _schema(
    "circulatio_analysis_packet",
    "Generate a bounded analysis packet for journaling, reflection, or analysis use. This remains summary-only and evidence-bounded.",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "packetFocus": {
            "type": "string",
            "enum": ["analysis", "journaling", "therapy_session", "threshold", "dream_series"],
        },
        "explicitQuestion": {"type": "string"},
        "persist": {"type": "boolean"},
        "safetyContext": {"type": "object"},
    },
)

LIST_PENDING_REVIEW_PROPOSALS_TOOL_SCHEMA = _schema(
    "circulatio_list_pending_review_proposals",
    "List pending approval-gated proposals on a living myth or threshold review record.",
    {
        "reviewId": {"type": "string"},
    },
    required=["reviewId"],
)

APPROVE_REVIEW_PROPOSALS_TOOL_SCHEMA = _schema(
    "circulatio_approve_review_proposals",
    "Approve one or more pending proposals attached to a living myth or threshold review.",
    {
        "reviewId": {"type": "string"},
        "proposalRefs": {"type": "array", "items": {"type": "string"}},
    },
    required=["reviewId", "proposalRefs"],
)

REJECT_REVIEW_PROPOSALS_TOOL_SCHEMA = _schema(
    "circulatio_reject_review_proposals",
    "Reject one or more pending proposals attached to a living myth or threshold review.",
    {
        "reviewId": {"type": "string"},
        "proposalRefs": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    required=["reviewId", "proposalRefs"],
)

WITNESS_STATE_TOOL_SCHEMA = _schema(
    "circulatio_witness_state",
    "Load Circulatio's current witness-state context for a time window without running interpretation or persisting a review.",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "materialId": {"type": "string"},
    },
    required=["windowStart", "windowEnd"],
)

CAPTURE_CONSCIOUS_ATTITUDE_TOOL_SCHEMA = _schema(
    "circulatio_capture_conscious_attitude",
    "Store an explicit conscious-attitude snapshot supplied by the user or host runtime.",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "stanceSummary": {"type": "string"},
        "activeValues": {"type": "array", "items": {"type": "string"}},
        "activeConflicts": {"type": "array", "items": {"type": "string"}},
        "avoidedThemes": {"type": "array", "items": {"type": "string"}},
        "emotionalTone": {"type": "string"},
        "egoPosition": {"type": "string"},
        "confidence": {"type": "string"},
        "relatedMaterialIds": {"type": "array", "items": {"type": "string"}},
        "relatedGoalIds": {"type": "array", "items": {"type": "string"}},
        "privacyClass": {"type": "string"},
    },
    required=["windowStart", "windowEnd", "stanceSummary"],
)

CAPTURE_REALITY_ANCHORS_TOOL_SCHEMA = _schema(
    "circulatio_capture_reality_anchors",
    "Store explicit user-reported reality anchors directly as a durable individuation record.",
    {
        "label": {"type": "string"},
        "summary": {"type": "string"},
        "anchorSummary": {"type": "string"},
        "workDailyLifeContinuity": {"type": "string"},
        "sleepBodyRegulation": {"type": "string"},
        "relationshipContact": {"type": "string"},
        "reflectiveCapacity": {"type": "string"},
        "groundingRecommendation": {"type": "string"},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "relatedMaterialIds": {"type": "array", "items": {"type": "string"}},
        "relatedSymbolIds": {"type": "array", "items": {"type": "string"}},
        "relatedGoalIds": {"type": "array", "items": {"type": "string"}},
        "privacyClass": {"type": "string"},
    },
    required=[
        "summary",
        "anchorSummary",
        "workDailyLifeContinuity",
        "sleepBodyRegulation",
        "relationshipContact",
        "reflectiveCapacity",
        "groundingRecommendation",
    ],
)

UPSERT_THRESHOLD_PROCESS_TOOL_SCHEMA = _schema(
    "circulatio_upsert_threshold_process",
    "Create or update an explicit threshold-process record from user-provided material.",
    {
        "thresholdId": {"type": "string"},
        "label": {"type": "string"},
        "summary": {"type": "string"},
        "thresholdName": {"type": "string"},
        "phase": {"type": "string"},
        "whatIsEnding": {"type": "string"},
        "notYetBegun": {"type": "string"},
        "bodyCarrying": {"type": "string"},
        "groundingStatus": {"type": "string"},
        "symbolicLens": {"type": "string"},
        "invitationReadiness": {"type": "string"},
        "normalizedThresholdKey": {"type": "string"},
        "relatedMaterialIds": {"type": "array", "items": {"type": "string"}},
        "relatedSymbolIds": {"type": "array", "items": {"type": "string"}},
        "relatedGoalIds": {"type": "array", "items": {"type": "string"}},
        "relatedDreamSeriesIds": {"type": "array", "items": {"type": "string"}},
        "privacyClass": {"type": "string"},
    },
    required=[
        "summary",
        "thresholdName",
        "phase",
        "whatIsEnding",
        "notYetBegun",
        "groundingStatus",
        "invitationReadiness",
        "normalizedThresholdKey",
    ],
)

RECORD_RELATIONAL_SCENE_TOOL_SCHEMA = _schema(
    "circulatio_record_relational_scene",
    "Store or merge a user-reported relational scene directly as a durable individuation record.",
    {
        "sceneId": {"type": "string"},
        "label": {"type": "string"},
        "summary": {"type": "string"},
        "sceneSummary": {"type": "string"},
        "chargedRoles": {"type": "array", "items": {"type": "object"}},
        "recurringAffect": {"type": "array", "items": {"type": "string"}},
        "recurrenceContexts": {"type": "array", "items": {"type": "string"}},
        "normalizedSceneKey": {"type": "string"},
        "relatedMaterialIds": {"type": "array", "items": {"type": "string"}},
        "relatedGoalIds": {"type": "array", "items": {"type": "string"}},
        "privacyClass": {"type": "string"},
    },
    required=["summary", "sceneSummary", "normalizedSceneKey"],
)

RECORD_INNER_OUTER_CORRESPONDENCE_TOOL_SCHEMA = _schema(
    "circulatio_record_inner_outer_correspondence",
    "Store or merge an explicit inner / outer correspondence without making causal claims.",
    {
        "correspondenceId": {"type": "string"},
        "label": {"type": "string"},
        "summary": {"type": "string"},
        "correspondenceSummary": {"type": "string"},
        "innerRefs": {"type": "array", "items": {"type": "string"}},
        "outerRefs": {"type": "array", "items": {"type": "string"}},
        "symbolIds": {"type": "array", "items": {"type": "string"}},
        "userCharge": {"type": "string"},
        "caveat": {"type": "string"},
        "normalizedCorrespondenceKey": {"type": "string"},
        "privacyClass": {"type": "string"},
    },
    required=[
        "summary",
        "correspondenceSummary",
        "userCharge",
        "caveat",
        "normalizedCorrespondenceKey",
    ],
)

RECORD_NUMINOUS_ENCOUNTER_TOOL_SCHEMA = _schema(
    "circulatio_record_numinous_encounter",
    "Store a user-reported numinous encounter as a durable record without forcing interpretation.",
    {
        "label": {"type": "string"},
        "summary": {"type": "string"},
        "encounterMedium": {"type": "string"},
        "affectTone": {"type": "string"},
        "containmentNeed": {"type": "string"},
        "interpretationConstraint": {"type": "string"},
        "relatedMaterialIds": {"type": "array", "items": {"type": "string"}},
        "relatedSymbolIds": {"type": "array", "items": {"type": "string"}},
        "privacyClass": {"type": "string"},
    },
    required=[
        "summary",
        "encounterMedium",
        "affectTone",
        "containmentNeed",
        "interpretationConstraint",
    ],
)

RECORD_AESTHETIC_RESONANCE_TOOL_SCHEMA = _schema(
    "circulatio_record_aesthetic_resonance",
    "Store a user-reported aesthetic resonance as a durable individuation record.",
    {
        "label": {"type": "string"},
        "summary": {"type": "string"},
        "medium": {"type": "string"},
        "objectDescription": {"type": "string"},
        "resonanceSummary": {"type": "string"},
        "feelingTone": {"type": "string"},
        "bodySensations": {"type": "array", "items": {"type": "string"}},
        "relatedMaterialIds": {"type": "array", "items": {"type": "string"}},
        "relatedSymbolIds": {"type": "array", "items": {"type": "string"}},
        "privacyClass": {"type": "string"},
    },
    required=["summary", "medium", "objectDescription", "resonanceSummary"],
)

SET_CONSENT_TOOL_SCHEMA = _schema(
    "circulatio_set_consent",
    "Set an explicit Circulatio consent/readiness preference for a witness-method scope.",
    {
        "scope": {"type": "string"},
        "status": {"type": "string"},
        "note": {"type": "string"},
        "source": {"type": "string"},
    },
    required=["scope", "status"],
)

ANSWER_AMPLIFICATION_TOOL_SCHEMA = _schema(
    "circulatio_answer_amplification",
    "Answer a pending amplification prompt or store a direct personal amplification. "
    "Use this only when Hermes has a pending amplification prompt or already knows "
    "canonicalName and surfaceText. Do not use it for generic fallback questions.",
    {
        "promptId": {"type": "string"},
        "materialId": {"type": "string"},
        "runId": {"type": "string"},
        "symbolId": {"type": "string"},
        "canonicalName": {"type": "string"},
        "surfaceText": {"type": "string"},
        "associationText": {"type": "string"},
        "feelingTone": {"type": "string"},
        "bodySensations": {"type": "array", "items": {"type": "string"}},
        "memoryRefs": {"type": "array", "items": {"type": "string"}},
        "privacyClass": {"type": "string"},
    },
    required=["canonicalName", "surfaceText", "associationText"],
)

METHOD_STATE_RESPOND_TOOL_SCHEMA = _schema(
    "circulatio_method_state_respond",
    "Process a context-bound follow-up response through Circulatio's method-state connector. Use this only when Hermes already knows the answer belongs to a prior Circulatio context such as a clarifying question, amplification prompt, body note, goal feedback, practice feedback, or other anchored follow-up. For context-only fallback clarification answers, call this once to record the answer, then stop. A no_capture result with continuationState.nextAction = await_user_input is not a reason to retry interpretation or suggest rerunning unchanged material. If asked what happened, say briefly that there is no separate user-facing bug report here. Do not use it as a generic capture-any intake, and do not expose raw continuationState, warning JSON, tool names, status codes, or ids in chat.",
    {
        "responseText": {"type": "string"},
        "source": {
            "type": "string",
            "enum": [
                "clarifying_answer",
                "freeform_followup",
                "body_note",
                "amplification_answer",
                "relational_scene",
                "dream_dynamics",
                "goal_feedback",
                "practice_feedback",
                "consent_update",
            ],
        },
        "anchorRefs": {
            "type": "object",
            "properties": {
                "materialId": {"type": "string"},
                "runId": {"type": "string"},
                "promptId": {"type": "string"},
                "clarificationRefKey": {"type": "string"},
                "practiceSessionId": {"type": "string"},
                "briefId": {"type": "string"},
                "reviewId": {"type": "string"},
                "goalId": {"type": "string"},
                "journeyId": {"type": "string"},
                "coachLoopKey": {"type": "string"},
                "coachMoveId": {"type": "string"},
                "resourceInvitationId": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "expectedTargets": {"type": "array", "items": {"type": "string"}},
        "observedAt": {"type": "string"},
        "privacyClass": {"type": "string"},
        "sessionContext": {"type": "object"},
        "lifeContextSnapshot": {"type": "object"},
        "safetyContext": {"type": "object"},
        "options": {"type": "object"},
    },
    required=["responseText", "source"],
)

UPSERT_GOAL_TOOL_SCHEMA = _schema(
    "circulatio_upsert_goal",
    "Create or update an explicit goal record in Circulatio.",
    {
        "goalId": {"type": "string"},
        "label": {"type": "string"},
        "description": {"type": "string"},
        "status": {"type": "string"},
        "valueTags": {"type": "array", "items": {"type": "string"}},
        "linkedMaterialIds": {"type": "array", "items": {"type": "string"}},
        "linkedSymbolIds": {"type": "array", "items": {"type": "string"}},
    },
    required=["label"],
)

UPSERT_GOAL_TENSION_TOOL_SCHEMA = _schema(
    "circulatio_upsert_goal_tension",
    "Create or update an explicit goal-tension record in Circulatio.",
    {
        "tensionId": {"type": "string"},
        "goalIds": {"type": "array", "items": {"type": "string"}},
        "tensionSummary": {"type": "string"},
        "polarityLabels": {"type": "array", "items": {"type": "string"}},
        "evidenceIds": {"type": "array", "items": {"type": "string"}},
        "status": {"type": "string"},
    },
    required=["goalIds", "tensionSummary"],
)

SET_CULTURAL_FRAME_TOOL_SCHEMA = _schema(
    "circulatio_set_cultural_frame",
    "Create or update an explicit cultural frame preference in Circulatio.",
    {
        "culturalFrameId": {"type": "string"},
        "label": {"type": "string"},
        "type": {"type": "string"},
        "allowedUses": {"type": "array", "items": {"type": "string"}},
        "avoidUses": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
        "status": {"type": "string"},
    },
    required=["label"],
)

GENERATE_PRACTICE_TOOL_SCHEMA = _schema(
    "circulatio_generate_practice_recommendation",
    "Generate a bounded LLM-shaped practice recommendation from recent Circulatio context. Safety and consent gates still apply. This generates the recommendation only; response recording stays in circulatio_respond_practice_recommendation.",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "trigger": {"type": "object"},
        "sessionContext": {"type": "object"},
        "explicitQuestion": {"type": "string"},
        "safetyContext": {"type": "object"},
        "options": {"type": "object"},
        "persist": {"type": "boolean"},
    },
)

RESPOND_PRACTICE_TOOL_SCHEMA = _schema(
    "circulatio_respond_practice_recommendation",
    "Accept or skip a previously recommended Circulatio practice.",
    {
        "practiceSessionId": {"type": "string"},
        "action": {"type": "string", "enum": ["accepted", "skipped"]},
        "note": {"type": "string"},
        "activationBefore": {"type": "string", "enum": ["low", "moderate", "high"]},
    },
    required=["practiceSessionId", "action"],
)

RECORD_INTERPRETATION_FEEDBACK_TOOL_SCHEMA = _schema(
    "circulatio_record_interpretation_feedback",
    "Record explicit user feedback on a Circulatio interpretation run without parsing free-text notes.",
    {
        "runId": {"type": "string"},
        "feedback": {
            "type": "string",
            "enum": [
                "too_much",
                "too_vague",
                "too_abstract",
                "good_level",
                "helpful",
                "not_helpful",
            ],
        },
        "note": {"type": "string"},
        "locale": {"type": "string"},
    },
    required=["runId", "feedback"],
)

RECORD_PRACTICE_FEEDBACK_TOOL_SCHEMA = _schema(
    "circulatio_record_practice_feedback",
    "Record explicit user feedback on a Circulatio practice recommendation or completed practice without parsing free-text notes.",
    {
        "practiceSessionId": {"type": "string"},
        "feedback": {
            "type": "string",
            "enum": [
                "good_fit",
                "not_for_me",
                "too_intense",
                "too_long",
                "helpful",
                "not_helpful",
            ],
        },
        "note": {"type": "string"},
        "locale": {"type": "string"},
    },
    required=["practiceSessionId", "feedback"],
)

GENERATE_RHYTHMIC_BRIEFS_TOOL_SCHEMA = _schema(
    "circulatio_generate_rhythmic_briefs",
    "Generate due rhythmic brief candidates for the current user.",
    {
        "windowStart": {"type": "string"},
        "windowEnd": {"type": "string"},
        "source": {"type": "string", "enum": ["manual", "scheduled"]},
        "limit": {"type": "integer"},
        "safetyContext": {"type": "object"},
    },
)

RESPOND_RHYTHMIC_BRIEF_TOOL_SCHEMA = _schema(
    "circulatio_respond_rhythmic_brief",
    "Mark a rhythmic brief as shown, dismissed, acted on, or deleted.",
    {
        "briefId": {"type": "string"},
        "action": {"type": "string", "enum": ["shown", "dismissed", "acted_on", "deleted"]},
        "note": {"type": "string"},
    },
    required=["briefId", "action"],
)

TOOL_SCHEMAS = [
    STORE_DREAM_TOOL_SCHEMA,
    STORE_EVENT_TOOL_SCHEMA,
    STORE_REFLECTION_TOOL_SCHEMA,
    STORE_SYMBOLIC_NOTE_TOOL_SCHEMA,
    STORE_BODY_STATE_TOOL_SCHEMA,
    ALIVE_TODAY_TOOL_SCHEMA,
    QUERY_GRAPH_TOOL_SCHEMA,
    MEMORY_KERNEL_TOOL_SCHEMA,
    DASHBOARD_SUMMARY_TOOL_SCHEMA,
    DISCOVERY_TOOL_SCHEMA,
    JOURNEY_PAGE_TOOL_SCHEMA,
    CREATE_JOURNEY_TOOL_SCHEMA,
    LIST_JOURNEYS_TOOL_SCHEMA,
    GET_JOURNEY_TOOL_SCHEMA,
    UPDATE_JOURNEY_TOOL_SCHEMA,
    SET_JOURNEY_STATUS_TOOL_SCHEMA,
    LIST_MATERIALS_TOOL_SCHEMA,
    GET_MATERIAL_TOOL_SCHEMA,
    INTERPRET_MATERIAL_TOOL_SCHEMA,
    LIST_PENDING_TOOL_SCHEMA,
    APPROVE_PROPOSALS_TOOL_SCHEMA,
    REJECT_PROPOSALS_TOOL_SCHEMA,
    REJECT_HYPOTHESES_TOOL_SCHEMA,
    REVISE_ENTITY_TOOL_SCHEMA,
    DELETE_ENTITY_TOOL_SCHEMA,
    SYMBOLS_LIST_TOOL_SCHEMA,
    SYMBOL_GET_TOOL_SCHEMA,
    SYMBOL_HISTORY_TOOL_SCHEMA,
    WEEKLY_REVIEW_TOOL_SCHEMA,
    THRESHOLD_REVIEW_TOOL_SCHEMA,
    LIVING_MYTH_REVIEW_TOOL_SCHEMA,
    ANALYSIS_PACKET_TOOL_SCHEMA,
    LIST_PENDING_REVIEW_PROPOSALS_TOOL_SCHEMA,
    APPROVE_REVIEW_PROPOSALS_TOOL_SCHEMA,
    REJECT_REVIEW_PROPOSALS_TOOL_SCHEMA,
    WITNESS_STATE_TOOL_SCHEMA,
    CAPTURE_CONSCIOUS_ATTITUDE_TOOL_SCHEMA,
    CAPTURE_REALITY_ANCHORS_TOOL_SCHEMA,
    UPSERT_THRESHOLD_PROCESS_TOOL_SCHEMA,
    RECORD_RELATIONAL_SCENE_TOOL_SCHEMA,
    RECORD_INNER_OUTER_CORRESPONDENCE_TOOL_SCHEMA,
    RECORD_NUMINOUS_ENCOUNTER_TOOL_SCHEMA,
    RECORD_AESTHETIC_RESONANCE_TOOL_SCHEMA,
    SET_CONSENT_TOOL_SCHEMA,
    ANSWER_AMPLIFICATION_TOOL_SCHEMA,
    METHOD_STATE_RESPOND_TOOL_SCHEMA,
    UPSERT_GOAL_TOOL_SCHEMA,
    UPSERT_GOAL_TENSION_TOOL_SCHEMA,
    SET_CULTURAL_FRAME_TOOL_SCHEMA,
    GENERATE_PRACTICE_TOOL_SCHEMA,
    RESPOND_PRACTICE_TOOL_SCHEMA,
    RECORD_INTERPRETATION_FEEDBACK_TOOL_SCHEMA,
    RECORD_PRACTICE_FEEDBACK_TOOL_SCHEMA,
    GENERATE_RHYTHMIC_BRIEFS_TOOL_SCHEMA,
    RESPOND_RHYTHMIC_BRIEF_TOOL_SCHEMA,
]
