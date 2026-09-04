"""The Document Model.

A structured description of one document's *content*. It carries no geometry:
no coordinates, no page numbers, no colours, no font sizes. Those are decided
by the template and the theme at render time.

Rule of thumb: if a value would change when the text changes, it does not
belong here.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- blocks


class Para(Base):
    """Body text. Supports two inline constructs: `code` and **bold**."""

    type: Literal["para"] = "para"
    text: str


class Subheading(Base):
    """A heading below section level. Single-tone, unlike a section heading."""

    type: Literal["subheading"] = "subheading"
    text: str


class Code(Base):
    """A code block. `file` renders in the header beside the language."""

    type: Literal["code"] = "code"
    lang: str
    text: str
    file: str | None = None


class Callout(Base):
    """A labelled aside: accent bar, tinted panel, mono label inside.

    `label` is free text so a template is never the place new callout kinds
    get registered — the theme decides how any label is tinted.
    """

    type: Literal["callout"] = "callout"
    label: str
    text: str
    subtitle: str | None = None
    tone: str = "accent"


class ListBlock(Base):
    type: Literal["list"] = "list"
    items: list[str]
    marker: Literal["arrow", "bullet", "number"] = "arrow"


class Badge(Base):
    """A standalone mono chip on its own line — `POST /v1/chat/completions`."""

    type: Literal["badge"] = "badge"
    text: str
    tone: str = "muted"


class Layer(Base):
    text: str
    width: Annotated[int, Field(ge=10, le=100)]
    tone: str
    note: str | None = None


class LayerStack(Base):
    """Figure archetype: centred bars of varying width, top to bottom.

    Figures are archetypes with data, never free drawing. A generator selects
    an archetype that exists; it cannot invent one.
    """

    type: Literal["figure"] = "figure"
    archetype: Literal["layer-stack"] = "layer-stack"
    layers: list[Layer]
    caption: str
    number: str | None = None


class CheatRow(Base):
    label: str
    code: str


class CheatSheet(Base):
    type: Literal["cheatsheet"] = "cheatsheet"
    rows: list[CheatRow]


Block = Annotated[
    Para | Subheading | Code | Callout | ListBlock | Badge | LayerStack | CheatSheet,
    Field(discriminator="type"),
]


# ---------------------------------------------------------------- structure


class Heading(Base):
    """Two-tone heading: `lead` in ink, `accent` in the accent colour.

    Both halves are content. Which colour each half takes is the theme's call.
    """

    lead: str
    accent: str | None = None


class Section(Base):
    label: str | None = None  # mono eyebrow: "OVERVIEW", "SECTION 1"
    heading: Heading | None = None
    blocks: list[Block] = Field(default_factory=list)
    rule_before: bool = False  # thin divider above this section


class Document(Base):
    title: str
    sections: list[Section]

    subtitle: str | None = None
    eyebrow: str | None = None  # cover + running header right: "MODULE 01"
    running_title: str | None = None  # running header left
    footer_text: str | None = None

    # Whether this document opens with a cover page. Explicit rather than
    # inferred from which optional fields happen to be present.
    cover: bool = False

    # Caller-supplied, never generated. The engine has no clock: a timestamp
    # invented at render time would make identical input produce different
    # output and break determinism.
    build_stamp: str | None = None

    versions: list[str] = Field(default_factory=list)
    chips: list[str] = Field(default_factory=list)


def load(data: dict) -> Document:
    """Validate a raw dict into a Document. Raises pydantic.ValidationError."""
    return Document.model_validate(data)


def json_schema() -> dict:
    """JSON Schema for the Document Model.

    Used from step 2 onward to constrain what a generator may emit.
    """
    return Document.model_json_schema()
