#!/usr/bin/env python3
"""
Circulatio Dream Interpretation Engine

Interprets dreams through Jungian amplification method with cultural context.
"""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Symbol:
    name: str
    category: str
    personal_meaning: str
    frequency: int = 1
    last_appeared: str = ""
    cultural_references: List[Dict] = None
    archetypal_resonance: str = ""


@dataclass
class Dream:
    id: str
    date: str
    narrative: str
    symbols: List[Symbol]
    archetypes: List[str]
    emotional_tone: str
    alchemical_stage: str
    life_events: List[str]
    interpretation: str = ""


class CirculatioInterpreter:
    """Main dream interpretation engine."""
    
    def __init__(self, culture: str = "Universal-Jungian", stage: str = "unknown"):
        self.culture = culture
        self.current_stage = stage
        self.symbol_dictionary: Dict[str, Symbol] = {}
        self.dream_history: List[Dream] = []
        
    def interpret_dream(self, narrative: str, life_context: str = "") -> Dict[str, Any]:
        """
        Main interpretation pipeline.
        
        Args:
            narrative: The dream description
            life_context: Recent life events or concerns
            
        Returns:
            Complete interpretation with amplification
        """
        # Step 1: Extract symbols
        symbols = self._extract_symbols(narrative)
        
        # Step 2: Check personal history
        for symbol in symbols:
            self._update_symbol_history(symbol)
        
        # Step 3: Detect alchemical stage
        detected_stage = self._detect_stage(narrative, symbols)
        
        # Step 4: Identify archetypes
        archetypes = self._identify_archetypes(symbols)
        
        # Step 5: Apply amplification
        amplification = self._amplify_symbols(symbols)
        
        # Step 6: Connect to life
        life_connections = self._connect_to_life(symbols, life_context)
        
        # Step 7: Generate interpretation
        interpretation = self._generate_interpretation(
            narrative, symbols, amplification, life_connections
        )
        
        # Step 8: Update circulatio graph
        dream_id = self._store_dream(
            narrative, symbols, archetypes, detected_stage, life_context
        )
        
        return {
            "dream_id": dream_id,
            "detected_stage": detected_stage,
            "symbols": [asdict(s) for s in symbols],
            "archetypes": archetypes,
            "amplification": amplification,
            "life_connections": life_connections,
            "interpretation": interpretation,
            "suggested_actions": self._suggest_actions(symbols, detected_stage)
        }
    
    def _extract_symbols(self, narrative: str) -> List[Symbol]:
        """Extract key symbols from dream narrative."""
        # Basic extraction - would be enhanced with NLP
        symbols = []
        
        # Common symbol patterns
        patterns = {
            "animal": r"\b(snake|raven|crow|bird|wolf|bear|deer|fish|spider)\b",
            "element": r"\b(water|fire|earth|air|wind|ocean|mountain|forest)\b",
            "figure": r"\b(old man|old woman|child|mother|father|stranger|shadow)\b",
            "place": r"\b(house|basement|attic|forest|desert|cave|bridge|door)\b",
            "object": r"\b(key|mirror|ring|book|chest|ladder|window|clock)\b"
        }
        
        for category, pattern in patterns.items():
            matches = re.findall(pattern, narrative.lower())
            for match in set(matches):
                symbols.append(Symbol(
                    name=match,
                    category=category,
                    personal_meaning=""
                ))
        
        return symbols
    
    def _update_symbol_history(self, symbol: Symbol):
        """Update personal symbol dictionary."""
        existing = self.symbol_dictionary.get(symbol.name)
        if existing:
            existing.frequency += 1
            existing.last_appeared = datetime.now().isoformat()
        else:
            symbol.frequency = 1
            symbol.last_appeared = datetime.now().isoformat()
            self.symbol_dictionary[symbol.name] = symbol
    
    def _detect_stage(self, narrative: str, symbols: List[Symbol]) -> str:
        """Detect alchemical stage from dream content."""
        narrative_lower = narrative.lower()
        
        # Stage indicators
        nigredo_indicators = ["dark", "black", "decay", "underground", "lost", "falling", "death", "shadow"]
        albedo_indicators = ["white", "silver", "washing", "clean", "clear", "mirror", "water", "snow"]
        citrinitas_indicators = ["gold", "yellow", "dawn", "sunrise", "light", "insight", "dawning"]
        rubedo_indicators = ["red", "rose", "union", "marriage", "phoenix", "blood", "wine", "integration"]
        
        scores = {
            "nigredo": sum(1 for w in nigredo_indicators if w in narrative_lower),
            "albedo": sum(1 for w in albedo_indicators if w in narrative_lower),
            "citrinitas": sum(1 for w in citrinitas_indicators if w in narrative_lower),
            "rubedo": sum(1 for w in rubedo_indicators if w in narrative_lower)
        }
        
        # Check symbol categories
        dark_symbols = ["snake", "raven", "crow", "shadow", "cave", "basement"]
        light_symbols = ["dove", "swan", "mirror", "water"]
        
        for symbol in symbols:
            if symbol.name in dark_symbols:
                scores["nigredo"] += 2
            if symbol.name in light_symbols:
                scores["albedo"] += 2
        
        detected = max(scores, key=scores.get)
        return detected if scores[detected] > 0 else self.current_stage
    
    def _identify_archetypes(self, symbols: List[Symbol]) -> List[str]:
        """Identify archetypes present in dream."""
        archetypes = []
        
        symbol_archetype_map = {
            "shadow": ["shadow", "dark figure", "stranger"],
            "anima": ["woman", "maiden", "goddess", "water"],
            "animus": ["man", "warrior", "king", "hero"],
            "wise_old_man": ["old man", "sage", "elder", "teacher"],
            "great_mother": ["mother", "earth", "ocean", "cave"],
            "self": ["mandala", "ring", "circle", "sun", "gold"]
        }
        
        symbol_names = [s.name.lower() for s in symbols]
        
        for archetype, indicators in symbol_archetype_map.items():
            if any(ind in symbol_names for ind in indicators):
                archetypes.append(archetype)
        
        return archetypes if archetypes else ["unknown"]
    
    def _amplify_symbols(self, symbols: List[Symbol]) -> Dict[str, Any]:
        """Apply amplification through cultural database."""
        amplifications = {}
        
        # Load cultural reference for user's culture
        culture_db = self._load_cultural_db()
        
        for symbol in symbols:
            personal = f"This {symbol.name} has appeared {symbol.frequency} time(s) in your dreams."
            if symbol.frequency > 1:
                personal += " This is a significant recurring symbol."
            
            cultural = culture_db.get(symbol.name, {
                "myth": "Universal symbol",
                "meaning": "Requires personal amplification"
            })
            
            archetypal = self._get_archetypal_meaning(symbol)
            
            amplifications[symbol.name] = {
                "personal": personal,
                "cultural": cultural,
                "archetypal": archetypal,
                "synthesis": f"Your {symbol.name} represents {archetypal} emerging through your {self.culture} heritage."
            }
        
        return amplifications
    
    def _load_cultural_db(self) -> Dict:
        """Load cultural amplification database."""
        # Placeholder - would load from references/cultural-myths/{culture}.md
        return {
            "snake": {
                "myth": "World Serpent (Jörmungandr in Norse, Shesha in Hindu)",
                "meaning": "Transformation, cyclical time, wisdom beyond duality"
            },
            "raven": {
                "myth": "Odin's messengers Huginn (Thought) and Muninn (Memory)",
                "meaning": "Conscious and unconscious, bringing wisdom from shadows"
            },
            "water": {
                "myth": "The Well of Urd (Norse), the Ganges (Hindu)",
                "meaning": "Unconscious, emotion, source of life and wisdom"
            }
        }
    
    def _get_archetypal_meaning(self, symbol: Symbol) -> str:
        """Get archetypal meaning of symbol."""
        archetypal_map = {
            "snake": "the Self in its transformative aspect — what must die to be reborn",
            "raven": "the Shadow bringing messages from the unconscious",
            "bird": "the transcendent function, spiritual aspiration",
            "water": "the collective unconscious, emotional depth",
            "fire": "transformation, passion, the spark of consciousness",
            "mountain": "the Self, the highest achievement of the ego",
            "house": "the psyche, with levels representing conscious/unconscious",
            "bridge": "the transcendent function, connecting opposites",
            "door": "opportunity, threshold between states",
            "mirror": "reflection, the anima/animus, seeing oneself truly"
        }
        return archetypal_map.get(symbol.name, "a personal symbol requiring exploration")
    
    def _connect_to_life(self, symbols: List[Symbol], life_context: str) -> List[str]:
        """Connect dream symbols to waking life."""
        connections = []
        
        if life_context:
            connections.append(f"Recent context: {life_context}")
        
        # Check for compensatory function
        for symbol in symbols:
            if symbol.name in ["shadow", "dark", "underground"]:
                connections.append("Compensatory: Your ego may be too identified with the light; the dream brings shadow integration")
            if symbol.name in ["water", "ocean", "flood"]:
                connections.append("Compensatory: Rationality may be dominating; dream brings emotional awareness")
        
        return connections if connections else ["No obvious day residue — consider archetypal activation"]
    
    def _generate_interpretation(
        self, narrative: str, symbols: List[Symbol],
        amplification: Dict, life_connections: List[str]
    ) -> str:
        """Generate final interpretation text."""
        parts = []
        
        # Opening
        parts.append(f"**Dream:** {narrative}\n")
        
        # Alchemical stage
        stage = self._detect_stage(narrative, symbols)
        parts.append(f"**Alchemical Stage:** {stage.upper()}")
        parts.append(f"This dream carries the signature of the {stage} — {self._stage_description(stage)}\n")
        
        # Symbols
        if symbols:
            parts.append("**Key Symbols:**")
            for symbol in symbols:
                amp = amplification.get(symbol.name, {})
                parts.append(f"- **{symbol.name.capitalize()}**: {amp.get('synthesis', 'Personal symbol')}")
            parts.append("")
        
        # Life connections
        if life_connections:
            parts.append("**Life Connections:**")
            for conn in life_connections:
                parts.append(f"- {conn}")
            parts.append("")
        
        # Closing
        parts.append(f"**The Work:** This dream invites {self._stage_invitation(stage)}")
        
        return "\n".join(parts)
    
    def _stage_description(self, stage: str) -> str:
        """Get stage description."""
        descriptions = {
            "nigredo": "the darkness before transformation, the descent into shadow",
            "albedo": "the washing away of impurities, gaining clarity",
            "citrinitas": "the dawning of insight, the golden shadow emerging",
            "rubedo": "the integration of opposites, the sacred marriage"
        }
        return descriptions.get(stage, "a stage in the Great Work")
    
    def _stage_invitation(self, stage: str) -> str:
        """Get stage-specific invitation."""
        invitations = {
            "nigredo": "you to descend into what has been hidden, to find the gold in darkness",
            "albedo": "you to release what no longer serves, to wash away ego attachments",
            "citrinitas": "you to open to new insight, to welcome the golden shadow",
            "rubedo": "you to rest in wholeness, to allow the union of opposites"
        }
        return invitations.get(stage, "you to continue the Great Work")
    
    def _suggest_actions(self, symbols: List[Symbol], stage: str) -> List[str]:
        """Suggest follow-up actions."""
        actions = [f"/circulatio meditate {stage}"]
        
        if len(symbols) > 0:
            actions.append(f"/circulatio amplification {symbols[0].name}")
        
        if any(s.name in ["old man", "old woman", "child", "stranger"] for s in symbols):
            figure = next((s.name for s in symbols if s.name in ["old man", "old woman", "child", "stranger"]), "figure")
            actions.append(f"/circulatio active {figure}")
        
        actions.append("/circulatio reflect [your waking insights]")
        
        return actions
    
    def _store_dream(self, narrative: str, symbols: List[Symbol],
                    archetypes: List[str], stage: str, life_context: str) -> str:
        """Store dream in circulatio graph."""
        dream_id = f"dream_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        dream = Dream(
            id=dream_id,
            date=datetime.now().isoformat(),
            narrative=narrative,
            symbols=symbols,
            archetypes=archetypes,
            emotional_tone="",
            alchemical_stage=stage,
            life_events=[life_context] if life_context else []
        )
        
        self.dream_history.append(dream)
        return dream_id


# CLI usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python dream_interpreter.py 'dream narrative'")
        sys.exit(1)
    
    narrative = sys.argv[1]
    culture = sys.argv[2] if len(sys.argv) > 2 else "Universal-Jungian"
    
    interpreter = CirculatioInterpreter(culture=culture)
    result = interpreter.interpret_dream(narrative)
    
    print(json.dumps(result, indent=2, default=str))
