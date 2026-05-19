from __future__ import annotations

import argparse
import json
import time
from typing import Protocol

import httpx
from websocket import create_connection


class TraceSource(Protocol):
    def fetch_trace(self, args: argparse.Namespace) -> dict: ...


class NativeEvalTraceSource:
    def fetch_trace(self, args: argparse.Namespace) -> dict:
        from fred_deepeval_cli.eval_client import build_eval_payload, build_headers

        with httpx.Client(
            timeout=httpx.Timeout(30.0, connect=5.0, read=None)
        ) as http_client:
            response = http_client.post(
                f"{args.base_url.rstrip('/')}/agents/evaluate",
                json=build_eval_payload(args),
                headers=build_headers(args),
            )
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise RuntimeError("Evaluate response must be a JSON object.")
            return result


def _agentic_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _ws_url(base_url: str) -> str:
    if base_url.startswith("https://"):
        return base_url.replace("https://", "wss://", 1) + "/chatbot/query/ws"
    if base_url.startswith("http://"):
        return base_url.replace("http://", "ws://", 1) + "/chatbot/query/ws"
    raise RuntimeError(f"Unsupported base URL: {base_url}")


def _extract_text_from_parts(parts: list[dict]) -> str:
    texts: list[str] = []
    for part in parts or []:
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            texts.append(part["text"])
    return "\n".join(t for t in texts if t).strip()


def _extract_tool_call(message: dict) -> tuple[str | None, dict]:
    for part in message.get("parts", []) or []:
        if part.get("type") == "tool_call":
            name = part.get("name")
            args = part.get("args", {})
            return (
                name if isinstance(name, str) else None,
                args if isinstance(args, dict) else {},
            )
    return None, {}


def _extract_tool_result(message: dict) -> str:
    texts: list[str] = []
    for part in message.get("parts", []) or []:
        if part.get("type") == "tool_result":
            content = part.get("content")
            if isinstance(content, str):
                texts.append(content)
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            texts.append(part["text"])
    return "\n".join(t for t in texts if t).strip()


def _history_to_evaltrace(
    *,
    session_id: str,
    agent_id: str,
    user_input: str,
    history: list[dict],
    latency_ms: int,
) -> dict:
    output = None
    error = None
    steps: list[dict] = []
    tools_called: list[str] = []
    retrieval_context: list[str] = []

    for msg in history:
        role = msg.get("role")
        channel = msg.get("channel")

        if role == "assistant" and channel == "tool_call":
            tool_name, tool_args = _extract_tool_call(msg)
            if tool_name:
                tools_called.append(tool_name)
                steps.append(
                    {
                        "kind": "tool_call",
                        "tool_name": tool_name,
                        "arguments": tool_args,
                    }
                )

        elif channel == "tool_result":
            content = _extract_tool_result(msg)
            steps.append(
                {
                    "kind": "tool_result",
                    "tool_name": msg.get("metadata", {}).get("tool_name"),
                    "content": content,
                    "is_error": False,
                }
            )
            if content:
                retrieval_context.append(content[:1000])

        elif role == "assistant" and channel == "final":
            text = _extract_text_from_parts(msg.get("parts", []))
            if text:
                output = text
                steps.append({"kind": "final", "content": text})

    if output is None:
        error = "No final assistant output found in Prism history."

    return {
        "session_id": session_id,
        "agent_id": agent_id,
        "input": user_input,
        "output": output,
        "error": error,
        "latency_ms": latency_ms,
        "model_name": None,
        "token_usage": None,
        "finish_reason": None,
        "steps": steps,
        "retrieval_context": retrieval_context,
        "tools_called": list(dict.fromkeys(tools_called)),
    }


class PrismAdaptedTraceSource:
    def fetch_trace(self, args: argparse.Namespace) -> dict:
        from fred_deepeval_cli.eval_client import build_headers

        base_url = _agentic_base_url(args.base_url)
        headers = build_headers(args)
        effective_team_id = args.team_id or "personal"
        final_seen = False

        def create_session(client: httpx.Client) -> str:
            session_resp = client.post(
                f"{base_url}/chatbot/session",
                json={
                    "agent_id": args.agent_id,
                    "team_id": effective_team_id,
                    "title": None,
                },
            )
            session_resp.raise_for_status()
            session = session_resp.json()
            session_id = session.get("id")
            if not isinstance(session_id, str) or not session_id:
                raise RuntimeError("Prism session creation returned no session id.")
            return session_id

        def delete_agent_sessions(client: httpx.Client) -> list[str]:
            sessions_resp = client.get(
                f"{base_url}/chatbot/sessions",
                params={"team_id": effective_team_id},
            )
            sessions_resp.raise_for_status()
            sessions = sessions_resp.json()
            if not isinstance(sessions, list):
                raise RuntimeError("Prism sessions response must be a JSON array.")

            deleted_ids: list[str] = []
            for session in sessions:
                if session.get("agent_id") != args.agent_id:
                    continue
                session_id = session.get("id")
                if not isinstance(session_id, str) or not session_id:
                    continue

                delete_resp = client.delete(f"{base_url}/chatbot/session/{session_id}")
                delete_resp.raise_for_status()
                deleted_ids.append(session_id)

            return deleted_ids

        with httpx.Client(
            timeout=httpx.Timeout(30.0, connect=5.0, read=120.0),
            headers=headers,
        ) as client:
            try:
                session_id = create_session(client)
            except httpx.HTTPStatusError as exc:
                deleted_ids: list[str] = []
                try:
                    deleted_ids = delete_agent_sessions(client)
                except Exception as delete_exc:
                    raise RuntimeError(
                        "Prism session creation failed, and cleanup of existing agent "
                        f"sessions also failed.\n"
                        f"Create error: {exc}\n"
                        f"Cleanup error: {delete_exc}"
                    ) from exc

                try:
                    session_id = create_session(client)
                except httpx.HTTPStatusError as retry_exc:
                    raise RuntimeError(
                        "Prism session creation failed even after deleting existing "
                        f"sessions for agent {args.agent_id!r} in team "
                        f"{effective_team_id!r}.\n"
                        f"Deleted sessions: {deleted_ids or 'none'}\n"
                        f"Retry error: {retry_exc}"
                    ) from retry_exc

            prefs = {
                "agent_id": args.agent_id,
                "searchPolicy": args.search_policy or "semantic",
                "team_id": effective_team_id,
            }

            prefs_resp = client.put(
                f"{base_url}/chatbot/session/{session_id}/preferences",
                json={"preferences": prefs},
            )
            prefs_resp.raise_for_status()

        ws_token = args.access_token or "dev-token"
        ws_headers = [f"Authorization: Bearer {ws_token}"]

        started = time.perf_counter()
        ws = create_connection(_ws_url(base_url), header=ws_headers)
        try:
            ws.send(
                json.dumps(
                    {
                        "type": "ask",
                        "session_id": session_id,
                        "agent_id": args.agent_id,
                        "message": args.input,
                        "runtime_context": {
                            "search_policy": args.search_policy or "semantic",
                        },
                    }
                )
            )

            while True:
                raw = ws.recv()
                if not raw:
                    continue
                event = json.loads(raw)
                event_type = event.get("type")
                if event_type == "final":
                    final_seen = True
                    break
                if event_type == "error":
                    break

            latency_ms = int((time.perf_counter() - started) * 1000)
        finally:
            ws.close()

        with httpx.Client(
            timeout=httpx.Timeout(30.0, connect=5.0, read=120.0),
            headers=headers,
        ) as client:
            history_resp = client.get(
                f"{base_url}/chatbot/session/{session_id}/history",
                params={"text_limit": 12000, "text_offset": 0},
            )
            history_resp.raise_for_status()
            history = history_resp.json()

        trace = _history_to_evaltrace(
            session_id=session_id,
            agent_id=args.agent_id,
            user_input=args.input,
            history=history,
            latency_ms=latency_ms,
        )

        if not final_seen and trace.get("error") is None:
            trace["error"] = "Prism run ended without a final event."

        return trace
