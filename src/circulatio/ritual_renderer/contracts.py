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


class RitualRenderOptions(TypedDict, total=False):
    mockProviders: bool
    dryRun: bool
    surfaces: list[str]
    publicBasePath: str
    providerProfile: str
    chutesTokenEnv: str
    transcribeCaptions: bool
    requestTimeoutSeconds: int
    maxCostUsd: float
    videoImage: str
    musicSteps: int
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
    surfaces: Required[dict[str, object]]
    timeline: Required[list[dict[str, object]]]
    interaction: Required[dict[str, object]]
    safety: Required[dict[str, object]]
    render: Required[dict[str, object]]


__all__ = ["AssetRef", "CaptionSegment", "RitualArtifactManifest", "RitualRenderOptions"]
