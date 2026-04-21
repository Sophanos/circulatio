from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from datetime import date, timedelta

from ..domain.errors import ValidationError
from .agent_bridge_contracts import BridgeOperation


@dataclass(frozen=True)
class ParsedCirculationCommand:
    operation: BridgeOperation
    payload: dict[str, object]
    subcommand: str


class CirculatioCommandParser:
    def parse(self, raw_args: str) -> ParsedCirculationCommand:
        normalized = raw_args.strip()
        if normalized.startswith("/circulation"):
            normalized = normalized[len("/circulation") :].strip()
        if not normalized:
            raise ValidationError("A Circulatio subcommand is required.")
        subcommand, _, remainder = normalized.partition(" ")
        if subcommand in {"dream", "reflect", "event"}:
            text = self._strip_outer_quotes(remainder.strip())
            if not text:
                raise ValidationError(f"/circulation {subcommand} requires text to interpret.")
            material_type = {
                "dream": "dream",
                "reflect": "reflection",
                "event": "charged_event",
            }[subcommand]
            return ParsedCirculationCommand(
                operation="circulatio.material.interpret",
                payload={"materialType": material_type, "text": text},
                subcommand=subcommand,
            )
        tokens = shlex.split(normalized)
        if not tokens:
            raise ValidationError("A Circulatio subcommand is required.")
        if tokens[0] == "approve":
            return self._parse_approve(tokens)
        if tokens[0] == "reject":
            return self._parse_reject(tokens)
        if tokens[0] == "symbols":
            return self._parse_symbols(tokens)
        if tokens[0] == "review":
            return self._parse_review(tokens)
        if tokens[0] == "discovery":
            return self._parse_discovery(tokens)
        if tokens[0] == "journey":
            return self._parse_journey(tokens)
        if tokens[0] == "packet":
            return self._parse_packet(tokens)
        if tokens[0] == "practice":
            return self._parse_practice(tokens)
        if tokens[0] == "brief":
            return self._parse_brief(tokens)
        if tokens[0] == "revise":
            return self._parse_revise(tokens)
        if tokens[0] == "delete":
            return self._parse_delete(tokens)
        raise ValidationError(f"Unknown /circulation subcommand: {tokens[0]}")

    def _parse_approve(self, tokens: list[str]) -> ParsedCirculationCommand:
        if len(tokens) < 3:
            raise ValidationError(
                "/circulation approve requires a run reference and at least one proposal reference."
            )
        run_ref = tokens[1]
        proposal_refs: list[str] = []
        note: str | None = None
        index = 2
        while index < len(tokens):
            token = tokens[index]
            if token == "--note":
                note = self._require_value(tokens, index, token)
                index += 2
                continue
            proposal_refs.append(token)
            index += 1
        if not proposal_refs:
            raise ValidationError("/circulation approve requires at least one proposal reference.")
        payload: dict[str, object] = {"runRef": run_ref, "proposalRefs": proposal_refs}
        if note:
            payload["note"] = note
        return ParsedCirculationCommand(
            operation="circulatio.proposals.approve",
            payload=payload,
            subcommand="approve",
        )

    def _parse_reject(self, tokens: list[str]) -> ParsedCirculationCommand:
        if len(tokens) < 3:
            raise ValidationError(
                "/circulation reject requires a run reference and at least one proposal reference."
            )
        run_ref = tokens[1]
        proposal_refs: list[str] = []
        reason: str | None = None
        index = 2
        while index < len(tokens):
            token = tokens[index]
            if token == "--reason":
                reason = self._require_value(tokens, index, token)
                index += 2
                continue
            proposal_refs.append(token)
            index += 1
        if not proposal_refs:
            raise ValidationError("/circulation reject requires at least one proposal reference.")
        payload: dict[str, object] = {"runRef": run_ref, "proposalRefs": proposal_refs}
        if reason:
            payload["reason"] = reason
        return ParsedCirculationCommand(
            operation="circulatio.proposals.reject",
            payload=payload,
            subcommand="reject",
        )

    def _parse_symbols(self, tokens: list[str]) -> ParsedCirculationCommand:
        payload: dict[str, object] = {}
        index = 1
        while index < len(tokens):
            token = tokens[index]
            if token == "--name":
                payload["symbolName"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--id":
                payload["symbolId"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--history":
                payload["includeHistory"] = True
                index += 1
                continue
            raise ValidationError(f"Unknown /circulation symbols option: {token}")
        operation: BridgeOperation = (
            "circulatio.symbols.get"
            if payload.get("symbolId") or payload.get("symbolName")
            else "circulatio.symbols.list"
        )
        return ParsedCirculationCommand(operation=operation, payload=payload, subcommand="symbols")

    def _parse_review(self, tokens: list[str]) -> ParsedCirculationCommand:
        if len(tokens) < 2:
            raise ValidationError("/circulation review requires a workflow name.")
        if tokens[1] == "week":
            return self._parse_review_week(tokens)
        if tokens[1] == "threshold":
            return self._parse_threshold_review(tokens)
        if tokens[1] in {"living-myth", "living_myth", "myth"}:
            return self._parse_living_myth_review(tokens)
        if tokens[1] == "approve":
            return self._parse_review_approve(tokens)
        if tokens[1] == "reject":
            return self._parse_review_reject(tokens)
        raise ValidationError(
            "/circulation review supports week, threshold, living-myth, approve, or reject."
        )

    def _parse_review_week(self, tokens: list[str]) -> ParsedCirculationCommand:
        today = date.today()
        window_end = today.isoformat()
        window_start = (today - timedelta(days=6)).isoformat()
        if len(tokens) >= 3:
            window_start = tokens[2]
        if len(tokens) >= 4:
            window_end = tokens[3]
        if len(tokens) > 4:
            raise ValidationError("/circulation review week accepts at most two ISO dates.")
        return ParsedCirculationCommand(
            operation="circulatio.review.weekly",
            payload={"windowStart": window_start, "windowEnd": window_end},
            subcommand="review week",
        )

    def _parse_threshold_review(self, tokens: list[str]) -> ParsedCirculationCommand:
        payload = self._parse_window_flags(tokens[2:])
        question_tokens: list[str] = []
        index = 2
        while index < len(tokens):
            token = tokens[index]
            if token in {"--window-start", "--window-end", "--threshold-id", "--persist"}:
                if token == "--persist":
                    payload["persist"] = (
                        self._require_value(tokens, index, token).lower() != "false"
                    )
                elif token == "--threshold-id":
                    payload["thresholdProcessId"] = self._require_value(tokens, index, token)
                index += 2
                continue
            question_tokens.append(token)
            index += 1
        explicit_question = " ".join(question_tokens).strip()
        if explicit_question:
            payload["explicitQuestion"] = explicit_question
        return ParsedCirculationCommand(
            operation="circulatio.review.threshold",
            payload=payload,
            subcommand="review threshold",
        )

    def _parse_living_myth_review(self, tokens: list[str]) -> ParsedCirculationCommand:
        payload = self._parse_window_flags(tokens[2:])
        question_tokens: list[str] = []
        index = 2
        while index < len(tokens):
            token = tokens[index]
            if token in {"--window-start", "--window-end", "--persist"}:
                if token == "--persist":
                    payload["persist"] = (
                        self._require_value(tokens, index, token).lower() != "false"
                    )
                index += 2
                continue
            question_tokens.append(token)
            index += 1
        explicit_question = " ".join(question_tokens).strip()
        if explicit_question:
            payload["explicitQuestion"] = explicit_question
        return ParsedCirculationCommand(
            operation="circulatio.review.living_myth",
            payload=payload,
            subcommand="review living-myth",
        )

    def _parse_review_approve(self, tokens: list[str]) -> ParsedCirculationCommand:
        if len(tokens) < 4:
            raise ValidationError(
                "/circulation review approve requires a review id "
                "and at least one proposal reference."
            )
        return ParsedCirculationCommand(
            operation="circulatio.review.proposals.approve",
            payload={"reviewId": tokens[2], "proposalRefs": tokens[3:]},
            subcommand="review approve",
        )

    def _parse_review_reject(self, tokens: list[str]) -> ParsedCirculationCommand:
        if len(tokens) < 4:
            raise ValidationError(
                "/circulation review reject requires a review id "
                "and at least one proposal reference."
            )
        proposal_refs: list[str] = []
        reason: str | None = None
        index = 3
        while index < len(tokens):
            token = tokens[index]
            if token == "--reason":
                reason = self._require_value(tokens, index, token)
                index += 2
                continue
            proposal_refs.append(token)
            index += 1
        if not proposal_refs:
            raise ValidationError(
                "/circulation review reject requires at least one proposal reference."
            )
        payload: dict[str, object] = {"reviewId": tokens[2], "proposalRefs": proposal_refs}
        if reason:
            payload["reason"] = reason
        return ParsedCirculationCommand(
            operation="circulatio.review.proposals.reject",
            payload=payload,
            subcommand="review reject",
        )

    def _parse_packet(self, tokens: list[str]) -> ParsedCirculationCommand:
        payload = self._parse_window_flags(tokens[1:])
        question_tokens: list[str] = []
        index = 1
        while index < len(tokens):
            token = tokens[index]
            if token in {"--window-start", "--window-end", "--focus", "--persist"}:
                if token == "--focus":
                    payload["packetFocus"] = self._require_value(tokens, index, token)
                elif token == "--persist":
                    payload["persist"] = (
                        self._require_value(tokens, index, token).lower() != "false"
                    )
                index += 2
                continue
            question_tokens.append(token)
            index += 1
        explicit_question = " ".join(question_tokens).strip()
        if explicit_question:
            payload["explicitQuestion"] = explicit_question
        return ParsedCirculationCommand(
            operation="circulatio.packet.analysis",
            payload=payload,
            subcommand="packet",
        )

    def _parse_discovery(self, tokens: list[str]) -> ParsedCirculationCommand:
        payload: dict[str, object] = {}
        question_tokens: list[str] = []
        index = 1
        while index < len(tokens):
            token = tokens[index]
            if token in {"--query"}:
                query = self._require_value(tokens, index, token)
                payload["explicitQuestion"] = query
                payload["textQuery"] = query
                index += 2
                continue
            if token in {"--from", "--start"}:
                payload["windowStart"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token in {"--to", "--end"}:
                payload["windowEnd"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--root":
                self._append_multi_value(
                    payload,
                    "rootNodeIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--limit":
                raw_limit = self._require_value(tokens, index, token)
                try:
                    payload["maxItems"] = int(raw_limit)
                except ValueError as exc:
                    raise ValidationError(
                        "/circulation discovery --limit must be an integer."
                    ) from exc
                index += 2
                continue
            if token == "--profile":
                profile = self._require_value(tokens, index, token)
                if profile not in {"default", "recency", "recurrence", "importance"}:
                    raise ValidationError(
                        "/circulation discovery --profile must be default, recency, "
                        "recurrence, or importance."
                    )
                payload["rankingProfile"] = profile
                index += 2
                continue
            if token.startswith("--"):
                raise ValidationError(f"Unknown /circulation discovery option: {token}")
            question_tokens.append(token)
            index += 1
        if question_tokens:
            if payload.get("textQuery"):
                raise ValidationError(
                    "/circulation discovery accepts either bare text or --query, not both."
                )
            question = " ".join(question_tokens).strip()
            if question:
                payload["explicitQuestion"] = question
                payload["textQuery"] = question
        return ParsedCirculationCommand(
            operation="circulatio.discovery",
            payload=payload,
            subcommand="discovery",
        )

    def _parse_journey(self, tokens: list[str]) -> ParsedCirculationCommand:
        if len(tokens) == 1:
            return self._parse_journey_page(tokens)
        if tokens[1] == "list":
            return self._parse_journey_list(tokens)
        if tokens[1] == "get":
            return self._parse_journey_get(tokens)
        if tokens[1] == "create":
            return self._parse_journey_create(tokens)
        if tokens[1] == "update":
            return self._parse_journey_update(tokens)
        if tokens[1] == "pause":
            return self._parse_journey_status(tokens, status="paused", subcommand="journey pause")
        if tokens[1] == "resume":
            return self._parse_journey_status(tokens, status="active", subcommand="journey resume")
        if tokens[1] == "complete":
            return self._parse_journey_status(
                tokens,
                status="completed",
                subcommand="journey complete",
            )
        if tokens[1] == "archive":
            return self._parse_journey_status(
                tokens,
                status="archived",
                subcommand="journey archive",
            )
        return self._parse_journey_page(tokens)

    def _parse_journey_page(self, tokens: list[str]) -> ParsedCirculationCommand:
        payload = self._parse_window_flags(tokens[1:])
        question_tokens: list[str] = []
        index = 1
        while index < len(tokens):
            token = tokens[index]
            if token in {"--window-start", "--window-end"}:
                index += 2
                continue
            if token == "--max-invitations":
                payload["maxInvitations"] = int(self._require_value(tokens, index, token))
                index += 2
                continue
            if token == "--include-analysis-packet":
                payload["includeAnalysisPacket"] = (
                    self._require_value(tokens, index, token).lower() != "false"
                )
                index += 2
                continue
            question_tokens.append(token)
            index += 1
        explicit_question = " ".join(question_tokens).strip()
        if explicit_question:
            payload["explicitQuestion"] = explicit_question
        return ParsedCirculationCommand(
            operation="circulatio.journey.page",
            payload=payload,
            subcommand="journey",
        )

    def _parse_journey_list(self, tokens: list[str]) -> ParsedCirculationCommand:
        payload: dict[str, object] = {}
        statuses: list[str] = []
        index = 2
        while index < len(tokens):
            token = tokens[index]
            if token == "--status":
                statuses.append(self._require_value(tokens, index, token))
                index += 2
                continue
            if token == "--include-deleted":
                payload["includeDeleted"] = True
                index += 1
                continue
            if token == "--limit":
                payload["limit"] = int(self._require_value(tokens, index, token))
                index += 2
                continue
            raise ValidationError(f"Unknown /circulation journey list option: {token}")
        if statuses:
            payload["statuses"] = statuses
        return ParsedCirculationCommand(
            operation="circulatio.journeys.list",
            payload=payload,
            subcommand="journey list",
        )

    def _parse_journey_get(self, tokens: list[str]) -> ParsedCirculationCommand:
        payload, index = self._parse_journey_reference(
            tokens,
            start_index=2,
            subcommand="journey get",
            allow_include_deleted=True,
        )
        if index != len(tokens):
            raise ValidationError(f"Unknown /circulation journey get option: {tokens[index]}")
        return ParsedCirculationCommand(
            operation="circulatio.journeys.get",
            payload=payload,
            subcommand="journey get",
        )

    def _parse_journey_create(self, tokens: list[str]) -> ParsedCirculationCommand:
        payload: dict[str, object] = {}
        index = 2
        while index < len(tokens):
            token = tokens[index]
            if token == "--label":
                payload["label"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--question":
                payload["currentQuestion"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--status":
                payload["status"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--next-review-due-at":
                payload["nextReviewDueAt"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--material-id":
                self._append_multi_value(
                    payload,
                    "relatedMaterialIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--symbol-id":
                self._append_multi_value(
                    payload,
                    "relatedSymbolIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--pattern-id":
                self._append_multi_value(
                    payload,
                    "relatedPatternIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--dream-series-id":
                self._append_multi_value(
                    payload,
                    "relatedDreamSeriesIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--goal-id":
                self._append_multi_value(
                    payload,
                    "relatedGoalIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            raise ValidationError(f"Unknown /circulation journey create option: {token}")
        if not payload.get("label"):
            raise ValidationError("/circulation journey create requires --label.")
        return ParsedCirculationCommand(
            operation="circulatio.journeys.create",
            payload=payload,
            subcommand="journey create",
        )

    def _parse_journey_update(self, tokens: list[str]) -> ParsedCirculationCommand:
        payload, index = self._parse_journey_reference(
            tokens,
            start_index=2,
            subcommand="journey update",
        )
        while index < len(tokens):
            token = tokens[index]
            if token == "--new-label":
                payload["label"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--question":
                payload["currentQuestion"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--next-review-due-at":
                payload["nextReviewDueAt"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--add-material-id":
                self._append_multi_value(
                    payload,
                    "addRelatedMaterialIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--remove-material-id":
                self._append_multi_value(
                    payload,
                    "removeRelatedMaterialIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--add-symbol-id":
                self._append_multi_value(
                    payload,
                    "addRelatedSymbolIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--remove-symbol-id":
                self._append_multi_value(
                    payload,
                    "removeRelatedSymbolIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--add-pattern-id":
                self._append_multi_value(
                    payload,
                    "addRelatedPatternIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--remove-pattern-id":
                self._append_multi_value(
                    payload,
                    "removeRelatedPatternIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--add-dream-series-id":
                self._append_multi_value(
                    payload,
                    "addRelatedDreamSeriesIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--remove-dream-series-id":
                self._append_multi_value(
                    payload,
                    "removeRelatedDreamSeriesIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--add-goal-id":
                self._append_multi_value(
                    payload,
                    "addRelatedGoalIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            if token == "--remove-goal-id":
                self._append_multi_value(
                    payload,
                    "removeRelatedGoalIds",
                    self._require_value(tokens, index, token),
                )
                index += 2
                continue
            raise ValidationError(f"Unknown /circulation journey update option: {token}")
        if not any(
            key in payload
            for key in {
                "label",
                "currentQuestion",
                "nextReviewDueAt",
                "addRelatedMaterialIds",
                "removeRelatedMaterialIds",
                "addRelatedSymbolIds",
                "removeRelatedSymbolIds",
                "addRelatedPatternIds",
                "removeRelatedPatternIds",
                "addRelatedDreamSeriesIds",
                "removeRelatedDreamSeriesIds",
                "addRelatedGoalIds",
                "removeRelatedGoalIds",
            }
        ):
            raise ValidationError("/circulation journey update requires at least one update flag.")
        return ParsedCirculationCommand(
            operation="circulatio.journeys.update",
            payload=payload,
            subcommand="journey update",
        )

    def _parse_journey_status(
        self,
        tokens: list[str],
        *,
        status: str,
        subcommand: str,
    ) -> ParsedCirculationCommand:
        payload, index = self._parse_journey_reference(
            tokens,
            start_index=2,
            subcommand=subcommand,
        )
        if index != len(tokens):
            raise ValidationError(f"Unknown /circulation {subcommand} option: {tokens[index]}")
        payload["status"] = status
        return ParsedCirculationCommand(
            operation="circulatio.journeys.set_status",
            payload=payload,
            subcommand=subcommand,
        )

    def _parse_journey_reference(
        self,
        tokens: list[str],
        *,
        start_index: int,
        subcommand: str,
        allow_include_deleted: bool = False,
    ) -> tuple[dict[str, object], int]:
        payload: dict[str, object] = {}
        index = start_index
        while index < len(tokens):
            token = tokens[index]
            if token == "--id":
                self._set_journey_reference(
                    payload,
                    key="journeyId",
                    value=self._require_value(tokens, index, token),
                    subcommand=subcommand,
                )
                index += 2
                continue
            if token == "--label":
                self._set_journey_reference(
                    payload,
                    key="journeyLabel",
                    value=self._require_value(tokens, index, token),
                    subcommand=subcommand,
                )
                index += 2
                continue
            if allow_include_deleted and token == "--include-deleted":
                payload["includeDeleted"] = True
                index += 1
                continue
            if token.startswith("--"):
                break
            self._set_journey_reference(
                payload,
                key="journeyId",
                value=token,
                subcommand=subcommand,
            )
            index += 1
            continue
        if "journeyId" not in payload and "journeyLabel" not in payload:
            raise ValidationError(f"/circulation {subcommand} requires a journey id or --label.")
        return payload, index

    def _set_journey_reference(
        self,
        payload: dict[str, object],
        *,
        key: str,
        value: str,
        subcommand: str,
    ) -> None:
        if "journeyId" in payload or "journeyLabel" in payload:
            raise ValidationError(f"/circulation {subcommand} accepts only one journey reference.")
        payload[key] = value

    def _append_multi_value(self, payload: dict[str, object], key: str, value: str) -> None:
        existing = payload.get(key)
        if not isinstance(existing, list):
            payload[key] = [value]
            return
        existing.append(value)

    def _parse_practice(self, tokens: list[str]) -> ParsedCirculationCommand:
        if len(tokens) == 1:
            return ParsedCirculationCommand(
                operation="circulatio.practice.generate",
                payload={},
                subcommand="practice",
            )
        if tokens[1] in {"accept", "skip"}:
            if len(tokens) < 3:
                raise ValidationError(
                    f"/circulation practice {tokens[1]} requires a practice session id."
                )
            payload: dict[str, object] = {
                "practiceSessionId": tokens[2],
                "action": "accepted" if tokens[1] == "accept" else "skipped",
            }
            index = 3
            while index < len(tokens):
                token = tokens[index]
                if token == "--note":
                    payload["note"] = self._require_value(tokens, index, token)
                    index += 2
                    continue
                if token == "--activation-before":
                    payload["activationBefore"] = self._require_value(tokens, index, token)
                    index += 2
                    continue
                note = " ".join(tokens[index:]).strip()
                if note:
                    payload["note"] = note
                break
            return ParsedCirculationCommand(
                operation="circulatio.practice.respond",
                payload=payload,
                subcommand=f"practice {tokens[1]}",
            )

        payload = self._parse_window_flags(tokens[1:])
        if "--persist" in tokens[1:]:
            persist_index = tokens.index("--persist")
            payload["persist"] = (
                self._require_value(tokens, persist_index, "--persist").lower() != "false"
            )
        question_tokens: list[str] = []
        index = 1
        while index < len(tokens):
            token = tokens[index]
            if token in {"--window-start", "--window-end", "--persist"}:
                index += 2
                continue
            question_tokens.append(token)
            index += 1
        explicit_question = " ".join(question_tokens).strip()
        if explicit_question:
            payload["explicitQuestion"] = explicit_question
        return ParsedCirculationCommand(
            operation="circulatio.practice.generate",
            payload=payload,
            subcommand="practice",
        )

    def _parse_brief(self, tokens: list[str]) -> ParsedCirculationCommand:
        if len(tokens) == 1:
            return ParsedCirculationCommand(
                operation="circulatio.briefs.generate",
                payload={},
                subcommand="brief",
            )
        action_map = {
            "show": "shown",
            "dismiss": "dismissed",
            "done": "acted_on",
            "delete": "deleted",
        }
        if tokens[1] in action_map:
            if len(tokens) < 3:
                raise ValidationError(f"/circulation brief {tokens[1]} requires a brief id.")
            payload: dict[str, object] = {
                "briefId": tokens[2],
                "action": action_map[tokens[1]],
            }
            if len(tokens) > 3:
                payload["note"] = " ".join(tokens[3:]).strip()
            return ParsedCirculationCommand(
                operation="circulatio.briefs.respond",
                payload=payload,
                subcommand=f"brief {tokens[1]}",
            )
        payload = self._parse_window_flags(tokens[1:])
        index = 1
        while index < len(tokens):
            token = tokens[index]
            if token in {"--window-start", "--window-end"}:
                index += 2
                continue
            if token == "--source":
                payload["source"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--limit":
                payload["limit"] = int(self._require_value(tokens, index, token))
                index += 2
                continue
            raise ValidationError(f"Unknown /circulation brief option: {token}")
        return ParsedCirculationCommand(
            operation="circulatio.briefs.generate",
            payload=payload,
            subcommand="brief",
        )

    def _parse_revise(self, tokens: list[str]) -> ParsedCirculationCommand:
        if len(tokens) < 3:
            raise ValidationError("/circulation revise requires an entity type and entity id.")
        payload: dict[str, object] = {
            "entityType": tokens[1],
            "entityId": tokens[2],
            "replacement": {},
        }
        index = 3
        while index < len(tokens):
            token = tokens[index]
            if token == "--note":
                payload["revisionNote"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--set":
                assignment = self._require_value(tokens, index, token)
                key, separator, value = assignment.partition("=")
                if not separator:
                    raise ValidationError("/circulation revise --set expects field=value.")
                replacement = payload["replacement"]
                assert isinstance(replacement, dict)
                replacement[key] = self._coerce_value(value)
                index += 2
                continue
            raise ValidationError(f"Unknown /circulation revise option: {token}")
        if not payload.get("revisionNote"):
            raise ValidationError("/circulation revise requires --note.")
        if not payload["replacement"]:
            payload.pop("replacement")
        return ParsedCirculationCommand(
            operation="circulatio.entity.revise",
            payload=payload,
            subcommand="revise",
        )

    def _parse_delete(self, tokens: list[str]) -> ParsedCirculationCommand:
        if len(tokens) < 3:
            raise ValidationError("/circulation delete requires an entity type and entity id.")
        payload: dict[str, object] = {
            "entityType": tokens[1],
            "entityId": tokens[2],
            "mode": "tombstone",
        }
        index = 3
        while index < len(tokens):
            token = tokens[index]
            if token == "--mode":
                payload["mode"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--reason":
                payload["reason"] = self._require_value(tokens, index, token)
                index += 2
                continue
            raise ValidationError(f"Unknown /circulation delete option: {token}")
        return ParsedCirculationCommand(
            operation="circulatio.entity.delete",
            payload=payload,
            subcommand="delete",
        )

    def _coerce_value(self, raw_value: str) -> object:
        if raw_value in {"true", "false", "null"}:
            return json.loads(raw_value)
        try:
            if raw_value.startswith(("{", "[", '"')):
                return json.loads(raw_value)
        except json.JSONDecodeError:
            return raw_value
        try:
            return int(raw_value)
        except ValueError:
            pass
        try:
            return float(raw_value)
        except ValueError:
            pass
        return raw_value

    def _strip_outer_quotes(self, text: str) -> str:
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
            return text[1:-1].strip()
        return text

    def _require_value(self, tokens: list[str], index: int, flag: str) -> str:
        if index + 1 >= len(tokens):
            raise ValidationError(f"{flag} requires a value.")
        return tokens[index + 1]

    def _parse_window_flags(self, tokens: list[str]) -> dict[str, object]:
        payload: dict[str, object] = {}
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token == "--window-start":
                payload["windowStart"] = self._require_value(tokens, index, token)
                index += 2
                continue
            if token == "--window-end":
                payload["windowEnd"] = self._require_value(tokens, index, token)
                index += 2
                continue
            index += 1
        return payload
