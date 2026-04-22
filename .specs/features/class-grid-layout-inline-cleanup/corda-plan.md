# CORDA Plan

## North

Move the weekly-plus-monthly workspace split from inline markup back into its canonical CSS owner.

## Why now

This is the highest-ROI remaining layout cleanup because:

1. it lives in a real operational surface
2. it is structural rather than decorative
3. it is small enough to close cleanly in one pass

## Risks

The main risk is not logic breakage. It is proportion drift:

1. the weekly and monthly blocks could lose the intended 2:1 rhythm
2. a cleanup could accidentally change spacing on desktop or stacked behavior on smaller screens

## Execution sequence

1. map the exact inline layout contract
2. extract it into workspace CSS with semantic class ownership
3. validate desktop rhythm and safe fallback behavior

## Success bar

This pass is done when:

1. no inline structural layout remains in the workspace split
2. the weekly-plus-monthly section keeps its intended 2:1 reading rhythm
3. the class grid keeps the same practical reading order
