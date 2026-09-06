"""Agent: LLM reasoning.

Owns model clients, prompts, decision logic and structured outputs. Knows
nothing about persistence, HTTP, or the application database, and never imports
a sibling subsystem -- if a decision needs a measurement from `engine/`, the
backend takes that measurement and passes it in as evidence.

M1 exposes one operation. The decision taxonomy arrives at M3.
"""

from agent.contracts import Document
from agent.generate import generate_document

__all__ = ["Document", "generate_document"]
