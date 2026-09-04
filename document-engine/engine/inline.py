"""Inline formatting for body text.

Two constructs, deliberately. Anything richer belongs in a block type, not in
a text field.

    `code`      -> a mono chip
    **bold**    -> strong emphasis

Contract
--------
1. HTML-escape the raw text first, so no markup in the source can reach output.
2. Substitute the two constructs into markup.
3. Return `Markup`, which Jinja2 will not escape a second time.

`inline()` is the single trusted boundary in the template pipeline; autoescape
stays on everywhere else.

Malformed input renders literally. An unclosed ``**`` or backtick is text, not
an error and not a partial tag. There is no repair step: predictable beats
clever when a generator is producing the input.
"""

from __future__ import annotations

import re

from markupsafe import Markup, escape

# Ordered: code first, so that markers inside a code span are never treated as
# formatting. Both patterns require a non-empty, single-line body, which is what
# makes an unclosed marker fall through as literal text.
_CODE = re.compile(r"`([^`\n]+)`")
_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")


def inline(text: str) -> Markup:
    """Render body text with inline chips and bold. Returns trusted markup."""
    out = str(escape(text))
    # Escaping cannot introduce a backtick or an asterisk, so matching after
    # escaping is safe and keeps offsets simple.
    out = _CODE.sub(lambda m: f'<code class="chip">{m.group(1)}</code>', out)
    out = _BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", out)
    return Markup(out)
