"""Overlay component - fullscreen diagram viewer."""

from __future__ import annotations

from htpy import Node, button, div, style


def overlay() -> Node:
    """Render the fullscreen overlay for diagram viewing.
    
    Returns:
        htpy Node for the overlay and hover popup.
    """
    return [
        # Main fullscreen overlay
        div(
            id="overlay",
            class_="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 hidden items-center justify-center p-8",
            onclick="hideOverlay()",
        )[
            button(
                class_="absolute top-4 right-4 w-10 h-10 flex items-center justify-center text-2xl text-text-muted hover:text-text-light bg-surface-card rounded-full border border-white/10 transition-colors",
                onclick="hideOverlay()",
            )["✕"],
            div(
                class_="w-[90vw] h-[85vh] overflow-auto bg-surface-card rounded-lg p-6 shadow-material-lg flex items-center justify-center",
                onclick="event.stopPropagation()",
            )[
                div(".mermaid.w-full.h-full", id="overlay-mermaid"),
            ],
        ],
        # Hover popup for side-by-side diagrams
        div(
            id="diagram-hover-popup",
            class_="fixed z-40 bg-surface-card rounded-lg shadow-material-lg border border-white/10 p-4 hidden max-w-xl",
            onmouseenter="keepDiagramHover()",
            onmouseleave="hideDiagramHover()",
            onclick="hideOverlay(); this.classList.add('hidden'); showDiagram(document.getElementById('hover-mermaid').innerHTML);",
        )[
            div(".mermaid", id="hover-mermaid"),
        ],
        # Styles for overlay behavior
        style[
            """
#overlay.active { display: flex !important; }
#diagram-hover-popup.active { display: block !important; }

/* Scale the mermaid SVG in overlay to fill available space */
#overlay-mermaid svg {
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
    min-height: 60vh;
}
"""
        ],
    ]
