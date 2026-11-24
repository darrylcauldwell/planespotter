from collections.abc import AsyncIterator
from datetime import date
from app.schemas.aircraft import AircraftWithPosition
from app.services.llm import llm_client

SYSTEM_PROMPT = """You describe one aircraft for someone watching it on a flight tracker, in \
three or four plain sentences. Use only the facts you are given. Do not guess at anything they \
do not state, such as its route, destination, passengers or history, and do not mention facts \
that are missing. No headings, lists or markdown."""

COMPASS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]

FEET_PER_METRE = 3.28084
KNOTS_PER_METRE_PER_SECOND = 1.94384
# Below this vertical rate (about 200 feet per minute) an aircraft is treated as level.
LEVEL_METRES_PER_SECOND = 1.0
# About 780 knots, beyond any airliner even in the strongest jet stream. OpenSky passes on a
# few bad decodes of over 1,000 knots in every poll, and the model repeats whatever it is given,
# so a speed above this is left out rather than described.
MAX_PLAUSIBLE_METRES_PER_SECOND = 400.0


def compass(degrees: float) -> str:
    """The compass point nearest a track angle."""
    return COMPASS[round(degrees / 45) % 8]


def built(value: str | None, today: date) -> str | None:
    """The year built, with the aircraft's age; the registry stores it as a year or a date."""
    if not value or not value[:4].isdigit():
        return None
    year = int(value[:4])
    age = today.year - year
    return f"{year} (about {age} years ago)" if age >= 1 else str(year)


def aircraft_facts(aircraft: AircraftWithPosition, today: date) -> str:
    """The facts the model may use, one per line.

    Units are converted and the age worked out here rather than left to the model: small models
    are unreliable at arithmetic, and the reader thinks in feet and knots, not metres per second.
    """
    facts = {
        "Registration": aircraft.registration,
        "Manufacturer": aircraft.manufacturername,
        "Model": aircraft.model,
        "ICAO type code": aircraft.typecode,
        "Operator": aircraft.operator,
        "Owner": aircraft.owner,
        "Engines": aircraft.engines,
        "Built": built(aircraft.built, today),
    }

    position = aircraft.position
    if position is None:
        facts["Live position"] = "not currently tracked"
    else:
        facts["Country of registration"] = position.origin_country
        facts["Callsign"] = (position.callsign or "").strip()
        if position.on_ground:
            facts["Live position"] = "on the ground"
        else:
            if position.baro_altitude is not None:
                facts["Altitude"] = f"{position.baro_altitude * FEET_PER_METRE:,.0f} feet"
            if position.velocity is not None and position.velocity <= MAX_PLAUSIBLE_METRES_PER_SECOND:
                facts["Ground speed"] = f"{position.velocity * KNOTS_PER_METRE_PER_SECOND:,.0f} knots"
            if position.true_track is not None:
                facts["Heading"] = compass(position.true_track)
            if position.vertical_rate is not None:
                rate = position.vertical_rate
                feet_per_minute = abs(rate) * FEET_PER_METRE * 60
                if abs(rate) < LEVEL_METRES_PER_SECOND:
                    facts["Vertical"] = "level"
                else:
                    direction = "climbing" if rate > 0 else "descending"
                    facts["Vertical"] = f"{direction} at {feet_per_minute:,.0f} feet per minute"

    return "\n".join(f"{name}: {value}" for name, value in facts.items() if value)


def tell_story(aircraft: AircraftWithPosition) -> AsyncIterator[str]:
    """Stream a short description of the aircraft, as the model writes it."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": aircraft_facts(aircraft, date.today())},
    ]
    return llm_client.stream("story", messages, max_tokens=200)
