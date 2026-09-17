from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class LocalTaskContentBindingError(ValueError):
    pass


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LocalTaskContentBindingError(
                f"duplicate JSON object key: {key}"
            )
        result[key] = value
    return result


def _reject_non_standard_constant(value: str) -> None:
    raise LocalTaskContentBindingError(
        f"non-standard JSON constant is not allowed: {value}"
    )


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise LocalTaskContentBindingError(
                f"non-finite JSON number at {path}"
            )
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return

    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise LocalTaskContentBindingError(
                    f"JSON object key at {path} must be a string"
                )
            _validate_json_value(item, f"{path}.{key}")
        return

    raise LocalTaskContentBindingError(
        f"unsupported JSON value at {path}: {type(value).__name__}"
    )


def parse_local_task_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_non_standard_constant,
        )
    except json.JSONDecodeError as exc:
        raise LocalTaskContentBindingError(
            f"invalid JSON: {exc.msg}"
        ) from exc

    if not isinstance(parsed, dict):
        raise LocalTaskContentBindingError(
            "local-task JSON root must be an object"
        )

    _validate_json_value(parsed)
    return parsed


def canonical_local_task_bytes(task: dict[str, Any]) -> bytes:
    if not isinstance(task, dict):
        raise LocalTaskContentBindingError(
            "local-task payload must be an object"
        )

    _validate_json_value(task)

    try:
        rendered = json.dumps(
            task,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return rendered.encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LocalTaskContentBindingError(
            f"cannot canonicalize local-task payload: {exc}"
        ) from exc


def compute_local_task_digest(task: dict[str, Any]) -> str:
    canonical = canonical_local_task_bytes(task)
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def is_valid_local_task_digest(value: object) -> bool:
    return isinstance(value, str) and _DIGEST_RE.fullmatch(value) is not None
