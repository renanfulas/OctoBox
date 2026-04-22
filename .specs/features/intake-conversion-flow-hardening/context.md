# Context

## Locked Decisions

1. This mountain should stay focused on the live intake conversion flow, not on all onboarding visuals.
2. Inline `onclick` behavior must leave the template and move into a JS asset owner.
3. Hardcoded student-creation paths inside the intake conversion flow must move to named routes or payload-owned links.
4. The premium finish of the drawer can survive, but only as controlled presentation, never as inline behavioral glue.
5. The current business behavior must remain intact: choose a plan, choose a payment path, and convert the intake without extra friction.
6. If runtime evidence proves the drawer is dormant instead of live, the correct move is to harden the live queue-to-student path first and remove dormant asset loading from the active page contract.

## Why This Mountain Exists

The intake conversion flow is still one of the highest-ROI live paths in the app, and it still carries visible structural debt:

1. inline `onclick` in `conversion_drawer.html`
2. hardcoded conversion href in `intake_queue_panel.html`
3. JS behavior exposed as global `window.*` hooks
4. presenter output still building conversion URLs by hand

In simple terms:

1. the store entrance is working
2. but the door closer, the lock, and part of the sign are still improvised

That is the right place to invest next.
