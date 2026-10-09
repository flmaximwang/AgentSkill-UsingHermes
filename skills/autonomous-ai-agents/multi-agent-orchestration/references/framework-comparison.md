# Multi-Agent Framework Comparison (Subagent Delegation)

*Last updated: 2026-06-23*
*Source: Conversation about per-item table data processing with subagent delegation*

---

## Status Summary

| Framework | Status | Stars | Notes |
|-----------|--------|-------|-------|
| AutoGen (microsoft/autogen) | ⚠️ **Maintenance mode** | 59.2k | No new features. New projects → MAF |
| Microsoft Agent Framework (microsoft/agent-framework) | ✅ Active | N/A | Official successor to AutoGen |
| LangGraph (LangChain) | ✅ Active | N/A | Graph-based orchestration |
| Hermes Agent (Nous Research) | ✅ Active | N/A | This conversation's host |
| DeepSeek-Reasonix (esengine) | ✅ Active | 24k ⭐ | ❌ Single-agent coding CLI, not orchestration |

---

## Feature Comparison

| Feature | Hermes `delegate_task` | AutoGen | MAF | LangGraph | Hand-written |
|---------|----------------------|---------|-----|-----------|-------------|
| **Skill defined once, used by N instances** | ❌ Subagent doesn't inherit skills | ✅ Agent = skill | ✅ Agent = skill | ✅ Subgraph = skill | ✅ import = skill |
| **Per-item isolation** | ✅ Full subagent isolate | ✅ Per-chat isolate | ✅ Per-instance | ✅ Per-subgraph instance | ✅ Per-asyncio task |
| **Skill sharing across profiles** | ⚠️ `--clone` workaround | ✅ Code = config | ✅ Code = config | ✅ Code = config | ✅ Code = config |
| **Built-in tools (browser, terminal)** | ✅ Full Hermes toolset | ✅ Via extensions | ✅ Via extensions | ✅ Via LangChain tools | ❌ Build yourself |
| **Concurrency control** | Built-in (max 3 children) | Via asyncio | Via asyncio | Via Send API | Via asyncio.Semaphore |
| **Checkpointing / Time-travel** | ❌ | ❌ | ✅ | ✅ (LangGraph Cloud) | ❌ |
| **Human-in-the-loop** | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Observability** | ❌ (logs only) | ❌ | ✅ OpenTelemetry | ✅ LangSmith | ❌ |
| **Multi-language** | Python only | Python + .NET | Python + .NET | Python + JS | Any |
| **Learning curve** | Low (if in Hermes) | Medium | Medium | High | Low |
| **Azure dependency** | None | None | **Heavy** | None | None |

---

## When Each Framework Makes Sense

### Choose Hermes `delegate_task` when:
- You're already inside a Hermes session and need quick subagent delegation
- Each item needs the full Hermes toolset (browser, terminal, file, code execution)
- Items are < 50 and SOP is simple enough to inline in `context`
- You don't mind the limitation that subagents don't inherit skills/memory

### Choose MAF when:
- You're building a production system with durability requirements
- You're already in the Azure ecosystem
- You want OpenTelemetry, checkpointing, and human-in-the-loop
- You need declarative agent definitions (YAML)

### Choose LangGraph when:
- Items have complex branching logic (if-this-then-that routing)
- You want strict state machines per item
- You prefer the LangChain ecosystem
- You need non-Microsoft but production-grade orchestration

### Choose hand-written asyncio when:
- Your SOP is simple (LLM + API calls, no interactive tools)
- You want zero framework dependencies
- You need full control over retry, error handling, and logging
- You want the lightest possible solution (~50 lines)

---

## AutoGen → MAF Migration Reference

AutoGen's maintenance mode announcement: commit `027ecf0` on main branch.
Migration guide: https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/

Key API mapping:

| AutoGen | MAF |
|---------|-----|
| `AssistantAgent(system_message=...)` | `Agent(instructions=...)` |
| `UserProxyAgent` | Orchestration workflows (graph-based) |
| `GroupChat` | Group collaboration (built into orchestration) |
| `autogenstudio` | DevUI (separate tool) |
| `autogen-ext[mcp]` | Built-in MCP support |

---

## Reasonix (esengine/DeepSeek-Reasonix)

**Not suitable for subagent delegation.** Reasonix is a single-agent terminal coding CLI (like Claude Code / Codex CLI), not a multi-agent orchestration framework.

- Architecture: one agent, one conversation, sequential execution
- No subagent spawning mechanism
- No external task dispatch interface
- No multi-agent patterns

If the user mentions Reasonix in this context, explain:
> Reasonix is a coding agent CLI (DeepSeek-native, terminal-based), not a multi-agent framework. It has no subagent delegation, no orchestrator pattern, and no batch dispatch mechanism. It's like Claude Code — one agent, one job at a time.

---

## Hermes Profile Skill Setup

Since new Hermes profiles start with an empty skills/ directory:

```bash
# Create a master template profile with all desired skills
hermes profile create master
# → install skills in master profile

# Clone for new use cases
hermes profile create <new-name> --clone master

# Or export/import for cross-machine distribution
hermes profile export master    # → master.tar.gz
hermes profile import master.tar.gz
```
