from __future__ import annotations

from copy import deepcopy


class FakeCirculatioLlm:
    def __init__(self) -> None:
        self.interpret_calls: list[dict[str, object]] = []
        self.review_calls: list[dict[str, object]] = []
        self.life_calls: list[dict[str, object]] = []
        self.practice_calls: list[dict[str, object]] = []
        self.brief_calls: list[dict[str, object]] = []
        self.threshold_review_calls: list[dict[str, object]] = []
        self.living_myth_review_calls: list[dict[str, object]] = []
        self.analysis_packet_calls: list[dict[str, object]] = []
        self.force_active_imagination = False

    async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
        payload = deepcopy(input_data)
        self.interpret_calls.append(payload)
        text = str(payload["materialText"]).lower()
        symbols: list[dict[str, object]] = []
        motifs: list[dict[str, object]] = []
        figures: list[dict[str, object]] = []
        observations: list[dict[str, object]] = []
        hypotheses: list[dict[str, object]] = []
        proposals: list[dict[str, object]] = []

        if "snake" in text:
            symbols.append(
                {
                    "refKey": "sym_snake",
                    "surfaceText": "snake",
                    "canonicalName": "snake",
                    "category": "animal",
                    "salience": 0.92,
                    "tone": "charged",
                }
            )
            proposals.append(
                {
                    "action": "upsert_personal_symbol",
                    "entityType": "PersonalSymbol",
                    "payload": {
                        "canonicalName": "snake",
                        "category": "animal",
                        "aliases": ["snake"],
                        "tone": "charged",
                    },
                    "reason": "The snake image appears central enough to remember if approved.",
                    "supportingRefs": ["sym_snake"],
                }
            )
        if "house" in text or "room" in text or "cellar" in text or "basement" in text:
            surface = (
                "house"
                if "house" in text
                else "room"
                if "room" in text
                else "cellar"
                if "cellar" in text
                else "basement"
            )
            symbols.append(
                {
                    "refKey": "sym_place",
                    "surfaceText": surface,
                    "canonicalName": surface,
                    "category": "place",
                    "salience": 0.73,
                }
            )
        if "authority" in text or "uniformed" in text:
            figures.append(
                {
                    "refKey": "fig_authority",
                    "surfaceText": "uniformed authority" if "uniformed" in text else "authority",
                    "label": "uniformed authority",
                    "role": "authority",
                    "salience": 0.74,
                }
            )
        if "locked" in text or "chest" in text:
            motifs.append(
                {
                    "refKey": "motif_containment",
                    "surfaceText": "locked chest" if "chest" in text else "locked",
                    "canonicalName": "containment",
                    "motifType": "containment",
                    "salience": 0.68,
                }
            )

        if symbols:
            observations.append(
                {
                    "kind": "image",
                    "statement": "The material concentrates around a small set of charged images.",
                    "supportingRefs": [item["refKey"] for item in symbols],
                }
            )
        if figures:
            observations.append(
                {
                    "kind": "figure",
                    "statement": "An authority figure appears as part of the symbolic field.",
                    "supportingRefs": ["fig_authority"],
                }
            )
        if motifs:
            observations.append(
                {
                    "kind": "motif",
                    "statement": "A containment motif appears in the material.",
                    "supportingRefs": ["motif_containment"],
                }
            )
        if payload.get("lifeContextSnapshot"):
            observations.append(
                {
                    "kind": "life_context_link",
                    "statement": "Recent life context may be shaping the way the image cluster is charged.",
                    "supportingRefs": ["life_event_1"],
                }
            )

        method_context = payload.get("methodContextSnapshot") or {}
        depth_readiness = {
            "status": "ready" if method_context else "limited",
            "allowedMoves": {
                "shadow_work": "ask_consent",
                "projection_language": "ask_consent",
                "collective_amplification": "allow"
                if payload.get("userAssociations") or method_context.get("personalAmplifications")
                else "withhold",
                "active_imagination": "allow"
                if method_context.get("consciousAttitude")
                else "ask_consent",
                "somatic_correlation": "allow",
                "proactive_briefing": "soften",
            },
            "reasons": ["llm_driven_method_assessment"],
        }
        method_gate = {
            "depthLevel": "depth_interpretation_allowed"
            if method_context.get("consciousAttitude")
            else "personal_amplification_needed",
            "missingPrerequisites": []
            if method_context.get("consciousAttitude")
            else ["conscious_attitude", "personal_amplification"],
            "blockedMoves": []
            if method_context.get("consciousAttitude")
            else ["compensation_assessment", "collective_amplification"],
            "requiredPrompts": []
            if payload.get("userAssociations") or method_context.get("personalAmplifications")
            else ["ask_for_personal_association"],
            "responseConstraints": ["stay tentative"],
        }
        if symbols:
            hypotheses.append(
                {
                    "claim": "One possible pattern is that the snake image carries a recurring tension rather than a one-off detail.",
                    "hypothesisType": "theme",
                    "confidence": "medium",
                    "supportingRefs": [symbols[0]["refKey"]],
                    "userTestPrompt": "Does the strongest image feel recurrent, or only situational here?",
                    "phrasingPolicy": "tentative",
                }
            )
        if figures and motifs:
            hypotheses.append(
                {
                    "claim": "One possible recurring tension here is an authority/autonomy pattern becoming charged across image and scene.",
                    "hypothesisType": "complex_candidate",
                    "confidence": "medium",
                    "supportingRefs": ["fig_authority", "motif_containment"],
                    "userTestPrompt": "Does this feel like a recurring tension between structure and instinct?",
                    "phrasingPolicy": "very_tentative",
                }
            )
            proposals.append(
                {
                    "action": "upsert_complex_candidate",
                    "entityType": "ComplexCandidate",
                    "payload": {
                        "label": "Authority / autonomy",
                        "formulation": "A recurring tension between structure and instinct may be charging the material.",
                        "confidence": "medium",
                    },
                    "reason": "This possible recurring tension should only be stored with explicit approval.",
                    "supportingRefs": ["fig_authority", "motif_containment"],
                }
            )
        active_goals = method_context.get("activeGoals") or []
        if isinstance(active_goals, list) and len(active_goals) >= 2:
            proposals.append(
                {
                    "action": "upsert_goal_tension",
                    "entityType": "GoalTension",
                    "payload": {
                        "goalIds": [
                            goal["id"]
                            for goal in active_goals[:2]
                            if isinstance(goal, dict) and goal.get("id")
                        ],
                        "tensionSummary": "Two explicit goals appear to be pulling in different directions.",
                        "polarityLabels": ["directness", "safety"],
                    },
                    "reason": "This tension should only be stored if the user wants it held across time.",
                    "supportingRefs": [item["refKey"] for item in symbols[:1]] or ["life_focus"],
                }
            )
        consent_preferences = {
            item["scope"]: item["status"]
            for item in method_context.get("consentPreferences", [])
            if isinstance(item, dict) and item.get("scope")
        }
        has_personal_amplification = bool(payload.get("userAssociations")) or bool(
            method_context.get("personalAmplifications")
        )
        if (
            payload.get("options", {}).get("allowCulturalAmplification", True)
            and has_personal_amplification
            and consent_preferences.get("collective_amplification") == "allow"
            and symbols
        ):
            proposals.append(
                {
                    "action": "create_collective_amplification",
                    "entityType": "CollectiveAmplification",
                    "payload": {
                        "canonicalName": symbols[0]["canonicalName"],
                        "amplificationText": "A mythic serpent frame may be relevant here as an optional lens.",
                        "lensLabel": "mythic",
                    },
                    "reason": "Offer a collective lens only if the user wants it retained.",
                    "supportingRefs": [symbols[0]["refKey"]],
                }
            )

        life_context_links = []
        snapshot = payload.get("lifeContextSnapshot") or {}
        if isinstance(snapshot, dict):
            if snapshot.get("lifeEventRefs"):
                first = snapshot["lifeEventRefs"][0]
                life_context_links.append(
                    {
                        "refKey": "life_event_1",
                        "lifeEventRefId": first["id"],
                        "summary": first.get("symbolicAnnotation") or first.get("summary") or "",
                    }
                )
            if snapshot.get("focusSummary"):
                life_context_links.append(
                    {
                        "refKey": "life_focus",
                        "stateSnapshotField": "focusSummary",
                        "summary": snapshot["focusSummary"],
                    }
                )

        return {
            "symbolMentions": symbols,
            "figureMentions": figures,
            "motifMentions": motifs,
            "lifeContextLinks": life_context_links,
            "observations": observations,
            "hypotheses": hypotheses,
            "depthReadiness": depth_readiness,
            "methodGate": method_gate,
            "amplificationPrompts": [
                {
                    "symbolRefKey": symbols[0]["refKey"],
                    "symbolMentionRefKey": symbols[0]["refKey"],
                    "canonicalName": symbols[0]["canonicalName"],
                    "surfaceText": symbols[0]["surfaceText"],
                    "promptText": "What is your own association to this image?",
                    "reason": "The method requires personal amplification before stronger symbolic claims.",
                }
            ]
            if symbols and "ask_for_personal_association" in method_gate["requiredPrompts"]
            else [],
            "dreamSeriesSuggestions": [
                {
                    "seriesId": "series_house_snake",
                    "label": "House / snake sequence",
                    "matchScore": 0.72,
                    "matchingFeatures": ["symbol_overlap", "setting_overlap"],
                    "narrativeRole": "continuation",
                    "confidence": "medium",
                    "egoStance": "watching from the threshold",
                    "lysisSummary": "The image remains unresolved.",
                    "progressionSummary": "The recurring image is becoming more direct.",
                    "compensationTrajectory": "from avoidance toward contact",
                    "supportingRefs": [symbols[0]["refKey"]],
                }
            ]
            if symbols and method_context.get("activeDreamSeries")
            else [],
            "practiceRecommendation": {
                "type": "active_imagination"
                if method_context.get("consciousAttitude") or self.force_active_imagination
                else "journaling",
                "target": symbols[0]["canonicalName"] if symbols else "image",
                "reason": "Use a short LLM-generated practice to test resonance without forcing certainty.",
                "durationMinutes": 10,
                "instructions": [
                    "Write the strongest image in your own words.",
                    "Note what resonates and what does not.",
                    "Decide whether anything should be remembered.",
                ],
                "requiresConsent": bool(method_context.get("consciousAttitude")),
                "templateId": "llm-guided-practice",
                "modality": "imaginal" if method_context.get("consciousAttitude") else "writing",
                "intensity": "moderate" if method_context.get("consciousAttitude") else "low",
                "script": [
                    {"instruction": "Return to the image and wait.", "pauseSeconds": 20},
                    {"instruction": "Write what answers back.", "pauseSeconds": 30},
                ],
                "followUpPrompt": "What changed in the image after staying with it?",
                "adaptationNotes": ["Prefer short guided practices."],
            },
            "proposalCandidates": proposals,
            "userFacingResponse": "LLM interpretation: a cautious symbolic reading is available.",
            "clarifyingQuestion": "Which image feels most alive to you right now?",
        }

    async def generate_weekly_review(self, input_data: dict[str, object]) -> dict[str, object]:
        self.review_calls.append(deepcopy(input_data))
        return {
            "userFacingResponse": "LLM weekly review: the symbol field shows continuity across the requested window.",
            "activeThemes": ["llm-theme"],
            "practiceRecommendation": {
                "type": "journaling",
                "reason": "Review what repeated and what changed.",
                "durationMinutes": 12,
                "instructions": [
                    "List the recurring image cluster.",
                    "Write what changed around it.",
                    "Choose whether anything should be saved.",
                ],
                "requiresConsent": False,
            },
        }

    async def summarize_life_context(
        self,
        *,
        user_id: str,
        window_start: str,
        window_end: str,
        raw_context: dict[str, object],
    ) -> dict[str, object]:
        self.life_calls.append(
            {
                "userId": user_id,
                "windowStart": window_start,
                "windowEnd": window_end,
                "rawContext": deepcopy(raw_context),
            }
        )
        event_refs = raw_context.get("userMessages", [])
        summary = "Derived from Hermes profile context."
        if event_refs:
            first = event_refs[0]
            summary = str(first.get("content", ""))[:120] or summary
        return {
            "windowStart": window_start,
            "windowEnd": window_end,
            "source": "hermes-life-os",
            "focusSummary": summary,
            "lifeEventRefs": [
                {
                    "id": str(item.get("id", f"life_{index}")),
                    "date": str(item.get("timestamp", window_start)),
                    "summary": str(item.get("content", ""))[:180],
                }
                for index, item in enumerate(raw_context.get("userMessages", [])[:3], start=1)
            ],
            "notableChanges": [str(item) for item in raw_context.get("userEntries", [])[:3]],
        }

    async def generate_practice(self, input_data: dict[str, object]) -> dict[str, object]:
        payload = deepcopy(input_data)
        self.practice_calls.append(payload)
        method_context = payload.get("methodContextSnapshot") or {}
        consent_preferences = {
            item["scope"]: item["status"]
            for item in method_context.get("consentPreferences", [])
            if isinstance(item, dict) and item.get("scope")
        }
        practice_type = (
            "active_imagination"
            if method_context.get("consciousAttitude")
            and consent_preferences.get("active_imagination") == "allow"
            else "journaling"
        )
        return {
            "practiceRecommendation": {
                "type": practice_type,
                "target": "image",
                "reason": "Stay with the strongest image without forcing certainty.",
                "durationMinutes": 9,
                "instructions": [
                    "Name the image in your own words.",
                    "Note what shifts when you stay with it briefly.",
                ],
                "requiresConsent": practice_type == "active_imagination",
                "templateId": "llm-practice",
                "modality": "imaginal" if practice_type == "active_imagination" else "writing",
                "intensity": "moderate" if practice_type == "active_imagination" else "low",
                "followUpPrompt": "What changed after giving the image a little room?",
                "adaptationNotes": ["Keep it brief."],
            },
            "userFacingResponse": "A short practice is available if you want it. You can skip it.",
            "followUpPrompt": "What changed after giving the image a little room?",
            "adaptationNotes": ["Keep it brief."],
        }

    async def generate_rhythmic_brief(self, input_data: dict[str, object]) -> dict[str, object]:
        payload = deepcopy(input_data)
        self.brief_calls.append(payload)
        seed = payload["seed"]
        title = str(seed.get("titleHint") or "Pattern note")
        summary = str(seed.get("summaryHint") or "A pattern may be ready for a light check-in.")
        suggested_action = str(
            seed.get("suggestedActionHint") or "You can simply note it and move on."
        )
        return {
            "title": title,
            "summary": summary,
            "suggestedAction": suggested_action,
            "userFacingResponse": f"{title}. {summary} {suggested_action}".strip(),
            "supportingRefs": [],
        }

    async def generate_threshold_review(self, input_data: dict[str, object]) -> dict[str, object]:
        payload = deepcopy(input_data)
        self.threshold_review_calls.append(payload)
        target = payload.get("targetThresholdProcess") or {}
        material_refs = [
            str(item.get("id") or "").strip()
            for item in payload.get("hermesMemoryContext", {}).get("recentMaterialSummaries", [])
            if str(item.get("id") or "").strip()
        ]
        threshold_process = {
            "id": str(target.get("id") or "threshold_generated"),
            "label": str(target.get("label") or "Threshold process"),
            "summary": str(
                target.get("summary") or "A liminal process is active in the requested window."
            ),
            "phase": str(target.get("phase") or "liminal"),
            "whatIsEnding": str(target.get("whatIsEnding") or "An older arrangement is loosening."),
            "notYetBegun": str(target.get("notYetBegun") or "The next form is not yet clear."),
            "groundingStatus": str(target.get("groundingStatus") or "unknown"),
            "invitationReadiness": str(target.get("invitationReadiness") or "ask"),
            "evidenceIds": list(target.get("evidenceIds", [])),
        }
        proposal_candidates = []
        if material_refs:
            proposal_candidates.append(
                {
                    "action": "upsert_relational_scene",
                    "entityType": "RelationalScene",
                    "payload": {
                        "sceneSummary": "A recurring authority scene remains active.",
                        "chargedRoles": [{"roleLabel": "authority"}],
                        "recurringAffect": ["pressure"],
                        "recurrenceContexts": ["work"],
                        "normalizedSceneKey": "authority-scene",
                    },
                    "reason": "Only store the relational scene if the user wants it held.",
                    "supportingRefs": [material_refs[0]],
                }
            )
        return {
            "userFacingResponse": "A threshold review is available and held cautiously.",
            "thresholdProcesses": [threshold_process],
            "realityAnchors": list(payload.get("relatedRealityAnchors", []))[:1],
            "proposalCandidates": proposal_candidates,
        }

    async def generate_living_myth_review(self, input_data: dict[str, object]) -> dict[str, object]:
        payload = deepcopy(input_data)
        self.living_myth_review_calls.append(payload)
        material_refs = [
            str(item.get("id") or "").strip()
            for item in payload.get("recentMaterialSummaries", [])
            if str(item.get("id") or "").strip()
        ] or [
            str(item.get("id") or "").strip()
            for item in payload.get("hermesMemoryContext", {}).get("recentMaterialSummaries", [])
            if str(item.get("id") or "").strip()
        ]
        proposal_candidates = []
        if material_refs:
            proposal_candidates = [
                {
                    "action": "upsert_threshold_process",
                    "entityType": "ThresholdProcess",
                    "payload": {
                        "thresholdName": "Vocational threshold",
                        "phase": "liminal",
                        "whatIsEnding": "An old work identity is loosening.",
                        "notYetBegun": "The next form is not yet stable.",
                        "groundingStatus": "steady",
                        "invitationReadiness": "ask",
                        "normalizedThresholdKey": "vocational-threshold",
                    },
                    "reason": "Hold this as a threshold only if the user wants it remembered.",
                    "supportingRefs": [material_refs[0]],
                },
                {
                    "action": "create_symbolic_wellbeing_snapshot",
                    "entityType": "SymbolicWellbeingSnapshot",
                    "payload": {
                        "capacitySummary": "Symbolic contact is present without much strain.",
                        "groundingCapacity": "steady",
                        "symbolicLiveliness": "steady",
                        "somaticContact": "available",
                        "relationalSpaciousness": "growing",
                        "agencyTone": "measured",
                    },
                    "reason": "A qualitative wellbeing snapshot may be useful if approved.",
                    "supportingRefs": [material_refs[0]],
                },
            ]
        return {
            "userFacingResponse": "A living myth review is available as a provisional chapter reading.",
            "lifeChapter": {
                "label": "Current chapter",
                "summary": "A tentative chapter is forming around a recurring symbolic tension.",
                "chapterLabel": "Current chapter",
                "chapterSummary": "A tentative chapter is forming around a recurring symbolic tension.",
                "governingQuestions": ["What is trying to become more conscious here?"],
                "governingSymbolIds": [],
                "activeOppositionIds": [],
                "thresholdProcessIds": [],
                "relationalSceneIds": [],
                "correspondenceIds": [],
            },
            "mythicQuestions": [
                {
                    "label": "Mythic question",
                    "summary": "What is trying to come into relation rather than remain split?",
                    "questionText": "What is trying to come into relation rather than remain split?",
                    "questionStatus": "active",
                    "evidenceIds": [],
                }
            ],
            "thresholdMarkers": [],
            "complexEncounters": [],
            "proposalCandidates": proposal_candidates,
        }

    async def generate_analysis_packet(self, input_data: dict[str, object]) -> dict[str, object]:
        payload = deepcopy(input_data)
        self.analysis_packet_calls.append(payload)
        threshold_id = str(
            ((payload.get("activeThresholdProcesses") or [{}])[0]).get("id") or ""
        ).strip()
        material_ids: list[str] = []
        evidence_ids: list[str] = []
        for item in payload.get("evidence", []):
            evidence_id = str(item.get("id") or "").strip()
            source_id = str(item.get("sourceId") or "").strip()
            if evidence_id and evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
            if (
                source_id
                and item.get("type") in {"material_text_span", "dream_text_span", "prior_material"}
                and source_id not in material_ids
            ):
                material_ids.append(source_id)
        return {
            "packetTitle": "Analysis packet",
            "sections": [
                {
                    "title": "What stayed alive",
                    "purpose": "Bound the material that remained active in the window.",
                    "items": [
                        {
                            "label": "Active threshold",
                            "summary": "A threshold process remained symbolically active.",
                            "evidenceIds": [],
                            "relatedRecordRefs": [],
                        }
                    ],
                }
            ],
            "includedMaterialIds": material_ids[:1],
            "includedRecordRefs": (
                [{"recordType": "ThresholdProcess", "recordId": threshold_id}]
                if threshold_id
                else []
            ),
            "evidenceIds": evidence_ids[:3],
            "userFacingResponse": "A bounded analysis packet is ready.",
            "supportingRefs": [item for item in [threshold_id, *material_ids[:1]] if item],
        }
