# Prompt Spec

Use this before drafting any serious prompt.

## Prompt Spec Template

- Objective: what the prompt must achieve
- Target model: what capabilities and limits matter
- Inputs: what the model will receive
- Assumptions: what you are choosing to believe
- Non-goals: what must stay out of scope
- Constraints: format, tone, length, safety, tools
- Output contract: exact structure the answer must follow
- Style: voice, depth, examples, language
- Edge cases: missing, messy, or conflicting inputs
- Evaluation: how you will judge success
- Version: prompt name and revision number

## Production Prompt Skeleton

```text
You are [role].

Mission:
[single primary outcome]

Context:
[only the facts that change the answer]

Inputs:
- [input 1]
- [input 2]

Constraints:
- [hard rule 1]
- [hard rule 2]

Output format:
- [exact sections or schema]

Fallback behavior:
- If [missing data], ask up to 3 questions.
- If [conflict], state the conflict and choose the safest assumption.

Quality bar:
- [what "good" means]
```

## Useful Prompt Contracts

- Use XML tags or fenced blocks for untrusted data.
- Use JSON only when downstream parsing matters.
- Use numbered output sections when order matters.
- Use examples when the task is ambiguous, style-sensitive, or easy to misunderstand.
