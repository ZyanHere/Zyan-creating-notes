"""HTTP surface. The only thing a client may talk to.

Thin on purpose: routes translate HTTP into service calls and back. No model
call, no template, no geometry lives here.

    uvicorn backend.api:app --reload --timeout-keep-alive 900
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

import engine
from agent import curriculum
from agent.providers import (
    NoProviderConfigured,
    OutputTruncated,
    ProviderRefused,
    ProviderUnavailable,
)
from backend import config, service  # noqa: F401  (config loads .env)
from backend.jobs import JOBS
from backend.planning import PlanService

app = FastAPI(title="Notes Engine", version="0.1.0")

# The frontend is a separate origin in development. Wide open on purpose: there
# is one local user and no credentials to protect. Narrow this the moment
# accounts exist.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    # Only simple response headers reach cross-origin JavaScript unless they are
    # named here, and the frontend is a separate origin in development. Without
    # this the export's own counts are invisible to the only client that asks
    # for them.
    expose_headers=["content-disposition", "x-modules-written", "x-modules-total"],
)


class GenerateRequest(BaseModel):
    request: str = Field(
        min_length=3,
        description="The learner's request, in their own words.",
        examples=["teach me binary search for a beginner"],
    )


class GenerateResponse(BaseModel):
    title: str
    pdf: str
    html: str
    pages: int
    input_tokens: int
    output_tokens: int
    provider: str
    model: str
    prompt_version: str
    repairs: int
    render_environment: dict[str, str]
    representation: dict


# ---------------------------------------------------------------------------
# Plan gate. System Design §9's candidate surface, with one change: intake is a
# field of the current view, not an endpoint -- a separate GET would imply
# questions are a phase, and they are a property of where the plan currently is.
# Synchronous: a turn is 20-60s. The job queue arrives at M4 with a reason.
# ---------------------------------------------------------------------------

_plans = PlanService()


class ProjectRequest(BaseModel):
    text: str = Field(min_length=3, description="The learner's request, in their own words.")


class UtteranceRequest(BaseModel):
    text: str = Field(min_length=1, description="A correction, in the user's own words.")


class ApproveRequest(BaseModel):
    decision_ids: list[str] = Field(
        default_factory=list,
        description="The set being approved. Idempotent: the same set is the same commitment.",
    )



# A model that returns unusable output twice is not a server fault, and a stack
# trace is not something a reader can act on. 502: the upstream answered badly.
_MODEL_FAILED = (
    "The model returned something unusable, twice. Nothing was lost — try again."
)


def _guard(work):
    """Run a plan turn, turning provider/validation failures into a clean 502.

    The provider's own failures are `RuntimeError` subclasses and were escaping
    as 500s with a stack trace -- a truncated completion took 518 seconds and
    then looked like a server crash. They carry readable messages; the caller
    should get those, not a traceback.
    """
    try:
        return work()
    except KeyError:
        raise HTTPException(status_code=404, detail="no such project")
    except NoProviderConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ProviderUnavailable as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "The model provider didn't answer, after several retries. "
                f"Nothing was lost — try again.\n\n{exc}"
            ),
        )
    except ProviderRefused as exc:
        # Retrying is pointless -- the request itself is wrong. The message
        # already names the fix (a withdrawn model, a spent rate limit).
        raise HTTPException(status_code=502, detail=str(exc))
    except OutputTruncated as exc:
        raise HTTPException(
            status_code=502,
            detail=f"The model ran out of room before it finished.\n\n{exc}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"{_MODEL_FAILED}\n\n{exc}")


@app.post("/projects")
def create_project(body: ProjectRequest) -> dict:
    return _guard(lambda: _plans.create(body.text).to_json())


@app.get("/projects")
def list_projects() -> list[dict]:
    """The project index: enough per row to tell two projects apart and reopen
    the right one.

    Every field is a durable fact -- derived subject, opening request, lifecycle
    state, and how much of the curriculum is on disk. Deliberately excluded:
    whether a generation is *currently* running or has failed. That lives in the
    in-memory job table, does not survive a restart, and a row that says
    "1 failed" until the server bounces is worse than a row that says nothing.
    """
    rows = []
    for summary in _plans.summaries():
        written, total = _module_counts(summary.id)
        rows.append(summary.to_json() | {"modules_done": written, "modules_total": total})
    return rows


@app.get("/projects/{project_id}/plan")
def get_plan(project_id: str) -> dict:
    try:
        return _plans.view(project_id).to_json()
    except KeyError:
        raise HTTPException(status_code=404, detail="no such project")


@app.post("/projects/{project_id}/utterances")
def add_utterance(project_id: str, body: UtteranceRequest) -> dict:
    """One box, two meanings. Before a plan exists the utterance answers an
    intake question; after one exists it corrects a decision. The client does
    not choose which -- the project's state does."""
    try:
        view = _plans.view(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="no such project")
    # Before a plan exists an utterance is testimony; after one exists it is a
    # correction. `needs_subject` and `ready` are *before* -- routing them to
    # `correct()` ran the correction router over a plan that does not exist,
    # which is neither quick nor recoverable, and the answer was never read.
    if view.state in ("asking", "needs_subject", "ready"):
        return _guard(lambda: _plans.answer(project_id, body.text).to_json())
    return _guard(lambda: _plans.correct(project_id, body.text).to_json())


@app.post("/projects/{project_id}/plan")
def force_plan(project_id: str) -> dict:
    """Plan now, on the defaults the open questions carry. Semantics §3: a
    question is an offer to correct early, never a blocker."""
    return _guard(lambda: _plans.proceed(project_id).to_json())


@app.post("/projects/{project_id}/plan/approve")
def approve_plan(project_id: str, body: ApproveRequest) -> dict:
    """[GATE, idempotent] Re-approving an identical decision set is identity."""
    try:
        commitment = _plans.approve(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="no such project")
    return {
        "id": commitment.id,
        "kind": commitment.kind,
        "approved_at": commitment.approved_at,
        "decision_ids": commitment.decision_ids,
        "snapshot": commitment.snapshot,
    }


# ---------------------------------------------------------------------------
# From the approved plan to a PDF. The gap this closes: `approve()` wrote a
# commitment nothing downstream read, and `/generate` took a raw string that had
# never been through a gate. Two working halves that did not meet.
#
# Off the request thread, because the model call is minutes long and has come
# back empty. See `backend/jobs.py` for why that is a thread and not a queue.
# ---------------------------------------------------------------------------


def _project_out(project_id: str) -> Path:
    # NOT `out/projects/` -- that is `FileStore`'s own root (backend/store.py).
    # A generated artifact living inside the store's directory is one careless
    # glob away from being read as a project.
    return service.OUT / "artifacts" / project_id


def _approved(project_id: str) -> dict:
    """The approved curriculum. Source of truth; never rewritten by generation."""
    commitments = _plans.store.commitments(project_id)
    if not commitments:
        raise HTTPException(status_code=409, detail="approve the plan first")
    return commitments[-1].snapshot


def _module_pdf(project_id: str, title: str) -> Path:
    """Where this module's PDF lands. `service.generate` names files from the
    document title, and a module's document is titled after the module."""
    return _project_out(project_id) / f"{service.slugify(title)}.pdf"


def _job_key(project_id: str, index: int) -> str:
    return f"{project_id}:{index}"


def _module_counts(project_id: str) -> tuple[int, int]:
    """(written, total) for the project index. Never raises: an unapproved or
    unreadable project has no curriculum yet, which is (0, 0), not an error that
    should cost the caller every other row."""
    try:
        plan = _approved(project_id)
    except HTTPException:
        return (0, 0)
    approved = curriculum.modules(plan)
    written = sum(1 for m in approved if _module_pdf(project_id, m.title).is_file())
    return (written, len(approved))


def _module_report(project_id: str, title: str) -> dict:
    """What a finished generation observed, read back from beside its PDF.

    `service.generate` has always written this sidecar and nothing ever read it,
    so page count, cost and the fulfilment check lived only in the in-memory job
    and died with the process: reopening a project showed a bare "done" for work
    the system had fully described on disk. Reading it here is what makes the
    from-disk path return the same shape as the live-job path.

    Best effort by design -- a missing or malformed sidecar means an older or
    interrupted generation, and the module is still legitimately done because
    the PDF exists.
    """
    path = _project_out(project_id) / f"{service.slugify(title)}.report.json"
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

    fulfilment = saved.get("fulfilment")
    body: dict = {"calls": saved.get("calls")}
    if fulfilment:
        body |= {"fulfilment": fulfilment, "satisfied": fulfilment.get("satisfied", True)}
    body["representation"] = {
        "stated_gaps": saved.get("stated_gaps") or [],
        "unrendered": saved.get("unrendered") or [],
    }
    return {k: v for k, v in body.items() if v is not None}


def _module_state(project_id: str, module) -> dict:
    """Generated, generating, or not yet -- for one module."""
    job = JOBS.get(_job_key(project_id, module.index))
    pdf = _module_pdf(project_id, module.title)
    body = module.to_json()

    if job is None:
        # A finished module survives a restart because its PDF does; the file is
        # the record, not the job table. The sidecar beside it carries what the
        # run observed, so a reopened project is as complete as a live one --
        # minus `pages`, which is a property of the PDF rather than of the run.
        body["state"] = "done" if pdf.is_file() else "idle"
        if body["state"] == "done":
            # `pages` is the one field the sidecar does not carry, because it is
            # a property of the rendered PDF rather than of the run. Counting it
            # from the file keeps older artifacts working too, which adding it
            # to the sidecar would not.
            body |= _module_report(project_id, module.title)
            body["pages"] = service.count_pages(pdf.read_bytes())
    else:
        body |= job.to_json()
        if job.state == "done":
            result = job.result
            body |= {
                "pages": result.pages_estimate,
                "calls": result.calls,
                "satisfied": (result.fulfilment or {}).get("satisfied", True),
                "fulfilment": result.fulfilment,
                "representation": {
                    "stated_gaps": list(result.representation.stated_gaps),
                    "unrendered": list(result.representation.unrendered),
                },
            }
    if body["state"] == "done":
        body["pdf"] = f"/projects/{project_id}/modules/{module.index}/artifact.pdf"
    return body


@app.get("/projects/{project_id}/modules")
def list_modules(project_id: str) -> dict:
    """The approved modules and which of them have been written.

    One entry per approved module; a plan written before the curriculum layer
    yields exactly one, so the client has a single shape to render.
    """
    try:
        _plans.view(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="no such project")
    plan = _approved(project_id)
    return {
        "modules": [_module_state(project_id, m) for m in curriculum.modules(plan)]
    }


@app.post("/projects/{project_id}/modules/{index}/generate")
def generate_module(project_id: str, index: int) -> dict:
    """[requires an approved plan] Write one module. Returns at once.

    One module at a time, on demand -- not a batch over the curriculum. The
    approved plan is read, never rewritten: `plan_for` derives a narrowed view
    of it so writing module 4 cannot change what module 5 was approved to be.
    """
    try:
        view = _plans.view(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="no such project")

    plan = _approved(project_id)
    try:
        scoped = curriculum.plan_for(plan, index)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    said = [u.text for u in _plans.store.utterances(project_id) if u.role == "user"]
    request = said[0] if said else view.title

    key = _job_key(project_id, index)
    JOBS.forget(key)
    JOBS.start(
        key,
        lambda: service.generate(
            request, out_dir=_project_out(project_id), plan=scoped
        ),
    )
    return {"state": "running", "index": index}


@app.get("/projects/{project_id}/export.zip")
def export_project(project_id: str) -> Response:
    """The whole project, in one download.

    A curriculum is several PDFs, and asking for 25 of them one at a time is not
    a download, it is a chore. Separate files rather than one merged PDF: each
    module is its own document with its own cover and page numbering, and
    merging them is a render-engine job (continuous pagination, a combined
    contents page), not a packaging one.

    The `NN-` prefix exists only inside the archive. On disk a module's PDF is
    named from its title with no ordering, so unzipping into a folder would
    otherwise present the curriculum alphabetically -- which is exactly the
    order the plan decided against.
    """
    try:
        summary = _plans.summary(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="no such project")

    plan = _approved(project_id)  # 409 when the plan was never approved
    approved = curriculum.modules(plan)
    written = [(m, _module_pdf(project_id, m.title)) for m in approved]
    written = [(m, p) for m, p in written if p.is_file()]
    if not written:
        raise HTTPException(
            status_code=409,
            detail="nothing to export yet -- no module of this project has been written.",
        )

    folder = service.slugify(summary.title)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for module, path in written:
            archive.write(path, f"{folder}/{module.index:02d}-{path.name}")
        # The approved curriculum travels with the documents: it is what the
        # user agreed to, and it names the modules that are missing from this
        # archive because they have not been written.
        archive.writestr(
            f"{folder}/plan.json", json.dumps(plan, indent=2, ensure_ascii=False)
        )

    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={
            "content-disposition": f'attachment; filename="{folder}.zip"',
            # So the client can say "12 of 25" without re-deriving it.
            "x-modules-written": str(len(written)),
            "x-modules-total": str(len(approved)),
        },
    )


@app.get("/projects/{project_id}/modules/{index}/artifact.pdf")
def module_artifact(project_id: str, index: int, download: bool = False) -> FileResponse:
    """Inline by default; `?download=1` to save it.

    `filename=` alone sets `content-disposition: attachment`, which makes the
    browser save the file instead of showing it.
    """
    plan = _approved(project_id)
    found = [m for m in curriculum.modules(plan) if m.index == index]
    if not found:
        raise HTTPException(status_code=404, detail=f"no module {index}")
    path = _module_pdf(project_id, found[0].title)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="this module has not been written yet")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
        content_disposition_type="attachment" if download else "inline",
    )


@app.get("/health")
def health() -> dict:
    """Liveness, plus what this process can see of the renderer.

    The renderer half is here because the answer that matters is the one *this
    process* computes: a check run in a terminal proves nothing about a server
    started from somewhere else, and diagnosing a refused generation by asking
    someone to read their own logs back is slower than asking the server.
    """
    return {"status": "ok", "renderer": engine.render.browser_status()}


@app.post("/generate", response_model=GenerateResponse)
def generate(body: GenerateRequest) -> GenerateResponse:
    """Synchronous through M3. Long-running by nature -- run uvicorn with a
    generous keep-alive timeout until M4 moves this to background execution."""
    result = service.generate(body.request)
    return GenerateResponse(
        title=result.title,
        pdf=str(result.pdf_path),
        html=str(result.html_path),
        pages=result.pages_estimate,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        provider=result.provider,
        model=result.model,
        prompt_version=result.prompt_version,
        repairs=result.repairs,
        render_environment=dict(result.render_environment),
        representation={
            "pairs": [list(p) for p in result.representation.pairs],
            "undiagnosed": result.representation.undiagnosed,
            "unlisted": list(result.representation.unlisted),
            "unrendered": list(result.representation.unrendered),
            "scale": result.representation.scale,
        },
    )


@app.get("/artifacts/{name}")
def artifact(name: str) -> FileResponse:
    path = (service.OUT / name).resolve()
    if not path.is_file() or service.OUT.resolve() not in path.parents:
        raise HTTPException(status_code=404, detail="no such artifact")
    return FileResponse(path)
