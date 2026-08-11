# Product Bible

## Document Purpose

This document is the current product source of truth for the proposed platform for AI-assisted personalized educational material.

Its purpose is to align future product and engineering work around:

- the problem being solved
- the user value being pursued
- the current product model
- the key hypotheses that still need validation
- the open questions that must remain open for now

This is intentionally **not** an engineering design document. It does not define system architecture, model orchestration, database choices, frontend structure, or implementation details.

## Status Legend

To avoid turning assumptions into facts, each section should be read with the following distinctions:

- **Vision**: the long-term product direction we are aiming toward
- **Current decision**: a working product decision for now
- **Hypothesis**: something we believe may be true and want to test
- **Open question**: something we have not decided yet

## 1. Product Vision

**Vision**

Build a platform that helps people get the **right educational material for their specific learning situation**, not just more generated content.

The long-term ambition is to support many subjects and learning contexts by using AI to determine:

- what a learner actually needs
- what should be covered
- what can be excluded
- how deep the material should go
- how the material should be structured

The product is fundamentally about **educational fit**: matching content scope, depth, and structure to the learner's real need.

## 2. Problem Statement

**Vision**

General-purpose LLMs are strong at producing educational text, but they do not reliably infer the learner's exact situation well enough to decide what material is most useful.

**Problem**

The same subject can require very different material depending on:

- the learner's goal
- available time
- starting knowledge
- required depth
- learning situation
- preferred way of consuming material

A request like "teach me Operating Systems" is underspecified. The user might need:

- last-minute exam revision
- a semester's worth of notes
- interview preparation
- beginner onboarding
- advanced conceptual depth
- research orientation
- a quick cheat sheet

The core product problem is therefore:

> Given a learner's specific situation, determine what educational material they actually need, how much of the subject should be covered, what depth is appropriate, and how that material should be structured.

**Current decision**

We will frame the product around better scope determination and planning, not around raw content generation alone.

## 3. Target Users

**Vision**

The platform should eventually support learners across multiple domains and learning situations.

**Current MVP direction**

Initial users should be narrowly defined so the core hypothesis can be tested clearly.

Likely early user profiles include:

- students preparing for a known exam in a technical domain
- software learners preparing for interviews
- learners who need compressed, high-utility material under time constraints

**Hypothesis**

Users with urgent, clearly bounded goals may feel the value of planning and scoping more strongly than users with vague exploratory goals.

**Open question**

Which initial user segment will produce the clearest signal of product value:

- exam preparation
- interview preparation
- structured self-learning

## 4. Jobs-to-be-Done

**Vision**

Users are not hiring the product to "generate notes." They are hiring it to reduce uncertainty about what to study and to obtain material matched to their real need.

**Core jobs**

- Help me figure out what I should study for my specific situation.
- Help me avoid wasting time on irrelevant topics.
- Help me get material at the right depth for my current goal.
- Help me see and control what will be covered before final generation.
- Help me transform a broad subject into a practical, usable study asset.

**Example job statements**

- When I have an exam soon, help me focus only on what matters most so I can revise efficiently.
- When I am preparing for an interview, help me cover the most relevant concepts at interview-appropriate depth.
- When I am new to a subject, help me get a structured roadmap that does not overwhelm me.
- When I already know some topics, help me avoid repetitive or unnecessary material.

## 5. Product Principles

**Current decisions**

1. The product must optimize for relevance of learning material, not volume of generated material.
2. The system should ask only questions that materially change the resulting output.
3. Users should not be forced through a giant questionnaire.
4. The user should see and control the intended scope before final content generation.
5. Artifact, Template, and Content Plan are distinct concepts and should remain distinct in product thinking.
6. The generated result should not feel like a black box.
7. The MVP should start narrow and validate the planning/scoping experience before expanding.

**Hypotheses**

- Scope preview may become one of the most important UX moments in the product.
- Sensible defaults and lightweight templates may reduce user effort without reducing fit.
- Users may trust generated educational material more when they can inspect its planned structure first.

## 6. Core User Experience

**Vision**

The product experience should feel like an intelligent educational planner first and a generator second.

**Desired UX characteristics**

- fast to start
- low-friction context capture
- clear recommendations
- visible reasoning through the content plan
- easy user control before generation
- output shaped to the user's situation, not just the subject

**Current decision**

The user should interact with a planning step before expensive final generation begins.

**Hypothesis**

The reviewable scope may create a meaningful feeling of precision, trust, and control that direct prompting does not provide.

## 7. Current Product Model

**Current decision**

The current working product model has four major concepts:

1. User Intent / Context
2. Artifact
3. Template
4. Content Planner

These concepts support the current high-level flow:

1. User expresses a learning need
2. System understands intent and context
3. System selects or recommends an artifact
4. System selects or recommends a template
5. Content planner determines coverage, depth, and structure
6. System presents the content plan / scope
7. User modifies or approves
8. AI generates the final learning material

**Current decision**

This is the working product model, not a final ontology or permanent architecture.

## 8. Artifact Concept

**Definition**

Artifact answers:

> What does the learner need?

**Current hypothesis**

Possible artifacts may include:

- Exam Preparation
- Interview Preparation
- Crash Course
- Complete Notes
- Semester Course
- Revision Guide
- Research Guide
- Learning Roadmap
- Cheat Sheet
- Question Bank
- Project/Lab Guide

**Current decision**

The artifact concept is useful as a user-facing abstraction because it captures the intended educational outcome.

**Explicit non-decision**

The artifact taxonomy is not final and should not yet be treated as locked.

**Open questions**

- Which artifacts are truly distinct in user value versus just different labels?
- Should artifacts be selected explicitly by users, recommended by the system, or both?
- Will artifacts remain the primary user-facing abstraction as the product matures?

## 9. Template Concept

**Definition**

Template answers:

> How should the material be presented?

**Current hypothesis**

Possible templates may include:

- Visual
- Quick
- Theory
- Q&A
- Comprehensive
- Adaptive

**Current decision**

Templates should influence presentation, density, and emphasis, not act as rigid rules about whether certain elements can exist.

For example:

- a quick revision guide may still include diagrams
- an interview artifact may still include diagrams
- a comprehensive output may still choose concise sections where appropriate

**Current decision**

Template is different from Artifact and different from Content Plan:

- Artifact = what the learner needs
- Template = how it is presented
- Content Plan = what is actually covered and how deeply

**Hypothesis**

Real preview samples of templates may be more effective than purely textual template descriptions.

**Open questions**

- Which templates are most understandable to users?
- Are templates better expressed as named modes, sliders, examples, or adaptive defaults?
- How many templates can exist before the model becomes confusing?

## 10. User Context / Intent

**Definition**

User context and intent describe the learner's situation and the factors that should materially change the resulting material.

**Examples of relevant context**

- goal
- available time
- current level
- required depth
- learning situation
- presence of a syllabus or source material
- preparation mode such as exam, interview, revision, research, or learning

**Current decision**

The system should ask only for information that materially changes output quality.

**Current decision**

Templates, defaults, and recommendations should reduce unnecessary questioning.

**Hypothesis**

A short sequence of high-leverage questions can capture enough context to outperform direct prompting without creating onboarding fatigue.

**Open questions**

- What is the minimum set of questions that materially improves content planning?
- Which context fields can be inferred safely versus explicitly asked?
- When should the system ask follow-up questions instead of using defaults?

## 11. Content Planning / Scope

**Definition**

Content Planning is the process that determines:

- what topics should be included
- what should be excluded
- how much depth each topic receives
- what order topics should follow
- which concepts deserve more emphasis
- what examples, exercises, or support material are necessary
- how much total material should be produced

**Current decision**

This is currently the most important internal product component.

**Current decision**

The planner should create a plan and scope before expensive final generation begins.

**Current decision**

Users should be able to inspect and modify the proposed scope before generation.

**Why this matters**

The scope preview is the mechanism through which the product makes its educational judgment visible. It allows the user to validate, reject, or refine what the AI intends to teach.

**Example**

For "I have an Operating Systems exam in 3 days," an appropriate plan might include:

- Processes
- Threads
- CPU Scheduling
- Synchronization
- Deadlocks
- Memory Management
- Virtual Memory

And might exclude:

- advanced filesystem internals
- distributed operating systems
- historical architecture details

**Hypothesis**

Better scope planning is the primary mechanism by which the product may outperform direct prompting.

**Open questions**

- How explicit should included versus excluded content be in the UI?
- How much granularity should the plan expose?
- What kinds of edits should users be able to make to the scope?
- How should the system balance user control with decision quality?

## 12. Core User Journey

**Current decision**

The current target journey is:

1. User describes a learning need.
2. System gathers only the most important missing context.
3. System recommends or confirms an artifact.
4. System recommends or confirms a template.
5. System produces a content plan with scope, emphasis, and exclusions.
6. User reviews and modifies the proposed plan.
7. User approves the plan.
8. System generates the final learning material.

**Desired UX outcome**

The user should feel:

- understood
- guided
- in control
- confident that the material matches their actual need

**Hypothesis**

This journey will produce a better user-perceived result than immediately asking a frontier model to generate material from a single prompt.

## 13. MVP Definition

**Current direction**

The MVP should validate the planning/scoping hypothesis, not attempt to solve education broadly.

**Current MVP boundaries**

- focus on one well-understood domain
- focus on one primary use case or a very small number of closely related use cases
- support the full end-to-end flow from need capture to plan review to final generation
- compare usefulness against direct prompting workflows

**Candidate MVP domains**

- Operating Systems
- DSA
- Software Engineering
- AI/ML

**Candidate MVP use cases**

- interview preparation
- exam preparation

**Success intent**

The MVP should tell us whether explicit planning and scope review produce meaningfully better educational outcomes and user trust.

**Explicit non-goal**

The MVP is not intended to be a broad multi-domain education platform.

## 14. Non-goals

**Current decisions**

The product is not currently being defined as:

- a generic AI course generator
- a system optimized primarily for producing more text
- a giant cross-domain educational platform from day one
- a finalized universal taxonomy of educational artifacts
- a finalized universal taxonomy of templates
- a complete subject knowledge graph or knowledge layer before validation
- an engineering architecture decision document
- a commitment to a specific model stack, agent system, database, or frontend architecture

## 15. Key Product Hypotheses

**Primary hypothesis**

An AI system that first understands the learner's situation and explicitly plans the appropriate scope can produce significantly more useful educational material than direct generation from a general-purpose frontier LLM.

**Supporting hypotheses**

1. The biggest product problem is deciding appropriate coverage and depth, not generating fluent text.
2. A visible content-plan preview is a major driver of usefulness and trust.
3. Artifact + Template + Context is a useful user-facing abstraction.
4. The best MVP will emerge from a narrow domain and tightly defined use case.
5. A lightweight planning layer may create clear value before any large persistent knowledge layer is built.
6. Presentation enhancements such as diagrams may be useful, but they are downstream of planning quality rather than the core problem.

## 16. Risks and Unknowns

**Key risks**

- Users may not perceive enough improvement over direct prompting to change behavior.
- Context capture may become too long or cognitively heavy.
- Artifact and Template concepts may feel artificial or confusing to users.
- Users may want to skip planning and jump directly to generation.
- Plan review may add friction without enough perceived benefit.
- High-quality planning may depend more on subject-specific knowledge than currently assumed.
- Different domains may require fundamentally different planning logic.

**Unknowns**

- How measurable the quality advantage over direct prompting will be
- Which domains are easiest to validate first
- Which user segment feels the strongest pain today
- How much manual scope editing users will want
- Whether the same abstraction holds across technical and non-technical domains

## 17. Competitive Differentiation Hypothesis

**Hypothesis**

The product may differentiate not by having a stronger base model, but by introducing a better educational decision layer between user need and content generation.

Potential points of differentiation:

- stronger understanding of the learner's actual situation
- explicit scope selection before generation
- clearer separation between educational outcome, presentation style, and topic plan
- user-visible planning rather than black-box output
- educational material optimized for relevance and fit, not just fluency

**Open question**

Will users perceive this as a distinct category of value, or merely as a better prompting wrapper around existing models?

## 18. Future Expansion Areas

**Vision**

If the core hypothesis is validated, the product may expand across:

- more domains
- more learner goals
- more artifact types
- richer template previews
- subject-specific planning logic
- stronger reuse of syllabi, source documents, or prior learner state
- persistent knowledge layers for consistency and reliability
- collaborative or iterative study workflows

**Current decision**

These are future expansion areas, not present commitments.

**Explicit non-decision**

We are not yet committing to:

- a knowledge graph architecture
- an agent architecture
- a database design
- a frontend architecture
- a long-term system decomposition

## 19. Open Questions

The following questions remain intentionally unresolved:

1. Which initial domain gives the fastest and clearest validation signal?
2. Should the first use case be exam preparation or interview preparation?
3. What minimum context is required to materially improve planning quality?
4. How should artifact selection be presented to users: explicit choice, recommendation, or hybrid?
5. How should template selection be presented to users: labels, examples, or adaptive defaults?
6. What is the right UI for scope review and editing?
7. How should usefulness be measured against direct prompting?
8. What evidence would be strong enough to validate the core product hypothesis?
9. When, if ever, does a persistent subject/domain knowledge layer become necessary?
10. Which parts of planning can stay domain-agnostic, and which require domain-specific logic?
11. How broad can the product become before the current abstraction breaks down?
12. What user behaviors would indicate that the planning step is truly valuable rather than tolerated?

## Summary

**Vision**

Create a system that helps learners get the right educational material for their exact situation.

**Current decisions**

- Focus product thinking on planning and scope, not just generation.
- Keep Artifact, Template, and Content Plan separate.
- Show users the plan before generating the final material.
- Start with a narrow MVP that can validate the core hypothesis.

**Core hypothesis**

Explicit learner-aware planning can produce meaningfully more useful educational material than direct prompting alone.

**What remains open**

- the best initial domain
- the best initial use case
- the final artifact taxonomy
- the final template taxonomy
- the eventual architecture and infrastructure decisions

This document should serve as the working source of truth until revised by product review.
