from app.schemas.ask import SearchFilters
from app.services.llm import Completion, llm_client

# The registry is sparse and inconsistent (operator is set on about 5% of rows, model codes vary
# between "A380-842" and "A380 861"), and every filter is an ANDed substring match, so the prompt
# steers the model to the fewest, shortest filters that still answer the question.
SYSTEM_PROMPT = """You turn a question about aircraft into filters for a search form over the \
OpenSky aircraft registry. Every filter you set must match, and each is a case-insensitive \
substring match, so set only the filters the question asks for and leave the rest null.

- registration: the tail number, such as G-EUPT or N12345.
- manufacturer: the maker, such as Airbus, Boeing or Cessna. Leave it null when the model \
already identifies the aircraft, because many rows have no manufacturer.
- model: the shortest distinctive model code, such as A380, 737, A320, 172 or R44.
- operator: the airline or company that flies it, such as Emirates, Ryanair or British Airways.
- owner: the registered owner. Name a specific organisation in full and spell out any \
abbreviation, because the registry stores full names: Royal Air Force, not RAF. For a kind of \
owner, use one distinctive word, such as police or club.
- status: airborne when the question is about aircraft flying now, ground when it is about \
aircraft not flying."""

EXAMPLES = [
    ("Emirates A380s in the air right now",
     SearchFilters(operator="Emirates", model="A380", status="airborne")),
    ("Cessna 172s owned by flying clubs", SearchFilters(model="172", owner="club")),
    ("Who owns G-EUPT?", SearchFilters(registration="G-EUPT")),
    ("RAF helicopters", SearchFilters(owner="Royal Air Force")),
    ("Police helicopters", SearchFilters(owner="police")),
]


async def interpret_question(question: str) -> Completion[SearchFilters]:
    """Ask the model which search filters answer a plain-English question."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for example_question, example_filters in EXAMPLES:
        messages.append({"role": "user", "content": example_question})
        messages.append({"role": "assistant", "content": example_filters.model_dump_json()})
    messages.append({"role": "user", "content": question})

    return await llm_client.complete("ask", messages, SearchFilters, max_tokens=128)
