# agent — SALVAGE

**This package does not import and does not run.** `models.py` was deleted, and
`__init__.py`, `fill.py` and `cli.py` all import from it.

Current source of truth: **`../Product-Semantics.md` (Rev. 2)**.
Recoverable in full from commit `07ebf72`, *"Snapshot before the vocabulary reset"*.

---

## What was deleted, and why

| Deleted | Reason |
|---|---|
| `models.py` | The single most-invalidated file in the repo. It **is** the dead vocabulary — `BlockSpec` as a union of 8, `SectionPlan`, `archetype: Literal["layer-stack"]`. No notion of artifact type, job, learning situation, or omission consequence. |
| `plans/*.json` | Hand-written stand-ins for a planner that never existed, in a format that is now wrong. `ai-ml-dl.json` is where a `layer-stack` was forced onto a **containment** relation — the case that started the reset. |
| `tests/` | Every assertion tested the dead vocabulary. The `FakeClient` technique is twelve lines and trivially re-invented. |

## What was kept, and why

| Kept | Value |
|---|---|
| `client.py` | **Survives whole.** Provider-neutral: one call, plain text in and out; OpenRouter reaches any model by changing a string. Also carries the `.env`-discovery fix — dotenv searches upward from the working directory, so a `.env` inside the package is never found without an absolute path. |
| `fill.py` | **Partly alive, kept intact rather than gutted.** Alive: the retry-with-reason loop, `_extract_json` (models emit fences and commentary regardless of instructions), and pass-through blocks restored to their planned positions. Dead: `_build_block`'s type table, `PROSE_TYPES`, and the findings model — see below. |
| `cli.py` | Shape only. The command changes from *"fill a plan"* to something that starts from a situation. |
| `requirements.txt` · `.env.example` · `pytest.ini` | Infrastructure. `.env.example` records that free model ids move — `llama-3.3-70b:free` went paid mid-session. |

## The part I got wrong: caps as findings

`fill.py` splits *structure fails* from *caps are findings*. The split is right; what
it measures is not.

A cap of 90 words is a proxy for treatment budget. Product Semantics §9 puts the
floor at **where treatment stops supporting the kind of capability targeted**, and a
word count cannot express that. "Five words over" is close to meaningless. The
finding that would matter is *this concept got a definition where a generative target
needs a worked example* — a judgment about treatment kind.

And §4 locks that this class of check is **partially verifiable**: a reader model, not
an assertion suite. `fill.py` has nowhere to put one.

So the contract shape survives — state it in the prompt, check it on return, retry
with the reason attached. What it checks does not.

## Why the rebuild is bigger here than in the engine

The engine loses its design and keeps its mechanism; HTML → Chromium is neutral
about everything the reset decided. The agent is the reverse. About half its code
carries over, but its **shape** does not:

```
OLD     spec → plan → fill                    three straight-line transforms

NEW     reconstruct the situation             interactive — ask only what
                                              materially changes the artifact
        derive job from artifact type         new
        scope + depth allocation
        project omission consequence          new; must precede any budget move
        structure
        select representations                now a first-class decision
        generate content
        negotiate the budget                  new: compress, remove leaves,
                                              truncate, mark the gap
```

Two of those are **loops** — one with the user, one with the renderer. The old chain
had neither, and a loop cannot be added to a straight line without rebuilding it.
