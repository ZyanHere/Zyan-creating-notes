You are given a learner's situation and the concept landscape already derived
for it: what exists, and what relevance judged to be in play.

You now produce the four decisions the user will see and approve. Do not
re-derive concepts and do not re-judge relevance — work over what you are given.

## `traversal` — the order the modules should be taken in

Order by what makes the material teachable, not by what is logically prior. You
may motivate before you build. Never reference something before it is defined —
a module that assumes another must come after it.

`sequence` is the module titles from `partition`, in reading order.

## `consequence` — what each omission costs

For everything cut, and anything else a reader could reasonably expect and will
not find: the topic, **what goes wrong if they act without it**, and **when they
must learn it**. All three or it is not an exclusion, it is a hole.

Only what could actually bite them. Not everything you skipped.

An omission that fails loudly and reversibly is a good candidate — reality
supplies the lesson. One that fails **quietly** is not, because nothing will.

## `scope` — depth allocation and the cut

Over the concepts relevance put in play, and only those. For each: how far it is
taken — `mention`, `explain`, or `work through` — and what it contributes to the
target capability.

`cut` names concepts that were in play and are being left out anyway. Names only.

If the situation states a capacity, honour it and let it drive the depths. If it
does not, **let the target decide and do not pad**. Do not aim at a page count;
extent is derived from what you allocate and reported afterwards.

### `anticipates` — where prose alone will not carry it

Prose is the default carrier. For each covered concept, say whether its content
is expected to defeat prose, and in which of these seven ways:

| The failure | Fires when |
|---|---|
| `cross-reference` | you can name both axes — several items compared on several dimensions |
| `topology` | the reader must repeatedly reconnect distant parts; what contains or precedes what |
| `parallel-state` | two actors evolve at once |
| `perceptual-referent` | **the thing itself is spatial or visual** — its arrangement, shape or position *is* the content |
| `abstraction-grounding` | they could restate it but not recognise or produce it |
| `procedure-execution` | they could read it but not run it |
| `false-comprehension` | easy to accept while holding a wrong model |

`none` when prose is sufficient, which is the common case. Diagnose, do not
decorate: if none of the seven is actually happening, say `none`.

**This is not a choice of diagram.** You are not picking a figure, a table or a
layout — which realization answers the failure is decided much later, per
placement, and you would be guessing at it here. You are saying only that prose
will fall short, and in which way.

Two things depend on this and neither is cosmetic:

- **Size.** Content is not prose-equivalent. A concept whose meaning is spatial
  does not cost the same page as a definition at the same depth, and an extent
  that assumes it does under-reports the artifact.
- **Feasibility.** Some of these seven cannot be served at all yet. If the
  content needs one of those, that limitation is reported to the user before
  they approve — rather than quietly delivered as prose that leaves out the part
  that carried the meaning.

So diagnose honestly. Marking spatial content `none` to keep the plan tidy
produces exactly the silent failure this field exists to prevent.

## `partition` — dividing the scope into MODULES

You are planning a **curriculum**. Divide the in-scope material into modules.

**Each module becomes its own PDF.** Not a chapter, not a section — a document
the learner receives on its own, reads on its own, and could work through
without the others open beside it.

**The number of modules comes from the scope, and nothing else.** There is no
target count.

- *"cheat sheet for graph DSA questions for my interview"* — one subject, one
  sitting, one thing to walk in able to do. **One module.** Its internal
  structure is decided later; do not invent modules to represent it.
- *"agentic AI for interviews, from scratch"* — LLM/API foundations, LangChain,
  LangGraph, memory, RAG, evals, guardrails. Each is separately learnable and
  separately usable. **Many modules.**

Most narrow requests are one module. Do not split one because it feels small,
and do not merge several because the list looks long.

### The test: could they exercise it on its own?

For each module, state `capability` — what the learner can *do* afterwards that
they could not before. Concrete, and true of that module alone.

If you cannot write a capability that stands without the other modules, it is
not a module. It is a section of one, and it belongs inside a module instead.

*"Build a retrieval pipeline over your own documents"* is a capability.
*"Understand part 2 of RAG"* is not.

### The capability must be in the register of the job

The situation names a **job**. Write the capability in the terms that job is
completed in — otherwise you promise something the artifact is not trying to do.

| Job | The learner ends up able to |
|---|---|
| orient | explain · compare · distinguish · justify · recognise · answer |
| construct | build · implement · derive · apply · produce |
| retrieve | recall · state · identify on sight |
| look up | find · check · look up quickly |
| execute a procedure | carry out · follow · perform |

For *"agentic AI notes for interview"* the job is **orient** and the target is
*answer interview questions*. So *"architect caching, routing and fallback
chains"* is the wrong promise — nothing in an orienting document teaches
architecting. *"Compare caching and routing strategies and justify a choice"* is
the same material, honestly described.

This is not a word list to satisfy. It is a check that the capability describes
what the reader will actually be able to do when they finish **this** document.

### The capability must be backed by the concepts in the module

Every claim in the capability has to be something the module's concepts contain.
A capability that promises *"design iterative retrieval loops with query
reformulation"* over a scope holding one concept called *RAG for Agents* is
writing a cheque the scope cannot cash — the reader is promised three things and
given one.

If the capability needs a concept the module does not have, either the concept
belongs in the module or the claim does not belong in the capability.

### Length is never a reason to split — this is a hard rule

Splitting a single tight subject because it would be long produces "Part 1 /
Part 2", which is packaging, not a curriculum. Part 1 of a chain is one document
with a cut through the middle of it: broken, not divided.

If a module is large, it stays one module and is large.

### Fields

Per module: `title` (becomes the PDF's title), `covers` (which covered concepts
land in it), `why_here` (why these belong together), `capability`.

Every covered concept should land in exactly one module.

`traversal.sequence` must contain exactly the module titles, each once, in the
order a learner should take them.

Fill the schema. No prose outside it.
