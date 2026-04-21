from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Literal, cast

CaseSplit = Literal["train", "dev", "holdout", "redteam", "regression"]
CaseSeverity = Literal["blocking", "major", "minor"]
CaseGateType = Literal["constraint", "deterministic", "execution", "judge"]

_ALLOWED_SPLITS = {"train", "dev", "holdout", "redteam", "regression"}
_ALLOWED_SEVERITIES = {"blocking", "major", "minor"}
_ALLOWED_GATE_TYPES = {"constraint", "deterministic", "execution", "judge"}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _normalized_schema_version(payload: dict[str, object]) -> int:
    raw = payload.get("schemaVersion")
    if raw is None:
        return 1
    if not isinstance(raw, int) or raw < 1:
        raise ValueError("schemaVersion must be a positive integer when provided.")
    return raw


def _normalized_split(payload: dict[str, object], *, dataset_name: str) -> CaseSplit:
    raw = str(payload.get("split") or "dev").strip().lower()
    if raw not in _ALLOWED_SPLITS:
        raise ValueError(f"{dataset_name} has unsupported split '{raw}'.")
    return cast(CaseSplit, raw)


def _normalized_severity(payload: dict[str, object], *, dataset_name: str) -> CaseSeverity:
    raw = str(payload.get("severity") or "blocking").strip().lower()
    if raw not in _ALLOWED_SEVERITIES:
        raise ValueError(f"{dataset_name} has unsupported severity '{raw}'.")
    return cast(CaseSeverity, raw)


def _normalized_gate_type(payload: dict[str, object], *, dataset_name: str) -> CaseGateType:
    raw = str(payload.get("gateType") or "deterministic").strip().lower()
    if raw not in _ALLOWED_GATE_TYPES:
        raise ValueError(f"{dataset_name} has unsupported gateType '{raw}'.")
    return cast(CaseGateType, raw)


def _normalize_case(payload: dict[str, object], *, path: Path) -> dict[str, object]:
    dataset_name = path.name
    schema_version = _normalized_schema_version(payload)
    normalized = dict(payload)
    normalized["schemaVersion"] = schema_version
    normalized["targetKinds"] = _string_list(payload.get("targetKinds"))
    normalized["split"] = _normalized_split(payload, dataset_name=dataset_name)
    normalized["severity"] = _normalized_severity(payload, dataset_name=dataset_name)
    normalized["gateType"] = _normalized_gate_type(payload, dataset_name=dataset_name)
    normalized["_dataset"] = dataset_name
    normalized["_datasetPath"] = str(path)
    return normalized


def load_jsonl_cases(path: Path) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number} must be a JSON object.")
        try:
            normalized = _normalize_case(payload, path=path)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number} {exc}") from exc
        cases.append(normalized)
    return cases


def case_target_kinds(case: dict[str, object]) -> list[str]:
    return _string_list(case.get("targetKinds"))


def case_execution_config(case: dict[str, object]) -> dict[str, object] | None:
    value = case.get("execution")
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def case_judge_config(case: dict[str, object]) -> dict[str, object] | None:
    value = case.get("judge")
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def load_case_set(
    paths: tuple[Path, ...] | list[Path],
    *,
    split_filter: Iterable[str] | None = None,
) -> list[dict[str, object]]:
    allowed_splits = {str(item).strip().lower() for item in split_filter or () if str(item).strip()}
    case_ids: set[str] = set()
    cases: list[dict[str, object]] = []
    for path in paths:
        for payload in load_jsonl_cases(path):
            case_id = str(payload.get("caseId") or "").strip()
            if not case_id:
                raise ValueError(f"{path} contains an eval case without caseId.")
            if case_id in case_ids:
                raise ValueError(f"Duplicate eval case id detected: {case_id}")
            if allowed_splits and str(payload.get("split") or "") not in allowed_splits:
                continue
            case_ids.add(case_id)
            cases.append(payload)
    return cases
