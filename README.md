# Agent Skill for Using Hermes

Verb keywords: install, remove, maintain

- Install: Add new things
- Remove: Remove things already existed
- Maintain: Move and check things already existed. Also modify existed content without contacting remote.
- Update: Contact with remote and modify existed content.

## Workflow

- Run `scripts/auto-generate-skill-structure.py` in the end to generate structures for every SKILL.md.
- Run `scripts/verify-skill-package.py skills/<name>` on the skills you touched (tree counts vs disk, and
  pointers), then commit both in the same commit as the edit. Details: `scripts/README.md`.