# Delivery Overlay

Use this when the prompt must drive a software-delivery workflow or a multi-step agentic execution path.

## Purpose

Keep the best parts of spec-driven delivery without forcing unnecessary ceremony into the prompt.

## Default Shape

1. Specify what success means.
2. Add design only if there are real architecture or pattern choices.
3. Break into tasks only if there are more than 3 obvious steps.
4. Execute one atomic step at a time.
5. Verify after every step.

## Override Rule

If the delivery scaffold conflicts with better prompt design, the prompt-engineer decision wins.

Examples:

- Use a shorter prompt if the task is small and the extra structure only adds noise.
- Keep traceability and verification if the task is risky or multi-step.
- Remove design/task phases if they do not change the answer.

## Good Use Cases

- Prompts for implementation agents
- Prompts for feature planning
- Prompts for debug workflows
- Prompts for review/validation pipelines

## Bad Use Cases

- Tiny one-shot prompt rewrites
- Pure copywriting tasks
- Tasks where the workflow scaffold does not change the result
