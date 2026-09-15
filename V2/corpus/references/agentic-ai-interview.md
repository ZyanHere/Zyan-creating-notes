# Reference — Agentic AI, interview preparation

**Request:** *"i need agentic ai notes for interview, from scratch"*
**Follow-up:** *"i can code but i've never built an agent or used any of these frameworks"*

Hand-written. Not what V1 produced, and not exhaustive — this is the standard a
curriculum is read against, and the shape a V2 domain model must be able to hold.

---

## 1. The situation, read correctly

| Axis | Reading | Binding? |
|---|---|---|
| subject | Agentic AI | stated |
| job | **orient** — answer questions under examination | inferred from "interview" |
| purpose | Interview preparation | stated |
| entry_point | **Codes; has built no agent; no framework exposure** | **stated** — "from scratch" |
| target_capability | Explain, compare and justify agent design choices aloud | inferred |
| capacity | Not stated | — |

The load-bearing one is `entry_point`. *"From scratch"* is a statement about
prior knowledge, and a reading that assumes ML/LLM literacy contradicts it. It is
not recoverable downstream: if the landscape is built assuming API fluency, API
foundations are never in the graph and no later decision can add them back.

**The job is orient, not construct.** The learner will be *talking* about agents,
not shipping one. Every capability below is written in explain/compare/justify
register. "Architect a multi-tool production agent" is the wrong promise for an
orienting document, however impressive it sounds.

## 2. Capability decomposition

This is the part V1 has no representation for. The target capability is not a
topic list — it decomposes into sub-capabilities, and each sub-capability is what
actually selects concepts.

```
TARGET: hold a 45-minute technical conversation about agentic AI
        without being caught out

├── C1  Explain what makes a system "agentic" vs a prompt chain
│        └── model calls · tool use · the loop · autonomy vs orchestration
├── C2  Walk through the agent loop and say where each step can fail
│        └── ReAct · observation handling · termination · error recovery
├── C3  Explain how an agent remembers, and the trade-offs
│        └── context window · scratchpad · summarisation · external memory
├── C4  Explain retrieval in an agent and how it differs from plain RAG
│        └── retrieval basics · query reformulation · iterative retrieval
├── C5  Compare named frameworks and justify a choice
│        └── LangGraph · CrewAI · AutoGen — separately, by name
├── C6  Say how you would know the agent works
│        └── trajectory vs outcome eval · benchmarks · regression cases
└── C7  Name the ways agents fail and what you would do about it
         └── loops · prompt injection · tool misuse · cost blowup · guardrails
```

**The test each clause must pass:** a concept in the module can answer it. C4
promising "design iterative retrieval loops with query reformulation" over a
scope holding one concept called *RAG for Agents* is a cheque the scope cannot
cash — three claims, one concept, and the reader finds out in the interview.

## 3. Concepts, and why each is present

Granularity rule: **if the learner must tell two things apart, they are two
concepts.** *"Why LangGraph over CrewAI"* is a standard interview question, so
the frameworks cannot be one node called "Major Frameworks (…)" — as one node it
can never be divided later, because there is nothing there to divide.

| Concept | Why it is in play |
|---|---|
| LLM API basics — messages, tokens, cost, latency | "From scratch" binds. Everything else sits on this. |
| Structured output / function calling | The mechanism tool use is actually built on |
| Tool use | C1, C2 |
| The agent loop (ReAct) | C1, C2 — the canonical thing they will be asked to draw |
| Termination and error recovery | C2 — the follow-up question after "describe the loop" |
| Context window and its limits | C3 — the constraint every memory design answers |
| Scratchpad / short-term memory | C3 |
| External / long-term memory | C3 |
| Retrieval basics | C4 — prerequisite; without it "agentic RAG" is words |
| Query reformulation | C4 |
| Iterative / agentic retrieval | C4 |
| LangGraph | C5 — named separately, on purpose |
| CrewAI | C5 |
| AutoGen | C5 |
| Trajectory vs outcome evaluation | C6 |
| Agent benchmarks (in outline) | C6 — mention depth; naming them is enough |
| Failure modes: loops, injection, tool misuse, cost | C7 |
| Guardrails and human-in-the-loop | C7 |

Cut, with consequence stated: multi-agent orchestration patterns (asked at senior
level only — say so); fine-tuning for agents (rarely asked, large); production
deployment and observability (a different interview).

## 4. Modules

Six. The count comes from the capability decomposition, not from a target.

**1 — Foundations: what an agent is actually made of**
*Covers:* LLM API basics · structured output / function calling · tool use
*Capability:* Explain what an LLM call is, how a tool call works mechanically, and what distinguishes an agent from a prompt chain.
*Why together:* This is the entry point "from scratch" requires. Nothing below is answerable without it.

**2 — The agent loop**
*Covers:* ReAct · observation handling · termination · error recovery
*Capability:* Draw the thought–action–observation loop, trace one iteration aloud, and name where it breaks.
*Why together:* One mechanism and its failure surface. Splitting the loop from its failure modes would let a reader "know" the loop and be unable to discuss it.

**3 — Memory and state**
*Covers:* context window · scratchpad · external memory
*Capability:* Explain what an agent remembers between steps, and justify a memory design against a context limit.
*Why together:* All three are answers to the same constraint.

**4 — Retrieval for agents**
*Covers:* retrieval basics · query reformulation · iterative retrieval
*Capability:* Explain how retrieval in an agent differs from single-shot RAG, and describe an iterative retrieval loop.
*Why together:* Genuinely built on each other; this is the module V1 funded with one concept.

**5 — The framework landscape**
*Covers:* LangGraph · CrewAI · AutoGen
*Capability:* Compare the three on state model, multi-agent support and maturity, and justify a choice for a described problem.
*Why together:* A comparison module. **Zero internal dependency is correct here** — the frameworks are not built on each other, and that is exactly what makes the comparison possible. A dependency-count rule would flag this module as incoherent, and would be wrong.

**6 — Failure, evaluation and guardrails**
*Covers:* failure modes (loops, injection, tool misuse, cost) · guardrails · human-in-the-loop · trajectory vs outcome eval · benchmarks
*Capability:* Name the common ways agents fail, say how you would detect each, and describe how you would evaluate an agent you had built.
*Why together:* **This is the module most at risk of becoming a leftovers bucket.** It is legitimate only because one capability unifies it: *knowing whether the thing works and what to do when it doesn't*. Safety, observability, cost and deployment thrown together because they are all "advanced" is the failure shape — the test is whether a single sentence describes what the reader can do afterwards.

*Order:* 1 → 2 → 3 → 4 → 5 → 6. Foundations first because the entry point demands
it; frameworks after the concepts they implement, so the comparison has something
to compare; evaluation last because it is about everything before it.

## 5. What this reference is testing

- Can the model represent **capability → sub-capability → concept**, or only concept → module?
- Can it express *"these five are separate concepts because the learner must distinguish them"*?
- Can it express *"zero internal dependency is correct for this module and wrong for that one"*?
- Can it hold *"cut, and here is what that costs"* as a first-class thing rather than an omission?
- Does depth attach to the **capability clause** it serves, rather than to the concept in isolation?
