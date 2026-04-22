# Spec

## Problem

Strategic workspaces already read better visually, but several decisions are still inferred too late by the front.

That creates a softer but still real form of friction:

1. correct data
2. decent layout
3. unclear urgency ranking

## Users

1. owner
2. manager
3. reception leadership paths that escalate into finance and intake
4. dashboard readers who need to know what matters first

## Requirements

### R1. Payloads must express priority directly

Management snapshots should carry enough information to explain:

1. why this is first
2. what action follows
3. what is support context instead of opening pressure

### R2. The front must not invent urgency that the backend already knows

If the backend can rank or explain a pressure source, that reasoning should travel in the payload.

### R3. Enrichment must stay lightweight

The result should improve decision quality without turning payloads into essays.

### R4. Routing and operational next steps must stay canonical

Any recommended next action must keep using named routes and current workspace contracts.

## Success bar

This feature succeeds when:

1. key payloads distinguish dominant pressure from supporting context
2. presenters need less guesswork to order actions
3. the resulting screens feel more decisive, not busier
