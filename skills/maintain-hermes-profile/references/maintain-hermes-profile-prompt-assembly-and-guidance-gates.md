# Prompt assembly and the model-gated guidance blocks

Answers "is this rule Hermes built-in or mine?", "where does my `SOUL.md` get injected?", "how do I turn a
built-in block off, or keep it for some models only?". The system prompt is assembled in **layers**, each
with its own owner, file and switch — so get the layer first. A behaviour question answered at the wrong
layer produces a fix that moves nothing.

## The layers, in assembly order

| Layer | File / source | Owner | Lever |
|---|---|---|---|
| Identity / persona ("slot #1") | `<home>/SOUL.md` | user | the user edits it |
| Memory + user profile | `<home>/memories/*.md` | mixed | `memory` tool |
| Skill index (one description line per installed skill) | `<home>/skills/**/SKILL.md` frontmatter | mixed | install / disable skills |
| Context files | `AGENTS.md`, `.cursorrules`, … | repo / user | edit the file |
| Tool schemas, platform hints, steer note | code | built-in | tool config |
| `# Execution discipline`, tool-use enforcement, Google operational, async handoff | code | built-in | the model gates below |

Measured on a git install (`~/.hermes/hermes-agent`): the block at the very top of the system prompt is
`SOUL.md` verbatim, and `# Execution discipline` is appended much further down — after the tool block.
**Nothing in the code ranks the layers**: SOUL's rules simply read earlier. So "my rule lost to the built-in
one" is not decided by file order, and the durable fixes are an explicit line in `SOUL.md` or turning that
block's gate off.

## The gates (`agent/system_prompt.py`)

`_model_gate(setting, model, default_models)` resolves a config gate:

- `True` / `False` → forced on / off.
- a string in the gate words (`auto`, `true`-ish, `false`-ish) → resolved as such.
- a **list** → case-insensitive substring match against the model name (`["deepseek", "kimi"]`).
- anything else (`"auto"`, the default) → substring match against the block's own default list.

| Config key (default) | Block it controls | Default model list |
|---|---|---|
| `agent.execution_guidance` (`auto`) | `OPENAI_MODEL_EXECUTION_GUIDANCE` = `# Execution discipline`: `<tool_persistence>`, `<mandatory_tool_use>`, `<act_dont_ask>`, `<prerequisite_checks>`, `<verification>`, `<external_state_verification>`, `<literal_preservation>`, `<missing_context>` | gpt, codex, grok, deepseek, kimi, qwen, glm, minimax, mimo, mistral, muse |
| `agent.tool_use_enforcement` (`auto`) | `TOOL_USE_ENFORCEMENT_GUIDANCE`, plus `GOOGLE_MODEL_OPERATIONAL_GUIDANCE` for gemini/gemma | gpt, codex, gemini, gemma, grok, glm, qwen, deepseek, muse |

Consequences worth stating before proposing any change:

- `hermes config set agent.execution_guidance false` drops the whole discipline block; a list narrows it to
  the named families. It is a **per-model** gate, so first establish that the session's model is gated in
  at all — if it is not, the block is not the cause of the behaviour.
- The switch is read at agent init: it takes effect in a **new** session, not mid-conversation.
- The block is one unit — "turn off the part I dislike" is not a supported granularity, and the list-valued
  form is the only narrowing lever.

## Probe it (re-runnable; use the install's own venv python)

```bash
PY=$(ls -d ~/.hermes/installs/*/environments/*/venv/bin/python | head -1)   # or the checkout's venv
cd <hermes checkout> && $PY - <<'PY'
import sys; sys.path.insert(0, '.')
from agent.system_prompt import _model_gate
from agent.prompt_builder import EXECUTION_GUIDANCE_MODELS as M, execution_guidance_text as T
model = "<the session's model>"
print("gated in:", _model_gate("auto", model, M), "| matched:", [p for p in M if p in model.lower()])
t = T()
print("block chars:", len(t), "| present:", [b for b in ("tool_persistence", "missing_context") if b in t])
PY
```

- Use the install's venv python, not the system `python3`: the tree uses PEP-604 annotations at import time
  (`str | object`) and a 3.9 interpreter dies with `TypeError: unsupported operand type(s) for |` before
  printing anything.
- Line numbers drift between versions. Re-find the block with
  `grep -n "<tool_persistence>\|<missing_context>" agent/prompt_builder.py` and the gate call sites with
  `grep -n "_model_gate\|GUIDANCE_MODELS" agent/system_prompt.py agent/prompt_builder.py`, and cite the
  constant/function name rather than a bare line number.
- The same grep answers "which layer wrote this sentence": a rule present in the guidance text is built-in no
  matter how much it reads like the user's own preference, and a rule found only in `<home>/SOUL.md` is
  theirs.

## Answer shape for "is this built-in?"

Give three things and then the consequence: the **layer** (user-owned file vs built-in block), the **file**
it lives in, and the **gate key with its current value** (`hermes config get agent.execution_guidance`).
Then: user-owned → the user edits it (hand them the path); built-in → the gate is the lever, and if the goal
is only "my rule should win", an explicit line in `SOUL.md` is the honest answer rather than an implied
re-rank. Do not claim the file order decides priority, and do not reconstruct the answer from memory of the
prompt — read the files and run the probe.
