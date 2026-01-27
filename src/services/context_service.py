"""
Context enrichment service for providing artist and album context
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextService:
    """
    Provides contextual information about artists, albums, and eras
    to improve gear inference accuracy
    """

    def __init__(self):
        # Will be enhanced with scrapers and caching in Phase 3
        pass

    async def get_artist_context(
        self,
        artist: str,
        song: str,
        year: Optional[int] = None
    ) -> Dict:
        """
        Gather contextual information about the artist's gear preferences,
        playing style, and the specific era/album

        Args:
            artist: Artist name
            song: Song title
            year: Optional year of recording/release

        Returns:
            Dictionary with contextual information
        """
        logger.info(f"Gathering context for {artist} - {song} ({year or 'unknown year'})")

        # Basic structure - will be populated by metadata scrapers in Phase 3
        context = {
            "artist": artist,
            "song": song,
            "year": year,
            "known_signature_gear": self._get_known_gear(artist),
            "era_characteristics": self._get_era_characteristics(year) if year else "",
            "genre": self._infer_genre(artist),
            "production_style": "",
            "similar_songs": [],
            "tone_keywords": []
        }

        return context

    def _get_known_gear(self, artist: str) -> List[Dict]:
        """
        Get well-documented signature gear for major artists
        This is a starter knowledge base that will be expanded
        """
        # Normalized artist name for matching
        artist_lower = artist.lower()

        # Knowledge base of famous artists' signature gear
        signature_gear_db = {
            "john mayer": [
                {"type": "guitar", "make": "Fender", "model": "Stratocaster", "notes": "Multiple vintages, especially 1964"},
                {"type": "guitar", "make": "PRS", "model": "Super Eagle", "notes": "Custom shop model"},
                {"type": "amp", "make": "Dumble", "model": "Overdrive Special", "notes": "Primary amp"},
                {"type": "amp", "make": "Two-Rock", "model": "Custom Reverb", "notes": "Touring amp"},
                {"type": "pedal", "make": "Ibanez", "model": "TS808 Tube Screamer", "notes": "Signature overdrive"}
            ],
            "eddie van halen": [
                {"type": "guitar", "make": "EVH", "model": "Frankenstein", "notes": "Iconic striped guitar"},
                {"type": "amp", "make": "Marshall", "model": "Plexi", "notes": "Modified"},
                {"type": "amp", "make": "Peavey", "model": "5150", "notes": "Signature amp"}
            ],
            "eric clapton": [
                {"type": "guitar", "make": "Fender", "model": "Stratocaster", "notes": "Blackie and Brownie"},
                {"type": "amp", "make": "Fender", "model": "Twin Reverb"},
                {"type": "amp", "make": "Marshall", "model": "JTM45"}
            ],
            "jimi hendrix": [
                {"type": "guitar", "make": "Fender", "model": "Stratocaster", "notes": "Left-handed"},
                {"type": "amp", "make": "Marshall", "model": "Super Lead"},
                {"type": "pedal", "make": "Dallas Arbiter", "model": "Fuzz Face"}
            ],
            "david gilmour": [
                {"type": "guitar", "make": "Fender", "model": "Stratocaster", "notes": "Black Strat"},
                {"type": "amp", "make": "Hiwatt", "model": "DR103"},
                {"type": "pedal", "make": "Electro-Harmonix", "model": "Big Muff"}
            ],
            "slash": [
                {"type": "guitar", "make": "Gibson", "model": "Les Paul", "notes": "Gold Top"},
                {"type": "amp", "make": "Marshall", "model": "JCM800"},
                {"type": "amp", "make": "Marshall", "model": "Silver Jubilee"}
            ],
            "stevie ray vaughan": [
                {"type": "guitar", "make": "Fender", "model": "Stratocaster", "notes": "Number One"},
                {"type": "amp", "make": "Fender", "model": "Vibroverb"},
                {"type": "pedal", "make": "Ibanez", "model": "TS808 Tube Screamer"}
            ],
            "kurt cobain": [
                {"type": "guitar", "make": "Fender", "model": "Jaguar"},
                {"type": "guitar", "make": "Fender", "model": "Mustang"},
                {"type": "pedal", "make": "Boss", "model": "DS-1"}
            ],
            "tom morello": [
                {"type": "guitar", "make": "Fender", "model": "Stratocaster", "notes": "Arm The Homeless"},
                {"type": "amp", "make": "Marshall", "model": "JCM800"},
                {"type": "pedal", "make": "DigiTech", "model": "Whammy"}
            ]
        }

        # Check for matches
        for known_artist, gear_list in signature_gear_db.items():
            if known_artist in artist_lower:
                logger.info(f"Found signature gear database entry for {artist}")
                return gear_list

        logger.debug(f"No signature gear database entry for {artist}")
        return []

    def _get_era_characteristics(self, year: int) -> str:
        """
        Describe typical production/gear characteristics by era
        """
        if year < 1960:
            return "1950s - Early electric era: Simple setups, clean tones, minimal effects. Fender and Gibson amps dominate."
        elif year < 1970:
            return "1960s - British Invasion era: Marshall stacks emerge, fuzz pedals, psychedelic experimentation. Transition to louder, more overdriven tones."
        elif year < 1980:
            return "1970s - Classic rock era: High gain becomes popular, MXR/Boss pedals emerge, larger amp stacks. More effects experimentation."
        elif year < 1990:
            return "1980s - Hair metal / New Wave era: High gain, chorus effects, rack gear, digital effects. Mesa Boogie, modified Marshalls common."
        elif year < 2000:
            return "1990s - Grunge / Alternative era: Back to basics with vintage gear, but heavier. More diverse tones from clean to extreme distortion."
        elif year < 2010:
            return "2000s - Digital integration era: Boutique amps gain popularity, digital modeling begins, pedalboards become complex. Mix of vintage and modern."
        else:
            return "2010s+ - Modern era: Boutique pedals everywhere, high-end amps, digital perfection. Huge variety in tones and approaches."

    def _infer_genre(self, artist: str) -> str:
        """
        Basic genre inference from artist name
        This is simplified - real implementation would use music databases
        """
        artist_lower = artist.lower()

        # Simple keyword matching (will be replaced with proper API in Phase 3)
        genre_keywords = {
            "Blues Rock": ["john mayer", "eric clapton", "stevie ray vaughan", "bb king", "gary clark"],
            "Metal": ["metallica", "slayer", "iron maiden", "megadeth", "pantera"],
            "Hard Rock": ["led zeppelin", "ac/dc", "guns n' roses", "van halen", "aerosmith"],
            "Grunge": ["nirvana", "pearl jam", "soundgarden", "alice in chains"],
            "Progressive Rock": ["pink floyd", "rush", "yes", "dream theater"],
            "Punk": ["ramones", "sex pistols", "green day", "the clash"],
            "Alternative Rock": ["radiohead", "foo fighters", "red hot chili peppers", "weezer"],
            "Jazz": ["pat metheny", "john scofield", "wes montgomery", "george benson"]
        }

        for genre, artists in genre_keywords.items():
            for known_artist in artists:
                if known_artist in artist_lower:
                    return genre

        return "Unknown"

    def format_context_for_prompt(self, context: Dict) -> str:
        """
        Format context data for inclusion in Claude prompt

        Args:
            context: Context dictionary from get_artist_context()

        Returns:
            Formatted string for prompt injection
        """
        lines = []

        lines.append(f"ARTIST CONTEXT FOR {context['artist']}:")
        lines.append("")

        if context.get('genre'):
            lines.append(f"Genre: {context['genre']}")

        if context.get('year') and context.get('era_characteristics'):
            lines.append(f"Era: {context['year']} - {context['era_characteristics']}")

        if context.get('known_signature_gear'):
            lines.append("")
            lines.append("Known Signature Gear:")
            for gear in context['known_signature_gear']:
                gear_desc = f"  - {gear['type'].title()}: {gear['make']} {gear['model']}"
                if gear.get('notes'):
                    gear_desc += f" ({gear['notes']})"
                lines.append(gear_desc)

        if not context.get('known_signature_gear') and not context.get('era_characteristics'):
            lines.append("Limited context available - rely on source data and general music knowledge.")

        lines.append("")
        return "\n".join(lines)
