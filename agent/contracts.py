"""Typed contracts between the agent and everything downstream.

M1 keeps one contract: a `Document`. The decision taxonomy of Architecture §3
arrives at M3; until then a single call produces the whole document, and this
module is the boundary that keeps the rest of the system from caring.

Block kinds are deliberately not "eight block types". They are the renderable
counterparts of the prose-failure modes in System Design Rev. 4 §13 -- a table
answers cross-reference failure, a worked example answers abstraction
grounding, and so on. The prompt names the diagnostic; the model chooses.
"""

from __future__ import annotations

from typing import Annotated, ClassVar, Literal, Union

from pydantic import BaseModel, Field, model_validator

# Representation Boundary Rev. 3 §10, stage 1: the honesty table admits *nothing*
# for family E. Perceptual form exists precisely to add what the specification
# could not supply, so no drawn block can preserve assertions over it -- §1's
# rule fails by construction, not by accident.
PERCEPTUAL_REFERENT = "perceptual-referent"


def normalize_diagnosis(raw: str) -> str:
    """`Perceptual Referent`, `perceptual_referent`, `unlisted: perceptual-referent`
    are all the same diagnosis. Free text is deliberate (see `Departure`); reading
    it exactly is not the same as reading it literally."""
    text = raw.strip().lower()
    if text.startswith("unlisted:"):
        text = text[len("unlisted:") :]
    return "-".join(text.replace("_", " ").replace("-", " ").split())


class Prose(BaseModel):
    """The default carrier. Every other block is a departure from this."""

    kind: Literal["prose"] = "prose"
    text: str = Field(description="One or more paragraphs, separated by a blank line.")


class Departure(BaseModel):
    """Anything that is not prose, carrying the reason it was licensed.

    Architecture §13 says the diagnosis selects the representation. The prompt asks
    for that diagnosis and the model performs it -- and then, until now, we threw it
    away and kept only the outcome. `kind` records what was drawn; `diagnosis`
    records what it was drawn *for*, which is the pair Architecture §12 calls the
    most valuable retained thing: which prose-failure fired on which node.

    Free text rather than an enum, deliberately. An enum of the seven failures in
    §13 would make the one interesting reading impossible: a model that needed a
    failure the taxonomy does not list. The prompt names the seven and tells the
    model to write `unlisted: <name>` when none fits, so the gap arrives as data.
    Representation Boundary Rev. 3 is reopened by exactly that reading.
    """

    realizes: ClassVar[bool] = True
    """Whether this block *is* the figure, or only talks about one.

    Every departure draws something except `Callout`, which is text in a box: it
    asserts no shape, order, containment or magnitude, so it cannot make a false
    spatial claim. That distinction is the whole of the exemption below.
    """

    diagnosis: str | None = Field(
        default=None,
        description=(
            "The prose failure this block answers. One of: cross-reference, "
            "topology, parallel-state, perceptual-referent, abstraction-grounding, "
            "procedure-execution, false-comprehension. If none of them fits what "
            "you actually diagnosed, write 'unlisted: <short name>'."
        ),
    )

    @model_validator(mode="after")
    def _perceptual_referent_licenses_no_realization(self):
        """A diagnosed E may not be drawn.

        This is the guard for the failure Representation Boundary Rev. 3 §8 calls
        a layering violation committed at the schema level: the model diagnoses
        that the reader needs to see the thing itself, then reaches for the
        nearest available block and draws boxes. `is-part-of` over
        [mucosa, submucosa, muscularis, serosa] renders, looks like a diagram,
        and is not what the reader needed.

        Nothing caught it before, because `diagnosis` and `kind` were recorded
        side by side and never compared. Here they are compared.

        What this does NOT catch: a *misdiagnosis*. A model that labels the same
        block `topology` draws exactly the same false figure and passes. That is
        Rev. 3 §6's brief test, which is a judgement about content and has no
        mechanical form. This guard catches self-contradiction only -- which is
        the case worth catching first, because a model that diagnosed correctly
        and drew anyway is the one we can still repair.
        """
        if self.realizes and self.diagnosis is not None:
            if normalize_diagnosis(self.diagnosis) == PERCEPTUAL_REFERENT:
                raise ValueError(
                    "perceptual-referent licenses no realization. This diagnosis "
                    "means the reader must see the thing itself, and nothing you "
                    "can draw from a specification shows it -- a drawn block here "
                    "puts content in the document that the document never "
                    "asserted. Two repairs, and only these two: (1) if the figure "
                    "really is needed, do not draw it -- emit a `callout` with "
                    'tone "warning", carrying this same diagnosis, whose text says '
                    "what the figure must show and that it is not included; "
                    "(2) if a list of named parts and the relation between them "
                    "would carry the meaning, the diagnosis was wrong -- use "
                    "`relation` with the diagnosis that is actually true. Do not "
                    "delete the diagnosis to make this pass."
                )
        return self


class BulletList(Departure):
    kind: Literal["list"] = "list"
    ordered: bool = False
    items: list[str]


class Code(Departure):
    """Answers abstraction grounding, or procedure execution when it is a trace."""

    kind: Literal["code"] = "code"
    language: str
    code: str
    caption: str | None = None


class Table(Departure):
    """Answers cross-reference failure. Every cell must be filled."""

    kind: Literal["table"] = "table"
    caption: str | None = None
    headers: list[str]
    rows: list[list[str]]


class WorkedExample(Departure):
    """Answers procedure execution: the reader can read it but cannot run it.

    Steps show state, not just instructions.
    """

    kind: Literal["example"] = "example"
    title: str
    steps: list[str]


class CheckQuestion(Departure):
    """Answers false comprehension: easy to accept while holding a wrong model."""

    kind: Literal["question"] = "question"
    prompt: str
    answer: str


class Callout(Departure):
    """Text in a box. The one departure that draws no geometry.

    Because it asserts no shape, order, containment or magnitude, it is the only
    block that can honestly carry a `perceptual-referent` diagnosis: it does not
    realize the figure, it reports that the figure is missing and says what it
    would have had to show. Visual-Requirement-Routing §4 -- the brief is the
    content, and a stated gap is worth more to the reader than either silence or
    a diagram answering a different question.
    """

    realizes: ClassVar[bool] = False

    kind: Literal["callout"] = "callout"
    tone: Literal["note", "warning"] = "note"
    label: str | None = Field(
        default=None, description="Small uppercase label above the box, e.g. CONCEPT."
    )
    title: str | None = None
    text: str


# --------------------------------------------------------------------------
# Added while reproducing a real designed document (see out/_ref).
# These are the block kinds one existing artifact demanded that the original
# seven could not express. Recorded as evidence for Product Semantics §14's
# open question about sizing the archetype library -- the list is growing from
# contact with real documents, not from guessing.
# --------------------------------------------------------------------------


class Subhead(Departure):
    """A small uppercase label inside a section: LEARNING OBJECTIVES, THE PROJECT.

    Not a heading -- it groups blocks below it without entering the outline.
    """

    kind: Literal["subhead"] = "subhead"
    label: str


class Heading(Departure):
    """A subheading within a section, e.g. 'OpenAI: Chat Completions API'."""

    kind: Literal["heading"] = "heading"
    text: str


class Chips(Departure):
    """A set of short topic labels, presented as a row of tags."""

    kind: Literal["chips"] = "chips"
    items: list[str]


class Entity(BaseModel):
    label: str
    note: str | None = Field(default=None, description="Short annotation for this entity.")
    emphasis: bool = False


class RelationalStructure(Departure):
    """Named entities and the relation that holds between them.

    Replaces `StackDiagram`, which was named after a *geometry*. That is the
    defect Representation Boundary Rev. 3 calls treating "diagram" as the
    decision: a stack says *sits on top of*, so containment and sequence both
    came out as pyramids and one of them was false. `AI contains ML` and
    `input precedes hidden` are different claims and must not be able to
    produce the same picture by accident.

    The model states the relation. It never names a geometry -- which geometry
    tells that relation's truth is Rev. 3 §2's honesty table, applied by the
    template.
    """

    kind: Literal["relation"] = "relation"
    relation: Literal[
        "is-subset-of",
        "is-part-of",
        "precedes",
        "causes",
        "associates-with",
    ] = Field(
        description=(
            "What holds between consecutive entities. "
            "'is-subset-of': every member of the next is a member of this one "
            "(AI contains ML contains DL). "
            "'is-part-of': the next is a component of this one, not an instance. "
            "'precedes': the next follows this one in order or time. "
            "'causes': this one brings about the next. "
            "'associates-with': related, with no direction or order."
        )
    )
    caption: str | None = None
    entities: list[Entity] = Field(
        description=(
            "Ordered by the relation's own direction: for 'is-subset-of' and "
            "'is-part-of', outermost/whole first; for 'precedes' and 'causes', "
            "earliest/cause first. Order is meaning, not layout."
        )
    )


Block = Annotated[
    Union[
        Prose,
        BulletList,
        Code,
        Table,
        WorkedExample,
        CheckQuestion,
        Callout,
        Subhead,
        Heading,
        Chips,
        RelationalStructure,
    ],
    Field(discriminator="kind"),
]


class Section(BaseModel):
    heading: str
    eyebrow: str | None = Field(
        default=None, description="Small label above the heading, e.g. SECTION 1."
    )
    heading_tail: str | None = Field(
        default=None,
        description="Trailing part of the heading, emphasised by the template.",
    )
    blocks: list[Block]


class Cover(BaseModel):
    """A title page. Optional -- most documents will not have one."""

    eyebrow: str
    label: str | None = None
    title: str
    title_tail: str | None = None
    subtitle_lines: list[str] = Field(default_factory=list)
    chips: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    footer_left: str | None = None
    footer_right: str | None = None


class MarkedGap(BaseModel):
    """Semantics §12. Omitting a concept is legitimate; omitting it silently is not.

    Complete form: the omitted boundary, its consequence, and when the reader
    must learn it. All three, or the gap is not marked -- it is just missing.
    """

    topic: str
    consequence: str = Field(description="What goes wrong if they act without it.")
    when_to_learn: str = Field(description="The point at which this becomes required.")


class Document(BaseModel):
    """One educational artifact."""

    title: str
    subtitle: str | None = None
    cover: Cover | None = None
    running_head_left: str | None = None
    running_head_right: str | None = None
    footer_text: str | None = None
    assumed_entry: str = Field(
        description="What this document assumes the reader already knows. "
        "Stated so the reader can tell whether it is for them."
    )
    target_capability: str = Field(
        description="What the reader can do after reading it. Concrete, not a topic list."
    )
    sections: list[Section]
    deliberate_omissions: list[MarkedGap] = Field(
        default_factory=list,
        description="Things deliberately left out, each with its consequence and "
        "when the reader must learn it.",
    )
