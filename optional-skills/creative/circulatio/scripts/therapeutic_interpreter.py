#!/usr/bin/env python3
"""
Circulatio Therapeutic Interpreter

A depth psychological engine that interprets dreams through:
- Linguistic analysis (ego vs archetype detection)
- Complex tracking and history
- Action/Intent/Dynamics/Outcome distillation
- The two standpoints (causal and prospective)
- Therapeutic confrontation when needed
"""

import json
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DreamPhase(Enum):
    EXPOSITION = "exposition"
    PERIPETIA = "peripetia"
    LYSIS = "lysis"


class CompensationType(Enum):
    OPPOSITE = "opposite"      # One-sided conscious attitude
    VARIATIONS = "variations"  # Balanced position
    EMPHASIS = "emphasis"      # Correct attitude


@dataclass
class LinguisticMarker:
    """Analysis of who is speaking in the dream."""
    subject: str              # "I", "we", "he", "they", third-person
    voice: str               # "active", "passive", "reflexive"
    position: str            # "ego", "archetype", "complex", "observer"
    
    def analyze(self) -> str:
        if self.subject == "I" and self.voice == "passive":
            return f"Ego in victim position - situation happening TO dreamer"
        elif self.subject == "I" and self.voice == "active":
            return f"Ego engaging with unconscious material"
        elif self.subject in ["he", "she", "they"] and self.voice == "third-person":
            return f"Archetypal activation - watching from outside"
        elif self.subject == "we":
            return f"Ego-Self dialogue - integration process"
        return "Ambiguous - needs exploration"


@dataclass
class DramaticStructure:
    """The three acts of the dream theater."""
    exposition: Dict          # Setting, atmosphere, initial state
    peripetia: List[Dict]    # Actions, what happens
    lysis: Dict              # Outcome, final image
    
    def distill(self) -> Dict[str, Any]:
        """Extract action, intent, dynamics, outcome."""
        return {
            "action": self._extract_action(),
            "intent": self._extract_intent(),
            "dynamics": self._extract_dynamics(),
            "outcome": self.lysis.get("final_state", "unclear")
        }
    
    def _extract_action(self) -> str:
        """What physically happens in the dream."""
        actions = []
        for event in self.peripetia:
            verb = event.get("verb", "")
            obj = event.get("object", "")
            if verb:
                actions.append(f"{verb} {obj}".strip())
        return "; ".join(actions) if actions else "unclear"
    
    def _extract_intent(self) -> str:
        """What the psyche is trying to achieve."""
        # Look for goal-oriented language
        goals = []
        for event in self.peripetia:
            intent = event.get("intent", "")
            if intent:
                goals.append(intent)
        
        # Infer from outcome
        if self.lysis.get("final_state") == "escape":
            goals.append("avoid confrontation")
        elif self.lysis.get("final_state") == "union":
            goals.append("integration")
        elif self.lysis.get("final_state") == "transformation":
            goals.append("psychic reorganization")
            
        return "; ".join(goals) if goals else "requires amplification"
    
    def _extract_dynamics(self) -> Dict[str, str]:
        """The relationship patterns (pursuer-pursued, etc.)."""
        dynamics = {}
        
        for event in self.peripetia:
            initiator = event.get("initiator", "")
            responder = event.get("responder", "")
            pattern = event.get("pattern", "")
            
            if pattern:
                dynamics["pattern"] = pattern
            if initiator and responder:
                dynamics["relationship"] = f"{initiator} → {responder}"
        
        # Classic patterns
        if "chase" in self._extract_action().lower():
            dynamics["archetypal"] = "shadow pursuing ego (what is avoided)"
        if "fight" in self._extract_action().lower():
            dynamics["archetypal"] = "ego-complex conflict"
        if "embrace" in self._extract_action().lower() or "union" in self._extract_action().lower():
            dynamics["archetypal"] = "conjunctio (sacred marriage)"
            
        return dynamics


@dataclass
class Complex:
    """A psychological complex - the architects of dreams."""
    name: str
    archetypal_core: str           # Shadow, Anima, etc.
    first_appearance: str
    frequency: int = 1
    emotional_charge_evolution: List[Tuple[str, str]] = field(default_factory=list)  # [(date, emotion), ...]
    pattern_triggers: List[str] = field(default_factory=list)
    associated_dreams: List[str] = field(default_factory=list)
    current_status: str = "active"  # active, resolving, integrated
    interpretation_history: List[Dict] = field(default_factory=list)
    
    def get_current_charge(self) -> str:
        """Latest emotional charge."""
        if self.emotional_charge_evolution:
            return self.emotional_charge_evolution[-1][1]
        return "unknown"
    
    def track_evolution(self) -> str:
        """Describe how the complex is evolving."""
        if len(self.emotional_charge_evolution) < 2:
            return "Insufficient data"
        
        first = self.emotional_charge_evolution[0][1]
        last = self.emotional_charge_evolution[-1][1]
        
        # Map emotions to integration stages
        negative = ["disgust", "anger", "fear", "revulsion", "hatred"]
        neutral = ["ambivalence", "curiosity", "neutrality"]
        positive = ["acceptance", "understanding", "compassion", "integration"]
        
        if first in negative and last in neutral:
            return f"Moving from rejection to ambivalence (integration in progress)"
        elif first in negative and last in positive:
            return f"Significant integration - from rejection to acceptance"
        elif last in negative:
            return f"Still rejected - strong ego defense"
        
        return f"Evolution: {first} → {last}"


@dataclass
class InterpretationStandpoint:
    """Causal and Prospective viewpoints."""
    causal: str                   # Why did this happen? (past)
    prospective: str              # What for? (future, purpose)
    synthesis: str                # How they integrate
    
    def analyze(self) -> str:
        return f"""
**Causal (Why?):** {self.causal}

**Prospective (What For?):** {self.prospective}

**Synthesis:** {self.synthesis}
"""


class TherapeuticInterpreter:
    """
    The therapeutic engine - not just interpreting but confronting,
    tracking complexes, and walking beside the dreamer.
    """
    
    def __init__(self, culture: str = "Universal-Jungian"):
        self.culture = culture
        self.complexes: Dict[str, Complex] = {}
        self.dream_history: List[Dict] = []
        self.conscious_attitudes: List[Dict] = []
        
    def interpret(self, dream_narrative: str, conscious_context: str = "") -> Dict[str, Any]:
        """
        Full therapeutic interpretation.
        
        Returns comprehensive analysis including:
        - Linguistic analysis (who is the "I")
        - Dramatic structure (action, intent, dynamics, outcome)
        - Complex detection and history
        - The two standpoints
        - Therapeutic confrontation
        """
        
        # Step 1: Linguistic analysis
        linguistic = self._analyze_language(dream_narrative)
        
        # Step 2: Dramatic structure
        dramatic = self._analyze_structure(dream_narrative)
        
        # Step 3: Complex detection
        detected_complexes = self._detect_complexes(dream_narrative, dramatic)
        
        # Step 4: The two standpoints
        standpoints = self._apply_standpoints(
            dream_narrative, detected_complexes, conscious_context
        )
        
        # Step 5: Compensation analysis
        compensation = self._analyze_compensation(dramatic, conscious_context)
        
        # Step 6: Generate therapeutic response
        therapeutic = self._generate_therapeutic_response(
            dream_narrative,
            linguistic,
            dramatic,
            detected_complexes,
            standpoints,
            compensation
        )
        
        # Store in history
        dream_id = self._store_dream(
            dream_narrative, linguistic, dramatic, 
            detected_complexes, standpoints, compensation
        )
        
        return {
            "dream_id": dream_id,
            "linguistic_analysis": {
                "markers": [m.__dict__ for m in linguistic],
                "summary": self._summarize_linguistic(linguistic)
            },
            "dramatic_structure": {
                "exposition": dramatic.exposition,
                "peripetia": dramatic.peripetia,
                "lysis": dramatic.lysis,
                "distillation": dramatic.distill()
            },
            "complexes": [self._complex_to_dict(c) for c in detected_complexes],
            "standpoints": {
                "causal": standpoints.causal,
                "prospective": standpoints.prospective,
                "synthesis": standpoints.synthesis
            },
            "compensation": {
                "type": compensation.value if compensation else "unclear",
                "analysis": self._compensation_analysis(compensation, conscious_context)
            },
            "therapeutic_response": therapeutic
        }
    
    def _analyze_language(self, narrative: str) -> List[LinguisticMarker]:
        """Analyze linguistic markers - who is the "I"?"""
        markers = []
        
        # Pattern matching for linguistic structures
        patterns = [
            # Passive ego
            (r"I was (chased|attacked|trapped|lost|confused)", "I", "passive", "ego"),
            # Active ego
            (r"I (went|entered|confronted|searched|found|took)", "I", "active", "ego"),
            # Archetypal observation
            (r"(He|She|They) (was|were) (.*)", "he/she/they", "third-person", "archetype"),
            # Integration
            (r"We (were|went|became|united)", "we", "active", "ego-self"),
        ]
        
        for pattern, subject, voice, position in patterns:
            if re.search(pattern, narrative, re.IGNORECASE):
                markers.append(LinguisticMarker(
                    subject=subject,
                    voice=voice,
                    position=position
                ))
        
        return markers
    
    def _summarize_linguistic(self, markers: List[LinguisticMarker]) -> str:
        """Summary of linguistic analysis."""
        if not markers:
            return "Ambiguous - unclear if ego or archetype dominates"
        
        ego_passive = sum(1 for m in markers if m.position == "ego" and m.voice == "passive")
        ego_active = sum(1 for m in markers if m.position == "ego" and m.voice == "active")
        archetypal = sum(1 for m in markers if m.position == "archetype")
        
        if ego_passive > ego_active:
            return "Ego in victim position - fleeing from unconscious contents"
        elif ego_active > ego_passive:
            return "Ego actively engaging - confrontation with unconscious"
        elif archetypal > 0:
            return "Archetypal activation - watching Self from distance"
        
        return "Mixed signals - requires careful amplification"
    
    def _analyze_structure(self, narrative: str) -> DramaticStructure:
        """Parse dream into three dramatic phases."""
        
        # Simple parsing - would be enhanced with NLP
        sentences = narrative.split('.')
        
        exposition = {
            "setting": sentences[0] if sentences else "unclear",
            "atmosphere": self._extract_atmosphere(narrative),
            "initial_state": "unknown"
        }
        
        peripetia = []
        for i, sentence in enumerate(sentences[1:-1], 1):
            peripetia.append({
                "act": i,
                "content": sentence.strip(),
                "verb": self._extract_verb(sentence),
                "object": self._extract_object(sentence),
                "initiator": self._extract_initiator(sentence),
                "responder": self._extract_responder(sentence),
                "pattern": self._extract_pattern(sentence),
                "intent": self._extract_intent_from_sentence(sentence)
            })
        
        lysis = {
            "final_state": self._extract_final_state(sentences[-1] if sentences else ""),
            "ending_image": sentences[-1] if sentences else "unclear",
            "resolution_type": self._determine_resolution(narrative)
        }
        
        return DramaticStructure(
            exposition=exposition,
            peripetia=peripetia,
            lysis=lysis
        )
    
    def _extract_atmosphere(self, narrative: str) -> str:
        """Extract emotional atmosphere."""
        dark_indicators = ["dark", "black", "shadow", "night", "basement", "cave", "forest"]
        light_indicators = ["bright", "white", "sun", "light", "clear", "open"]
        
        dark_count = sum(1 for w in dark_indicators if w in narrative.lower())
        light_count = sum(1 for w in light_indicators if w in narrative.lower())
        
        if dark_count > light_count:
            return "nigredo atmosphere - unconscious material rising"
        elif light_count > dark_count:
            return "albedo/citrinitas atmosphere - illumination"
        return "neutral - requires amplification"
    
    def _extract_verb(self, sentence: str) -> str:
        """Extract main action verb."""
        action_verbs = ["ran", "chased", "found", "entered", "confronted", "fled", 
                       "embraced", "fought", "searched", "descended", "ascended"]
        for verb in action_verbs:
            if verb in sentence.lower():
                return verb
        return ""
    
    def _extract_object(self, sentence: str) -> str:
        """Extract object of action."""
        # Simplified - would use NLP
        return ""
    
    def _extract_initiator(self, sentence: str) -> str:
        """Who starts the action."""
        if "I" in sentence:
            return "ego"
        return "complex/other"
    
    def _extract_responder(self, sentence: str) -> str:
        """Who reacts."""
        if re.search(r"(me|I was)", sentence, re.IGNORECASE):
            return "ego"
        return "complex/other"
    
    def _extract_pattern(self, sentence: str) -> str:
        """Extract relational pattern."""
        if re.search(r"(chased|pursued|fled)", sentence, re.IGNORECASE):
            return "pursuer-pursued"
        if re.search(r"(fought|attacked|defended)", sentence, re.IGNORECASE):
            return "conflict"
        if re.search(r"(embraced|united|married)", sentence, re.IGNORECASE):
            return "union"
        return ""
    
    def _extract_intent_from_sentence(self, sentence: str) -> str:
        """Infer psychological intent."""
        if re.search(r"(search|look|find)", sentence, re.IGNORECASE):
            return "seeking something lost"
        if re.search(r"(flee|escape|run)", sentence, re.IGNORECASE):
            return "avoiding confrontation"
        if re.search(r"(enter|descend|open)", sentence, re.IGNORECASE):
            return "approaching unconscious"
        return ""
    
    def _extract_final_state(self, last_sentence: str) -> str:
        """Determine how the dream ends."""
        if re.search(r"(woke|woke up|awoke)", last_sentence, re.IGNORECASE):
            return "awakening (consciousness intruding)"
        if re.search(r"(escaped|fled|left)", last_sentence, re.IGNORECASE):
            return "escape (avoidance)"
        if re.search(r"(found|united|became|transformed)", last_sentence, re.IGNORECASE):
            return "transformation/union"
        return "unclear"
    
    def _determine_resolution(self, narrative: str) -> str:
        """Determine type of resolution."""
        if "escape" in narrative.lower():
            return "flight - ego avoiding unconscious content"
        if "found" in narrative.lower() or "discovered" in narrative.lower():
            return "discovery - ego encountering unconscious"
        if "united" in narrative.lower() or "merged" in narrative.lower():
            return "integration - conjunctio"
        return "unresolved - requires further dreams"
    
    def _detect_complexes(self, narrative: str, dramatic: DramaticStructure) -> List[Complex]:
        """Detect which complexes are active in this dream."""
        detected = []
        
        # Complex indicators
        complex_patterns = {
            "father": ["father", "dad", "man in uniform", "authority", "general", "military"],
            "mother": ["mother", "mom", "nurturing figure", "overprotective"],
            "authority": ["police", "military", "boss", "teacher", "judge", "uniform"],
            "abandonment": ["left behind", "alone", "deserted", "nobody came"],
            "shadow": ["dark figure", "stranger", "pursuer", "attacker", "unknown"],
            "anima": ["unknown woman", "mysterious woman", "maiden", "goddess"],
            "animus": ["unknown man", "hero", "warrior", "sage"],
            "child": ["child", "baby", "young person", "innocent"],
            "senex": ["old man", "elder", "wise man", "hermit"]
        }
        
        for complex_name, indicators in complex_patterns.items():
            if any(ind in narrative.lower() for ind in indicators):
                # Check if we already track this complex
                existing = self.complexes.get(complex_name)
                
                if existing:
                    existing.frequency += 1
                    existing.associated_dreams.append(datetime.now().isoformat())
                    detected.append(existing)
                else:
                    # Create new complex
                    new_complex = Complex(
                        name=complex_name,
                        archetypal_core=self._map_to_archetype(complex_name),
                        first_appearance=datetime.now().isoformat(),
                        frequency=1,
                        associated_dreams=[datetime.now().isoformat()]
                    )
                    self.complexes[complex_name] = new_complex
                    detected.append(new_complex)
        
        return detected
    
    def _map_to_archetype(self, complex_name: str) -> str:
        """Map complex to archetypal core."""
        mapping = {
            "father": "Senex (Wise Old Man distorted)",
            "mother": "Great Mother",
            "authority": "Senex/Puer dynamic",
            "abandonment": "Orphan",
            "shadow": "Shadow",
            "anima": "Anima",
            "animus": "Animus",
            "child": "Divine Child",
            "senex": "Wise Old Man"
        }
        return mapping.get(complex_name, "Unknown")
    
    def _apply_standpoints(self, narrative: str, complexes: List[Complex], 
                          conscious_context: str) -> InterpretationStandpoint:
        """Apply causal and prospective interpretation."""
        
        # Causal: Why did this happen? (Past)
        causal_parts = []
        for c in complexes:
            if c.name == "father" and "military" in narrative.lower():
                causal_parts.append(
                    f"The {c.name} complex activated by themes of authority. "
                    f"Likely originates in early relationship with father figure."
                )
            elif c.name == "shadow":
                causal_parts.append(
                    f"Shadow content emerging - disowned aspects seeking integration. "
                    f"Originates in what ego has rejected."
                )
        
        causal = " ".join(causal_parts) if causal_parts else "Requires personal amplification"
        
        # Prospective: What for? (Future purpose)
        prospective_parts = []
        for c in complexes:
            if c.name == "authority" and c.frequency > 2:
                prospective_parts.append(
                    f"Recurring {c.name} theme suggests: you're being called to integrate "
                    f"your own authority, not reject external authority."
                )
            elif c.name == "shadow":
                prospective_parts.append(
                    f"Shadow pursuit suggests: what you flee contains what you need. "
                    f"Integration of disowned aspects leads to wholeness."
                )
        
        prospective = " ".join(prospective_parts) if prospective_parts else "Requires dialogue"
        
        # Synthesis
        synthesis = (
            f"The unconscious is not merely replaying the past (causal), "
            f"but preparing you for who you must become (prospective). "
            f"The {', '.join([c.name for c in complexes])} complex(es) represent "
            f"both your wound and your necessary development."
        )
        
        return InterpretationStandpoint(
            causal=causal,
            prospective=prospective,
            synthesis=synthesis
        )
    
    def _analyze_compensation(self, dramatic: DramaticStructure, 
                              conscious_context: str) -> Optional[CompensationType]:
        """Determine what type of compensation is occurring."""
        
        # This would be informed by user's conscious attitude history
        # Simplified version:
        
        if "escape" in dramatic.lysis.get("final_state", "").lower():
            return CompensationType.OPPOSITE  # One-sided, needs opposite
        
        if "union" in dramatic.lysis.get("final_state", "").lower():
            return CompensationType.EMPHASIS  # On track
        
        return CompensationType.VARIATIONS  # Balanced
    
    def _compensation_analysis(self, comp: Optional[CompensationType], 
                               conscious_context: str) -> str:
        """Explain the compensation."""
        if comp == CompensationType.OPPOSITE:
            return (
                "Your conscious attitude is one-sided. The dream takes the opposite position "
                "to compensate. What you're avoiding in waking life, the dream confronts you with."
            )
        elif comp == CompensationType.VARIATIONS:
            return (
                "Your conscious position is balanced. The dream offers nuance, "
                "not opposition."
            )
        elif comp == CompensationType.EMPHASIS:
            return (
                "Your conscious attitude is adequate. The dream confirms and deepens "
                "your current direction."
            )
        return "Compensation unclear - needs conscious attitude assessment"
    
    def _generate_therapeutic_response(self, narrative: str,
                                       linguistic: List[LinguisticMarker],
                                       dramatic: DramaticStructure,
                                       complexes: List[Complex],
                                       standpoints: InterpretationStandpoint,
                                       compensation: Optional[CompensationType]) -> str:
        """Generate the therapeutic dialogue."""
        
        response_parts = []
        
        # Opening - acknowledge the dream
        response_parts.append(f"**The Dream:** {narrative}\n")
        
        # Linguistic analysis
        ling_summary = self._summarize_linguistic(linguistic)
        response_parts.append(f"**Linguistic Analysis:** {ling_summary}\n")
        
        # Dramatic structure
        distillation = dramatic.distill()
        response_parts.append(
            f"**The Inner Theater:**\n"
            f"- **Action:** {distillation['action']}\n"
            f"- **Intent:** {distillation['intent']}\n"
            f"- **Dynamics:** {distillation['dynamics']}\n"
            f"- **Outcome:** {distillation['outcome']}\n"
        )
        
        # Complex detection
        if complexes:
            response_parts.append("**Complexes Detected:**")
            for c in complexes:
                response_parts.append(
                    f"- **{c.name.capitalize()} Complex** (appeared {c.frequency} time(s))\n"
                    f"  Archetypal core: {c.archetypal_core}\n"
                    f"  Status: {c.current_status}"
                )
                if c.frequency > 2:
                    response_parts.append(
                        f"  **Confrontation:** This complex has appeared {c.frequency} times. "
                        f"When will you recognize it as yours?"
                    )
            response_parts.append("")
        
        # The two standpoints
        response_parts.append(f"**The Two Standpoints:**{standpoints.analyze()}\n")
        
        # Therapeutic confrontation
        response_parts.append("**The Confrontation:**\n")
        
        if compensation == CompensationType.OPPOSITE:
            response_parts.append(
                "Your conscious attitude is one-sided. The dream is not attacking you—"
                "it's compensating for what you're not seeing.\n\n"
                "Look at the lysis (the ending): "
            )
            if "escape" in dramatic.lysis.get("final_state", "").lower():
                response_parts.append(
                    "You fled. The dream ends with flight, not integration. "
                    "This is NOT what the Self wants. The Self wants confrontation, not escape.\n\n"
                    "The question is not 'Why did I have this nightmare?' but "
                    "'What am I refusing to face?'"
                )
        
        elif any(c.name == "authority" for c in complexes):
            response_parts.append(
                "I notice you describe the authority figure with disgust. "
                "What if this reaction IS the complex?\n\n"
                "The causal interpretation says: 'This is your father wound.'\n"
                "The prospective interpretation says: 'This is who you must become.'\n\n"
                "Authority isn't inherently tyrannical. Your rejection of ALL authority "
                "prevents you from embodying your own."
            )
        
        # Closing
        response_parts.append(
            "\n**The Work:** This dream is a letter from your Self. "
            "It shows your inner truth—not as you wish it to be, but as it is.\n\n"
            "What is it asking you to integrate?"
        )
        
        return "\n".join(response_parts)
    
    def _store_dream(self, narrative: str, linguistic: List[LinguisticMarker],
                    dramatic: DramaticStructure, complexes: List[Complex],
                    standpoints: InterpretationStandpoint,
                    compensation: Optional[CompensationType]) -> str:
        """Store dream in history."""
        dream_id = f"dream_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.dream_history.append({
            "id": dream_id,
            "date": datetime.now().isoformat(),
            "narrative": narrative,
            "complexes": [c.name for c in complexes],
            "interpretation": standpoints.synthesis
        })
        
        return dream_id
    
    def _complex_to_dict(self, c: Complex) -> Dict:
        """Convert complex to dictionary."""
        return {
            "name": c.name,
            "archetypal_core": c.archetypal_core,
            "frequency": c.frequency,
            "current_status": c.current_status,
            "evolution": c.track_evolution()
        }


# CLI usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python therapeutic_interpreter.py 'dream narrative'")
        sys.exit(1)
    
    narrative = sys.argv[1]
    
    interpreter = TherapeuticInterpreter()
    result = interpreter.interpret(narrative)
    
    print(json.dumps(result, indent=2, default=str))
