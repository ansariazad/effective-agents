# 🤖 Effective Agents — Composable Agentic Workflows + MCP STDIO Client

Production-ready agentic workflow patterns from Anthropic's "Building Effective Agents" guide — with live MCP STDIO integration.

## ✨ Features

- **5 Agentic Patterns** — Chain, Parallelization, Routing, Orchestrator-Subagent, Evaluator-Optimizer
- **MCP STDIO Client** — spawns `04_mcp_server.py` as a subprocess, communicates via JSON-RPC 2.0
- **Live tool calls** — Weather alerts, forecast, AI playbook search over STDIO protocol
- **Ollama integration** — LLM-enhanced routing via `llama3.2`, offline fallback always works
- **ACI guardrails** — relative-path-only file access enforcement

## 🔄 Workflow Patterns

| Pattern | Description |
|---------|-------------|
| `workflow_chain()` | Sequential steps: plan → draft → critique → polish |
| `workflow_parallelization()` | Fan-out subtasks, fan-in with consensus |
| `workflow_routing()` | LLM classifies query → specialist handler |
| `workflow_orchestrator()` | Dynamic subagent dispatch with context |
| `workflow_evaluator()` | Iterative self-improvement loop |
| `workflow_mcp_stdio_integration()` | Live MCP tool calls over STDIO |

## 🚀 Quick Start

```bash
pip install torch numpy httpx mcp

# Offline mode
python 03_effective_agents.py

# With Ollama + live MCP tools
OLLAMA_MODEL=llama3.2 python 03_effective_agents.py
```

## 🛠️ MCP STDIO Integration

The agent spawns `04_mcp_server.py` as a subprocess and calls tools via JSON-RPC 2.0:

```
Agent → stdin → MCP Server
Agent ← stdout ← {"content": [{"type": "text", "text": "..."}]}
```

Tools called: `get_alerts`, `get_forecast`, `search_ai_playbooks`

## 🔗 References

- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) — Anthropic
- [MCP Specification](https://spec.modelcontextprotocol.io/) — Anthropic
- [ACI Paper](https://arxiv.org/abs/2411.15671) — Agent-Computer Interfaces

## 📄 License

MIT
