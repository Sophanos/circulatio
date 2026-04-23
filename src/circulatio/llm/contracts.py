from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict


class LlmSymbolCandidate(TypedDict, total=False):
    refKey: Required[str]
    surfaceText: Required[str]
    canonicalName: Required[str]
    category: Required[str]
    salience: Required[float]
    tone: NotRequired[str]


class LlmFigureCandidate(TypedDict, total=False):
    refKey: Required[str]
    surfaceText: Required[str]
    label: Required[str]
    role: Required[str]
    salience: Required[float]


class LlmMotifCandidate(TypedDict, total=False):
    refKey: Required[str]
    surfaceText: Required[str]
    canonicalName: Required[str]
    motifType: Required[str]
    salience: Required[float]


class LlmLifeContextLinkCandidate(TypedDict, total=False):
    refKey: Required[str]
    summary: Required[str]
    lifeEventRefId: NotRequired[str]
    stateSnapshotField: NotRequired[str]


class LlmObservationCandidate(TypedDict, total=False):
    kind: Required[str]
    statement: Required[str]
    supportingRefs: Required[list[str]]


class LlmHypothesisCandidate(TypedDict, total=False):
    claim: Required[str]
    hypothesisType: Required[str]
    confidence: Required[str]
    supportingRefs: Required[list[str]]
    counterRefs: NotRequired[list[str]]
    userTestPrompt: Required[str]
    phrasingPolicy: Required[str]


class LlmPracticeCandidate(TypedDict, total=False):
    type: Required[str]
    target: NotRequired[str]
    reason: Required[str]
    durationMinutes: Required[int]
    instructions: Required[list[str]]
    requiresConsent: Required[bool]
    templateId: NotRequired[str]
    modality: NotRequired[str]
    intensity: NotRequired[str]
    script: NotRequired[list[dict[str, object]]]
    followUpPrompt: NotRequired[str]
    adaptationNotes: NotRequired[list[str]]


class LlmProposalCandidate(TypedDict, total=False):
    action: Required[str]
    entityType: Required[str]
    payload: Required[dict[str, object]]
    reason: Required[str]
    supportingRefs: Required[list[str]]


class LlmDepthReadinessCandidate(TypedDict, total=False):
    status: Required[str]
    allowedMoves: Required[dict[str, str]]
    reasons: Required[list[str]]
    requiredUserAction: NotRequired[str]
    evidenceRefs: NotRequired[list[str]]


class LlmMethodGateCandidate(TypedDict, total=False):
    depthLevel: Required[str]
    missingPrerequisites: Required[list[str]]
    blockedMoves: Required[list[str]]
    requiredPrompts: Required[list[str]]
    responseConstraints: Required[list[str]]


class LlmAmplificationPromptCandidate(TypedDict, total=False):
    symbolRefKey: NotRequired[str]
    symbolMentionRefKey: NotRequired[str]
    canonicalName: Required[str]
    surfaceText: Required[str]
    promptText: Required[str]
    reason: Required[str]


class LlmDreamSeriesSuggestionCandidate(TypedDict, total=False):
    seriesId: NotRequired[str]
    label: Required[str]
    matchScore: Required[float]
    matchingFeatures: Required[list[str]]
    narrativeRole: Required[str]
    confidence: Required[str]
    ambiguityNote: NotRequired[str]
    supportingRefs: NotRequired[list[str]]
    egoStance: NotRequired[str]
    lysisSummary: NotRequired[str]
    progressionSummary: NotRequired[str]
    compensationTrajectory: NotRequired[str]


class LlmTypologySignalCandidate(TypedDict, total=False):
    id: NotRequired[str]
    category: Required[str]
    function: Required[str]
    orientation: Required[str]
    statement: Required[str]
    strength: Required[str]
    evidenceIds: Required[list[str]]


class LlmTypologyHypothesisCandidate(TypedDict, total=False):
    id: NotRequired[str]
    claim: Required[str]
    role: Required[str]
    function: Required[str]
    confidence: Required[str]
    evidenceIds: Required[list[str]]
    counterevidenceIds: NotRequired[list[str]]
    userTestPrompt: Required[str]
    normalizedClaimKey: NotRequired[str]


class LlmTypologyAssessmentCandidate(TypedDict, total=False):
    status: Required[str]
    typologySignals: NotRequired[list[LlmTypologySignalCandidate]]
    typologyHypotheses: NotRequired[list[LlmTypologyHypothesisCandidate]]
    possibleDominantFunction: NotRequired[str]
    possibleAuxiliaryFunction: NotRequired[str]
    possibleInferiorFunction: NotRequired[str]
    compensationLink: NotRequired[str]
    userTestPrompt: NotRequired[str]


class LlmClarificationIntent(TypedDict, total=False):
    refKey: Required[str]
    questionText: Required[str]
    expectedTargets: Required[list[str]]
    anchorRefs: Required[dict[str, object]]
    consentScopes: Required[list[str]]
    storagePolicy: Required[str]
    expiresAt: Required[str]


class LlmClarificationPlanCandidate(TypedDict, total=False):
    questionText: Required[str]
    questionKey: NotRequired[str]
    intent: Required[str]
    captureTarget: Required[str]
    expectedAnswerKind: Required[str]
    answerSlots: NotRequired[dict[str, object]]
    routingHints: NotRequired[dict[str, object]]
    supportingRefs: NotRequired[list[str]]
    anchorRefs: NotRequired[dict[str, object]]
    consentScopes: NotRequired[list[str]]


class LlmIndividuationCandidateBase(TypedDict, total=False):
    label: Required[str]
    summary: Required[str]
    confidence: Required[Literal["low", "medium", "high"]]
    supportingRefs: Required[list[str]]
    counterRefs: NotRequired[list[str]]
    reason: Required[str]


class LlmRealityAnchorCandidate(LlmIndividuationCandidateBase, total=False):
    anchorSummary: Required[str]
    workDailyLifeContinuity: Required[str]
    sleepBodyRegulation: Required[str]
    relationshipContact: Required[str]
    reflectiveCapacity: Required[str]
    groundingRecommendation: Required[str]
    reasons: Required[list[str]]


class LlmSelfOrientationCandidate(LlmIndividuationCandidateBase, total=False):
    orientationSummary: Required[str]
    emergentDirection: Required[str]
    egoRelation: Required[str]
    movementLanguage: Required[list[str]]


class LlmPsychicOppositionCandidate(LlmIndividuationCandidateBase, total=False):
    poleA: Required[str]
    poleB: Required[str]
    oppositionSummary: Required[str]
    currentHoldingPattern: Required[str]
    pressureTone: NotRequired[str]
    holdingInstruction: NotRequired[str]
    normalizedOppositionKey: Required[str]


class LlmEmergentThirdCandidate(LlmIndividuationCandidateBase, total=False):
    signalType: Required[str]
    signalSummary: Required[str]
    oppositionIds: NotRequired[list[str]]
    novelty: Required[str]


class LlmBridgeMomentCandidate(LlmIndividuationCandidateBase, total=False):
    bridgeType: Required[str]
    bridgeSummary: Required[str]
    beforeAfter: NotRequired[str]


class LlmNuminousEncounterCandidate(LlmIndividuationCandidateBase, total=False):
    encounterMedium: Required[str]
    affectTone: Required[str]
    containmentNeed: Required[str]
    interpretationConstraint: Required[str]


class LlmAestheticResonanceCandidate(LlmIndividuationCandidateBase, total=False):
    medium: Required[str]
    objectDescription: Required[str]
    resonanceSummary: Required[str]
    feelingTone: NotRequired[str]
    bodySensations: NotRequired[list[str]]


class LlmArchetypalPatternCandidate(LlmIndividuationCandidateBase, total=False):
    patternFamily: Required[str]
    resonanceSummary: Required[str]
    caveat: Required[str]
    phrasingPolicy: Required[str]


class LlmThresholdProcessCandidate(LlmIndividuationCandidateBase, total=False):
    thresholdName: Required[str]
    phase: Required[str]
    whatIsEnding: Required[str]
    notYetBegun: Required[str]
    bodyCarrying: NotRequired[str]
    groundingStatus: Required[str]
    symbolicLens: NotRequired[str]
    invitationReadiness: Required[str]
    normalizedThresholdKey: Required[str]


class LlmRelationalSceneCandidate(LlmIndividuationCandidateBase, total=False):
    sceneSummary: Required[str]
    chargedRoles: Required[list[dict[str, object]]]
    recurringAffect: Required[list[str]]
    recurrenceContexts: Required[list[str]]
    normalizedSceneKey: Required[str]


class LlmProjectionHypothesisCandidate(LlmIndividuationCandidateBase, total=False):
    relationalSceneId: NotRequired[str]
    hypothesisSummary: Required[str]
    projectionPattern: Required[str]
    userTestPrompt: Required[str]
    phrasingPolicy: Required[str]
    normalizedHypothesisKey: Required[str]


class LlmInnerOuterCorrespondenceCandidate(LlmIndividuationCandidateBase, total=False):
    correspondenceSummary: Required[str]
    innerRefs: Required[list[str]]
    outerRefs: Required[list[str]]
    symbolIds: Required[list[str]]
    timeWindowStart: NotRequired[str]
    timeWindowEnd: NotRequired[str]
    userCharge: Required[str]
    caveat: Required[str]
    causalityPolicy: Required[str]
    normalizedCorrespondenceKey: Required[str]


class LlmIndividuationCandidateSet(TypedDict, total=False):
    realityAnchors: NotRequired[list[LlmRealityAnchorCandidate]]
    selfOrientationSnapshots: NotRequired[list[LlmSelfOrientationCandidate]]
    psychicOppositions: NotRequired[list[LlmPsychicOppositionCandidate]]
    emergentThirdSignals: NotRequired[list[LlmEmergentThirdCandidate]]
    bridgeMoments: NotRequired[list[LlmBridgeMomentCandidate]]
    numinousEncounters: NotRequired[list[LlmNuminousEncounterCandidate]]
    aestheticResonances: NotRequired[list[LlmAestheticResonanceCandidate]]
    archetypalPatterns: NotRequired[list[LlmArchetypalPatternCandidate]]
    thresholdProcesses: NotRequired[list[LlmThresholdProcessCandidate]]
    relationalScenes: NotRequired[list[LlmRelationalSceneCandidate]]
    projectionHypotheses: NotRequired[list[LlmProjectionHypothesisCandidate]]
    innerOuterCorrespondences: NotRequired[list[LlmInnerOuterCorrespondenceCandidate]]


class LlmInterpretationOutput(TypedDict, total=False):
    symbolMentions: Required[list[LlmSymbolCandidate]]
    figureMentions: Required[list[LlmFigureCandidate]]
    motifMentions: Required[list[LlmMotifCandidate]]
    lifeContextLinks: Required[list[LlmLifeContextLinkCandidate]]
    observations: Required[list[LlmObservationCandidate]]
    hypotheses: Required[list[LlmHypothesisCandidate]]
    depthReadiness: NotRequired[LlmDepthReadinessCandidate]
    methodGate: NotRequired[LlmMethodGateCandidate]
    amplificationPrompts: NotRequired[list[LlmAmplificationPromptCandidate]]
    dreamSeriesSuggestions: NotRequired[list[LlmDreamSeriesSuggestionCandidate]]
    typologyAssessment: NotRequired[LlmTypologyAssessmentCandidate]
    individuation: NotRequired[LlmIndividuationCandidateSet]
    practiceRecommendation: Required[LlmPracticeCandidate]
    proposalCandidates: Required[list[LlmProposalCandidate]]
    userFacingResponse: Required[str]
    clarifyingQuestion: NotRequired[str]
    clarificationPlan: NotRequired[LlmClarificationPlanCandidate]
    clarificationIntent: NotRequired[LlmClarificationIntent]


class LlmWeeklyReviewOutput(TypedDict, total=False):
    userFacingResponse: Required[str]
    activeThemes: NotRequired[list[str]]
    practiceRecommendation: NotRequired[LlmPracticeCandidate]
    longitudinalObservations: NotRequired[list[LlmObservationCandidate]]


class LlmAliveTodayOutput(TypedDict, total=False):
    userFacingResponse: Required[str]
    activeThemes: NotRequired[list[str]]
    selectedCoachLoopKey: NotRequired[str]
    coachMoveKind: NotRequired[str]
    followUpQuestion: NotRequired[str]
    suggestedAction: NotRequired[str]
    practiceRecommendation: NotRequired[LlmPracticeCandidate]
    resourceInvitation: NotRequired[dict[str, object]]
    withheldReason: NotRequired[str]


class LlmPracticeOutput(TypedDict, total=False):
    practiceRecommendation: Required[LlmPracticeCandidate]
    userFacingResponse: Required[str]
    followUpPrompt: NotRequired[str]
    adaptationNotes: NotRequired[list[str]]
    resourceInvitation: NotRequired[dict[str, object]]


class LlmRhythmicBriefOutput(TypedDict, total=False):
    title: Required[str]
    summary: Required[str]
    suggestedAction: NotRequired[str]
    userFacingResponse: Required[str]
    supportingRefs: NotRequired[list[str]]
    resourceInvitation: NotRequired[dict[str, object]]


class LlmInvitationCandidate(TypedDict, total=False):
    briefType: Required[str]
    label: Required[str]
    summary: Required[str]
    supportingRefs: Required[list[str]]


class LlmLifeChapterCandidate(TypedDict, total=False):
    label: Required[str]
    summary: Required[str]
    confidence: Required[Literal["low", "medium", "high"]]
    supportingRefs: Required[list[str]]
    chapterLabel: Required[str]
    chapterSummary: Required[str]
    governingSymbolIds: Required[list[str]]
    governingQuestions: Required[list[str]]
    activeOppositionIds: Required[list[str]]
    thresholdProcessIds: Required[list[str]]
    relationalSceneIds: Required[list[str]]
    correspondenceIds: Required[list[str]]
    chapterTone: NotRequired[str]


class LlmMythicQuestionCandidate(TypedDict, total=False):
    label: Required[str]
    summary: Required[str]
    confidence: Required[Literal["low", "medium", "high"]]
    supportingRefs: Required[list[str]]
    questionText: Required[str]
    questionStatus: Required[str]
    relatedChapterId: NotRequired[str]
    lastReturnedAt: NotRequired[str]


class LlmThresholdMarkerCandidate(TypedDict, total=False):
    label: Required[str]
    summary: Required[str]
    confidence: Required[Literal["low", "medium", "high"]]
    supportingRefs: Required[list[str]]
    markerType: Required[str]
    markerSummary: Required[str]
    thresholdProcessId: NotRequired[str]


class LlmComplexEncounterCandidate(TypedDict, total=False):
    label: Required[str]
    summary: Required[str]
    confidence: Required[Literal["low", "medium", "high"]]
    supportingRefs: Required[list[str]]
    complexCandidateId: NotRequired[str]
    patternId: NotRequired[str]
    encounterSummary: Required[str]
    trajectorySummary: Required[str]
    movement: Required[str]


class LlmIntegrationContourCandidate(TypedDict, total=False):
    label: Required[str]
    summary: Required[str]
    confidence: Required[Literal["low", "medium", "high"]]
    supportingRefs: Required[list[str]]
    contourSummary: Required[str]
    symbolicStrands: Required[list[str]]
    somaticStrands: Required[list[str]]
    relationalStrands: Required[list[str]]
    existentialStrands: Required[list[str]]
    tensionsHeld: Required[list[str]]
    assimilatedSignals: Required[list[str]]
    unassimilatedEdges: Required[list[str]]
    nextQuestions: Required[list[str]]


class LlmSymbolicWellbeingCandidate(TypedDict, total=False):
    label: Required[str]
    summary: Required[str]
    confidence: Required[Literal["low", "medium", "high"]]
    supportingRefs: Required[list[str]]
    capacitySummary: Required[str]
    groundingCapacity: Required[str]
    symbolicLiveliness: Required[str]
    somaticContact: Required[str]
    relationalSpaciousness: Required[str]
    agencyTone: Required[str]
    supportNeeded: NotRequired[str]


class LlmThresholdReviewOutput(TypedDict, total=False):
    userFacingResponse: Required[str]
    thresholdProcesses: Required[list[LlmThresholdProcessCandidate]]
    realityAnchors: NotRequired[list[LlmRealityAnchorCandidate]]
    invitations: NotRequired[list[LlmInvitationCandidate]]
    practiceRecommendation: NotRequired[LlmPracticeCandidate]
    proposalCandidates: NotRequired[list[LlmProposalCandidate]]


class LlmLivingMythReviewOutput(TypedDict, total=False):
    userFacingResponse: Required[str]
    lifeChapter: NotRequired[LlmLifeChapterCandidate]
    mythicQuestions: Required[list[LlmMythicQuestionCandidate]]
    thresholdMarkers: Required[list[LlmThresholdMarkerCandidate]]
    complexEncounters: Required[list[LlmComplexEncounterCandidate]]
    integrationContour: NotRequired[LlmIntegrationContourCandidate]
    symbolicWellbeing: NotRequired[LlmSymbolicWellbeingCandidate]
    practiceRecommendation: NotRequired[LlmPracticeCandidate]
    proposalCandidates: NotRequired[list[LlmProposalCandidate]]


class LlmAnalysisPacketSection(TypedDict, total=False):
    title: Required[str]
    purpose: Required[str]
    items: Required[list[dict[str, object]]]


class LlmAnalysisPacketFunctionDynamicsSummary(TypedDict, total=False):
    status: Required[str]
    summary: Required[str]
    foregroundFunctions: Required[list[str]]
    compensatoryFunctions: Required[list[str]]
    backgroundFunctions: Required[list[str]]
    ambiguityNotes: NotRequired[list[str]]
    supportingRefs: Required[list[str]]


class LlmAnalysisPacketOutput(TypedDict, total=False):
    packetTitle: Required[str]
    sections: Required[list[LlmAnalysisPacketSection]]
    includedMaterialIds: NotRequired[list[str]]
    includedRecordRefs: NotRequired[list[dict[str, object]]]
    evidenceIds: NotRequired[list[str]]
    functionDynamics: NotRequired[LlmAnalysisPacketFunctionDynamicsSummary]
    userFacingResponse: Required[str]
    supportingRefs: Required[list[str]]


class LlmMethodStateEvidenceSpan(TypedDict, total=False):
    refKey: Required[str]
    quote: NotRequired[str]
    summary: NotRequired[str]
    targetKinds: Required[list[str]]


class LlmMethodStateCaptureCandidate(TypedDict, total=False):
    targetKind: Required[str]
    application: Required[str]
    confidence: Required[Literal["low", "medium", "high"]]
    payload: Required[dict[str, object]]
    supportingEvidenceRefs: Required[list[str]]
    consentScopes: Required[list[str]]
    reason: Required[str]


class LlmMethodStateRoutingOutput(TypedDict, total=False):
    answerSummary: Required[str]
    evidenceSpans: Required[list[LlmMethodStateEvidenceSpan]]
    captureCandidates: Required[list[LlmMethodStateCaptureCandidate]]
    followUpPrompts: Required[list[str]]
    routingWarnings: Required[list[str]]
