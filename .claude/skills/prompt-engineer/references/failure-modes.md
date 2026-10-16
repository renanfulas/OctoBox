# Failure Modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Vague answer | Objective is too broad | Reduce the prompt to one job |
| Long but useless answer | No output contract | Add exact sections or schema |
| Model ignores important rules | Priority is unclear | Move critical rules to the top |
| Creative drift | Too much open-ended language | Replace soft wording with hard constraints |
| Hallucinated details | Missing source boundaries | Mark what is known, unknown, and forbidden |
| Bad formatting | No format guardrails | Show the expected shape explicitly |
| Weak edge-case handling | Only happy path was specified | Add missing, conflicting, and empty cases |
| Prompt bloat | Too many goals and examples | Cut context and keep the smallest useful set |

## Fast Debug Loop

1. Find the first failure mode.
2. Decide whether the problem is objective, context, constraint, format, or evaluation.
3. Fix only that layer.
4. Retest with a hostile or messy input.

## Anti-Patterns

- "Make it better" without defining better
- Multiple unrelated goals in one prompt
- Examples that secretly act like rules
- Hidden assumptions the model cannot infer
- No fallback when the input is incomplete
