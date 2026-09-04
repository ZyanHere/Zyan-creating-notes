"""The Document Plan — structure without content.

A plan says *what blocks a section contains and what each should cover*. It
carries no prose. `fill()` turns a plan into a Document by writing the content
of each block, and nothing else: it cannot add a block, drop one, or change a
type.

Two kinds of block appear here:

* **prose specs** (para, subheading, code, callout, list, badge) declare a
  brief and a cap; the model writes them.
* **structural blocks** (figure, cheatsheet) arrive already authored and are
  copied through. A figure is an archetype with data — the model selects from
  archetypes that exist, it never invents one — so for now that data is
  hand-written rather than generated.
"""

from __future__ import annotations

from typing import Annotated, Literal

from engine.schema import CheatRow, Heading, Layer
from pydantic import BaseModel, ConfigDict, Field


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ------------------------------------------------------------ prose specs


class ParaSpec(Base):
    type: Literal["para"] = "para"
    brief: str
    max_words: int = 90


class SubheadingSpec(Base):
    type: Literal["subheading"] = "subheading"
    brief: str
    max_words: int = 8


class CodeSpec(Base):
    type: Literal["code"] = "code"
    lang: str
    brief: str
    file: str | None = None
    max_lines: int = 30


class CalloutSpec(Base):
    type: Literal["callout"] = "callout"
    label: str
    brief: str
    subtitle: str | None = None
    max_words: int = 70


class ListSpec(Base):
    type: Literal["list"] = "list"
    brief: str
    count: int = 5
    marker: Literal["arrow", "bullet", "number"] = "arrow"
    max_words_per_item: int = 25


class BadgeSpec(Base):
    type: Literal["badge"] = "badge"
    brief: str
    max_words: int = 6


# ------------------------------------------------- pre-authored structure


class FigureSpec(Base):
    """Already authored. Copied through untouched."""

    type: Literal["figure"] = "figure"
    archetype: Literal["layer-stack"] = "layer-stack"
    layers: list[Layer]
    caption: str
    number: str | None = None


class CheatSheetSpec(Base):
    """Already authored. Copied through untouched."""

    type: Literal["cheatsheet"] = "cheatsheet"
    rows: list[CheatRow]


BlockSpec = Annotated[
    ParaSpec
    | SubheadingSpec
    | CodeSpec
    | CalloutSpec
    | ListSpec
    | BadgeSpec
    | FigureSpec
    | CheatSheetSpec,
    Field(discriminator="type"),
]

# Which specs the model writes, and which are copied through.
PROSE_TYPES = {"para", "subheading", "code", "callout", "list", "badge"}


# ---------------------------------------------------------------- plan


class SectionPlan(Base):
    label: str | None = None
    heading: Heading | None = None
    blocks: list[BlockSpec] = Field(default_factory=list)
    rule_before: bool = False


class DocumentPlan(Base):
    title: str
    sections: list[SectionPlan]

    subtitle: str | None = None
    eyebrow: str | None = None
    running_title: str | None = None
    footer_text: str | None = None
    cover: bool = False
    build_stamp: str | None = None

    # Free text describing who this is for and what it is doing. Goes into the
    # prompt so the model writes to a situation rather than in the abstract.
    context: str = ""


def load_plan(data: dict) -> DocumentPlan:
    return DocumentPlan.model_validate(data)
