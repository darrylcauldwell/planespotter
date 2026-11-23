from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AskRequest(BaseModel):
    """A search written in plain English."""

    question: str = Field(..., min_length=1, max_length=300, description="The search in plain English")


class SearchFilters(BaseModel):
    """The search form's filters, as the model understood the question.

    This class is also the JSON schema the language model must answer in. The length limits are
    there for the model as much as for validation: a small model held to a grammar can otherwise
    repeat itself until it runs out of tokens and leave unparseable JSON.
    """

    model_config = ConfigDict(extra="forbid")

    registration: str | None = Field(None, max_length=12)
    manufacturer: str | None = Field(None, max_length=40)
    model: str | None = Field(None, max_length=40)
    operator: str | None = Field(None, max_length=40)
    owner: str | None = Field(None, max_length=60)
    status: Literal["airborne", "ground"] | None = None

    @field_validator("*", mode="before")
    @classmethod
    def blank_is_no_filter(cls, value):
        """Treat an empty or whitespace-only value as no filter."""
        if isinstance(value, str):
            return value.strip() or None
        return value


class AskResponse(BaseModel):
    """Filters for the existing search, and which model chose them and how quickly."""

    question: str
    filters: SearchFilters
    model: str = Field(..., description="Model that answered, as its server names it")
    elapsed_ms: int = Field(..., description="Time the model took, in milliseconds")
