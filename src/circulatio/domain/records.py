from __future__ import annotations

from typing import Literal

RecordStatus = Literal["active", "revised", "archived", "deleted"]
DeletionMode = Literal["tombstone", "erase"]
DecisionStatus = Literal["pending", "approved", "rejected", "superseded"]
RevisionReason = Literal["user_requested", "incorrect", "privacy", "new_information", "other"]
MaterialSource = Literal["hermes_command", "hermes_ui", "import", "system"]
ContextSnapshotSource = Literal[
    "current-conversation",
    "circulatio-backend",
    "circulatio-life-os",
    "hermes-life-os",
    "manual-session-context",
    "seed-demo",
]
