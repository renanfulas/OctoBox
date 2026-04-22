# Spec

**Status**: Draft

## Problem

Two reception session cards still carried inline style debt, which weakens maintainability and breaks the canonical front-end discipline already adopted in the reception workspace.

## Requirements

### RSSC-01
Both session card templates must stop using inline style.

### RSSC-02
The visual finish must move into the correct reception CSS owner.

### RSSC-03
The cleanup must document whether these cards are live runtime surfaces or residual stock.

## Success Criteria

1. no `style=` remains in the two target templates
2. `class-grid.css` owns the extracted presentation
3. the final note explains whether the pieces are active or residual
