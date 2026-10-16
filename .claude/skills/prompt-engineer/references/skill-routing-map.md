# Skill Routing Map

Use this file as the fast lookup index for skills and workflows in this environment.

## Fast Lookup Order

1. Check `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\skills\`
2. Check `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\workflows\`
3. Check `C:\Users\renan\.codex\skills\.system\`
4. Check plugin skill roots only when the task is clearly Figma or GitHub

Do not start with broad recursive search if the task obviously matches one of the routes below.

## Local Repo Skills

Root:

- `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\skills\`

Direct paths:

- Prompt daily -> `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\skills\prompt-daily\SKILL.md`
- Prompt engineer -> `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\skills\prompt-engineer\SKILL.md`
- CSS / front-end -> `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\skills\css_front_end_architect\SKILL.md`
- Debug -> `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\skills\master_debugger\SKILL.md`
- Performance -> `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\skills\performance_architect\SKILL.md`
- Security / anti-cheat -> `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\skills\security_performance_engineer\SKILL.md`
- Payments UX -> `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\skills\ui_ux_payments\SKILL.md`
- Offensive security -> `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\skills\white_hat_hacker\SKILL.md`

## Local Repo Workflows

Root:

- `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\workflows\`

Direct paths:

- Software delivery workflow -> `C:\Users\renan\OneDrive\Documents\OctoBOX\.agents\workflows\SDD\SKILL.md`

## Codex System Skills

Root:

- `C:\Users\renan\.codex\skills\.system\`

Available system skills:

- Image generation -> `C:\Users\renan\.codex\skills\.system\imagegen\SKILL.md`
- OpenAI docs -> `C:\Users\renan\.codex\skills\.system\openai-docs\SKILL.md`
- Plugin creator -> `C:\Users\renan\.codex\skills\.system\plugin-creator\SKILL.md`
- Skill creator -> `C:\Users\renan\.codex\skills\.system\skill-creator\SKILL.md`
- Skill installer -> `C:\Users\renan\.codex\skills\.system\skill-installer\SKILL.md`

## Plugin Skill Roots

Use only when the task clearly maps to plugin workflows.

Figma root:

- `C:\Users\renan\.codex\plugins\cache\openai-curated\figma\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\`

Figma skill paths:

- Code connect -> `C:\Users\renan\.codex\plugins\cache\openai-curated\figma\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\figma-code-connect-components\SKILL.md`
- Design system rules -> `C:\Users\renan\.codex\plugins\cache\openai-curated\figma\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\figma-create-design-system-rules\SKILL.md`
- New file -> `C:\Users\renan\.codex\plugins\cache\openai-curated\figma\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\figma-create-new-file\SKILL.md`
- Generate design -> `C:\Users\renan\.codex\plugins\cache\openai-curated\figma\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\figma-generate-design\SKILL.md`
- Generate library -> `C:\Users\renan\.codex\plugins\cache\openai-curated\figma\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\figma-generate-library\SKILL.md`
- Implement design -> `C:\Users\renan\.codex\plugins\cache\openai-curated\figma\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\figma-implement-design\SKILL.md`
- Figma use -> `C:\Users\renan\.codex\plugins\cache\openai-curated\figma\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\figma-use\SKILL.md`

GitHub root:

- `C:\Users\renan\.codex\plugins\cache\openai-curated\github\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\`

GitHub skill paths:

- Address comments -> `C:\Users\renan\.codex\plugins\cache\openai-curated\github\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\gh-address-comments\SKILL.md`
- Fix CI -> `C:\Users\renan\.codex\plugins\cache\openai-curated\github\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\gh-fix-ci\SKILL.md`
- General GitHub -> `C:\Users\renan\.codex\plugins\cache\openai-curated\github\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\github\SKILL.md`
- Publish / PR -> `C:\Users\renan\.codex\plugins\cache\openai-curated\github\d88301d4694edc6282ca554e97fb8425cbd5a250\skills\yeet\SKILL.md`

## Intent Routing Cheatsheet

Use this routing first:

- Quick everyday prompt -> `prompt-daily`
- Prompt system, prompt refactor, project plan -> `prompt-engineer`
- UI, CSS, front-end polish, visual hierarchy -> `css_front_end_architect`
- Bug, traceback, unstable behavior -> `master_debugger`
- Latency, heavy queries, throughput -> `performance_architect`
- Security hardening, anti-fraud, abuse vectors -> `security_performance_engineer`
- Payment UX, checkout, friction in billing -> `ui_ux_payments`
- Adversarial security review, offensive analysis -> `white_hat_hacker`
- Structured software delivery flow -> `SDD`
- Figma implementation or generation -> Figma plugin skills
- GitHub PR, review comments, CI, publish -> GitHub plugin skills

## Search Guardrail

Before broad search, ask:

1. Is the task obviously prompt, UI, debug, performance, security, payments, Figma, GitHub, or delivery workflow?
2. If yes, jump straight to the mapped path above.
3. Only search deeper when the route is still ambiguous after this map.
