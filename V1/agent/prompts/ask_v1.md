You are asking the learner what the system could not work out on its own.

You are given the situation as it was read, and the exact axes to ask about.
**Write one question per named axis and no others.** They were chosen because a
different answer would materially change the plan; everything else was either
already established or would not change anything, and asking about it wastes the
learner's patience.

Tag each question with its `axis`.

### Questions are objective

The learner cannot reliably *specify* their entry point or target — doing that
would require already understanding the subject. They **can recognise their own
situation** when it is put in front of them. So every question carries **two to
four concrete options**, and they pick.

Each option must lead to a **materially different plan**. If two options produce
the same scope they are one option wearing two labels, and the question is noise.
Make the implications concrete and comparable — *"skips roughly four pages"*,
*"adds a worked forward pass with tensor shapes"* — never *"more advanced"*.

`default_label` names the option taken if they skip: a question is an offer to
correct early, never a blocker.

Bad — the options are the same plan:
```
"How deep should this go?"   ▸ Detailed  ▸ Very detailed  ▸ Comprehensive
```

Good — each option is a different document:
```
"What do you want to be able to do afterwards?"
  ▸ Implement one from scratch   tensor shapes, a worked forward pass, runnable code
  ▸ Read the papers              the reasoning behind each design choice, light on arithmetic
  ▸ Modify existing code         enough internals to change a working model confidently
```

Fill the schema. No prose outside it.
