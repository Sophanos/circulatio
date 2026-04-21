#!/usr/bin/env python3
"""
Circulatio Alchemical Meditation Generator

Generates stage-specific guided meditations for Jungian consciousness work.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Meditation:
    stage: str
    title: str
    duration: int  # minutes
    opening: str
    body: List[str]
    closing: str
    mantra: str


class MeditationGenerator:
    """Generates alchemical stage meditations."""
    
    STAGE_CONFIGS = {
        "nigredo": {
            "title": "Descent into the Shadow",
            "theme": "confronting the unconscious, embracing darkness",
            "visualization": "dark forest, descent into cave, meeting the rejected",
            "breath": "deep, slow, into the abdomen, grounding",
            "color": "black, dark purple, midnight blue",
            "element": "earth, lead, Saturn"
        },
        "albedo": {
            "title": "The Washing",
            "theme": "purification, releasing attachments, clarity",
            "visualization": "silver stream, washing clean, mirror reflection",
            "breath": "cleansing, releasing tension, cooling",
            "color": "white, silver, pale moonlight",
            "element": "water, silver, Moon"
        },
        "citrinitas": {
            "title": "The Golden Dawn",
            "theme": "illumination, the golden shadow, insight",
            "visualization": "sunrise, golden light filling the body, dawning awareness",
            "breath": "expanding, opening, warming",
            "color": "gold, yellow, amber, dawn light",
            "element": "air, gold, Mercury"
        },
        "rubedo": {
            "title": "The Sacred Marriage",
            "theme": "integration, union of opposites, wholeness",
            "visualization": "the phoenix rising, union of king and queen, the rose blooming",
            "breath": "balanced, harmonious, complete",
            "color": "red, crimson, rose, ruby",
            "element": "fire, ruby, Sun"
        }
    }
    
    def __init__(self, culture: str = "Universal-Jungian"):
        self.culture = culture
    
    def generate(self, stage: str, duration: int = 15) -> Meditation:
        """Generate meditation for specific alchemical stage."""
        if stage not in self.STAGE_CONFIGS:
            stage = "nigredo"  # default
        
        config = self.STAGE_CONFIGS[stage]
        
        return Meditation(
            stage=stage,
            title=config["title"],
            duration=duration,
            opening=self._generate_opening(stage, config),
            body=self._generate_body(stage, config, duration),
            closing=self._generate_closing(stage, config),
            mantra=self._generate_mantra(stage)
        )
    
    def _generate_opening(self, stage: str, config: Dict) -> str:
        """Generate meditation opening."""
        openings = {
            "nigredo": f"""Welcome to the {config['title']}.

Find a comfortable position, either sitting or lying down. 
Allow your body to settle into the support beneath you.

Today we enter the {config['element']}. This is the work of {config['theme']}.

The alchemists called this Nigredo—the blackening. It is not a mistake or failure, 
but a necessary first stage. What must rot becomes fertilizer for what will bloom.

Close your eyes, and prepare to descend.
""",
            "albedo": f"""Welcome to the {config['title']}.

Settle into your position, spine upright but not rigid. 
Allow the shoulders to release their burden.

Today we work with {config['element']}. This is the work of {config['theme']}.

The alchemists called this Albedo—the whitening. The washing away of what obscures 
your true nature. The gaining of clarity.

Close your eyes, and prepare to be washed clean.
""",
            "citrinitas": f"""Welcome to the {config['title']}.

Sit with dignity, as if you were the meeting place of heaven and earth. 
Let your face soften into a gentle smile.

Today we invoke {config['element']}. This is the work of {config['theme']}.

The alchemists called this Citrinitas—the yellowing. The dawn after the dark night. 
The first rays illuminating what was hidden.

Close your eyes, and prepare for the light.
""",
            "rubedo": f"""Welcome to the {config['title']}.

Sit or lie in a posture of completion, as if you have already arrived 
at your destination.

Today we embody {config['element']}. This is the work of {config['theme']}.

The alchemists called this Rubedo—the reddening. The sacred marriage of opposites. 
The philosopher's stone.

Close your eyes, and prepare for union.
"""
        }
        return openings.get(stage, openings["nigredo"])
    
    def _generate_body(self, stage: str, config: Dict, duration: int) -> List[str]:
        """Generate meditation body sections."""
        sections = []
        
        # Breath work
        sections.append(f"""
[Minute 1-3: Arrival]

Bring your attention to your breath. 
{config['breath']}.

Breathe in for four counts... hold for four... 
out for four... hold for four...

The color of {stage} is {config['color']}. 
Imagine this color surrounding you like a gentle mist.
""")
        
        # Visualization
        sections.append(f"""
[Minute 4-8: Visualization]

{config['visualization'].capitalize()}...

See yourself in this place. It is safe. It is necessary. 
It is exactly where you need to be.

Notice what arises without judgment. 
This is the unconscious presenting itself.
""")
        
        # Deepening
        if stage == "nigredo":
            sections.append("""
[Minute 9-12: The Descent]

As you breathe, feel yourself descending.
Deeper into the earth... into the shadow... into what has been rejected.

This is not punishment. This is archaeology.
You are excavating the gold that was buried in darkness.

Ask: "What have I refused to see?"

Do not demand an answer. Let the question settle.
""")
        elif stage == "albedo":
            sections.append("""
[Minute 9-12: The Washing]

Feel the silver stream washing over you.
Where it touches, tension dissolves.
Where it flows, ego attachments release.

This is not loss. This is space being created.

Ask: "What am I ready to release?"

Let the water carry away what no longer serves.
""")
        elif stage == "citrinitas":
            sections.append("""
[Minute 9-12: The Dawning]

Feel the golden light filling your body.
From the crown down... through the heart... to the root.

This is not blinding. This is clarity.
The golden shadow—that part of you that shines too brightly 
for your ego to bear.

Ask: "What truth is ready to emerge?"

Let the light find the places still in shadow.
""")
        elif stage == "rubedo":
            sections.append("""
[Minute 9-12: The Union]

See the opposites within you—the conscious and unconscious, 
light and shadow, masculine and feminine.

They approach each other. They recognize each other.
In the center of your being, they merge.

This is the conjunctio—the sacred marriage.
The philosopher's stone is not outside you. It is this union.

Rest in the completeness.
""")
        
        # Mantra
        sections.append(f"""
[Minute 13-14: Mantra]

On each breath, repeat silently:

"{self._generate_mantra(stage)}"

Let the words dissolve into feeling.
Let feeling dissolve into presence.
""")
        
        return sections
    
    def _generate_closing(self, stage: str, config: Dict) -> str:
        """Generate meditation closing."""
        closings = {
            "nigredo": """[Minute 15: Return]

Begin to feel your breath deepening.
The descent is complete for now.

Carry the darkness with you—not as burden, but as womb.
The gold is here, being formed.

When you're ready, wiggle fingers and toes.
Open your eyes, returning slowly.

Remember: Nigredo is not depression. It is preparation.
The work continues.
""",
            "albedo": """[Minute 15: Return]

Begin to feel your breath returning to normal.
The washing is complete for now.

Carry the clarity with you—space where tension once lived.

When you're ready, wiggle fingers and toes.
Open your eyes, returning slowly.

Remember: Albedo is not emptiness. It is spaciousness.
The work continues.
""",
            "citrinitas": """[Minute 15: Return]

Begin to feel the golden light settling within you.
The dawn has broken; the day awaits.

Carry the insight with you—gentle, not demanding.

When you're ready, wiggle fingers and toes.
Open your eyes, returning slowly.

Remember: Citrinitas is not enlightenment. It is illumination.
The work continues.
""",
            "rubedo": """[Minute 15: Return]

Begin to feel the completeness that is always here.
The marriage has happened; the stone is within.

Carry the wholeness with you—nothing to add, nothing to remove.

When you're ready, wiggle fingers and toes.
Open your eyes, returning slowly.

Remember: Rubedo is not the end. It is the beginning of the next cycle.
The work continues.
"""
        }
        return closings.get(stage, closings["nigredo"])
    
    def _generate_mantra(self, stage: str) -> str:
        """Generate stage-specific mantra."""
        mantras = {
            "nigredo": "I descend to find what I've forgotten",
            "albedo": "I release what no longer serves",
            "citrinitas": "I embrace the light I've feared",
            "rubedo": "I am whole, containing all opposites"
        }
        return mantras.get(stage, "I am the work")
    
    def to_text(self, meditation: Meditation) -> str:
        """Convert meditation to readable text."""
        lines = [
            f"# {meditation.title}",
            f"**Alchemical Stage:** {meditation.stage.capitalize()}",
            f"**Duration:** {meditation.duration} minutes\n",
            "---\n",
            meditation.opening,
        ]
        
        for section in meditation.body:
            lines.append(section)
        
        lines.append(meditation.closing)
        
        lines.append(f"""
---

**Mantra:** {meditation.mantra}

*Save this meditation or use `/circulato meditate {meditation.stage}` anytime.*
""")
        
        return "\n".join(lines)


# CLI usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python meditation_generator.py [stage] [duration]")
        print("Stages: nigredo, albedo, citrinitas, rubedo")
        print("Duration: minutes (default 15)")
        sys.exit(1)
    
    stage = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    
    generator = MeditationGenerator()
    meditation = generator.generate(stage, duration)
    
    print(generator.to_text(meditation))
