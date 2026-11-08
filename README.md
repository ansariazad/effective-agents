# Effective Agents

**effective-agents** is a production-ready implementation of every agentic workflow pattern from Anthropic's ["Building Effective Agents"](https://www.anthropic.com/engineering/building-effective-agents) engineering guide — Prompt Chaining, Routing, Parallelization, Orchestrator-Workers, Evaluator-Optimizer, and a live MCP STDIO client that calls real tools over JSON-RPC 2.0.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Anthropic](https://img.shields.io/badge/Pattern-Anthropic_Agents-blueviolet)
![MCP](https://img.shields.io/badge/MCP-STDIO_Client-orange)
![Ollama](https://img.shields.io/badge/Ollama-llama3.2-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![Evals](https://img.shields.io/badge/Evals-100%25_Pass-brightgreen)

---

## What is this?

A single-file reference implementation of all 6 agentic workflow patterns described in Anthropic's guide, plus a live MCP STDIO client that connects to `04_mcp_server.py` over subprocess stdin/stdout using JSON-RPC 2.0. Every pattern includes real callable functions — not pseudocode.

Key design principles followed from the Anthropic guide:
- **ACI poka-yoke guardrails** — file access tools enforce relative paths only (Appendix 2 of the guide)
- **Minimal footprint** — no LangChain, no agent frameworks; pure Python + stdlib
- **Offline-first** — deterministic fallback for every LLM call; Ollama enhances but never blocks

---

## Key Features

- **Prompt Chaining** — `workflow_chain()`: sequential plan → draft → critique → polish with explicit gate checks between steps
- **Routing** — `workflow_routing()`: classifies query intent and dispatches to specialist handlers; LLM-enhanced via Ollama when available
- **Parallelization** — `workflow_parallelization()`: fans out 3 independent guardrail checks via `ThreadPoolExecutor`, aggregates votes with consensus logic
- **Orchestrator-Workers** — `workflow_orchestrator()`: central orchestrator dynamically plans subtasks, dispatches workers, synthesizes results
- **Evaluator-Optimizer** — `workflow_evaluator()`: iterative generate → critique → refine loop until quality rubric is satisfied
- **MCP STDIO Client** — `MCPStdioClient` spawns `04_mcp_server.py` as a subprocess, communicates via JSON-RPC 2.0 on stdin/stdout — calls `get_alerts`, `get_forecast`, `search_ai_playbooks` live
- **Ollama integration** — `call_ollama_or_fallback()` calls `http://localhost:11434/api/generate`; silently falls back offline

---

## Workflow Patterns

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTIC WORKFLOW PATTERNS                     │
├─────────────────┬───────────────────────────────────────────────┤
│ Pattern         │ Description                                    │
├─────────────────┼───────────────────────────────────────────────┤
│ Chaining        │ Step 1 → gate ✓ → Step 2 → gate ✓ → Step 3  │
│ Routing         │ Classify(Q) → handler_A | handler_B | ...     │
│ Parallelization │ [Task1, Task2, Task3] → ThreadPool → Merge    │
│ Orchestrator    │ Plan → [Worker1, Worker2, ...] → Synthesize   │
│ Evaluator-Opt.  │ Generate → Critique → Refine → (loop)         │
│ MCP STDIO       │ Agent ↔ JSON-RPC 2.0 ↔ MCP Server subprocess │
└─────────────────┴───────────────────────────────────────────────┘
```

### MCP STDIO Architecture

```
 effective-agents (parent process)
         │
         │  subprocess.Popen(04_mcp_server.py)
         │
         ▼
 ┌──────────────────────────────────┐
 │  MCPStdioClient                  │
 │                                  │
 │  stdin  ──→  JSON-RPC Request   │
 │  stdout ←──  JSON-RPC Response  │
 │  stderr       (logs only)        │
 └──────────────────────────────────┘
         │
         ▼
   04_mcp_server.py
   Tools: get_alerts | get_forecast | search_ai_playbooks
```

---

## Prerequisites

**Python 3.11+** required. Core patterns run with zero external dependencies.

### macOS
```bash
brew install python@3.11

# Optional: Ollama for real LLM routing
brew install ollama
ollama serve &
ollama pull llama3.2
```

### Windows / Linux
```bash
pip install httpx   # only needed for Ollama HTTP calls
```

> [!NOTE]
> The MCP STDIO client requires `04_mcp_server.py` from the [mcp-server](https://github.com/ansariazad/mcp-server) repo to be in the same directory for the `search_ai_playbooks` tool.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/ansariazad/effective-agents.git
cd effective-agents

# 2. Run all 7 workflows (offline mode)
python3 03_effective_agents.py

# 3. Run with Ollama LLM for enhanced routing
OLLAMA_MODEL=llama3.2 python3 03_effective_agents.py
```

---

## Usage

### Run all workflows
```bash
python3 03_effective_agents.py
```

**Expected output:**
```
=== 1. Prompt Chaining ===
[Chain] Step 1/3: Planning...  ✓
[Chain] Step 2/3: Drafting...  ✓
[Chain] Step 3/3: Polishing... ✓
Result: "Comprehensive AI Engineering roadmap: ..."

=== 2. Routing ===
[Router] Classified: code_review → specialist handler
Result: "Code quality assessment: ..."

=== 3. Parallelization ===
[Parallel] Running 3 guardrails concurrently...
[Vote] 3/3 passed — SAFE

=== 4. Orchestrator-Workers ===
[Orch] Planned 3 subtasks → dispatched
[Workers] Completed: data_analysis, summarization, formatting
[Orch] Synthesized final report

=== 5. Evaluator-Optimizer ===
[Iter 1] Quality score: 0.62 — refining...
[Iter 2] Quality score: 0.89 — PASS ✓

=== 6. Autonomous Agent Loop ===
[Agent] Tool call: read_file("data.txt") → content
[Agent] Tool call: analyze(...) → insights
[Agent] STOP — goal achieved

=== 7. MCP STDIO Integration ===
[MCP] Tools discovered: get_alerts, get_forecast, search_ai_playbooks
[MCP] get_alerts(CA) → "No active alerts for California"
[MCP] get_forecast(37.77, -122.42) → "Tuesday: Partly cloudy, 68°F"
[MCP] search_ai_playbooks(...) → "CRAG improves recall by..."
```

### With Ollama
```bash
OLLAMA_MODEL=llama3.2 python3 03_effective_agents.py
# [Router] LLM classified intent: "technical_question" → specialist
```

---

## ACI Guardrail

Following Anthropic Appendix 2, the agent's file tool enforces relative paths:

```python
# In ACITool.read_file():
if Path(path).is_absolute():
    raise ValueError("ACI guardrail: absolute paths not allowed. Use relative paths.")
```

This is verified by `L1_Agent_ACI_Relative_Path_Guardrail` in the eval suite.

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OLLAMA_MODEL` | Local Ollama model for LLM-enhanced routing | `llama3.2` |

```bash
cp .env.example .env
# Edit .env to set OLLAMA_MODEL
```

---

## File Structure

```
effective-agents/
├── 03_effective_agents.py  # All 6 patterns + MCP STDIO client
├── setup_and_run_mac.sh    # macOS one-shot setup
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
├── .gitignore
└── README.md
```

---

## Eval Results

Tested by [`ai-evals-suite`](https://github.com/ansariazad/ai-evals-suite):

| Assertion | Result |
|-----------|--------|
| `L1_Agent_ACI_Relative_Path_Guardrail` | ✅ PASS |
| `L1_MCP_STDIO_End_To_End_Tool_Invocation` | ✅ PASS — all 3 tools |

---

## References

- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) — Erik Schluntz & Barry Zhang (Anthropic)
- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/) — Anthropic
- [ACI: Agent-Computer Interfaces](https://arxiv.org/abs/2411.15671) — Wang et al., 2024
- [ReAct: Synergizing Reasoning and Acting](https://arxiv.org/abs/2210.03629) — Yao et al., 2022

---

## Contributing

Pull requests welcome! Suggested additions: human-in-the-loop approval step, persistent agent memory, tool use with real web search.

---

## License

MIT © 2026

---

## Author

**Azad Ansari** — [GitHub](https://github.com/ansariazad) | [AutoShorts](https://github.com/ansariazad/AutoShorts)
