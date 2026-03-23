"""Sandbox Runner — executes a Claude agent with intercepted tool calls.

Implements the tool-call loop directly using the Anthropic Python SDK.
Every tool call is routed to mock_tools instead of real systems.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import anthropic

from ..models import AgentAction, AgentDefinition, RunContext, SandboxRun, StateDiff
from .mock_tools import TOOL_REGISTRY, TOOL_SCHEMAS


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SandboxRunner:
    """Runs a Claude agent in a sandboxed environment."""

    def __init__(self, run: SandboxRun):
        self.run = run
        self.client = anthropic.Anthropic()
        self.sequence = 0
        self._enabled_tools: set[str] = {
            t.name for t in run.agent_definition.tools if t.enabled
        }

    def _tool_schemas(self) -> list[dict]:
        return [s for s in TOOL_SCHEMAS if s["name"] in self._enabled_tools]

    def _add_action(
        self,
        action_type: str,
        content: dict,
        duration_ms: int = 0,
        mock_system: str | None = None,
    ) -> AgentAction:
        self.sequence += 1
        action = AgentAction(
            sequence=self.sequence,
            action_type=action_type,
            content=content,
            timestamp=_now(),
            duration_ms=duration_ms,
            mock_system=mock_system,
        )
        self.run.actions.append(action)
        return action

    def _build_system_prompt(self) -> str:
        ctx = self.run.run_context
        parts = [
            f"You are an autonomous agent. Your goal: {self.run.agent_definition.goal}",
            f"User persona: {ctx.user_persona}",
        ]
        if ctx.initial_state:
            parts.append(f"Initial system state: {json.dumps(ctx.initial_state)}")
        parts.append(
            "Use the available tools to accomplish your goal. "
            "When you are done, provide a final summary of what you accomplished."
        )
        return "\n\n".join(parts)

    def _execute_tool(self, name: str, args: dict) -> tuple[dict, list[StateDiff]]:
        fn = TOOL_REGISTRY.get(name)
        if fn is None:
            return {"error": f"Unknown tool: {name}"}, []
        return fn(**args)

    async def run_agent(self) -> AsyncIterator[AgentAction]:
        """Execute the agent loop, yielding each action as it happens."""
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": self.run.agent_definition.goal}
        ]
        system_prompt = self._build_system_prompt()
        tools = self._tool_schemas()

        try:
            for _iteration in range(20):  # hard cap on iterations
                t0 = time.monotonic()
                response = await asyncio.to_thread(
                    self.client.messages.create,
                    model=self.run.agent_definition.model,
                    max_tokens=self.run.agent_definition.max_tokens,
                    temperature=self.run.agent_definition.temperature,
                    system=system_prompt,
                    tools=tools,
                    messages=messages,
                )
                elapsed = int((time.monotonic() - t0) * 1000)

                # Process response content blocks
                tool_use_blocks = []
                for block in response.content:
                    if block.type == "text" and block.text.strip():
                        if response.stop_reason == "end_turn":
                            action = self._add_action(
                                "final_output",
                                {"text": block.text},
                                duration_ms=elapsed,
                            )
                        else:
                            action = self._add_action(
                                "thought",
                                {"text": block.text},
                                duration_ms=elapsed,
                            )
                        yield action
                    elif block.type == "tool_use":
                        tool_use_blocks.append(block)

                # If no tool use, we're done
                if response.stop_reason == "end_turn" or not tool_use_blocks:
                    break

                # Append the full assistant message to conversation
                messages.append({
                    "role": "assistant",
                    "content": [self._block_to_dict(b) for b in response.content],
                })

                # Execute each tool call
                tool_results = []
                for tool_block in tool_use_blocks:
                    tool_name = tool_block.name
                    tool_args = tool_block.input if isinstance(tool_block.input, dict) else {}

                    # Record the tool call
                    call_action = self._add_action(
                        "tool_call",
                        {"tool": tool_name, "arguments": tool_args, "tool_use_id": tool_block.id},
                        mock_system=tool_name.split("_")[0] if "_" in tool_name else tool_name,
                    )
                    yield call_action

                    # Execute against mock
                    t1 = time.monotonic()
                    result, diffs = self._execute_tool(tool_name, tool_args)
                    tool_elapsed = int((time.monotonic() - t1) * 1000)

                    self.run.diffs.extend(diffs)

                    # Record the tool response
                    resp_action = self._add_action(
                        "tool_response",
                        {"tool": tool_name, "result": result},
                        duration_ms=tool_elapsed,
                        mock_system=tool_name.split("_")[0] if "_" in tool_name else tool_name,
                    )
                    yield resp_action

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": json.dumps(result),
                    })

                messages.append({"role": "user", "content": tool_results})

            self.run.status = "complete"

        except Exception as e:
            self.run.status = "failed"
            self.run.error = str(e)
            action = self._add_action("final_output", {"error": str(e)})
            yield action

    @staticmethod
    def _block_to_dict(block: Any) -> dict:
        if block.type == "text":
            return {"type": "text", "text": block.text}
        elif block.type == "tool_use":
            return {
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            }
        return {"type": block.type}
