// pytest-aitest Report Scripts

// Initialize Mermaid
mermaid.initialize({ 
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose'
});

// Fullscreen diagram viewer
function showDiagram(mermaidCode) {
    const overlay = document.getElementById('overlay');
    const content = document.getElementById('overlay-mermaid');
    content.innerHTML = mermaidCode;
    overlay.classList.add('active');
    mermaid.run({ nodes: [content] });
}

function hideOverlay() {
    document.getElementById('overlay').classList.remove('active');
}

// Close overlay on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') hideOverlay();
});

// Side-by-side test selector
function showSideBySideTest(testId) {
    // Hide all groups
    document.querySelectorAll('.side-by-side-group').forEach(group => {
        group.classList.remove('active');
    });
    // Show selected group
    const selected = document.getElementById(testId);
    if (selected) {
        selected.classList.add('active');
        // Re-render mermaid diagrams in the newly visible group
        mermaid.run({ nodes: selected.querySelectorAll('.mermaid') });
    }
}
