# Design

## Core question

The live refactor in `hero.css` touches several dimensions at once:

1. gap and spacing rhythm
2. stack width and copy width
3. action row density
4. button sizing
5. mobile heading behavior
6. baseline typography for eyebrow and actions

## What we are testing

Does the shared hero become:

1. more composed
2. more premium
3. more consistent across consumers

without becoming:

1. too wide or too editorial for transactional screens
2. too heavy for quick operational contexts
3. too clever to maintain

## Inventory conclusion

The live diff is not one thing. It is a bundle of six contract moves:

1. more elastic global spacing
2. wider shared reading mass
3. denser and clearer action rail behavior
4. stronger baseline button presence
5. explicit eyebrow typography
6. explicit mobile fallback for heading/copy rhythm

Because local consumers already override several of these values, the next decision must classify each move separately instead of accepting or rejecting the whole patch as one unit.

## Classification result

### Keep

These moves strengthen the shared contract itself:

1. explicit mobile fallback for heading/copy/stack rhythm
2. explicit eyebrow baseline
3. clearer action-row alignment defaults
4. explicit shared action gap token

### Soften

These moves are good in direction, but should stay conservative in shared authority:

1. elastic global spacing
2. wider shared stack width
3. wider shared copy width
4. stronger button density

### Avoid as hard shared baseline

The refactor should not push transactional surfaces into a slower, more editorial hero posture by default.

## Decision shape

This is likely not an all-or-nothing refactor.

We should expect some changes to:

1. stay
2. be softened
3. or move back to local consumers instead of the shared contract
