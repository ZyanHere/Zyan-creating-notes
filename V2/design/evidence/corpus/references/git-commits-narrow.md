# Reference — Git commit messages

**Request:** *"how to write good git commit messages"*

Hand-written. This reference exists to pin the **partition floor**: the correct
answer is one module, and the interesting question is whether a system can say
"this is small and stays one thing" without being told a count.

---

## 1. The situation, read correctly

| Axis | Reading | Binding? |
|---|---|---|
| subject | Git commit messages | stated |
| job | **construct** — they will write one tomorrow | inferred |
| purpose | Do it better at work | inferred |
| entry_point | Uses git daily; commits are messy | inferred |
| target_capability | Write a commit message a reviewer can act on | inferred |
| capacity | Not stated | — |

Almost nothing is stated, and almost nothing needs to be asked. A different
answer on purpose or entry point would not move scope, depth or partition
meaningfully — the material is the same either way. **An axis whose answer would
not change the plan is not a question, however unknown it is.** The honest intake
here asks zero or one question.

## 2. Capability decomposition

```
TARGET: write a commit message a reviewer can act on

├── C1  Write a subject line that survives `git log --oneline`
├── C2  Write a body that explains WHY, not what
├── C3  Follow a team convention without thinking about it
└── C4  Recognise and avoid the messages that cause real problems
```

Four sub-capabilities, all exercised in the same act, at the same moment, by the
same person. That is the test for one module: **there is no point at which a
learner would use one of these without the others.**

## 3. Concepts

| Concept | Depth | Why |
|---|---|---|
| The 50/72 shape and why it exists | explain | C1 — tooling-driven, so the reason is checkable |
| Imperative mood | mention | C1 — a convention, not a concept; one line is enough |
| Why-not-what | **work through** | C2 — the actual skill, and the one that needs before/after examples |
| Conventional Commits | explain | C3 — one widely-used concrete convention |
| Atomic commits / one change per commit | explain | C2, C4 — the message problem is usually a commit-scoping problem |
| Anti-patterns: "fix", "wip", "address review comments" | explain | C4 — recognition, taught by counter-example |
| Trailers (Co-Authored-By, Refs) | mention | C3 |

Cut, with consequence: rebase and history rewriting — *"you will eventually want
to fix a bad message; you will need interactive rebase, and it is a different and
riskier skill. Learn it before you rewrite anything already pushed."*

## 4. The module

**One.** Title: *Writing commit messages a reviewer can use.*

*Capability:* Write a commit message — subject, body, trailers — that tells a
reviewer why the change exists, and recognise the messages that will cause
trouble later.

*Sections (inside the module, not modules):*
1. What a commit message is for — the reader six months from now
2. The subject line
3. The body: why, not what
4. Scoping: the message problem is usually a commit problem
5. A convention to adopt: Conventional Commits
6. Anti-patterns, as failing cases

**Why this is not two modules.** The obvious split — "Fundamentals" and
"Advanced" / "Part 1" and "Part 2" — is packaging, not curriculum. Part 1 of a
chain is one document with a cut through the middle of it. There is no
`capability` you can write for "Part 1" that stands on its own: *"understand the
first half of commit messages"* is not something anyone can do.

**Length is not a reason to split.** If this module runs long, it stays one
module and is long.

## 5. What this reference is testing

- Can the model produce **module_count = 1** without being told to?
- Is `capability` actually used as the partition test, or is it written after the
  partition is already chosen?
- Is the distinction between **section** and **module** representable at all?
  (V1 has no planned section decision — sections are one-per-concept by default,
  which would turn these six sections into six sections only by accident.)
- Does the out-of-scope correction in this case (*"make it dark themed with
  orange accents"*) get **deferred** as a presentation concern, or absorbed into
  a plan decision? Absorbing it is worse than deferring it, because the user
  believes it was handled.
