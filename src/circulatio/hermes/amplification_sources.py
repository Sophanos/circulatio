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
            "Primary amplification source. Curated symbol reference with explicit "
            "Jungian/depth-psychology orientation. Prefer first for compact symbol "
            "amplification."
        ),
    },
    {
        "label": "ARAS",
        "url": "https://aras.org/",
        "kind": "scholarly_reference",
        "language": "en",
        "notes": (
            "Cross-cultural archetypal symbolism archive. Use for image-based, ritual, mythic, "
            "and cultural amplification with stronger scholarly framing."
        ),
    },
    {
        "label": "Jung Lexicon",
        "url": "https://jungpage.org/learn/jung-lexicon",
        "kind": "scholarly_reference",
        "language": "en",
        "notes": (
            "Use for Jungian method and terminology such as amplification, archetype, shadow, "
            "anima/animus, and Self. Better for concepts than symbol lookup."
        ),
    },
    {
        "label": "Traumarbeit Dictionary of Symbols",
        "url": "https://traumarbeit.org/en/dictionary-of-symbols/",
        "kind": "symbol_reference",
        "language": "en",
        "notes": (
            "Depth-psychology-oriented symbol notes that explicitly avoid one fixed meaning. "
            "Good secondary check after personal association and Symbolonline."
        ),
    },
    {
        "label": "Warburg Iconographic Database",
        "url": "https://iconographic.warburg.sas.ac.uk/",
        "kind": "scholarly_reference",
        "language": "en",
        "notes": (
            "Use for iconographic amplification across mythology, religion, allegory, ritual, "
            "literature, and art history."
        ),
    },
    {
        "label": "Iconclass",
        "url": "https://iconclass.org/",
        "kind": "scholarly_reference",
        "language": "en",
        "notes": (
            "Art-historical classification system for motifs, figures, gestures, animals, "
            "objects, saints, and mythological scenes."
        ),
    },
    {
        "label": "Theoi Project",
        "url": "https://www.theoi.com/",
        "kind": "primary_text",
        "language": "en",
        "notes": (
            "Strong for Greek myth amplification through deities, monsters, attributes, "
            "classical texts, and ancient art."
        ),
    },
    {
        "label": "Internet Sacred Text Archive",
        "url": "https://sacred-texts.com/index.htm",
        "kind": "primary_text",
        "language": "en",
        "notes": (
            "Use for primary or older religious, mythological, esoteric, and folklore texts "
            "when a symbol calls for source material rather than summary."
        ),
    },
    {
        "label": "Stith Thompson Motif-Index",
        "url": "https://www.ruthenia.ru/folklore/thompson/d.htm",
        "kind": "scholarly_reference",
        "language": "en",
        "notes": (
            "Use when a dream image resembles a fairy-tale or folklore motif such as helpers, "
            "tests, taboo, transformation, magical objects, or animals."
        ),
    },
    {
        "label": "Adam McLean Alchemy Website",
        "url": "https://www.alchemywebsite.com/emblems.html",
        "kind": "scholarly_reference",
        "language": "en",
        "notes": (
            "Use for alchemical amplification, emblem imagery, and symbolic layers relevant to "
            "Jungian alchemical reading."
        ),
    },
    {
        "label": "Internet Archive Symbol Dictionaries",
        "url": "https://archive.org/details/dictionaryofsymb00cirl",
        "kind": "scholarly_reference",
        "language": "en",
        "notes": (
            "Entry point for classic symbol lexicons such as Cirlot and Chevalier when a deeper "
            "lexical comparison is useful."
        ),
    },
    {
        "label": "Carl Jung Depth Psychology",
        "url": "https://carljungdepthpsychologysite.blog/",
        "kind": "depth_psychology_archive",
        "language": "en",
        "notes": (
            "Secondary archive/commentary source. Useful for Jungian exposition and essays, but "
            "treat as lower authority than primary texts or curated reference works."
        ),
    },
)


def default_trusted_amplification_sources() -> list[AmplificationSourceSummary]:
    return deepcopy(list(_TRUSTED_AMPLIFICATION_SOURCES))


__all__ = ["default_trusted_amplification_sources"]
