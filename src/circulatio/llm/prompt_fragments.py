from __future__ import annotations

INTERPRETATION_APPROVAL_BOUNDARY = "Do not assume any proposal is already approved."
INTERPRETATION_EVIDENCE_POLICY = (
    "Use only material text, compact life context, method context, session context, and "
    "approved symbolic memory supplied here."
)
INTERPRETATION_STYLE_POLICY = (
    "Tentative, symbolic, non-diagnostic, and explicit about uncertainty. Keep "
    "userFacingResponse short and collaborative — usually one brief paragraph or one direct "
    "question."
)
INTERPRETATION_METHOD_POLICY = (
    "Use the provided method context, including any methodState and clarificationState "
    "summaries, to derive readiness, method gating, amplification prompts, dream-series "
    "suggestions, and practice structure inside the JSON response. If witnessState is "
    "present, treat it as the backend's current behavior contract for tone, pacing, blocked "
    "moves, and phrasing boundaries. Prefer LLM judgment over local heuristics, but stay "
    "within safety and evidence boundaries."
)
INTERPRETATION_RESPONSE_POLICY = (
    "When the user wants to go deeper, the userFacingResponse should invite associative work "
    "rather than explain symbolism. Keep it short, plain, and grounded in lived feeling. "
    "Prefer one real question and at most one brief reflection. Use everyday relational or "
    "bodily language the user can actually feel. Do not use unexplained Jungian jargon like "
    "anima, Great Mother, or archetype."
)
ACTION_DYNAMICS_POLICY = (
    "Action and relational dynamics come before or alongside symbolic decoding. In dreams, "
    "what the ego DOES (running, hiding, approaching, freezing, speaking) is often more "
    "revealing than what appears. In waking reflections, what the person did or felt pulled "
    "to do matters more than what the place or object 'means.' Always ask about the felt "
    "sense during the action, the body state, and the relational stance before offering "
    "symbolic labels. If the user ran from something, ask what running felt like and what "
    "standing still might have felt like. Do not reduce action to symbols (e.g., 'running "
    "means avoiding the unconscious'). Keep the action alive as a lived, bodily choice."
)
INTERPRETATION_REF_KEY_POLICY = (
    "Every symbol/figure/motif/lifeContext link must have a stable refKey that "
    "observations, hypotheses, proposalCandidates, and any evidence-backed dream-series "
    "suggestions reference via supportingRefs."
)
INTERPRETATION_SCHEMA_CONTRACT = (
    "Do not return narrative-only JSON. If userFacingResponse is non-empty, also populate "
    "grounded interpretive fields. If the material is too thin, keep interpretive arrays "
    "empty and use clarifyingQuestion instead of polished interpretation. A "
    "clarifyingQuestion with empty interpretive arrays is a valid first-pass response."
)
CLARIFICATION_ROUTING_POLICY = (
    "When you ask a clarifyingQuestion, also emit clarificationPlan with questionText, "
    "intent, captureTarget, expectedAnswerKind, and any supportingRefs or routingHints that "
    "make the question reusable. clarificationPlan should prefer capture targets that can "
    "route into durable typed records rather than answer_only."
)
CLARIFICATION_INTENT_POLICY = (
    "When you ask a clarifyingQuestion, also emit clarificationIntent with a stable refKey, "
    "expectedTargets, anchorRefs, consentScopes, storagePolicy, and expiresAt. "
    "clarificationIntent is routing metadata only, not a memory proposal."
)
WITNESS_METHOD_POLICY = (
    "Personal amplification comes before collective amplification. Dream-series suggestions "
    "are suggestions, not facts. Soma, goal, culture, and series continuity should be "
    "phrased as tentative co-occurrence unless the supplied context already confirms them."
)
INTERPRETATION_CONSENT_POLICY = (
    "Only suggest collective amplification or deeper imaginal work when the supplied "
    "consent and method context allow it. If a move is blocked, withhold it or ask consent "
    "instead of smuggling it into practice."
)
INTERPRETATION_SOURCE_POLICY = (
    "If trustedAmplificationSources are supplied, use them during collective amplification "
    "when helpful and method-allowed. Active cultural frames indicate which amplification "
    "lens may fit more strongly, but they do not force collective amplification. Some "
    "amplification will resonate and some will not; offer it as candidate resonance, not "
    "proof. Never claim to have read, quoted, or verified a source unless its contents are "
    "actually supplied in the input or evidence."
)
INTERPRETATION_PROPOSAL_POLICY = (
    "Produce fewer approval-gated proposals with clear supporting refs. Never use raw "
    "symbol-dictionary meanings or deterministic-sounding claims."
)
PROJECTION_HANDLING_POLICY = (
    "Treat relational scenes before projection claims, hold inner-outer correspondence "
    "non-causally, keep Self-orientation phenomenological, and keep archetypal language very "
    "tentative. If prerequisites or consent are missing, return empty individuation arrays "
    "instead of forcing symbolic depth."
)
TYPOLOGY_RESTRAINT_POLICY = (
    "Typology is always weak and evidence-backed here. Never use identity language, clamp "
    "typology confidence to low or medium, require userTestPrompt, and omit typology "
    "hypotheses that do not have supporting refs."
)
RUNTIME_HINT_POLICY = (
    "Treat communicationHints, interpretationHints, and practiceHints as derived runtime "
    "guidance only. Explicit preferences override learned policy. Safety and method gates "
    "override both."
)

WEEKLY_REVIEW_STYLE_POLICY = (
    "Keep longitudinal observations neutral, symbolic, and bounded by the supplied summaries."
)
WEEKLY_REVIEW_SIGNAL_POLICY = (
    "Treat longitudinal signals as co-occurrence material, not proof or causality."
)

LIFE_CONTEXT_GOAL = "Summarize only the individuation-relevant context Hermes already stores."
LIFE_CONTEXT_SOURCE_POLICY = "Use bounded summaries, not raw telemetry dumps."
LIFE_CONTEXT_SOURCE = "hermes-life-os"
LIFE_CONTEXT_EVENT_LIMIT = 5
LIFE_CONTEXT_CHANGE_LIMIT = 5

PRACTICE_STYLE_POLICY = (
    "Keep the witness language gentle, bounded, and easy to skip. If methodContextSnapshot."
    "witnessState is present, honor its tone, pacing, and avoided phrasing."
)
PRACTICE_DYNAMICS_POLICY = (
    "Return one bounded practice recommendation. The content must remain LLM-shaped rather "
    "than template-routed."
)
PRACTICE_CONSENT_POLICY = (
    "Do not push active imagination or somatic tracking when the supplied consent or method "
    "context blocks it."
)
PRACTICE_PACING_POLICY = (
    "Use derived practice hints as soft preference guidance except for explicit "
    "maxDurationMinutes, which is a hard ceiling. Explicit preferences override learned "
    "policy. Safety and method gates override both."
)

RHYTHMIC_BRIEF_STYLE_POLICY = (
    "Brief, witness-like, non-pressuring, and easy to ignore. If methodContextSnapshot."
    "witnessState is present, honor its tone, pacing, and avoided phrasing."
)
RHYTHMIC_BRIEF_POLICY = (
    "Surface one pattern without over-interpreting it. Prefer one suggested action or an "
    "explicit option to simply note it."
)
RHYTHMIC_BRIEF_CONSENT_POLICY = (
    "Do not smuggle deeper active imagination, shadow, or projection work into the brief "
    "when the supplied method context blocks it."
)

THRESHOLD_STYLE_POLICY = (
    "Hold liminal material carefully, pacing depth with grounding and evidence."
)
THRESHOLD_PROCESS_POLICY = (
    "Describe threshold processes as containers, not fixed stages. If grounding is weak, "
    "prefer pacing, containment, or grounding-first language."
)
THRESHOLD_CONSENT_POLICY = (
    "Do not intensify archetypal or projection language when consent or method readiness is "
    "missing."
)
THRESHOLD_PROPOSAL_POLICY = (
    "Threshold-derived durable writes remain approval-gated. If you emit proposalCandidates, "
    "supportingRefs must cite existing item ids from the payload so infrastructure can carry "
    "evidence without reinterpreting the result."
)

LIVING_MYTH_STYLE_POLICY = (
    "Weave longitudinal material into a collaborative life-chapter reading without turning "
    "it into identity or doctrine."
)
LIVING_MYTH_CHAPTER_POLICY = (
    "A life chapter is a provisional snapshot, not an essence, score, or permanent stage."
)
LIVING_MYTH_CONSENT_POLICY = (
    "If living myth synthesis feels too strong for the supplied consent or readiness, return "
    "lighter chapter/question material rather than forcing mythic closure."
)
LIVING_MYTH_PROPOSAL_POLICY = (
    "Durable chapter, contour, and wellbeing records remain approval-gated. If you emit "
    "proposalCandidates, supportingRefs must cite existing item ids from the payload so "
    "infrastructure can carry evidence without reinterpreting the result."
)

METHOD_STATE_EXTRACTION_POLICY = (
    "Extract only what the user actually said or clearly confirmed. Do not infer symbolic "
    "meaning, archetypal claims, or typology from tone or isolated wording."
)
METHOD_STATE_STORAGE_POLICY = (
    "This contract routes typed capture candidates only. Do not perform memory writes. "
    "Personal amplification is the user's own association, not dictionary meaning."
)
METHOD_STATE_CONSENT_POLICY = (
    "Projection hypotheses, inner-outer correspondence, typology, and other symbolic claims "
    "should become approval_proposal or withheld when consent or evidence is thin."
)
METHOD_STATE_CLARITY_POLICY = (
    "If the answer is too thin, return needs_clarification or followUpPrompts instead of "
    "polished certainty."
)

ANALYSIS_PACKET_STYLE_POLICY = (
    "Build a bounded packet that is legible for reflection, journaling, or analysis without "
    "pretending to replace the human encounter."
)
ANALYSIS_PACKET_POLICY = (
    "Prefer concise sections with evidence-grounded items. Do not dump raw material text or "
    "expand beyond what stayed alive in the window."
)
ANALYSIS_PACKET_BOUNDARY_POLICY = (
    "Package existing summaries and tensions. Do not invent new durable claims or a mythic "
    "master theory."
)
ANALYSIS_PACKET_PROVENANCE_POLICY = (
    "includedMaterialIds, includedRecordRefs, evidenceIds, and supportingRefs must cite "
    "existing ids from the payload only. Do not invent ids or derive metadata from free "
    "text."
)


def interpretation_instruction_block() -> dict[str, str]:
    return {
        "approvalBoundary": INTERPRETATION_APPROVAL_BOUNDARY,
        "evidencePolicy": INTERPRETATION_EVIDENCE_POLICY,
        "style": INTERPRETATION_STYLE_POLICY,
        "methodPolicy": INTERPRETATION_METHOD_POLICY,
        "responsePolicy": INTERPRETATION_RESPONSE_POLICY,
        "actionDynamicsPolicy": ACTION_DYNAMICS_POLICY,
        "refKeyPolicy": INTERPRETATION_REF_KEY_POLICY,
        "schemaContract": INTERPRETATION_SCHEMA_CONTRACT,
        "clarificationPlanPolicy": CLARIFICATION_ROUTING_POLICY,
        "clarificationIntentPolicy": CLARIFICATION_INTENT_POLICY,
        "witnessMethod": WITNESS_METHOD_POLICY,
        "consentPolicy": INTERPRETATION_CONSENT_POLICY,
        "sourcePolicy": INTERPRETATION_SOURCE_POLICY,
        "proposalPolicy": INTERPRETATION_PROPOSAL_POLICY,
        "individuationPolicy": PROJECTION_HANDLING_POLICY,
        "typologyPolicy": TYPOLOGY_RESTRAINT_POLICY,
        "adaptationPolicy": RUNTIME_HINT_POLICY,
    }


def weekly_review_instruction_block() -> dict[str, str]:
    return {
        "style": WEEKLY_REVIEW_STYLE_POLICY,
        "signalPolicy": WEEKLY_REVIEW_SIGNAL_POLICY,
    }


def life_context_instruction_block() -> dict[str, object]:
    return {
        "goal": LIFE_CONTEXT_GOAL,
        "sourcePolicy": LIFE_CONTEXT_SOURCE_POLICY,
        "eventLimit": LIFE_CONTEXT_EVENT_LIMIT,
        "changeLimit": LIFE_CONTEXT_CHANGE_LIMIT,
        "source": LIFE_CONTEXT_SOURCE,
    }


def practice_instruction_block() -> dict[str, str]:
    return {
        "style": PRACTICE_STYLE_POLICY,
        "practicePolicy": PRACTICE_DYNAMICS_POLICY,
        "consentPolicy": PRACTICE_CONSENT_POLICY,
        "adaptationPolicy": PRACTICE_PACING_POLICY,
    }


def rhythmic_brief_instruction_block() -> dict[str, str]:
    return {
        "style": RHYTHMIC_BRIEF_STYLE_POLICY,
        "briefPolicy": RHYTHMIC_BRIEF_POLICY,
        "consentPolicy": RHYTHMIC_BRIEF_CONSENT_POLICY,
    }


def threshold_review_instruction_block() -> dict[str, str]:
    return {
        "style": THRESHOLD_STYLE_POLICY,
        "thresholdPolicy": THRESHOLD_PROCESS_POLICY,
        "consentPolicy": THRESHOLD_CONSENT_POLICY,
        "proposalPolicy": THRESHOLD_PROPOSAL_POLICY,
    }


def living_myth_instruction_block() -> dict[str, str]:
    return {
        "style": LIVING_MYTH_STYLE_POLICY,
        "chapterPolicy": LIVING_MYTH_CHAPTER_POLICY,
        "consentPolicy": LIVING_MYTH_CONSENT_POLICY,
        "proposalPolicy": LIVING_MYTH_PROPOSAL_POLICY,
    }


def method_state_routing_instruction_block() -> dict[str, str]:
    return {
        "extractionPolicy": METHOD_STATE_EXTRACTION_POLICY,
        "storagePolicy": METHOD_STATE_STORAGE_POLICY,
        "consentPolicy": METHOD_STATE_CONSENT_POLICY,
        "clarityPolicy": METHOD_STATE_CLARITY_POLICY,
    }


def analysis_packet_instruction_block() -> dict[str, str]:
    return {
        "style": ANALYSIS_PACKET_STYLE_POLICY,
        "packetPolicy": ANALYSIS_PACKET_POLICY,
        "boundaryPolicy": ANALYSIS_PACKET_BOUNDARY_POLICY,
        "provenancePolicy": ANALYSIS_PACKET_PROVENANCE_POLICY,
    }


__all__ = [
    "ACTION_DYNAMICS_POLICY",
    "ANALYSIS_PACKET_BOUNDARY_POLICY",
    "ANALYSIS_PACKET_POLICY",
    "ANALYSIS_PACKET_PROVENANCE_POLICY",
    "ANALYSIS_PACKET_STYLE_POLICY",
    "CLARIFICATION_INTENT_POLICY",
    "CLARIFICATION_ROUTING_POLICY",
    "INTERPRETATION_APPROVAL_BOUNDARY",
    "INTERPRETATION_CONSENT_POLICY",
    "INTERPRETATION_EVIDENCE_POLICY",
    "INTERPRETATION_METHOD_POLICY",
    "INTERPRETATION_PROPOSAL_POLICY",
    "INTERPRETATION_REF_KEY_POLICY",
    "INTERPRETATION_RESPONSE_POLICY",
    "INTERPRETATION_SCHEMA_CONTRACT",
    "INTERPRETATION_SOURCE_POLICY",
    "INTERPRETATION_STYLE_POLICY",
    "LIFE_CONTEXT_CHANGE_LIMIT",
    "LIFE_CONTEXT_EVENT_LIMIT",
    "LIFE_CONTEXT_GOAL",
    "LIFE_CONTEXT_SOURCE",
    "LIFE_CONTEXT_SOURCE_POLICY",
    "LIVING_MYTH_CHAPTER_POLICY",
    "LIVING_MYTH_CONSENT_POLICY",
    "LIVING_MYTH_PROPOSAL_POLICY",
    "LIVING_MYTH_STYLE_POLICY",
    "METHOD_STATE_CLARITY_POLICY",
    "METHOD_STATE_CONSENT_POLICY",
    "METHOD_STATE_EXTRACTION_POLICY",
    "METHOD_STATE_STORAGE_POLICY",
    "PRACTICE_CONSENT_POLICY",
    "PRACTICE_DYNAMICS_POLICY",
    "PRACTICE_PACING_POLICY",
    "PRACTICE_STYLE_POLICY",
    "PROJECTION_HANDLING_POLICY",
    "RHYTHMIC_BRIEF_CONSENT_POLICY",
    "RHYTHMIC_BRIEF_POLICY",
    "RHYTHMIC_BRIEF_STYLE_POLICY",
    "RUNTIME_HINT_POLICY",
    "THRESHOLD_CONSENT_POLICY",
    "THRESHOLD_PROCESS_POLICY",
    "THRESHOLD_PROPOSAL_POLICY",
    "THRESHOLD_STYLE_POLICY",
    "TYPOLOGY_RESTRAINT_POLICY",
    "WEEKLY_REVIEW_SIGNAL_POLICY",
    "WEEKLY_REVIEW_STYLE_POLICY",
    "WITNESS_METHOD_POLICY",
    "analysis_packet_instruction_block",
    "interpretation_instruction_block",
    "life_context_instruction_block",
    "living_myth_instruction_block",
    "method_state_routing_instruction_block",
    "practice_instruction_block",
    "rhythmic_brief_instruction_block",
    "threshold_review_instruction_block",
    "weekly_review_instruction_block",
]
