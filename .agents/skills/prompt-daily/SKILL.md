---
name: prompt-daily
description: Fast everyday prompt writing, cleanup, and rewrites for short tasks. Use when the user wants a prompt right now, needs to sharpen a rough idea, shorten a verbose prompt, fix one weak instruction, or get a clear output template without a full project workflow. Escalate to $prompt-engineer when the request becomes a project, refactor, system prompt, multi-step agent workflow, or evaluation harness.
---

# Prompt Daily

Fast lane for practical prompts you use every day.

## Use This When

- Turning a rough idea into a prompt
- Cleaning up a prompt that is too long or vague
- Fixing one weak instruction
- Making the output format explicit
- Creating a quick prompt for a one-off task

If the task is becoming a project, refactor, reusable system, or multi-step workflow, stop and escalate to $prompt-engineer.

## Quick Method

1. Identify the one job.
2. Keep only the facts that change the answer.
3. Write the output format explicitly.
4. Add one fallback rule for missing input.
5. Return the prompt and a short reason.

## Daily Prompt Card

Use this shape unless the user asks for something else:

```text
You are [role].

Task:
[one clear job]

Context:
[only the facts that matter]

Constraints:
- [hard rule 1]
- [hard rule 2]

Output:
[exact format or structure]

Fallback:
If something critical is missing, ask up to 1 question.
```

## Guardrails

- One prompt, one outcome.
- Prefer short over clever.
- Do not add ceremony that does not improve the result.
- If the answer needs architecture, evaluation, or versioning, escalate to $prompt-engineer.

## Delivery

When helpful, return:

- The cleaned-up prompt
- One sentence explaining the improvement
- One test or sanity check
