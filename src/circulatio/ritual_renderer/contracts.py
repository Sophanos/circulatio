from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict


class AssetRef(TypedDict, total=False):
    src: Required[str | None]
    mimeType: NotRequired[str | None]
    provider: NotRequired[str | None]
    durationMs: NotRequired[int | None]
    checksum: NotRequired[str | None]


class CaptionSegment(TypedDict):
    id: str
    startMs: int
    endMs: int
    text: str


class RitualManifestSection(TypedDict, total=False):
    id: Required[str]
    title: Required[str]
    startMs: Required[int]
    endMs: Required[int]
    kind: Required[Literal["arrival", "breath", "image", "reflection", "closing"]]
    preferredLens: NotRequired[Literal["cinema", "photo", "breath", "meditation", "body"]]
    capturePrompt: NotRequired[str]
    transcript: NotRequired[str]
    captionCount: NotRequired[int]
    skippable: NotRequired[bool]
    channels: NotRequired[dict[str, bool]]


class RitualRenderOptions(TypedDict, total=False):
    mockProviders: bool
    dryRun: bool
    surfaces: list[str]
    publicBasePath: str
    providerProfile: str
    chutesTokenEnv: str
    openaiApiKeyEnv: str
    transcribeCaptions: bool
    transcriptionProvider: Literal["fallback", "chutes", "openai"]
    openaiTranscriptionModel: str
    openaiTranscriptionResponseFormat: str
    requestTimeoutSeconds: int
    maxCostUsd: float
    videoImage: str
    musicSteps: int
    musicDurationSeconds: int
    allowBetaMusic: bool
    allowBetaVideo: bool


class RitualArtifactManifest(TypedDict, total=False):
    schemaVersion: Required[Literal["hermes_ritual_artifact.v1"]]
    artifactId: Required[str]
    planId: Required[str]
    createdAt: Required[str]
    title: Required[str]
    description: Required[str]
    privacyClass: Required[str]
    locale: Required[str]
    sourceRefs: Required[list[dict[str, object]]]
    durationMs: Required[int]
    sections: Required[list[RitualManifestSection]]
    surfaces: Required[dict[str, object]]
    timeline: Required[list[dict[str, object]]]
    interaction: Required[dict[str, object]]
    safety: Required[dict[str, object]]
    render: Required[dict[str, object]]


__all__ = [
    "AssetRef",
    "CaptionSegment",
    "RitualArtifactManifest",
    "RitualManifestSection",
    "RitualRenderOptions",
]
