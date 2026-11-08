#!/usr/bin/env python3
"""
03_effective_agents.py — Composable Agentic Workflows & Autonomous Agents
=========================================================================
Reference Source:
  - Erik Schluntz & Barry Zhang (Anthropic Engineering),
    "Building effective AI agents"
    https://www.anthropic.com/engineering/building-effective-agents

Implemented Architectural Patterns:
  1. Building Block — The Augmented LLM:
     LLM enhanced with retrieval, poka-yoked ACI tools (enforcing absolute file paths
     as recommended in Appendix 2 of the Anthropic guide), and structured memory.
  2. Workflow 1 — Prompt Chaining:
     Sequential decomposition with an explicit programmatic gate check between steps.
  3. Workflow 2 — Routing:
     Classifies input intent and dispatches to specialized prompts/handlers.
  4. Workflow 3 — Parallelization (Sectioning & Voting):
     Runs independent guardrails/evaluations concurrently via `ThreadPoolExecutor` and aggregates votes.
  5. Workflow 4 — Orchestrator-Workers:
     Central orchestrator dynamically plans subtasks, dispatches workers, and synthesizes results.
  6. Workflow 5 — Evaluator-Optimizer:
     Iterative generation and rubric-based critique loop until quality criteria are met.
  7. Autonomous Agent Loop:
     Open-ended tool-use loop grounded in environmental feedback with stopping conditions.

Usage on macOS:
  python3 03_effective_agents.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


def call_ollama_or_fallback(prompt: str, fallback: str) -> str:
    """
    Calls local Ollama on macOS (OLLAMA_MODEL env var) when available.
    Falls back to the deterministic offline `fallback` string otherwise.
    Keeps all agentic workflows runnable without any API key or LLM service.
    """
    ollama_model = os.environ.get("OLLAMA_MODEL", "")
    if ollama_model:
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=json.dumps({"model": ollama_model, "prompt": prompt, "stream": False}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode())
                llm_response = str(payload.get("response", "")).strip()
                if llm_response:
                    return llm_response
        except Exception:
            pass
    return fallback


@dataclass
class ToolSpec:
    """
    Clear, poka-yoked tool specification (Anthropic Appendix 2: "Prompt engineering your tools").
    Includes description, example usage, edge cases, and input validation.
    """
    name: str
    description: str
    example_usage: str
    fn: Callable[[Dict[str, Any]], str]


def tool_read_local_file(args: Dict[str, Any]) -> str:
    """
    Poka-yoked file inspection tool: requires an ABSOLUTE filepath so the agent never
    makes relative-path mistakes after changing directories (Anthropic SWE-bench insight).
    """
    raw_path = str(args.get("absolute_path", ""))
    if not raw_path.startswith("/"):
        return (
            "ACI_POKA_YOKE_ERROR: `absolute_path` must start with '/'. "
            "Relative paths are rejected to prevent working-directory drift."
        )
    p = Path(raw_path)
    if not p.exists():
        return f"FILE_NOT_FOUND: {raw_path}"
    text = p.read_text(encoding="utf-8")[:600]
    return f"READ_OK ({len(text)} chars preview from {p.name}): {text.splitlines()[0]}"


def tool_query_architecture_notes(args: Dict[str, Any]) -> str:
    """Retrieves verified architectural guidance from the 5 reference sources."""
    topic = str(args.get("topic", "")).lower()
    notes = {
        "gpt": "Decoder-only Transformer using masked causal self-attention (https://www.youtube.com/watch?v=kCc8FmEb1nY).",
        "rag": "Multi-query RRF fusion + Corrective RAG document grading (https://www.youtube.com/watch?v=sVcwVQRHIc8).",
        "agents": "Start simple; use composable workflows before full autonomy (https://www.anthropic.com/engineering/building-effective-agents).",
        "mcp": "Expose typed tools over STDIO; log strictly to stderr (https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server).",
        "evals": "3 levels: Unit Assertions, Trace + Human/LLM Judge, and A/B Testing (https://hamel.dev/blog/posts/evals/index.html).",
    }
    for key, val in notes.items():
        if key in topic:
            return val
    return "Available topics: gpt, rag, agents, mcp, evals."


class AugmentedLLM:
    """Foundational building block enhanced with retrieval, tools, and memory."""

    def __init__(self) -> None:
        self.memory: List[str] = []
        self.tools: Dict[str, ToolSpec] = {}

    def register_tool(self, spec: ToolSpec) -> None:
        self.tools[spec.name] = spec

    def call_tool(self, name: str, args: Dict[str, Any]) -> str:
        if name not in self.tools:
            return f"ERROR: Unknown tool '{name}'. Available: {list(self.tools.keys())}"
        result = self.tools[name].fn(args)
        self.memory.append(f"tool:{name}({args}) -> {result}")
        return result


def workflow_prompt_chaining(task_topic: str) -> Dict[str, Any]:
    """Workflow 1: Prompt Chaining with programmatic gate check."""
    outline = [
        f"1. Problem Statement & Simplicity Baseline for {task_topic}",
        "2. Agent-Computer Interface (ACI) & Tool Poka-Yoking",
        "3. Verification & Evaluation Harness (Level 1-3 Evals)",
    ]

    gate_passed = (
        len(outline) >= 3
        and any("ACI" in item for item in outline)
        and any("Evaluation" in item for item in outline)
    )
    if not gate_passed:
        raise ValueError("Prompt Chaining Gate Failed: Outline missing required sections.")

    specification = (
        f"Validated Technical Spec ({len(outline)} sections): "
        + " | ".join(outline)
        + " [Ref: https://www.anthropic.com/engineering/building-effective-agents]"
    )
    return {"outline": outline, "gate_passed": gate_passed, "specification": specification}


def workflow_routing(user_query: str) -> Dict[str, str]:
    """Workflow 2: Routing by intent and complexity tier. Uses Ollama LLM when available."""
    q = user_query.lower()
    if any(k in q for k in ["refund", "billing", "invoice", "cancel"]):
        category = "billing_and_refund_workflow"
        model_tier = "claude-haiku-4-5 (fast structured action path)"
        deterministic_response = "Routed to transactional refund workflow with order verification gate."
    elif any(k in q for k in ["architecture", "swe-bench", "debug", "agent", "mcp"]):
        category = "deep_engineering_specialist"
        model_tier = "claude-sonnet-4-5 (complex reasoning & code synthesis)"
        deterministic_response = "Routed to engineering specialist with ACI codebase tools enabled."
    else:
        category = "general_faq_responder"
        model_tier = "claude-haiku-4-5 (low-latency FAQ tier)"
        deterministic_response = "Routed to concise FAQ responder."

    response = call_ollama_or_fallback(
        f"Classify the following user query into a routing category and write a one-sentence routing decision.\nQuery: {user_query}\nCategory: {category}\nDecision:",
        fallback=deterministic_response,
    )

    return {"query": user_query, "category": category, "model_tier": model_tier, "response": response}


def workflow_parallelization(code_snippet: str) -> Dict[str, Any]:
    """Workflow 3: Parallelization (Sectioning + Consensus Voting)."""
    reviewers: List[Tuple[str, Callable[[str], Tuple[bool, str]]]] = [
        (
            "stdio_safety_reviewer",
            lambda code: (
                "print(" not in code,
                "PASS: No stdout print() pollution" if "print(" not in code else "FAIL: Found print() in STDIO server",
            ),
        ),
        (
            "filepath_poka_yoke_reviewer",
            lambda code: (
                "startswith(" in code or "Path(" in code,
                "PASS: Uses explicit path handling",
            ),
        ),
        (
            "error_handling_reviewer",
            lambda code: (
                "try:" in code or "except" in code or "if not" in code,
                "PASS: Includes defensive error guards",
            ),
        ),
    ]

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            name: pool.submit(check_fn, code_snippet)
            for name, check_fn in reviewers
        }
        votes = {name: fut.result() for name, fut in futures.items()}

    approvals = sum(1 for passed, _ in votes.values() if passed)
    return {
        "total_reviewers": len(reviewers),
        "approvals": approvals,
        "consensus_approved": approvals == len(reviewers),
        "details": {k: {"passed": v[0], "note": v[1]} for k, v in votes.items()},
    }


def workflow_orchestrator_workers(complex_goal: str) -> Dict[str, Any]:
    """Workflow 4: Orchestrator-Workers dynamic task delegation."""
    planned_subtasks = [
        {"worker": "model_worker", "target": "01_apna_gpt.py", "focus": "Causal self-attention & MPS support"},
        {"worker": "retrieval_worker", "target": "02_rag_from_scratch.py", "focus": "RRF multi-query fusion & CRAG grading"},
        {"worker": "protocol_worker", "target": "04_mcp_server.py", "focus": "STDIO tool registration & stderr logging"},
        {"worker": "eval_worker", "target": "05_ai_evals_suite.py", "focus": "3-level assertions, traces, and judge alignment"},
    ]

    def run_worker(task: Dict[str, str]) -> str:
        return f"[{task['worker']}] Completed {task['target']} ({task['focus']})"

    with ThreadPoolExecutor(max_workers=4) as pool:
        worker_outputs = list(pool.map(run_worker, planned_subtasks))

    return {
        "goal": complex_goal,
        "subtasks_dispatched": len(planned_subtasks),
        "worker_reports": worker_outputs,
    }


def workflow_evaluator_optimizer(initial_draft: str, max_rounds: int = 3) -> Dict[str, Any]:
    """Workflow 5: Evaluator-Optimizer iterative critique loop."""
    current = initial_draft
    history: List[Dict[str, Any]] = []

    for round_idx in range(1, max_rounds + 1):
        missing: List[str] = []
        if "Args:" not in current:
            missing.append("Add explicit Args parameter documentation")
        if "absolute" not in current.lower():
            missing.append("Specify poka-yoke requirement: filepath must be an absolute path")
        if "https://" not in current:
            missing.append("Include canonical reference URL")

        passed = len(missing) == 0
        history.append({"round": round_idx, "passed": passed, "feedback": missing, "text": current})
        if passed:
            break

        if "Args:" not in current:
            current += "\nArgs:\n  absolute_path: Full path starting with '/' (e.g., '/Users/you/project/file.py')."
        if "https://" not in current:
            current += "\nReference: https://www.anthropic.com/engineering/building-effective-agents"

    return {"rounds_taken": len(history), "final_passed": history[-1]["passed"], "final_text": current, "history": history}


def run_autonomous_agent(goal: str, target_file: str, max_steps: int = 4) -> Dict[str, Any]:
    """Autonomous tool-using agent loop with ACI feedback recovery."""
    llm = AugmentedLLM()
    llm.register_tool(
        ToolSpec(
            name="read_local_file",
            description="Reads the header of a local file. Requires an absolute path starting with '/'.",
            example_usage='read_local_file({"absolute_path": "/Users/mac/01_apna_gpt.py"})',
            fn=tool_read_local_file,
        )
    )
    llm.register_tool(
        ToolSpec(
            name="query_architecture_notes",
            description="Queries verified reference notes for gpt, rag, agents, mcp, or evals.",
            example_usage='query_architecture_notes({"topic": "agents"})',
            fn=tool_query_architecture_notes,
        )
    )

    trace: List[Dict[str, str]] = []
    resolved_path = str(Path(target_file).resolve())

    for step in range(1, max_steps + 1):
        if step == 1:
            obs = llm.call_tool("read_local_file", {"absolute_path": Path(target_file).name})
            trace.append({"step": str(step), "action": f"read_local_file(relative='{Path(target_file).name}')", "observation": obs})
        elif step == 2:
            obs = llm.call_tool("read_local_file", {"absolute_path": resolved_path})
            trace.append({"step": str(step), "action": f"read_local_file(absolute='{resolved_path}')", "observation": obs})
        elif step == 3:
            obs = llm.call_tool("query_architecture_notes", {"topic": "agents"})
            trace.append({"step": str(step), "action": "query_architecture_notes(topic='agents')", "observation": obs})
            break

    return {"goal": goal, "steps_executed": len(trace), "trace": trace}


# ===========================================================================
# MCP STDIO Client — Spawns 04_mcp_server.py and invokes tools over JSON-RPC 2.0
# ===========================================================================
class MCPStdioClient:
    """
    Spawns an MCP server as a subprocess (STDIO transport) and communicates
    via JSON-RPC 2.0 on stdin/stdout, exactly matching the MCP STDIO spec
    (https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server).
    """

    def __init__(self, server_script: str) -> None:
        self.server_script = str(Path(server_script).resolve())
        self._proc: subprocess.Popen[str] | None = None
        self._req_id = 0

    def start(self) -> None:
        """Launch the MCP server subprocess over STDIO."""
        python = str(Path(sys.executable).resolve())
        self._proc = subprocess.Popen(
            [python, self.server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(self.server_script).parent),
        )

    def _send_request(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request and read the response."""
        assert self._proc is not None and self._proc.stdin is not None and self._proc.stdout is not None
        self._req_id += 1
        request: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": method,
        }
        if params is not None:
            request["params"] = params
        self._proc.stdin.write(json.dumps(request) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline().strip()
        if not line:
            return {"error": "Empty response from MCP server"}
        return json.loads(line)

    def initialize(self) -> Dict[str, Any]:
        """Send MCP initialize handshake."""
        return self._send_request("initialize", {
            "protocolVersion": "2026-07-28",
            "clientInfo": {"name": "effective-agents-client", "version": "1.0.0"},
            "capabilities": {},
        })

    def list_tools(self) -> Dict[str, Any]:
        """Request the server's tool catalog via tools/list."""
        return self._send_request("tools/list")

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a registered MCP tool via tools/call."""
        return self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

    def stop(self) -> str:
        """Terminate the subprocess and return any stderr output."""
        if self._proc is None:
            return ""
        self._proc.stdin.close() if self._proc.stdin else None
        stderr_out = ""
        try:
            self._proc.terminate()
            _, stderr_out = self._proc.communicate(timeout=5)
        except Exception:
            self._proc.kill()
        return stderr_out or ""


def workflow_mcp_stdio_integration() -> Dict[str, Any]:
    """
    Spawns 04_mcp_server.py over STDIO and invokes all 3 MCP tools end-to-end:
      1. get_alerts("CA")
      2. get_forecast(37.7749, -122.4194)
      3. search_ai_playbooks("How does CRAG work?")

    This demonstrates the Anthropic-recommended pattern of an Augmented LLM
    connecting to external tool servers via the Model Context Protocol.
    """
    server_path = str(Path(__file__).parent / "04_mcp_server.py")
    client = MCPStdioClient(server_path)
    results: Dict[str, Any] = {"tools_available": [], "tool_results": {}, "server_stderr": ""}

    try:
        client.start()
        init_resp = client.initialize()
        results["init_response"] = init_resp

        tools_resp = client.list_tools()
        tool_schemas = tools_resp.get("result", {}).get("tools", [])
        results["tools_available"] = [t.get("name", "unknown") for t in tool_schemas]

        # Invoke all 3 tools
        alerts_resp = client.call_tool("get_alerts", {"state": "CA"})
        results["tool_results"]["get_alerts"] = alerts_resp.get("result", alerts_resp)

        forecast_resp = client.call_tool("get_forecast", {"latitude": 37.7749, "longitude": -122.4194})
        results["tool_results"]["get_forecast"] = forecast_resp.get("result", forecast_resp)

        playbooks_resp = client.call_tool("search_ai_playbooks", {"query": "How does CRAG work?"})
        results["tool_results"]["search_ai_playbooks"] = playbooks_resp.get("result", playbooks_resp)

    except Exception as exc:
        results["error"] = str(exc)
    finally:
        results["server_stderr"] = client.stop()

    return results


def main() -> None:
    print("=" * 72)
    print("EFFECTIVE AI AGENTS — 5 Composable Workflows + Autonomous Agent Loop")
    print("Reference: https://www.anthropic.com/engineering/building-effective-agents")
    print("=" * 72)

    chain_res = workflow_prompt_chaining("Production MCP + RAG Agent")
    print(f"\n[1. Prompt Chaining] Gate Passed: {chain_res['gate_passed']}")
    print(f"    Output: {chain_res['specification']}")

    route_res = workflow_routing("How do I debug an MCP server and SWE-bench coding agent?")
    print(f"\n[2. Routing] Category: {route_res['category']} -> Model: {route_res['model_tier']}")

    sample_code = "import logging\nlogger = logging.getLogger(__name__)\nif not path.startswith('/'): raise ValueError('bad path')"
    par_res = workflow_parallelization(sample_code)
    print(f"\n[3. Parallelization & Voting] Consensus Approved: {par_res['consensus_approved']} ({par_res['approvals']}/{par_res['total_reviewers']} votes)")

    orch_res = workflow_orchestrator_workers("Build full-stack AI suite for macOS")
    print(f"\n[4. Orchestrator-Workers] Dispatched {orch_res['subtasks_dispatched']} workers:")
    for rep in orch_res["worker_reports"]:
        print(f"    - {rep}")

    eval_opt_res = workflow_evaluator_optimizer("Tool `read_local_file`: reads a file from disk.")
    print(f"\n[5. Evaluator-Optimizer] Converged in {eval_opt_res['rounds_taken']} rounds (Passed={eval_opt_res['final_passed']})")

    agent_res = run_autonomous_agent("Inspect local codebase and architecture notes", __file__)
    print(f"\n[6. Autonomous Agent Loop] Completed in {agent_res['steps_executed']} environment steps:")
    for entry in agent_res["trace"]:
        print(f"    Step {entry['step']}: {entry['action']} -> {entry['observation']}")

    mcp_res = workflow_mcp_stdio_integration()
    print(f"\n[7. MCP STDIO Integration] Spawned 04_mcp_server.py over STDIO")
    print(f"    Tools Available : {mcp_res['tools_available']}")
    for tool_name, tool_result in mcp_res.get("tool_results", {}).items():
        result_str = str(tool_result)[:120]
        print(f"    [{tool_name}] -> {result_str}...")
    if mcp_res.get("error"):
        print(f"    Error: {mcp_res['error']}")
    print("=" * 72)


if __name__ == "__main__":
    main()
