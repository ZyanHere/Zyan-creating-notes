"""The application boundary.

The backend coordinates the agent and the engine; neither knows about the
other. It holds no pedagogy (that is the agent's) and no geometry (that is the
engine's) -- what it owns is the sequence, and later the persistence, jobs and
lifecycle that the sequence needs.

M1's sequence is two steps. It stays this shape as steps are added.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import agent
import engine
from backend import config

OUT = Path("out")


@dataclass(frozen=True, slots=True)
class RepresentationReport:
    """What this run says about the representation vocabulary itself.

    M1 is now an instrument as well as a product. Representation Boundary Rev. 3
    is frozen and is reopened only by a measured contradiction, so the run has to
    be able to produce one. Everything here is a reading, not a repair.
    """

    pairs: tuple[tuple[str, str, str, str], ...]
    """(diagnosis, kind, relation, realization) for every departure from prose.

    Four columns, not two. `relation` is the claim the model made; `realization`
    is the geometry the template chose to make it with. Collapsing them is the
    defect this build removes -- `topology -> stack` twice concealed one true
    figure and one false one, because neither the claim nor the chosen geometry
    was written down.

    Architecture §12: the most valuable retained thing is the smallest -- which
    prose-failure fired on which node. Until Rev. 3 the model computed this and
    we discarded it, keeping only the outcome.
    """

    undiagnosed: int
    """Departures with no diagnosis. A departure from prose that cannot name its
    licence is decoration, which §13 exists to prevent."""

    unlisted: tuple[str, ...]
    """Diagnoses the model wrote as `unlisted: ...` -- a prose failure the §13
    taxonomy does not carry. This is the reading that reopens the frozen
    baseline, and the reason `diagnosis` is free text rather than an enum."""

    unrendered: tuple[str, ...]
    """Kinds the template could not draw. The document said it; the paper did not."""

    scale: float
    """What Chromium shrank the document to. Below 1.0, a figure overflowed."""

    def is_clean(self) -> bool:
        return not (self.undiagnosed or self.unlisted or self.unrendered) and self.scale >= 1.0


@dataclass(frozen=True, slots=True)
class GenerateResult:
    title: str
    pdf_path: Path
    html_path: Path
    pages_estimate: int
    input_tokens: int
    output_tokens: int
    provider: str
    model: str
    prompt_version: str
    repairs: int
    render_environment: Mapping[str, str]
    representation: RepresentationReport


def slugify(text: str, *, limit: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:limit].rstrip("-")) or "document"


def generate(
    request: str, *, out_dir: Path = OUT, template_id: str | None = None
) -> GenerateResult:
    """One learner request in; one PDF on disk out.

    Synchronous on purpose. Background execution arrives at M4 when a set of
    members makes the wait genuinely long; adding it now would be infrastructure
    ahead of a reason.
    """
    if not config.provider_is_configured():
        raise RuntimeError(
            "No model provider configured. Generation is refused rather than "
            "silently producing something hand-authored -- set OPENROUTER_API_KEY "
            "in .env (see .env.example)."
        )

    generated = agent.generate_document(request)
    doc = generated.document

    # Semantics §2: the template is the user's, and it constrains presentation
    # only. Passing it here rather than hardcoding the default is what makes that
    # separation real -- the same Document renders in any visual language.
    kwargs = {"template_id": template_id} if template_id else {}
    rendered = engine.render_pdf(doc.model_dump(), **kwargs)
    report = _representation_report(doc, rendered)

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = slugify(doc.title)
    if template_id and template_id != engine.render.DEFAULT_TEMPLATE:
        stem = f"{stem}--{template_id}"
    pdf_path = out_dir / f"{stem}.pdf"
    html_path = out_dir / f"{stem}.html"
    pdf_path.write_bytes(rendered.pdf)
    html_path.write_text(rendered.html, encoding="utf-8")
    # Keep the Document. A template fix should not cost another generation --
    # and at M5 this is the row that moves into the decision table.
    (out_dir / f"{stem}.json").write_text(
        doc.model_dump_json(indent=2), encoding="utf-8"
    )
    # Kept beside the document, not inside it: the document is re-renderable
    # input, the report is what this run observed about the vocabulary. One
    # run says little; the file exists so runs can accumulate into the sizing
    # evidence Product Semantics §14 asks for.
    (out_dir / f"{stem}.report.json").write_text(
        json.dumps(
            {
                "request": request,
                "title": doc.title,
                "prompt_version": generated.prompt_version,
                "model": f"{generated.provider}/{generated.model}",
                "pairs": [list(pair) for pair in report.pairs],
                "undiagnosed": report.undiagnosed,
                "unlisted": list(report.unlisted),
                "unrendered": list(report.unrendered),
                "scale": report.scale,
                "template": rendered.render_environment.get("template_id"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return GenerateResult(
        title=doc.title,
        pdf_path=pdf_path,
        html_path=html_path,
        pages_estimate=_count_pages(rendered.pdf),
        input_tokens=generated.input_tokens,
        output_tokens=generated.output_tokens,
        provider=generated.provider,
        model=generated.model,
        prompt_version=generated.prompt_version,
        repairs=generated.repairs,
        render_environment=rendered.render_environment,
        representation=report,
    )


def _representation_report(doc, rendered) -> RepresentationReport:
    """Read the run. Diagnose nothing, repair nothing, hide nothing."""
    pairs: list[tuple[str, str]] = []
    undiagnosed = 0
    unlisted: list[str] = []

    # Realizations come back in document order, one per relational block that a
    # template actually drew, so they zip onto the relational blocks in order.
    drawn = list(rendered.realizations)

    for section in doc.sections:
        for block in section.blocks:
            if block.kind == "prose":
                continue
            relation = getattr(block, "relation", "") or ""
            realization = ""
            if block.kind == "relation":
                realization = drawn.pop(0)[1] if drawn else "(none)"
            diagnosis = getattr(block, "diagnosis", None)
            if not diagnosis:
                undiagnosed += 1
                continue
            pairs.append((diagnosis, block.kind, relation, realization))
            if diagnosis.strip().lower().startswith("unlisted"):
                unlisted.append(diagnosis.strip())

    return RepresentationReport(
        pairs=tuple(pairs),
        undiagnosed=undiagnosed,
        unlisted=tuple(unlisted),
        unrendered=tuple(sorted(set(rendered.unrendered))),
        scale=rendered.scale,
    )


def _count_pages(pdf: bytes) -> int:
    """Page count without a PDF library: /Type /Page occurrences, minus /Pages."""
    return max(pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages"), 1)
