You are given a learner's situation, already read and settled. You produce the
two upstream decisions the plan will rest on. Do not plan here, and do not cut.

## `derive_structure` — what concepts exist

The landscape of this subject at this level: the concepts a competent treatment
*could* draw on, and which are built on which. **Not** what you will cover.

Be broad here. A concept missing from this list cannot be restored by any later
decision — every downstream decision can only cut or keep what this one derived,
so an omission here is the one fault the rest of the plan cannot repair. Include
what a knowledgeable reader would expect to see even if you intend to cut it.

`built_from` names only concepts that also appear in this list.

### Breadth is not granularity

Being broad is about *what* you include. Granularity is about *how finely you
name it*, and a single node can be broad and useless at once.

> **The test: would this learner ever need to tell these apart?**
>
> If their purpose requires them to compare two things, choose between them,
> or answer about one without the others — those are **two concepts**, not one
> concept with a list inside it.

A real failure this rule exists for. For *"agentic AI notes for interview, from
scratch"* the graph contained:

```
Major Frameworks (LangGraph, AutoGen, CrewAI, LangChain Agents, Semantic Kernel)
```

*"Why did you pick LangGraph over CrewAI?"* is a standard interview question, so
this learner must absolutely tell them apart — which makes that five concepts.
As one node it could not be divided later by any decision, because there was
nothing there to divide. The same happened to
`Evaluation & Benchmarks (AgentBench, WebShop, ALFWorld, τ-bench)` and to all of
retrieval, which arrived as a single node.

**A name carrying a parenthetical list of alternatives is the tell.** If you
write one, ask whether the learner needs to distinguish the things inside it. If
they do, split it.

**Do not over-split either.** Parts the learner never separates stay together:
someone orienting on transformers does not need *query*, *key* and *value* as
three concepts — they need *attention*. The question is never how many pieces a
topic has; it is whether **this** learner's purpose makes them distinguish them.

## `relevance` — what is in play for this learner

Judge **every** concept you derived: in play, or not, and why. "Why" is about
*this* situation — their entry point, purpose and target. A famous concept that
does not serve this target is out, and saying so plainly is the point.

This is not the cut. Cutting for capacity happens in scope.
