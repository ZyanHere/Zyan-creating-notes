# Product Bible

## Document Purpose

This document is the current product source of truth for the platform.

It defines what the product is, how it should behave, what concepts are currently locked, what remains a working hypothesis, and what is still open. It is intentionally not an engineering design document. It does not define agent orchestration, LangGraph architecture, backend/frontend architecture, database schemas, or implementation details.

## Status Legend

- **Locked / Current product decision**: agreed product definition for now
- **Current hypothesis**: a working belief that still requires validation
- **Open question**: intentionally unresolved

## 1. Product Definition

### Locked / Current Product Decisions

The product is an **AI-powered notes generation platform**.

Its purpose is to help users generate high-quality educational or professional notes and related learning materials for a particular topic and purpose.

The product is fundamentally about:

- understanding the user's topic and situation
- determining appropriate coverage and depth
- planning the structure before expensive generation
- generating one or more concrete documents that fit the need

The core experience is:

1. User has a topic or notes need.
2. The platform understands the context and purpose.
3. The platform determines what material is appropriate.
4. The user chooses or reviews the desired output style.
5. The platform creates a Content Plan.
6. The user can review and edit the plan.
7. The platform generates the actual documents.

### Product Definition Clarification

The product is not primarily:

- an LMS
- an AI tutor
- a virtual university
- a student progress-management system
- a generic chatbot
- a course marketplace

## 2. Vision

### Vision

Build a platform that helps people get the **right notes and learning materials for their exact topic and use case**, not just more generated text.

The long-term ambition is to support many domains and many contexts by using AI to decide:

- what should be covered
- what can be excluded
- how deep the material should go
- how it should be sequenced
- what kind of supporting material is actually useful

## 3. Problem

### Locked / Current Product Decisions

The central product problem is not simply generating fluent text.

It is determining:

> What should be covered for this user, this purpose, this topic, and this situation?

The same topic can require very different outputs depending on context.

For example, "Deep Learning notes" could mean:

- a 5-page crash revision sheet
- semester notes
- interview preparation
- mathematical derivations
- research-oriented notes
- an implementation-focused guide

The platform must therefore decide:

- scope
- coverage
- depth
- priority
- sequencing
- document size
- examples
- exercises
- diagrams or visuals where useful
- equations, tables, code, or Q&A where appropriate

## 4. Product Principles

### Locked / Current Product Decisions

1. User intent comes before generation.
2. Scope should be planned before expensive generation.
3. Users should be able to inspect and modify important planning decisions.
4. A Project maintains topic-level context over time.
5. Workstreams separate different purposes within the same topic.
6. Artifacts are concrete generated documents.
7. Large and small Workstreams use the same underlying planning model.
8. Modules are optional, not required.
9. The system should not over-question users.
10. The product should not expose internal AI architecture as a user responsibility.
11. The product should not be framed as an LMS.
12. The system should support one Artifact or many Artifacts under the same Project.
13. Different Workstreams can coexist independently inside a Project.
14. The product should eventually support many domains and use cases.

### Current Hypotheses

- Scope preview may become one of the most important trust-building moments in the product.
- Template previews with sample output may improve decision quality more than template labels alone.
- Project-level context reuse may reduce repetition and improve later outputs without turning the product into a mastery-tracking system.

## 5. Target Users

### Locked / Current Product Decisions

The product is for users who need high-quality notes or related materials for a specific topic and purpose.

Representative user contexts include:

- university study
- exam preparation
- interview preparation
- self-learning
- research orientation
- professional work
- competitive exam preparation

### Current Hypotheses

Early value may be strongest for users with bounded, high-pressure needs such as:

- exam preparation
- interview preparation
- quick revision

### Open Questions

- Which initial user segment gives the clearest validation signal?
- Which domain should be used first to test the product most effectively?

## 6. Core User Experience

### Locked / Current Product Decisions

The product experience should feel like an intelligent notes planner first and a generator second.

Desired user experience characteristics:

- fast to start
- low-friction context capture
- clear recommendations
- visible planning before generation
- meaningful user control
- outputs shaped to purpose, not just subject

The user should not need to understand internal AI architecture to use the product well.

## 7. Project

### Locked / Current Product Decisions

A **Project** is the primary user-facing, persistent topic or context workspace.

Examples:

- `Project: Generative AI`
- `Project: Electrical Machines`
- `Project: English BA 2nd Semester - Paper 2`

A Project:

- is topic or context anchored
- persists over time
- remains available for future work
- can contain many bodies of work and generated documents

A Project does **not** mean:

- one PDF
- one curriculum
- one goal
- one conversation
- one generation job

### Behavioral Expectation

If a user asks for notes on a clearly different topic, the system should create or switch to a different Project instead of mixing unrelated material into the current one.

If the topic boundary is ambiguous, the system should ask the user whether to keep it in the current Project or start a new one.

## 8. Workstream

### Locked / Current Product Decisions

A **Workstream** is a purpose-scoped body of work inside a Project.

It answers:

> Why does this particular body of work exist?

Examples inside `Project: Generative AI`:

- `Workstream: Research Notes`
- `Workstream: Quick Revision`
- `Workstream: Interview Preparation`

Workstreams are independent from one another. They may have:

- different scope
- different depth
- different Content Plans
- different Templates
- different numbers of modules
- different numbers of generated documents
- independent Jobs
- independent revision cycles

### Clarification

Workstream is not the same as:

- a Project
- a concrete document
- a conversation
- a generation run

### Current Hypotheses

The exact Workstream taxonomy should remain flexible rather than permanently fixed.

## 9. Content Plan

### Locked / Current Product Decisions

Every Workstream has a **Content Plan**.

The Content Plan is the core planning object. It determines:

- what topics are included
- what topics are excluded
- coverage
- depth
- sequencing
- priorities
- examples
- exercises
- diagrams or visuals where useful
- equations
- code
- Q&A
- approximate size
- module breakdown where necessary

Users should ideally be able to inspect and modify the plan before expensive generation.

### Clarification

The Content Plan is not the generated output itself. It is the explicit representation of what the system intends to generate.

## 10. Module

### Locked / Current Product Decisions

A **Module** is optional.

It exists when a Content Plan is large enough to benefit from subdivision.

Examples:

- `Module: Foundations`
- `Module: Transformers`
- `Module: Diffusion`

A small Workstream may have no Modules and still be valid.

### Clarification

Module is a convenience structure for larger plans. It is not a required hierarchy level for all Workstreams.

## 11. Artifact

### Locked / Current Product Decisions

An **Artifact** is a concrete generated document.

Examples:

- `Transformers Notes.pdf`
- `Diffusion Models Notes.pdf`
- `Quick Revision Sheet.pdf`

This distinction is important:

- `Research Notes` = Workstream
- `Transformers Notes.pdf` = Artifact

Artifact must not be used to mean a purpose, a collection of documents, or a body of work.

### Open Questions

- What exact artifact taxonomy is useful for users versus unnecessarily complex?
- Should artifacts always map one-to-one with files, or can some future artifact types be bundles?

## 12. Template

### Locked / Current Product Decisions

Template is separate from Workstream.

Workstream answers:

> What and why do I need this material?

Template answers:

> How do I want it presented?

Example Templates:

- Visual
- Quick
- Theory
- Q&A
- Comprehensive
- Adaptive

The same Workstream can use different Templates.

Templates influence:

- density
- structure
- emphasis
- presentation style

They do not rigidly determine whether diagrams, examples, Q&A, or other elements can exist.

### Current Hypotheses

Template previews using sample pages or sample outputs may be more understandable than text labels alone.

### Open Questions

- What is the right template taxonomy?
- How should users choose templates: labels, examples, or adaptive defaults?

## 13. Conversations

### Locked / Current Product Decisions

A Project can contain multiple conversations.

Conversations are interfaces into Project context, not the Project itself.

Example:

- `Let's decide what I need`
- `Create research notes`
- `Continue Transformers`
- `Create interview prep`
- `Make quick revision notes`

The user should not be forced into one giant conversation forever.

### Clarification

Conversation is not the full source of truth. Project context must persist beyond any single chat thread.

## 14. Sources

### Locked / Current Product Decisions

A Project can contain relevant **Sources** such as:

- syllabus material
- uploaded notes
- source documents
- topic references
- user-provided context material

Sources belong alongside the Project and can inform Workstreams and Content Plans.

### Open Questions

- What source types should be supported first?
- How should source quality or relevance be surfaced to users?

## 15. Jobs

### Locked / Current Product Decisions

A **Job** represents one execution of work.

Examples:

- generate `Transformers Notes.pdf`
- regenerate a module after revision
- produce a new revision sheet from an approved Content Plan

A Workstream can have many Jobs.

Jobs are operational entities, not primary user-facing product containers.

### Open Questions

- How visible should Jobs be in the user experience?
- Which Job states matter to users versus internal systems only?

## 16. Project Context / Memory

### Locked / Current Product Decisions

A Project persists over time and should retain relevant context such as:

- topic
- purpose and context
- conversations
- sources
- previous Content Plans
- generated Artifacts
- Workstreams
- previous decisions
- project-level preferences
- relevant coverage already generated

Different Workstreams in the same Project may benefit from previous Workstreams.

Example:

If `Research Notes` already deeply covered Transformers, Diffusion, and GANs, a later `Interview Preparation` Workstream may reuse that context and avoid unnecessary repetition.

### Clarification

This is Project-level context reuse, not LMS-style mastery tracking.

### Open Questions

- What exact Project memory should be stored as product-level truth?
- How should reused context be surfaced to the user, if at all?

## 17. Coverage & Scope Planning

### Locked / Current Product Decisions

Coverage and scope planning is the central product intelligence problem.

The platform must make explicit decisions about:

- what matters
- what does not matter
- how much depth is appropriate
- what to prioritize first
- what form the final material should take

The Content Plan is the mechanism that makes these decisions visible and editable.

### Clarification

Diagrams are not the central product problem.

Diagrams are one possible component of a generated document, alongside:

- tables
- equations
- examples
- exercises
- code
- Q&A
- case studies
- visual explanations

The central problem is deciding appropriate coverage, not merely deciding whether to draw diagrams.

## 18. User Flow

### Locked / Current Product Decisions

The intended high-level flow is:

1. User expresses a topic or notes need.
2. System identifies whether this belongs to an existing Project or a new Project.
3. System gathers only the context that materially affects output.
4. System proposes or confirms a Workstream.
5. System proposes or confirms a Template.
6. System creates a Content Plan.
7. User reviews and edits the Content Plan.
8. User approves the plan.
9. System runs Jobs to generate one or more Artifacts.

### Current Hypotheses

- Recommending Workstream + Template combinations may reduce friction and improve output fit.
- Lightweight adaptive questioning may outperform both giant questionnaires and zero-context prompting.

## 19. Example User Scenarios

### Scenario 1: New Topic, Research Notes

User says:

`I need notes on Generative AI.`

System creates:

- `Project: Generative AI`
- `Workstream: Research Notes` or another recommended Workstream if context suggests it

Then the system proposes a Content Plan and generates one or more Artifacts after approval.

### Scenario 2: Same Topic, Different Purpose

Inside `Project: Generative AI`, the user later says:

`I have my interview tomorrow. Make quick prep notes.`

The system should create a separate Workstream such as:

- `Workstream: Interview Preparation`

It should not overwrite or merge the existing `Research Notes` Workstream.

### Scenario 3: Small Workstream

User needs:

`Quick revision notes on Operating Systems for tomorrow's exam.`

The resulting Workstream may have:

- one Content Plan
- no Modules
- one Artifact

### Scenario 4: Topic Change

While inside `Project: Generative AI`, the user says:

`I need notes on Electrical Machines.`

This should normally create or switch to:

- `Project: Electrical Machines`

It should not pollute the Generative AI Project.

## 20. Product Boundaries / Non-goals

### Locked / Current Product Decisions

The product is not currently defined as:

- a Learning Journey product
- a goal-centric hierarchy
- a student mastery-tracking system
- an LMS architecture
- an AI tutoring platform
- a progress dashboard product
- a course marketplace
- a generic chatbot
- an engineering design document

The product should avoid obsolete framing such as:

- `Learning Journey` as a core entity
- `Goal` as a required hierarchy level
- `Curriculum` as a separate required core entity
- tutoring as the primary product definition

### Clarification

A large Content Plan may effectively behave like a curriculum, but `Curriculum` is not a separate required core product entity.

## 21. Current Architecture Hypothesis

### Locked / Current Product Decisions

The current conceptual product hierarchy is:

```text
USER
  -> PROJECT
    -> WORKSTREAM
      -> CONTENT PLAN
        -> MODULE (optional)
          -> ARTIFACT
```

Alongside that:

```text
PROJECT
  -> CONVERSATIONS
  -> SOURCES

WORKSTREAM
  -> JOBS
```

Important distinctions:

- Project != Workstream
- Workstream != Artifact
- Content Plan != Artifact
- Module != required
- Curriculum != separate required core entity
- PDF = Artifact
- Project != PDF

### Current Hypotheses

- The user-facing model above is stable enough to guide product design now.
- The internal implementation may later require additional entities, but those should not be exposed unless they clearly improve the product.

### Open Questions

- What internal orchestration model best supports this product structure?
- What storage model best supports persistent Project context?
- What parts of the hierarchy should be directly visible in the UI?

## 22. Open Questions

The following remain intentionally unresolved:

1. Which initial domain gives the fastest and clearest validation signal?
2. Which initial user segment should be prioritized first?
3. What exact Workstream taxonomy is most intuitive?
4. What exact Template taxonomy is most intuitive?
5. How should topic-boundary detection work in ambiguous cases?
6. How much control should users have when editing Content Plans?
7. How granular should Modules be when they exist?
8. How should Project context reuse be made visible to users?
9. How should usefulness be measured against direct prompting workflows?
10. What evidence would strongly validate the planning-first product hypothesis?

## 23. Future Possibilities

### Vision

If the core model is validated, future expansion may include:

- more domains
- more Workstream types
- richer Template previews
- better reuse of source material
- stronger Project memory and continuity
- collaborative or iterative note-building workflows
- better artifact sets for different professional and educational contexts

### Clarification

These are future possibilities, not current commitments.

## Locked Summary

### Locked / Current Product Decisions

- The product is an AI-powered notes generation platform.
- Project is the primary persistent topic-level workspace.
- Workstream is a purpose-scoped body of work inside a Project.
- Content Plan is the core planning object.
- Module is optional.
- Artifact means a concrete generated document.
- Template is separate from Workstream and controls presentation style.
- Conversations and Sources belong to the Project context.
- Jobs are operational entities attached to Workstreams.
- Coverage and scope planning are more central than raw text generation.
- Curriculum is not a separate required core entity.
- The product is not an LMS, tutoring platform, or Learning Journey system.

## Current Hypotheses Summary

- Scope review may be a key trust and differentiation moment.
- Recommended Workstream + Template combinations may reduce friction.
- Template previews may be more effective than labels alone.
- Project-level context reuse may materially improve later outputs.

## Source Of Truth Statement

This document is the current canonical Product Bible for the product as of August 14, 2026. It should be used as the source of truth for product behavior and product terminology until superseded by a later approved revision.
