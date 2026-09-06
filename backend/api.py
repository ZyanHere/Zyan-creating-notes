"""HTTP surface. The only thing a client may talk to.

Thin on purpose: routes translate HTTP into service calls and back. No model
call, no template, no geometry lives here.

    uvicorn backend.api:app --reload --timeout-keep-alive 900
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend import config, service  # noqa: F401  (config loads .env)
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


@app.post("/projects")
def create_project(body: ProjectRequest) -> dict:
    return _plans.create(body.text).to_json()


@app.get("/projects")
def list_projects() -> list[dict]:
    return [
        {"id": p.id, "title": p.title, "created_at": p.created_at}
        for p in _plans.store.projects()
    ]


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
    if view.state == "asking":
        return _plans.answer(project_id, body.text).to_json()
    return _plans.correct(project_id, body.text).to_json()


@app.post("/projects/{project_id}/plan")
def force_plan(project_id: str) -> dict:
    """Plan now, on the defaults the open questions carry. Semantics §3: a
    question is an offer to correct early, never a blocker."""
    try:
        return _plans.proceed(project_id).to_json()
    except KeyError:
        raise HTTPException(status_code=404, detail="no such project")


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
