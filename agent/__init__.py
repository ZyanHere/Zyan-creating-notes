"""agent — planning and generation. The only place an LLM is called.

Step 2 of Phase 1: `fill` writes the content of blocks a plan has already
declared. It cannot add a block, drop one, or change a type.
"""

from .client import Client, MissingKey, have_key, make_client
from .fill import FillError, FillResult, Finding, build_prompt, fill, validate_section
from .models import DocumentPlan, SectionPlan, load_plan

__all__ = [
    "Client", "make_client", "have_key", "MissingKey",
    "DocumentPlan", "SectionPlan", "load_plan",
    "fill", "FillResult", "FillError", "Finding",
    "build_prompt", "validate_section",
]
