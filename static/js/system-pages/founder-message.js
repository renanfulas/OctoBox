(function () {
    const root = document.querySelector('[data-page="founder-message"]');

    if (!root || typeof window.confetti !== 'function') {
        return;
    }

    const end = Date.now() + 3000;
    const colors = ['#00ffff', '#ffffff'];

    function frame() {
        window.confetti({
            particleCount: 2,
            angle: 60,
            spread: 55,
            origin: { x: 0 },
            colors,
        });

        window.confetti({
            particleCount: 2,
            angle: 120,
            spread: 55,
            origin: { x: 1 },
            colors,
        });

        if (Date.now() < end) {
            window.requestAnimationFrame(frame);
        }
    }

    frame();
}());
