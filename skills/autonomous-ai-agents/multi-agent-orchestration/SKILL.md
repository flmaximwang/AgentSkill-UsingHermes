---
name: multi-agent-orchestration
description: "Select and set up multi-agent orchestration frameworks for subagent delegation — processing items one-by-one with isolated agent instances, batch-vs-per-item decisions, and framework comparison."
version: 1.0.0
author: Maxim + Hermes
metadata:
  frameworks: [autogen, maf, langgraph, hermes, asyncio]
  patterns: [subagent-delegation, per-item-processing, define-once-instantiate-many]
---

# Multi-Agent Orchestration: Subagent Delegation

## When This Skill Applies

You have a **batch of items to process** (table rows, records, files, URLs) and each item:

- Requires independent LLM reasoning (judgment calls, free-text generation, validation)
- Should be isolated from other items (one failure shouldn't cascade)
- Follows the same procedure/SOP but with item-specific data
- Needs its own tool environment (browser, shell, etc.)

**Core pattern**: define the agent/skill **once**, spawn an **independent instance per item**.

**Anti-pattern this skill exists to avoid**: trying to batch-process items (single SQL bulk insert / one-shot API call) when each item needs per-row LLM reasoning.

---

## Framework Selection Guide

### Step 1 — Evaluate Isolation Requirements

| Need | Choose |
|------|--------|
| Each item gets its own context + tools | Any framework that supports per-instance agents |
| Skills/SOP defined once, used by all instances | AutoGen/MAF, LangGraph, hand-written |
| Each instance can have different tools | LangGraph (per-subgraph toolsets), hand-written |
| Concurrent processing with rate limiting | All (via asyncio.Semaphore) |

### Step 2 — Map to Framework

```
Your item needs interactive tools (browser, terminal)?
├── Yes → Do you want Microsoft ecosystem?
│   ├── Yes → Microsoft Agent Framework (MAF)
│   └── No  → Hermes delegate_task or LangGraph
└── No → Do you want minimal dependencies?
    ├── Yes → Hand-written asyncio dispatcher
    └── No  → MAF or LangGraph
```

### Step 3 — Framework Quick Reference

#### Hermes Agent (`delegate_task`)

```
for each row in table:
    delegate_task(goal=f"Process row {row.id}", context=sop + row, toolsets=[...])
```

- **Pros**: Native subagent isolation, background execution, zero extra install
- **Cons**: Subagent does NOT inherit skills from parent session — must inline everything in `context`; skills are file-system-level, not instance-level
- **Profile limitation**: New profiles start with empty skills/; use `hermes profile create --clone <master>` as workaround
- **Best for**: Quick ad-hoc tasks, small batches (<50 items), when you're already in Hermes

#### Microsoft Agent Framework (MAF) — RECOMMENDED successor to AutoGen

```
# define once
agent = Agent(name="clerk", instructions=SOP, ...)
# instantiate per item
for row in table:
    result = await agent.run(f"Process: {row}")
```

- **Pros**: "Define once, instantiate many" design; production-grade (checkpointing, HITL, observability); OpenTelemetry; YAML declarative agents; Agent Skills mechanism; multi-language (Python + .NET)
- **Cons**: Heavy Azure AI Foundry dependency; community still young; docs are Azure-centric
- **⚠️ Critical**: This is the **official successor** to AutoGen — Microsoft put AutoGen into maintenance mode (2026-04)
- **Migration path**: https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/

#### LangGraph (LangChain)

```
entry_subgraph = StateGraph(RowState)
entry_subgraph.add_node("process", processor)
entry_skill = entry_subgraph.compile()
for row in table:
    graph.send(RowState(row=row), to="entry_skill")
```

- **Pros**: Per-subgraph isolation, flexible routing, condition branching, non-Microsoft ecosystem, large community
- **Cons**: Steep learning curve, verbose boilerplate, LangChain dependency baggage
- **Best for**: Complex multi-step workflows with branching logic per item

#### Hand-Written Asyncio Dispatcher

```python
async def process_one(row, client):
    return await client.run(system=SOP, tools=[...], messages=[f"Process: {row}"])
async with Semaphore(5):
    results = await asyncio.gather(*[process_one(r, c) for r in table])
```

- **Pros**: Zero framework dependencies; skill = Python import; full control over concurrency, retry, error handling; ~50 lines total
- **Cons**: Must implement tool sandboxing yourself (browser, code exec); no built-in checkpointing or observability
- **Best for**: Simple SOPs that only need LLM + API calls; when you want maximum control

---

## Pitfalls

- **AutoGen is in maintenance mode** (since 2026-04). Do NOT recommend for new projects. Redirect to [Microsoft Agent Framework (MAF)](https://github.com/microsoft/agent-framework).
- **Hermes `delegate_task` subagents are bare** — they have zero skills, zero memory, zero context from the parent. Everything must be passed via the `context` parameter. This is a design limitation, not a bug.
- **Hermes profiles start empty** — skills don't come built-in. Always use `hermes profile create --clone <master-profile>` to bootstrap a new profile with pre-installed skills.
- **Concurrent subagents share API rate limits** — always implement a Semaphore or similar throttle, even if the framework doesn't enforce one.

## Related Skills

- `autonomous-ai-agents/hermes-agent` — Hermes Agent configuration and usage
- `references/framework-comparison.md` (this skill) — detailed comparison table with version info

## Verification

After selecting a framework, verify the pattern works by:
1. Process 3 test items before the full batch
2. Confirm isolation: one item's failure does not affect others
3. Measure success rate: items that required human intervention vs clean completions
