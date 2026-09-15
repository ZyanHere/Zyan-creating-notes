"""The plan gate's application boundary.

Owns the sequence — propose, correct, revise, approve — and the record of what
each turn changed. Holds no pedagogy (the agent's) and no geometry (there is
none at this gate; nothing renders before the plan is approved).

Scoped to proving the interaction converges. Not here, on purpose: the
invalidation closure walk, decision versioning beyond append, verification
classes, jobs. Those are downstream of knowing a human can have this
conversation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import agent.plan as planning
from agent.coherence import analyse, capability_support
from agent.coherence import support_to_json
from agent.coherence import to_json as coherence_json
from agent.sufficiency import DEFAULT_BUDGET, AxisReading, decide, from_json, improved
from agent.plan import (
    ALL_DECISIONS,
    INTERACTION_DECISIONS,
    PLAN_DECISIONS,
    UPSTREAM_DECISIONS,
    Partition,
    Scope,
    Situation,
    derive_extent,
    derive_feasibility,
)
from backend.store import (
    Commitment,
    Decision,
    FileStore,
    Store,
    commit_hash,
    inputs_hash,
)

USER = "local"  # single user until accounts exist; one column to change


@dataclass(frozen=True, slots=True)
class Routed:
    """One correction and what it did.

    `claimed` is what the router said it was changing; `actual` is what changed
    in the decision rows. Recording both is the point: "revise only what you
    routed to" is a claim, and a claim nobody checks is a wish. Divergence is
    reported, never repaired.
    """

    correction: str
    reading: str
    claimed: tuple[str, ...]
    actual: tuple[str, ...]
    out_of_scope: str | None = None

    @property
    def unclaimed_drift(self) -> tuple[str, ...]:
        return tuple(d for d in self.actual if d not in self.claimed)

    @property
    def claimed_but_unchanged(self) -> tuple[str, ...]:
        return tuple(d for d in self.claimed if d not in self.actual)

    @property
    def not_understood(self) -> bool:
        """Routed nowhere and deferred nothing: the correction did not land."""
        return not self.claimed and not self.out_of_scope


@dataclass
class PlanView:
    """What a client renders. A projection over decision rows, never stored."""

    project_id: str
    title: str
    decisions: dict[str, dict]
    extent: dict
    feasibility: dict
    approved: bool
    capability_support: list = field(default_factory=list)
    """Which claims in each module's capability are backed by concepts it
    actually covers. DIAGNOSTIC ONLY -- see agent/coherence.py."""
    coherence: list = field(default_factory=list)
    """Where each module's dependencies live. DIAGNOSTIC ONLY -- nothing reads
    it to decide anything, and no threshold is applied. See agent/coherence.py."""
    state: str = "planned"  # needs_subject | asking | ready | planned
    sufficiency: dict = field(default_factory=dict)
    last_turn: Routed | None = None
    transcript: list[dict] = field(default_factory=list)

    @property
    def questions(self) -> list[dict]:
        return self.decisions.get("intake_strategy", {}).get("questions", [])

    def to_json(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "decisions": self.decisions,
            "questions": self.questions,
            "extent": self.extent,
            "feasibility": self.feasibility,
            "approved": self.approved,
            "state": self.state,
            "sufficiency": self.sufficiency,
            "coherence": self.coherence,
            "capability_support": self.capability_support,
            "transcript": self.transcript,
            "last_turn": None if self.last_turn is None else _turn_json(self.last_turn),
        }


def lifecycle_state(current: dict[str, Decision]) -> str:
    """Where a project has got to, from its decision rows alone.

    Module-level and shared, because two callers need it and they must not
    disagree: `view()` renders one project, `summary()` lists many. A project
    that reads `ready` on the index and `asking` when opened is a bug the user
    experiences as the app forgetting what it asked them.
    """
    intake = current.get("intake_strategy")
    intake_output = intake.output if intake else {}
    sufficiency = intake_output.get("sufficiency", {})

    if "scope" in current:
        return "planned"
    if not current:
        # No decision rows at all: the opening read never landed, so the request
        # was stored and nothing was ever made of it. Reported rather than
        # folded into `ready`, because "ready to plan" over an empty project is
        # the index telling the user work exists when none does -- and 30 of the
        # 35 projects on this machine are exactly that, from provider outages.
        return "unread"
    if sufficiency.get("verdict") == "needs_subject":
        return "needs_subject"
    if (intake_output.get("questions") or []) and not intake_output.get("exhausted"):
        return "asking"
    # Enough is known and no plan has been built. The normal end of a
    # conversation, not a failure: planning costs minutes, so the user asks for
    # it rather than being charged for it by surprise.
    return "ready"


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    """One row of the project index.

    Deliberately not a `PlanView`. Listing every project through `view()` would
    run coherence and capability analysis N times to render N list rows that
    show neither -- so this reads the same rows and computes only what a row
    displays.

    `title` is DERIVED, never stored: the subject the system settled on, falling
    back to the raw query until one exists. `project.title` is the first 80
    characters of what the user typed, which is why the index used to be a
    column of identical rows. Deriving it here rather than rewriting the stored
    title also means a correction that changes the subject relabels the project
    on the next read, with nothing to keep in sync.
    """

    id: str
    title: str
    query: str
    created_at: str
    state: str
    approved: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "query": self.query,
            "created_at": self.created_at,
            "state": self.state,
            "approved": self.approved,
        }


@dataclass(frozen=True, slots=True)
class _SystemDecision:
    """A decision the system made, with no model behind it.

    `_write` records what a decision cost. Some decisions cost nothing because
    no model was asked -- closing the intake conversation is code applying a
    rule, and recording it as a zero-cost call is more honest than inventing a
    provider for it.
    """

    model: str = ""
    prompt_version: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


_NO_CALL = _SystemDecision()


class PlanService:
    """Every method takes a project id. No session state lives here."""

    def __init__(
        self,
        store: Store | None = None,
        *,
        provider=None,
        question_budget: int = DEFAULT_BUDGET,
    ) -> None:
        self.store = store or FileStore()
        self.provider = provider
        # A conversational constraint, not an architectural one: how many
        # questions this product spends before planning. Every weak,
        # plan-changing axis is asked within it; the rest are carried as
        # visible assumptions rather than dropped.
        self.question_budget = question_budget

    # -- turns --------------------------------------------------------------

    # A crash barrier, not a policy: sufficiency and progress decide when to
    # stop asking. This only stops a model that keeps producing new material
    # unknowns after every answer.
    MAX_INTAKE_ROUNDS = 4

    def create(self, text: str) -> PlanView:
        """A request in, read and answered. **Never plans.**

        A conversational turn is one narrowly scoped model call: read what they
        said, and ask the one thing that matters. This used to run `_plan()`
        inline whenever the first reading came back sufficient, so a request
        that stated its own purpose and entry point -- *"short revision notes on
        signals and systems for GATE, i've done the basics"* -- paid for
        curriculum derivation before the user had seen a single word back.

        Planning is `proceed()`, and the user asks for it.
        """
        project = self.store.create_project(USER, title=text[:80])
        self.store.add_utterance(project.id, "user", text)
        self._read(project.id)
        return self.view(project.id)

    def answer(self, project_id: str, text: str) -> PlanView:
        """An answer is testimony, so the whole transcript is re-read and
        sufficiency is judged again from scratch.

        Readiness is sufficiency, never a turn count. The only other exit is
        *no progress*: if an answer strengthened nothing, asking again will not
        either, and the plan is derived on what is known. `MAX_INTAKE_ROUNDS` is
        a crash barrier behind both, not a definition of ready.
        """
        before = from_json(self._sufficiency(project_id))
        # A turn that dies after this write leaves the answer persisted, so
        # pressing the button again appends it a second time -- one real project
        # reached four identical copies. An identical answer repeated with
        # nothing said in between is a retry, not new testimony, and duplicating
        # it inflates the transcript that every later span resolves against.
        #
        # Only on the intake path. A repeated *correction* can be meaningful:
        # "shorter" then "shorter" plausibly asks for shorter still.
        said = [u.text for u in self.store.utterances(project_id) if u.role == "user"]
        if not said or said[-1] != text:
            self.store.add_utterance(project_id, "user", text)
        self._read(project_id)
        after = from_json(self._sufficiency(project_id))

        rounds = sum(
            1 for d in self.store.decision_history(project_id) if d.kind == "intake_strategy"
        )
        stalled = after is not None and not improved(before, after)
        # These conditions used to trigger `_plan()` here. They still decide the
        # same thing -- whether asking again is worth a turn -- but the answer is
        # now a *state*, not an action: the conversation is over, and the user
        # decides when to spend minutes on a plan.
        if (
            after is None
            or after.verdict == "sufficient"
            or stalled
            or rounds >= self.MAX_INTAKE_ROUNDS
            or not self._pending(project_id)
        ):
            self._close_intake(project_id, stalled=stalled, rounds=rounds)
        return self.view(project_id)

    def _close_intake(self, project_id: str, *, stalled: bool, rounds: int) -> None:
        """Record that the conversation is finished, and why.

        The questions are kept rather than deleted -- what the decider wanted to
        ask, and why it stopped asking, is exactly the evidence `intake_strategy`
        exists to hold.
        """
        current = self.store.current_decisions(project_id).get("intake_strategy")
        if current is None or current.output.get("exhausted"):
            return
        reason = (
            "the last answer strengthened nothing"
            if stalled
            else f"{rounds} rounds of questions"
            if rounds >= self.MAX_INTAKE_ROUNDS
            else "nothing material left to ask"
        )
        self._write(
            project_id,
            "intake_strategy",
            {**current.output, "exhausted": True, "closed_because": reason},
            _NO_CALL,
        )

    def proceed(self, project_id: str) -> PlanView:
        """Plan now, on the defaults each open question carries. Semantics §3:
        a question never blocks."""
        if "scope" not in self.store.current_decisions(project_id):
            self._plan(project_id)
        return self.view(project_id)

    def correct(self, project_id: str, text: str) -> PlanView:
        """One natural-language correction: routed, then applied to its rows."""
        self.store.add_utterance(project_id, "user", text)
        current = self.store.current_decisions(project_id)
        outputs = {kind: d.output for kind, d in current.items()}

        call = planning.revise(outputs, text, provider=self.provider)
        routing = call.routing
        assert routing is not None

        actual: list[str] = []
        for kind, output in call.outputs.items():
            if output != outputs.get(kind):
                self._write(project_id, kind, output, call)
                actual.append(kind)

        turn = Routed(
            correction=text,
            reading=routing.reading,
            claimed=tuple(routing.targets),
            actual=tuple(k for k in ALL_DECISIONS if k in actual),
            out_of_scope=routing.out_of_scope,
        )
        # The router's turn is testimony too: append-only, ordered, and part of
        # the transcript a later intake decision reads. `utterance.role` is free
        # text and this is the system's turn in the conversation.
        self.store.add_utterance(project_id, "router", json.dumps(_turn_json(turn)))
        return self.view(project_id)

    def approve(self, project_id: str) -> Commitment:
        """The gate. Idempotent by the set of decisions committed."""
        current = self.store.current_decisions(project_id)
        # Every decision the plan rests on, including the upstream two: the user
        # approved a meaning that depends on them, and if one drifts later the
        # approval rested on a derivation they never saw. `intake_strategy` is
        # excluded -- it governs the conversation, not the artifact.
        committed = [current[k] for k in PLAN_DECISIONS + UPSTREAM_DECISIONS if k in current]
        ids = [d.id for d in committed]
        hash_ = commit_hash(ids)

        existing = self.store.commitment_by_hash(project_id, hash_)
        if existing is not None:
            return existing

        for decision in committed:
            decision.status = "committed"
            self.store.put_decision(decision)

        return self.store.add_commitment(
            Commitment(
                id=__import__("uuid").uuid4().hex,
                project_id=project_id,
                kind="plan",
                snapshot=self._snapshot(current),
                decision_ids=ids,
                decision_ids_hash=hash_,
                decision_environment={
                    "prompt_versions": sorted(
                        {d.prompt_version for d in committed if d.prompt_version}
                    ),
                    "models": sorted({d.model for d in committed if d.model}),
                },
                approved_by=USER,
            )
        )

    # -- reads --------------------------------------------------------------

    def summary(self, project_id: str) -> ProjectSummary:
        """One project, as the index shows it. Cheaper than `view()` by design."""
        project = self.store.get_project(project_id)
        if project is None:
            raise KeyError(project_id)
        current = self.store.current_decisions(project_id)
        situation = (current["interpret_situation"].output or {}) if (
            "interpret_situation" in current
        ) else {}
        said = [u.text for u in self.store.utterances(project_id) if u.role == "user"]
        return ProjectSummary(
            id=project.id,
            title=situation.get("subject") or project.title,
            # The opening request, not the whole transcript: it is what the user
            # recognises the project by, and later corrections are refinements
            # of it rather than alternative names for it.
            query=said[0] if said else project.title,
            created_at=project.created_at,
            state=lifecycle_state(current),
            approved=bool(self.store.commitments(project_id)),
        )

    def summaries(self) -> list[ProjectSummary]:
        """Every project, newest first. Skips any that fail to load rather than
        failing the whole index -- one unreadable file must not cost the user
        every other project."""
        out = []
        for project in self.store.projects():
            try:
                out.append(self.summary(project.id))
            except (KeyError, ValueError, TypeError):
                continue
        return out

    def view(self, project_id: str) -> PlanView:
        project = self.store.get_project(project_id)
        if project is None:
            raise KeyError(project_id)
        current = self.store.current_decisions(project_id)
        decisions = {k: d.output for k, d in current.items()}
        utterances = self.store.utterances(project_id)
        router = [u for u in utterances if u.role == "router"]
        intake = current.get("intake_strategy")
        sufficiency = intake.output.get("sufficiency", {}) if intake else {}
        return PlanView(
            state=lifecycle_state(current),
            sufficiency=sufficiency,
            project_id=project_id,
            title=project.title,
            decisions=decisions,
            extent=_extent(decisions),
            coherence=coherence_json(
                analyse(decisions.get("derive_structure"), decisions.get("partition"))
            ),
            capability_support=support_to_json(
                capability_support(decisions.get("partition"))
            ),
            feasibility=_feasibility(decisions),
            approved=bool(self.store.commitments(project_id)),
            last_turn=_turn_from_json(json.loads(router[-1].text)) if router else None,
            transcript=[
                {"role": u.role, "text": u.text} for u in utterances if u.role == "user"
            ],
        )

    # -- internals ----------------------------------------------------------

    def _read(self, project_id: str) -> None:
        """Read the request, decide what is worth asking, then write only those.

        Three steps, and the middle one is free:

            interpret   a model call -- what the request says, and what backs it
            decide()    pure code -- which axes are weak, material and askable
            ask()       a model call ONLY if `asking` is non-empty

        The model used to do steps 1 and 3 in one call, authoring questions for
        every weak axis it could see. `_read` then discarded the ones policy did
        not choose -- all of them whenever the verdict was `sufficient`, which is
        the common case. Measured on "i need notes on VLSI": 102s and five
        questions written, of which the budget could use at most four and
        `asking` typically names one or two.

        The model still chooses nothing about *what* is asked. `decide()` names
        the axes from the model's own readings; `ask()` writes the wording.
        """
        said = [u.text for u in self.store.utterances(project_id) if u.role == "user"]
        call = planning.interpret("\n\n".join(said), provider=self.provider)

        self._write(project_id, "interpret_situation", call.outputs["interpret_situation"], call)

        readings = [AxisReading(**a) for a in call.outputs.get("axes", [])]
        # Semantics §1: stated constraints bind. The decider needs them to see
        # when a statement about an axis came back as an inference on that axis.
        situation = call.outputs["interpret_situation"] or {}
        stated = situation.get("stated") or []
        sufficiency = decide(
            readings, said, stated=stated, budget=self.question_budget
        )

        questions: list[dict] = []
        intake_call = call
        if sufficiency.asking:
            intake_call = planning.ask(
                Situation(**situation), sufficiency.asking, provider=self.provider
            )
            # The wording is the model's; the axes are not. Anything it wrote for
            # an axis nobody asked about is dropped rather than shown.
            questions = [
                q
                for q in intake_call.outputs.get("questions", [])
                if q.get("axis") in sufficiency.asking
            ]

        self._write(
            project_id,
            "intake_strategy",
            {"questions": questions, "sufficiency": sufficiency.to_json()},
            intake_call,
        )

    def _plan(self, project_id: str) -> None:
        """The six decisions downstream of a sufficient situation, in two calls:
        what exists and what is in play, then the plan over it."""
        current = self.store.current_decisions(project_id)
        situation = Situation(**current["interpret_situation"].output)

        landscape_call = planning.derive(situation, provider=self.provider)
        for kind, output in landscape_call.outputs.items():
            self._write(project_id, kind, output, landscape_call)

        landscape = planning.Landscape(**landscape_call.outputs)
        plan_call = planning.plan(situation, landscape, provider=self.provider)
        for kind, output in plan_call.outputs.items():
            self._write(project_id, kind, output, plan_call)

    def _pending(self, project_id: str) -> list[dict]:
        """Questions that actually survived to be asked.

        The decider names axes worth asking about; the model authors the
        questions. Nothing makes those agree -- `_read` intersects them, and the
        intersection can be empty, which is how a request for a graph cheat
        sheet reached a page that said "I'd rather ask than guess" and then
        asked nothing.

        A question that does not exist cannot be answered, so it cannot be a
        reason to wait. Semantics §3: a question is an offer to correct early,
        never a blocker.
        """
        intake = self.store.current_decisions(project_id).get("intake_strategy")
        return (intake.output.get("questions") if intake else None) or []

    def _sufficiency(self, project_id: str) -> dict:
        intake = self.store.current_decisions(project_id).get("intake_strategy")
        if intake is None:
            return {"verdict": "sufficient", "axes": []}
        return intake.output.get("sufficiency", {"verdict": "sufficient", "axes": []})

    def _write(self, project_id: str, kind: str, output: dict, call) -> Decision:
        return self.store.put_decision(
            Decision(
                id=__import__("uuid").uuid4().hex,
                project_id=project_id,
                kind=kind,
                status="candidate",
                freshness="current",
                inputs_hash=inputs_hash(kind, output),
                output=output,
                model=call.model or None,
                prompt_version=call.prompt_version or None,
                cost={"in": call.input_tokens, "out": call.output_tokens},
            )
        )

    def _snapshot(self, current: dict[str, Decision]) -> dict:
        """System Design §4: stands alone. The plan's own content, so it still
        says what was agreed with the decision table dropped."""
        snapshot = {k: current[k].output for k in PLAN_DECISIONS if k in current}
        snapshot["extent"] = _extent({k: d.output for k, d in current.items()})
        return snapshot


def _feasibility(decisions: dict[str, dict]) -> dict:
    """Derived, never written by the model. Architecture §13/§14: an unservable
    prose failure is reported before approval, not answered with prose."""
    if "scope" not in decisions:
        return {}
    return derive_feasibility(Scope(**decisions["scope"]))


def _turn_json(turn: Routed) -> dict:
    return {
        "correction": turn.correction,
        "reading": turn.reading,
        "claimed": list(turn.claimed),
        "actual": list(turn.actual),
        "unchanged": [d for d in ALL_DECISIONS if d not in turn.actual],
        "unclaimed_drift": list(turn.unclaimed_drift),
        "claimed_but_unchanged": list(turn.claimed_but_unchanged),
        "out_of_scope": turn.out_of_scope,
        "not_understood": turn.not_understood,
    }


def _turn_from_json(data: dict) -> Routed:
    return Routed(
        correction=data["correction"],
        reading=data["reading"],
        claimed=tuple(data["claimed"]),
        actual=tuple(data["actual"]),
        out_of_scope=data.get("out_of_scope"),
    )


def _extent(decisions: dict[str, dict]) -> dict:
    """Derived, never written by the model (Architecture §14)."""
    if "scope" not in decisions or "partition" not in decisions:
        return {}
    return derive_extent(Scope(**decisions["scope"]), Partition(**decisions["partition"]))


__all__ = [
    "PlanService",
    "PlanView",
    "Routed",
    "ALL_DECISIONS",
    "PLAN_DECISIONS",
    "UPSTREAM_DECISIONS",
    "INTERACTION_DECISIONS",
    "PlanBody",
]
