# Presentation Boundary — WORKING MODEL

Where a correction is presentation and where it is content.

Companion to [Representation-Boundary.md](Representation-Boundary.md) (Rev. 3, frozen).
That document draws the line between the LLM's educational decision and the engine's
realization. This one draws the line between a user's words and where they route.

**Not a new layer.** *Render configuration* is already named in Architecture §5 and
already ungated. It has a name and no substance; this fills in the substance and the
routing rule, and nothing else.

---

## 1. Already recorded

- **Architecture §5** — the **Demo** gate commits **treatment policy**, on user approval.
  The user approves having seen a page, not having chosen an object.
- **Architecture §5** — *"Not gated: traversal, consequence, derived relevance,
  **render configuration**. Internal, cheap to redo, nothing relies on them."*
- **Architecture §7** — *"A correction is not a stage. It is a routing operation over
  the decision graph."* Appendix A4 — *one correction, seven meanings* — is this
  problem, already worked for content.
- **Semantics §2** — a template constrains presentation, never content.
- **System Design §9** — `engine.preview(doc_model, template_id)`.
- **System Design §7** — the demo shows the page of **highest treatment variance**,
  *computable from the `representation` records*.

---

## 2. Two objects, one of them invisible

> **Correction, 2026-09-08.** This section previously said templates were internal and
> that users never select them. That contradicted **Semantics §1's axis table** (Template
> — *user* — biasing) and **Semantics §2, LOCKED**, which shows the selection literally:
> *Artifact: Long notes / Template: Diagram-heavy*. The error was conflating the two
> objects below — the claim "render configuration is not a theme picker" is true and was
> wrongly extended to templates. Rules 2 and 4–9 were unaffected and stand.

**Template** — the editorial and layout language: structure, page furniture, how each
block kind is drawn. **User-selected**, from the set belonging to the chosen artifact
type (Semantics §2: *"templates are per-artifact-type sets, not a global list"*).
Authored editorially, versioned with the engine. Biasing, never binding — silence
selects a default rather than blocking.

**Render configuration** — bounded, per-project, ungated: ground polarity, palette role
assignments, type pairing, density. This is where *"make it black with yellow and orange
accents, different fonts"* lands, in full. **Internal.** The user never names it, and
there is **no theme picker**.

So the user picks a template and *describes* everything else.

How that selection is stored and rendered — a design specification the user picks by looking at a rendered exemplar, rather than a `.j2` file — is worked in [Design-Library.md](Design-Library.md), deferred until the flow runs end to end.

---

## 3. The rules

1. **Template is user-selected, from the artifact type's set.** Semantics §1 (user-set,
   biasing) and §2 LOCKED. Because the sets are per-artifact-type, **artifact type is a
   prerequisite for offering the menu** — the same dependency shape `subject` has for
   planning. Biasing, not binding: no selection means a default, never a block.
2. **Render configuration is an ungated, per-project decision.** Architecture §5 already
   places it outside the gates: internal, cheap to redo, nothing relies on it.
3. **Everything below the template is expressed in natural language**, especially at the
   demo gate and in corrections. The user names a *template*; they never name a theme, a
   palette or a font stack. "Use the diagram-heavy one" is a selection; "make it black
   with yellow accents" is render configuration.
4. **Classification happens before routing.** A correction is classified first; only then
   does Architecture §7's routing operation run.
5. **If a correction can be satisfied without changing the document's asserted content or
   semantic claim, route it to render configuration.**
6. **If it changes semantic representation, coverage, structure, or meaning, route it into
   the decision graph.**
7. **On ambiguity, bias toward the decision graph.** Never silently treat a correction as
   presentation-only.
8. **A render configuration change requires no model call.** Same `Document`, new
   configuration, re-render.
9. **The effective render configuration persists into the committed artifact version** at
   the layout/delivery commitment.

---

## 4. The classifier

Rule 5's test is Representation Boundary §1's assertion preservation, applied to a
sentence instead of a figure:

> If it can be honoured without changing any proposition the document asserts, it is
> render configuration. Otherwise it routes into the decision graph.

The tell is **not** whether the words sound visual. All four of these sound visual:

| Correction | Routes to |
|---|---|
| "make it black with yellow and orange accents" | render configuration |
| "use different fonts" | render configuration |
| "this diagram should be a Venn" | representation — the honesty table, Rev. 3 §2 |
| "too many tables" | representation mix — decision 15, Rev. 3 §12 |
| "make it shorter" | scope — reopens an approved plan gate |

Black-on-yellow changes no proposition. A Venn changes what the geometry claims.
"Shorter" changes what is asserted at all.

### A requested representation binds, it does not merely route

*"Show AI, ML and DL as nested sets"* is not a style preference and not a template
choice. It is a **constraint on the representation decision** — it names the claim the
figure must make, which is the one thing render configuration may never touch.

Routing it correctly is necessary and not sufficient. Rev. 3 §10 has the template
ranking whatever survives the honesty and structural filters; a user constraint is an
input to that ranking, and §13 already records the ranking as unspecified. So a
requested realization **binds** stage 3, subject to the earlier filters: a request that
the honesty table forbids for the asserted relation is refused, not honoured — the user
may constrain the choice, never license a figure that misstates the claim.

A **reference image** is the same constraint arriving in a second form. Untested, and
distinct from perceptual form (Rev. 3 family E): here the image specifies *how to draw*,
it is not itself the content.

---

## 5. The asymmetry — why rule 7 is not a preference

The two misroutings do not cost the same.

```
presentation -> decision graph     costs a regeneration
content      -> render config      changes meaning through an UNGATED path
```

Render configuration is ungated by design, so nothing approves what passes through it.
A content correction misrouted there alters what the reader believes with no gate in its
way. Render configuration must therefore be the narrow, well-lit door, and uncertainty
resolves outward.

---

## 6. Two consequences

**Presentation corrections are instant and free.** Rule 8 is not an optimisation; it is
what makes the demo gate usable. "Make it black" re-renders an unchanged `Document`.
This is also the second reason misrouting content into it is dangerous: it is the fast
path, and speed hides the change.

**`engine.preview` takes both.** System Design §9's signature carries a `template_id`, which
the user does select (rule 1) — but it is not sufficient on its own, because the render
configuration layered over it is what rule 8 re-renders for free. The preview signature needs
the pair, not either alone.

---

## 7. Open

- **Where render configuration commits.** It is ungated, but it must survive to delivery,
  and a commitment snapshot must stand alone (System Design §4). The **layout** gate is
  the likely home; not settled.
- **The bounds of render configuration.** Ground polarity, palette roles, type pairing and
  density are the obvious fields. What else is admissible without becoming a presentation
  decision the model or the user is making unbounded is unsettled — and unbounded CSS is
  excluded: a free choice of geometry can make a figure assert what the document does not.
- **Classifier confidence.** Rule 7 says bias outward, but a correction carrying both a
  presentation and a content claim — *"make it black and cut the last section"* — has to
  split rather than route once. Untested.
- **Whether a rejected presentation correction is a correction at all.** Architecture §16
  asks when the right answer to a correction is to refuse it. Nothing here refuses.
