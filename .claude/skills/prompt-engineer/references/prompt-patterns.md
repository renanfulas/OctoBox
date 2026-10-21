# Prompt Patterns

## Extractor

Use when the model must turn text into structure.

```text
Extract only the requested fields. Return JSON only. If a field is missing, use null.
```

## Classifier

Use when the model must choose a label or category.

```text
Choose exactly one label from the allowed set. Explain the choice in one sentence.
```

## Planner

Use when the model must break work into ordered steps.

```text
Create a step-by-step plan. Each step must be atomic, ordered, and independently verifiable.
```

## Writer

Use when the model must produce polished prose.

```text
Write in the requested voice. Follow the output structure exactly. Keep the scope narrow.
```

## Critic

Use when the model must review or improve a draft.

```text
Review the draft against the rubric. List failures first, then fixes, then a revised version.
```

## Tool-Using Agent

Use when the model can call tools or must decide when to act.

```text
Decide whether to use a tool. State the reason, the expected result, and the next action.
```

## Tutor

Use when the model must teach a person.

```text
Explain the expert version first, then give a simple analogy, then check understanding.
```
