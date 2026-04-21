from __future__ import annotations

from .agent_bridge_contracts import BridgePendingProposal, BridgeResponseEnvelope


class CirculatioResultRenderer:
    def render(self, response: BridgeResponseEnvelope) -> str:
        lines: list[str] = [response["message"]]
        if response.get("replayed"):
            lines.append("This response was replayed from the prior idempotent request.")
        result = response.get("result", {})
        journey_page = result.get("journeyPage")
        if isinstance(journey_page, dict):
            fallback_text = str(journey_page.get("fallbackText") or "").strip()
            message_text = str(response["message"]).strip()
            if fallback_text and fallback_text not in message_text:
                lines.extend(self._render_journey_page(journey_page))
        discovery = result.get("discovery")
        if isinstance(discovery, dict):
            fallback_text = str(discovery.get("fallbackText") or "").strip()
            message_text = str(response["message"]).strip()
            if not fallback_text or fallback_text not in message_text:
                lines.extend(self._render_discovery(discovery))
        journey = result.get("journey")
        if isinstance(journey, dict):
            lines.extend(self._render_journey(journey))
        journeys = result.get("journeys")
        if isinstance(journeys, list) and journeys:
            lines.extend(self._render_journey_list(journeys))
        if result.get("materialId"):
            lines.append(f"Material: {result['materialId']}")
        if result.get("runId"):
            lines.append(f"Run: {result['runId']}")
        llm_health = result.get("llmInterpretationHealth")
        if isinstance(llm_health, dict):
            status = str(llm_health.get("status") or "unknown")
            source = str(llm_health.get("source") or "unknown")
            counts = ", ".join(
                [
                    f"symbols={llm_health.get('symbolMentions', 0)}",
                    f"observations={llm_health.get('observations', 0)}",
                    f"hypotheses={llm_health.get('hypotheses', 0)}",
                    f"proposals={llm_health.get('proposalCandidates', 0)}",
                ]
            )
            lines.append(f"LLM schema: {status} via {source} ({counts})")
            if llm_health.get("reason"):
                lines.append(f"LLM schema reason: {llm_health['reason']}")
        if result.get("integrationId"):
            lines.append(f"Integration: {result['integrationId']}")
        if result.get("reviewId"):
            lines.append(f"Review: {result['reviewId']}")
        if result.get("packetId"):
            lines.append(f"Packet: {result['packetId']}")
        if result.get("packetTitle"):
            lines.append(f"Packet title: {result['packetTitle']}")
        practice_recommendation = result.get("practiceRecommendation")
        if isinstance(practice_recommendation, dict):
            practice_type = str(practice_recommendation.get("type") or "practice")
            duration = practice_recommendation.get("durationMinutes")
            lines.append(
                f"Practice: {practice_type.replace('_', ' ')}"
                + (f" ({duration} min)" if duration else "")
            )
            instructions = practice_recommendation.get("instructions")
            if isinstance(instructions, list):
                for item in instructions[:3]:
                    lines.append(f"- {item}")
            if practice_recommendation.get("requiresConsent"):
                lines.append("Consent: explicit acceptance required before doing this.")
        practice_session = result.get("practiceSession")
        if isinstance(practice_session, dict):
            practice_id = str(practice_session.get("id") or "").strip()
            status = str(practice_session.get("status") or "unknown").strip()
            lines.append(f"Practice session: {practice_id} ({status})")
            if practice_id and status == "recommended":
                lines.append(f"Accept: /circulation practice accept {practice_id}")
                lines.append(f'Skip: /circulation practice skip {practice_id} --note "not now"')
        briefs = result.get("briefs")
        if isinstance(briefs, list) and briefs:
            lines.append("Rhythmic briefs:")
            for brief in briefs[:3]:
                if not isinstance(brief, dict):
                    continue
                lines.append(
                    "- "
                    f"{brief.get('title', brief.get('briefType', 'brief'))} "
                    f"({brief.get('id', 'unknown')})"
                )
                if brief.get("summary"):
                    lines.append(f"  {brief['summary']}")
                if brief.get("suggestedAction"):
                    lines.append(f"  Action: {brief['suggestedAction']}")
                brief_id = brief.get("id")
                if brief_id:
                    lines.append(f"  Show: /circulation brief show {brief_id}")
                    lines.append(f"  Dismiss: /circulation brief dismiss {brief_id}")
                    lines.append(f"  Done: /circulation brief done {brief_id}")
        brief = result.get("brief")
        if isinstance(brief, dict):
            lines.append(f"Brief: {brief.get('id', 'unknown')} ({brief.get('status', 'unknown')})")
        symbols = result.get("symbols")
        if isinstance(symbols, list) and symbols:
            lines.append("Symbols:")
            for symbol in symbols:
                if not isinstance(symbol, dict):
                    continue
                lines.append(
                    "- "
                    f"{symbol.get('canonicalName', symbol.get('id', 'unknown'))} "
                    f"({symbol.get('id', 'unknown')})"
                )
        history = result.get("history")
        if isinstance(history, list) and history:
            lines.append("History:")
            for item in history[:5]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"- {item.get('eventType', 'event')} at {item.get('createdAt', 'unknown time')}"
                )
        linked_materials = result.get("linkedMaterials")
        if isinstance(linked_materials, list) and linked_materials:
            lines.append("Linked materials:")
            for material in linked_materials[:5]:
                if not isinstance(material, dict):
                    continue
                lines.append(
                    f"- {material.get('id', 'unknown')} "
                    f"({material.get('materialType', 'material')})"
                )
        pending = response.get("pendingProposals", [])
        if pending:
            run_id = result.get("runId")
            lines.append("")
            lines.append("Pending memory proposals - not written yet:")
            for proposal in pending:
                lines.extend(self._render_pending_proposal(proposal))
            if run_id:
                aliases = " ".join(proposal["alias"] for proposal in pending)
                lines.append("")
                lines.append(f"Approve: /circulation approve {run_id} {aliases}")
                lines.append(
                    f'Reject: /circulation reject {run_id} {aliases} --reason "do not save this"'
                )
            review_id = result.get("reviewId")
            if review_id and not run_id:
                aliases = " ".join(proposal["alias"] for proposal in pending)
                lines.append("")
                lines.append(f"Approve: /circulation review approve {review_id} {aliases}")
                lines.append(
                    "Reject: /circulation review reject "
                    f'{review_id} {aliases} --reason "do not save this"'
                )
        errors = response.get("errors", [])
        if errors:
            lines.append("")
            lines.append("Errors:")
            for error in errors:
                lines.append(f"- {error['code']}: {error['message']}")
        return "\n".join(line for line in lines if line is not None)

    def _render_pending_proposal(self, proposal: BridgePendingProposal) -> list[str]:
        lines = [f"[{proposal['alias']}] {proposal['entityType']} via {proposal['action']}"]
        payload = proposal.get("payload")
        if isinstance(payload, dict):
            label = (
                payload.get("canonicalName")
                or payload.get("label")
                or payload.get("summary")
                or payload.get("claim")
            )
            if label:
                lines.append(f"    target: {label}")
        lines.append(f"    reason: {proposal['reason']}")
        return lines

    def _render_journey_page(self, page: dict[str, object]) -> list[str]:
        lines = [str(page.get("title") or "Journey page")]
        window_start = page.get("windowStart")
        window_end = page.get("windowEnd")
        if window_start and window_end:
            lines.append(f"Window: {window_start} -> {window_end}")
        cards = page.get("cards")
        if not isinstance(cards, list):
            return lines
        for card in cards:
            if not isinstance(card, dict):
                continue
            lines.append("")
            lines.append(f"{card.get('title', 'Section')}:")
            body = str(card.get("body") or "").strip()
            if body:
                lines.append(body)
            actions = card.get("actions")
            if isinstance(actions, list) and actions:
                labels = [
                    str(action.get("label") or "").strip()
                    for action in actions[:3]
                    if isinstance(action, dict) and str(action.get("label") or "").strip()
                ]
                if labels:
                    lines.append("Actions: " + ", ".join(labels))
        return lines

    def _render_discovery(self, discovery: dict[str, object]) -> list[str]:
        fallback_text = str(discovery.get("fallbackText") or "").strip()
        if fallback_text:
            return fallback_text.splitlines()
        lines = ["Discovery digest"]
        window_start = discovery.get("windowStart")
        window_end = discovery.get("windowEnd")
        if window_start and window_end:
            lines.append(f"Window: {window_start} -> {window_end}")
        sections = discovery.get("sections")
        if not isinstance(sections, list):
            return lines
        for section in sections:
            if not isinstance(section, dict):
                continue
            lines.append("")
            lines.append(str(section.get("title") or "Section"))
            items = section.get("items")
            if not isinstance(items, list) or not items:
                summary = str(section.get("summary") or "").strip()
                if summary:
                    lines.append(summary)
                continue
            for item in items[:5]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()
                if label:
                    lines.append(f"- {label}")
        return lines

    def _render_journey(self, journey: dict[str, object]) -> list[str]:
        lines: list[str] = []
        journey_id = journey.get("id")
        label = str(journey.get("label") or "Journey")
        status = str(journey.get("status") or "unknown")
        lines.append(f"Journey: {label} ({status})")
        if journey_id:
            lines.append(f"Journey id: {journey_id}")
        current_question = str(journey.get("currentQuestion") or "").strip()
        if current_question:
            lines.append(f"Question: {current_question}")
        next_review_due_at = str(journey.get("nextReviewDueAt") or "").strip()
        if next_review_due_at:
            lines.append(f"Next review: {next_review_due_at}")
        link_counts = []
        for key, label_text in (
            ("relatedMaterialIds", "materials"),
            ("relatedSymbolIds", "symbols"),
            ("relatedPatternIds", "patterns"),
            ("relatedDreamSeriesIds", "dream series"),
            ("relatedGoalIds", "goals"),
        ):
            values = journey.get(key)
            if isinstance(values, list) and values:
                link_counts.append(f"{label_text}={len(values)}")
        if link_counts:
            lines.append("Links: " + ", ".join(link_counts))
        if journey_id:
            lines.append(f"Get: /circulation journey get {journey_id}")
            if status == "active":
                lines.append(f"Pause: /circulation journey pause {journey_id}")
            elif status == "paused":
                lines.append(f"Resume: /circulation journey resume {journey_id}")
        return lines

    def _render_journey_list(self, journeys: list[object]) -> list[str]:
        lines = ["Journeys:"]
        for item in journeys[:10]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "Journey")
            status = str(item.get("status") or "unknown")
            journey_id = str(item.get("id") or "unknown")
            current_question = str(item.get("currentQuestion") or "").strip()
            line = f"- {label} ({status}) [{journey_id}]"
            if current_question:
                line += f" Question: {current_question}"
            lines.append(line)
        return lines
