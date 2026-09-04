# The Thin Vertical Slice — Phase 1 Build Plan

**1 Sep 2026 — companion to `Foundation.md` (Rev. 4) and `System-Design.md` (Rev. 3)**

> ## ⚠ STEPS 1–2 DONE · STEPS 3–5 SUPERSEDED — 4 Sep 2026
>
> Read **`Product-Semantics.md` (Rev. 1)** first.
>
> **Steps 1 and 2 were built and work.** `document-engine/` renders a plan to a PDF;
> `agent/fill.py` has an LLM write the content. Two documents were generated end to
> end. The code is in the tree.
>
> **Steps 3–5 are dead as written.** `plan.py` and `spec.py` were designed to emit a
> vocabulary of eight block types and one figure archetype. That vocabulary is what
> the reset rejected — see Product-Semantics §5 and §12.
>
> **Still alive.** *Build backwards from the renderer* — each stage's output format is
> defined by what consumes it. That ordering rule survives and should govern whatever
> replaces this plan.

Every stage of the pipeline present, all of them minimal, producing one real PDF from one real topic — in about a week.

Web version: https://claude.ai/code/artifact/659125a8-75ca-4bb6-a7d1-779a7ad1cf11

---

## 1. The goal, and the one rule

> **A terminal command that turns a topic string into a PDF you would actually read.**

No web UI. No database. No chat. No approval screens. A script and a file on disk. Everything else in the architecture gets added *after* that works — and each addition then has a proven consumer downstream.

### Build backwards, from the renderer toward the input

This is the ordering rule, and it decides everything below: **each stage's output format is defined by what consumes it.**

- You cannot write the `fill` prompt until you know what block types exist.
- You do not know what block types exist until the template defines them.
- You cannot design the Spec until you know what the planner needs from it.

So the render path is built first, with hand-written data — then each LLM stage is added upstream of it, replacing hand-written input with generated input. At every point you have a working end-to-end pipeline; only the front of it gets longer.

---

## 2. The five steps

### Step 1 — Engine renders a hand-written fixture · 1–2 days

No AI anywhere. You write a document model by hand as JSON, you write one template by hand, and the engine turns them into a PDF.

```
document-engine/
    engine/
        schema.py      Document → Section → Block   (5 block types)
        merge.py       doc_model + template → HTML  (Jinja2)
        render.py      HTML → PDF                   (Playwright)
    templates/
        study-notes/
            template.html
            style.css                                print CSS, page breaks
    tests/fixtures/
        sample.json    hand-written doc model — a test, not content
```

The minimal Document Model. Five block types cover a flowing notes document; add more only when something needs them:

```json
{
  "title": "API Foundations for Agentic AI",
  "sections": [
    { "heading": "What an API actually is",
      "blocks": [
        { "type": "para",    "text": "..." },
        { "type": "code",    "lang": "python", "text": "..." },
        { "type": "callout", "variant": "key", "text": "..." },
        { "type": "list",    "ordered": false, "items": ["...", "..."] }
      ] }
  ]
}
```

**Authoring `template.html` by hand is the design work of this whole phase.** Deciding what a block looks like, what a callout looks like, how code sits on the page, where the page breaks — that is where the Template schema is discovered. It is also the artifact you keep.

> **Proves:** the render path works end to end, and the Document Model schema is real rather than imagined.
> **Done when:** the PDF looks like a document you would be willing to study from. Not beautiful — legible, well-spaced, sensible page breaks.

### Step 2 — The LLM fills blocks · 1 day

The section structure stays hand-written. The model writes only the content of each block, emitting JSON keyed to block positions — **never HTML**.

```
agent/
    fill.py        section outline → block content JSON
```

This is the first real test of contract 1 and contract 2, and where you find out whether caps are enforceable at all.

> **Proves:** the model writes to a schema instead of writing prose. That it respects block types, does not invent new ones, does not leak markdown into JSON fields, and stays near declared length limits.
> **Done when:** you can regenerate the same section three times and get three valid documents.

### Step 3 — The LLM plans the document · 1 day

Replaces your hand-written section list. Takes a slice of scope and produces sections, block types, and rough sizing.

```
agent/
    plan.py        spec slice → sections + block types
```

> **Proves:** structure generation works — that the model produces a sensible breakdown rather than an undifferentiated wall.
> **Done when:** you read the section list and would not substantially reorder it.

### Step 4 — The LLM produces the Spec · 1–2 days

The front of the chain. A situation — topic, purpose, level, hours — becomes span, coverage, exclusions, depth, sequencing rule.

```
agent/
    spec.py        situation → Spec
    run.py         the whole chain, one command

python -m agent.run "API foundations for agentic AI, 3 days, junior backend dev"
    →  out/document.pdf
```

> **Proves: the product thesis.** Not that the code runs — that the scope decision is any good.
> **Done when:** you read the Spec and would approve it without major edits, and the resulting document is one you would give a student.

### Step 5 — Minimal UI · 1 day

A text box, a Generate button, a progress line, a PDF link. That is the entire interface. It calls the same script.

> **Proves:** nothing technical. It exists so you can run the thing without a terminal, and so other people can try it.

---

## 3. The judgment moment

> **After step 4 you have a real document, generated from a real topic, by the real pipeline.**

That is the point to judge it, and the questions worth asking are specific:

| Question | If the answer is no |
|---|---|
| Is the scope right — nothing important missing, nothing wasteful included? | The Spec prompt needs work, or the Spec needs more inputs. Architecture is fine. |
| Does it start where it says it starts? | Span enforcement needs to move into the prompt, not just validation. |
| Does it read as one document, or as stitched fragments? | Fill granularity is wrong — try document-level instead of section-level. |
| Does it look like something worth keeping? | Template work, which is Phase 2 anyway. |
| **Is it better than one good prompt to a frontier model?** | **The one that matters.** If no, the answer is not more architecture. |

---

## 4. Deliberately not in Phase 1

No database · no job queue · no Set Plan · no multi-document sets · no verification layers · no approval gates · no template gallery · no retrieval or sources · no auth · no feasibility check · no `solve`, `annotate` or `paginate` modules — the browser's own print CSS handles pagination for flowing documents.

Every one of those is in the architecture and every one of them is real. None of them can be designed well until a document exists to design them around. Adding them in that order is Phase 2 onward.

### Dependencies to install, when you reach them

```
Step 1:   jinja2, playwright  +  playwright install chromium
Step 2:   an LLM SDK (anthropic or openai)
Step 5:   nothing new — the existing Next.js frontend calls the script
```

Chromium is a ~150 MB download. It is needed from step 1, since the renderer is the first thing built.

---

## 5. Order of work, at a glance

```
DAY 1–2   template.html + style.css by hand
          schema.py, merge.py, render.py
          sample.json → PDF                        ← no AI yet

DAY 3     fill.py — model writes block content
          regenerate three times, compare          ← contract test

DAY 4     plan.py — model produces the structure

DAY 5–6   spec.py + run.py — the full chain
          one command, one topic, one PDF          ← JUDGE HERE

DAY 7     minimal UI: box, button, PDF link
```

Roughly a week of focused work. The first two days produce no AI output at all, and that is intentional — the renderer defines every contract above it.

---

*First file: `document-engine/templates/study-notes/template.html`*
