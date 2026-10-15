# Project and Refactor Playbook

Use this when the work is bigger than a one-off prompt rewrite.

## When to Use

- Building a reusable prompt system
- Designing a prompt library for a project
- Refactoring a prompt that keeps failing in similar ways
- Replacing an old prompt stack with a better one
- Adding evaluation, versioning, or migration controls

## Decision Tree

### Patch

Use when:

- One prompt is mostly fine
- One failure mode is obvious
- The fix is local

### Refactor

Use when:

- The prompt works, but it is hard to maintain
- Multiple prompts depend on the same logic
- You need clearer contracts or better testability

### Rewrite

Use when:

- The prompt has too many goals
- The output contract is broken or missing
- The instruction hierarchy is confused
- The system is full of hidden assumptions

## Project Mode Workflow

1. Define the goal.
2. Define the user or downstream agent.
3. List inputs, constraints, and output contract.
4. Decide whether the system needs one prompt or many.
5. Define reusable prompt modules.
6. Add failure-mode tests.
7. Add a review rubric.
8. Define versioning and rollout.

## Refactor Mode Workflow

1. Inventory the current prompt stack.
2. Mark what must stay.
3. Mark what must change.
4. Identify repeated failures.
5. Find instruction conflicts.
6. Remove hidden assumptions.
7. Simplify the contract.
8. Compare old and new behavior.

## Required Deliverables

- Prompt brief
- Prompt architecture map
- Supporting prompt inventory
- Failure-mode list
- Evaluation rubric
- Migration notes when replacing an existing system

## Prompt Architecture Map

Use a simple table:

| Layer | Purpose | Owns |
| --- | --- | --- |
| System prompt | Non-negotiable policy and role | Safety, boundaries, identity |
| Developer prompt | Task strategy and workflow | How to solve the task |
| User prompt | Instance-specific request | The current job |
| Output schema | Shape of the answer | Validation and downstream use |
| Eval set | How to judge quality | Regression detection |

## Refactor Checklist

- One primary objective per prompt
- No duplicate instructions across layers
- No examples acting as hidden rules
- No output format ambiguity
- No missing fallback behavior
- No test case gap on the main failure mode

## Shipping Rule

Do not ship the new prompt system until:

- It can be explained in one minute
- It passes the evaluation rubric
- It survives at least one messy or adversarial test
- The migration path is clear if it replaces an old system

## Output Shape

When asked to do project or refactor work, return:

1. Diagnosis
2. Chosen mode: patch, refactor, or rewrite
3. Target architecture
4. Draft prompt system or revised prompt
5. Failure tests
6. Short rationale
