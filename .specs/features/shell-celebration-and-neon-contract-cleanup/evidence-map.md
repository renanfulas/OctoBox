# Evidence Map

## Before

`shell.js` owned visual output through:

1. `piece.style.setProperty(...)`
2. `piece.style.left`
3. `piece.style.animationDelay`
4. `toast.style.opacity`
5. `toast.style.transform`
6. `toast.style.transition`
7. `topbar.style.cursor`
8. `neonOverlay.style.top/left/width/height/animation`

## After

The active runtime now uses:

1. [shell.js](C:/Users/renan/OneDrive/Documents/OctoBOX/static/js/core/shell.js) for state and timing only
2. [topbar.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/topbar.css) for celebration visuals and topbar affordance
3. [sessions_board.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/dashboard/sessions_board.css) for sessions neon animation

## Validation

1. search in `shell.js` for `style.` returned clean
2. `python manage.py check` passed clean
