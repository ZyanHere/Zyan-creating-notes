# agent

Planning and generation. **The only place in the system an LLM is called.**

This is step 2 of Phase 1 in `../Phase-1-Build-Plan.md`: given a plan that
already declares the blocks, the model writes their content — and nothing else.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ..\document-engine

Copy-Item .env.example .env          # then add an OpenRouter key

python -m agent fill plans\module-01.json --pdf out\generated.pdf
```

## What `fill` does

```
DocumentPlan  ──fill()──>  Document  ──engine.render()──>  PDF
(structure)                (structure + content)
```

The plan declares each block's type, its constraints and a brief. The model
returns content keyed to those blocks. **It cannot add a block, drop one,
reorder them, or change a type.**

```json
{ "type": "para", "max_words": 75,
  "brief": "LangChain is a good abstraction, but when something breaks you
            need to know what is underneath…" }
```

Two kinds of block appear in a plan:

- **prose specs** — `para` `subheading` `code` `callout` `list` `badge`.
  The model writes these.
- **structural blocks** — `figure` `cheatsheet`. Already authored, copied
  through untouched, and never shown to the model. A figure is an archetype
  with data; the model selects from archetypes that exist, it never invents
  one. Generating that data is later work.

## The contract, stated and checked

Contract 8 of `../Foundation.md`: *every constraint the verifier checks is also
stated in the prompt.* Validation is a safety net, not the mechanism — a
pipeline that relies on checking alone burns retries on failures a sentence
would have prevented.

Stated in the prompt **and** checked on return:

| | fails | notes |
|---|---|---|
| block count, types, order | ✓ | fixed by the plan |
| required fields present | ✓ | |
| no HTML in any text | ✓ | the template owns presentation |
| Document Model validity | ✓ | the engine's own Pydantic models |
| word / line / item caps | | recorded as **findings** |

Caps are a budget for the writer, not a structural requirement: a 95-word
paragraph against a 90-word cap is a note, not a broken document. Structure is
what fails, and a failure is retried with the reason attached — up to three
attempts, then it gives up rather than shipping something malformed.

## Why not the provider's JSON-schema mode

OpenRouter is OpenAI-API compatible, so one client reaches any model by
changing `OPENROUTER_MODEL`. Free models mostly do **not** support strict
JSON-schema output, and depending on it would quietly make the pipeline
provider-specific.

So the agent validates and retries instead. That works everywhere, and it is
the honest form of the question step 2 exists to answer: *can a model hold to a
schema?* — not *can the API force it to?*

Responses wrapped in markdown fences or surrounded by commentary are unwrapped
rather than rejected; models do that regardless of instructions.

## Tests

```bash
python -m pytest agent/tests -q          # 18 tests, no API key needed
python -m pytest agent/tests -q -m live  # one real call, needs a key
```

The contract lives in `validate_section`, so nearly all of it is testable
offline; a scripted fake client exercises the retry loop. The live test is
step 2's success criterion: **regenerate the same section three times and get
three valid documents.**
