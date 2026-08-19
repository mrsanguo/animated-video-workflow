# Installation guidance for agents

These instructions apply to the repository root.

When a user asks you to install this repository as an Agent Skill:

1. Install only `skills/animated-video-workflow`; the repository root is not the Skill directory.
2. Prefer your native Skill installer. For Codex, use the repository tree URL:
   `https://github.com/mrsanguo/animated-video-workflow/tree/main/skills/animated-video-workflow`.
3. If no native installer is available, use:
   `npx skills add mrsanguo/animated-video-workflow --skill animated-video-workflow -g`.
4. Verify that the installed directory contains `SKILL.md`, `scripts/`, `references/`, and `agents/openai.yaml`.
5. Report the installation destination and tell the user whether the current agent session must be restarted.

Installing the Skill does not require running the video workflow, installing optional rendering engines, or uploading any user media.

