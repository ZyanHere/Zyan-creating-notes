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
    state: str = "planned"  # needs_subject | asking | planned
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
            "transcript": self.transcript,
            "last_turn": None if self.last_turn is None else _turn_json(self.last_turn),
        }


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
        """A request in. Read it, and ask before planning if anything material
        is genuinely unknown -- Architecture §4 puts the intake loop first and
        terminates it on sufficiency, not on a fixed number of turns."""
        project = self.store.create_project(USER, title=text[:80])
        self.store.add_utterance(project.id, "user", text)
        self._read(project.id)
        if self._sufficiency(project.id)["verdict"] == "sufficient" or not self._pending(
            project.id
        ):
            self._plan(project.id)
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
        self.store.add_utterance(project_id, "user", text)
        self._read(project_id)
        after = from_json(self._sufficiency(project_id))

        rounds = sum(
            1 for d in self.store.decision_history(project_id) if d.kind == "intake_strategy"
        )
        stalled = after is not None and not improved(before, after)
        if (
            after is None
            or after.verdict == "sufficient"
            or stalled
            or rounds >= self.MAX_INTAKE_ROUNDS
            or not self._pending(project_id)
        ):
            self._plan(project_id)
        return self.view(project_id)

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
        questions = (intake.output.get("questions") if intake else None) or []
        if "scope" in current:
            state = "planned"
        elif sufficiency.get("verdict") == "needs_subject":
            state = "needs_subject"
        elif questions:
            state = "asking"
        else:
            # No plan, nothing to ask, and a subject we have. Reachable only if
            # planning failed after the read -- a provider fault, say. `asking`
            # here used to strand the user on a page with no control at all.
            state = "unplanned"
        return PlanView(
            state=state,
            sufficiency=sufficiency,
            project_id=project_id,
            title=project.title,
            decisions=decisions,
            extent=_extent(decisions),
            feasibility=_feasibility(decisions),
            approved=bool(self.store.commitments(project_id)),
            last_turn=_turn_from_json(json.loads(router[-1].text)) if router else None,
            transcript=[
                {"role": u.role, "text": u.text} for u in utterances if u.role == "user"
            ],
        )

    # -- internals ----------------------------------------------------------

    def _read(self, project_id: str) -> None:
        """interpret_situation, then the decider over the model's axis readings.

        The model proposes; policy and the budget dispose. `intake_strategy`
        holds both the surviving questions and the sufficiency record, so why
        each axis was or was not asked outlives the turn.
        """
        said = [u.text for u in self.store.utterances(project_id) if u.role == "user"]
        call = planning.interpret("\n\n".join(said), provider=self.provider)

        self._write(project_id, "interpret_situation", call.outputs["interpret_situation"], call)

        readings = [AxisReading(**a) for a in call.outputs.get("axes", [])]
        sufficiency = decide(readings, said, budget=self.question_budget)
        proposed = call.outputs.get("proposed_questions", [])
        surviving = [q for q in proposed if q.get("axis") in sufficiency.asking]

        self._write(
            project_id,
            "intake_strategy",
            {"questions": surviving, "sufficiency": sufficiency.to_json()},
            call,
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
