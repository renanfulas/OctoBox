# Spec

**Status**: Draft

## Problem

`financial.css` still contains a detached block of `elite-*` classes that appears no longer connected to the current runtime path.

If this block is truly dead, keeping it causes:

1. noise in the design-system layer
2. false authority for future maintainers
3. extra hesitation every time someone touches financial UI

If the block is not truly dead, deleting it without evidence could break a hidden path.

## Users

1. developers maintaining the financial workspace
2. future UI refactors that rely on accurate ownership maps
3. reviewers trying to understand whether legacy still matters

## Requirements

### FDRR-01
The detached `elite-*` block in `financial.css` must be explicitly verified against real runtime usage before removal.

### FDRR-02
Only classes with sufficient evidence of non-use may be retired in this pass.

### FDRR-03
If any detached class is discovered to be live, it must be reclassified rather than deleted blindly.

### FDRR-04
The cleanup must preserve runtime integrity and pass `python manage.py check`.

### FDRR-05
The outcome must clearly state what was removed, what was retained, and why.

## Success Criteria

1. the detached `elite-*` block is classified with evidence
2. dead code is removed if evidence supports it
3. no runtime regression is introduced
4. the repo becomes easier to read and trust in the financial design-system layer
