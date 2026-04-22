# Architecture Delivery Contract

Use this structure for substantial architecture work.

Keep the response tight, but do not skip any section that materially changes the decision.

## 1. Context

Capture:

- problem statement
- business objective
- current state
- constraints
- assumptions

## 2. Audit

Describe:

- strengths worth preserving
- weaknesses or structural bottlenecks
- immediate risks
- likely future risks under growth

## 3. Architecture direction

State:

- recommended target shape
- why this shape fits the product ambition
- what stays as-is
- what changes now
- what should wait

## 4. Trade-offs

List the important trade-offs explicitly:

- latency
- consistency
- delivery speed
- operational complexity
- cost
- maintainability

## 5. High-level diagrams

Use Mermaid when it adds clarity.

Preferred diagrams:

1. system context
2. container view
3. component or flow view for the critical path

## 6. ADR slice

For each major decision, include:

- Decision
- Status
- Context
- Chosen option
- Alternatives considered
- Consequences

## 7. Migration path

Prefer phases. For each phase, define:

- goal
- concrete changes
- dependencies
- rollback or containment strategy
- success signal

## 8. Operational guardrails

Cover:

- observability
- security
- idempotency
- backpressure or failure handling
- performance expectations
- cost watchpoints

## 9. Validation

Close with:

- how to test the architecture direction
- what metrics would prove it is working
- what signals would prove the decision is wrong

## Teaching rule

If the user is still learning, explain the recommendation twice:

1. technical explanation
2. simple analogy
