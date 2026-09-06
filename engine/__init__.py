"""Engine: rendering.

A genuinely separate responsibility from the agent, not a helper it calls.
Imports no model SDK and makes no network call -- that purity is what makes
golden-image testing possible later, and it is enforced by
tests/test_boundaries.py rather than by convention.

M1 is merge -> print. Measurement, connector solving, annotation and layout
validation arrive at M7 with the layout gate; the pipeline is written so they
slot between the two ends rather than replacing them.
"""

from engine.render import RenderResult, render_pdf, render_html

__all__ = ["RenderResult", "render_pdf", "render_html"]
