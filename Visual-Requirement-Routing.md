# Visual Requirement Routing

How a visual requirement is represented and routed when the engine cannot construct it.

Not new representation architecture. Representation-Boundary Rev. 3 is frozen and already
decides the *what*: §5's four classes, §6's asset test on generated figures, §10's filter
chain terminating at escalation. This document is the *how it flows through the build*,
and it exists because the build cannot currently express the frozen answer.

Proposes no image pipeline. Implements nothing.

---

## 1. What is actually broken

Not the taxonomy. `agent/treatment.py` already diagnoses at the plan gate, weights extent
by it, and reports what it cannot serve before approval. That half works — a real run on
human digestion produced `perceptual-referent: [Villi and microvilli, Liver structure]`
unprompted, and the plan said so.

The break is one layer down. **In `agent/contracts.py`, a block is a realization.**
`Block` is a union of eleven things that can be drawn. There is no member meaning *a
figure is required here* that is independent of a figure existing.

So a model that has correctly diagnosed `perceptual-referent` while writing section 4 has
three exits, and the schema offers no fourth:

| Exit | What it is |
|---|---|
| write prose anyway | the silent substitution Architecture §13 forbids |
| emit `RelationalStructure` | boxes and arrows for a heart |
| omit it | the quiet omission Semantics §12 forbids |

The second is the dangerous one, and it is *available*: `relation: is-part-of` over
`[mucosa, submucosa, muscularis, serosa]` will render, will look like a diagram, and will
not be what the reader needed. Nothing detects it, because `Departure.diagnosis` is free
text attached to a block that was drawn — the diagnosis and the realization are never
compared.

**The system cannot route what it cannot represent.** That is the whole finding.

---

## 2. `served: bool` hides two different things

`treatment.py`'s capability table has one boolean, and two rows fail it for unrelated
reasons:

- **`parallel-state`** is unserved because nobody has built swimlanes. It is
  constructible from a payload — actors, states, order — and that payload is already in
  A3's contract. This is a backlog item.
- **`perceptual-referent`** is unserved because **no payload can produce it.** Rev. 3 §1:
  family E exists precisely to add what the model could not specify. This is a permanent
  boundary.

They route differently and today they print identically, under one heading that implies
both are permanent. One is a missing feature; the other is the shape of the problem.

**Replace the boolean with a construction path.**

```
constructible     engine draws it from the payload            A1-A5, B, C, D, F1, F2
not-built         constructible, no realization exists yet    parallel-state today
requires-asset    no payload can produce it; only an asset    E, permanently
```

`not-built` escalates as a product gap. `requires-asset` emits an asset request. Only the
second is the subject of this document.

---

## 3. The requirement is an element; the figure is a binding

The missing element carries what Rev. 3 §4 already specifies, and nothing more:

```
figure requirement
  diagnosis   which prose failure fired
  spec        A1..A5 | B | C | D | E | F1 | F2
  brief       what the figure must show, for E; payload for the rest
  emphasis    what the reader must take from it        REQUIRED
```

It has exactly three terminal states, and a document must be able to print all three:

```
                    FIGURE REQUIREMENT
                           |
              is there a construction path?
                           |
    +----------------------+----------------------+
    |                      |                      |
CONSTRUCTIBLE          NOT BUILT            REQUIRES ASSET
    |                      |                      |
 REALIZED             escalate                asset lookup
 engine draws it      Rev.3 §10 stage 5            |
 from the payload     challenge upstream    +------+------+
                                            |             |
                                          BOUND        UNBOUND
                                       an asset      nothing binds
                                       satisfies it        |
                                            |         STATED GAP
                                       versioned,     printed, not
                                       correctable    swallowed
```

The three states are not error levels. They are all normal document content.

---

## 4. The unbound state prints, and it is useful

An unbound figure requirement is not a hole and not an apology. It is a marked gap in
exactly Semantics §12's sense, applied to representation instead of to scope — and the
brief is the content:

> **Figure not included.** This section needs a labelled cross-section of an intestinal
> villus showing the epithelium, the lacteal, the capillary network and the brush border,
> with the lacteal's position relative to the capillaries visible. We cannot draw it.

That is more honest than silence and more useful than boxes. The reader learns what to
look for and where the document stops. It costs two lines and is available today.

Rev. 3 §6 route 1 — *report the gap* — is not a placeholder for a better mechanism. It is
the correct default, and this is its printed form.

---

## 5. Why this makes the image decision cheap later

A brief with required referents **is** an asset request in Architecture §8's sense:
identified, stable across runs, correctable, versioned. It passes the asset test for the
reason §6 already gave — ask an image model twice and get two small intestines, with no
way to accumulate a correction.

So the requirement is a socket. Retrieval (§6 route 2) and generation (§6 route 3) both
bind the same socket, and **the document does not change shape when either is built.**
The answer to "when do we build image generation" is therefore: whenever we want, and not
now, because nothing downstream is waiting on it. What is waiting is the socket.

This is also why the anchor problem in §6 does not need solving yet. Annotation needs
coordinates; an unbound requirement has no surface to annotate; a bound retrieved figure
has coordinates for free. The ordering falls out.

---

## 6. Two guards, both cheap, both missing

**Guard 1 — a diagnosed E may not be realized.** Rev. 3 §10 stage 1 admits *nothing* for
family E, so the chain terminates at escalation by construction. But that only bites if
the model stops naming realizations. As long as its output is `kind: "relation"`, the
substitution is one judgement away and nothing sees it.

Detectable against today's schema without any of the above:

```
diagnosis == "perceptual-referent" and the block was drawn  ->  hard error
```

Not a warning. Rev. 3 §8 already calls this a layering violation committed at the schema
level; this is the assertion that catches it.

**Guard 2 — the brief test, against over-diagnosis.** Rev. 3 §6: *most apparent E is A in
disguise, and the disguise is expensive.* Over-diagnosing E manufactures a permanent gap
where the engine could have drawn something true. The test is the brief itself:

> Write down what the figure must show. If everything written is named parts and the
> relation between them, it is family A and the engine can draw it. If it includes shape,
> proportion or appearance that no list of parts captures, it is E.

The gut wall — mucosa, submucosa, muscularis, serosa, in order, adjacent — passes as A2.
The villus fails it: the lacteal's position inside the finger is spatial truth, and a list
of parts does not carry it.

Under-diagnosis gives prose where a figure was needed. Over-diagnosis gives a gap where a
diagram would have served. Both are wrong; the brief is the same instrument for both.

---

## 7. What this does not decide

- **Which realization**, for anything constructible. Rev. 3 §10's filter chain, at the
  demo gate, unchanged.
- **Whether to retrieve or generate.** Rev. 3 §6 ranks the routes; nothing here picks one.
- **Where assets live.** `backend/ids/__init__.py` carries an unfilled `asset_version`
  field and there is no store. Out of scope until something binds a socket.
- **Whether `not-built` reads differently from `requires-asset` on the plan page.** It
  should, and the wording is a product question, not an architectural one.
