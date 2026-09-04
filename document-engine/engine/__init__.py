"""document-engine — Document Model + Template + Theme -> PDF.

No LLM, no network at render time, no clock. The engine reports; it never
edits content.

Determinism is scoped to a pinned environment: the Chromium build below is
what golden images were captured against. Changing it is a deliberate act that
invalidates them.
"""

from .merge import TemplateGap, merge
from .render import render
from .schema import Document, json_schema, load

__version__ = "0.1.0"
CHROMIUM_VERSION = "151.0.7922.34"  # playwright==1.62.0

__all__ = [
    "Document",
    "load",
    "json_schema",
    "merge",
    "render",
    "TemplateGap",
    "__version__",
    "CHROMIUM_VERSION",
]
