# Evaluation Rubric

Use this to score a prompt before shipping it.

## Score Each Category 0-5

- Clarity: does the prompt state one clear mission?
- Specificity: are inputs, constraints, and outputs explicit?
- Robustness: does it survive missing or conflicting input?
- Brevity: is it short enough to stay readable?
- Testability: can you tell if it worked?
- Maintainability: can a future prompt editor change it safely?

## Pass Rule

- Average score should be 4 or higher.
- No category should be below 3 on a production prompt.

## Red-Team Tests

- Missing input
- Conflicting instruction
- Long input
- Empty input
- Adversarial input
- Wrong format request
- Edge case request

## What Good Looks Like

- The prompt still works when the input is messy.
- The model returns the expected structure without hand-holding.
- The prompt fails safely when information is missing.
- The prompt is easy to revise without breaking unrelated behavior.

## Mini Review Checklist

- One primary objective?
- Clear output contract?
- Explicit fallback?
- No hidden assumptions?
- Evaluation path defined?
