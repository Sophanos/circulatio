from __future__ import annotations

from copy import deepcopy

from ..domain.types import AmplificationSourceSummary

_TRUSTED_AMPLIFICATION_SOURCES: tuple[AmplificationSourceSummary, ...] = (
    {
        "label": "Symbolonline",
        "url": "https://symbolonline.eu/index.php?title=Hauptseite",
        "kind": "symbol_reference",
        "language": "de",
        "notes": (
            "Curated symbol reference with explicit Jungian/depth-psychology orientation. "
            "Prefer first for compact symbol amplification."
        ),
    },
    {
        "label": "Carl Jung Depth Psychology",
        "url": "https://carljungdepthpsychologysite.blog/",
        "kind": "depth_psychology_archive",
        "language": "en",
        "notes": (
            "Secondary archive/commentary source. Useful for Jungian exposition, "
            "but treat as lower authority than primary texts or curated reference works."
        ),
    },
)


def default_trusted_amplification_sources() -> list[AmplificationSourceSummary]:
    return deepcopy(list(_TRUSTED_AMPLIFICATION_SOURCES))


__all__ = ["default_trusted_amplification_sources"]
