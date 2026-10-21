"""The only door between this platform and a third-party inference provider.

Shape of the integration
------------------------
Every AVP residue module is deterministic. None of them may import this.
``app.processing.intel`` is guarded by ``TestNoModelImports`` in
``backend/tests/test_intel_layer.py``, which fails the build on an ``httpx``
import in six modules. The residue modules therefore receive an already-
enriched payload as an argument, and the router — which is outside that guard —
is what calls this gateway. The deterministic computation happens first and is
never outsourced; only the judgement capability.py calls irreducible is.

What this module will not do
----------------------------
- **It will not raise into a caller on a provider failure.** Every transient
  path returns ``None``. An outage degrades a report to its deterministic form;
  it does not take the intel endpoint down. The architecture is
  deterministic-first, and an exception here would invert that.
- **It will not call a tool that is not on the allowlist.** AIMI publishes 89
  tools. This platform may use eleven of them. The rest either execute arbitrary
  code server-side (``tool_aimi_sandbox_execute``), mutate the provider's own
  infrastructure (``tool_aimi_vpn_rotate``, ``tool_aimi_iron_dome_block_ip``),
  or change policy state (``tool_aimi_set_sovereign_override``). An allowlist is
  the only safe default when the upstream catalogue can grow without notice.
- **It will not send anything the redaction module refuses.** See
  ``app.ai.aimi.redaction``.
- **It will not run unless enabled.** ``AIMI_ENABLED`` defaults to False and no
  environment sets it, so this platform today makes no outbound AIMI call.

Transport
---------
AIMI speaks MCP over SSE: ``GET {base_url}/mcp/sse`` yields a postable session
endpoint, messages are POSTed to it, and replies arrive asynchronously on the
original stream. This module therefore blocks, and is synchronous by design —
the router calls it through ``run_in_threadpool`` so FastAPI's event loop is
never held. The listener is a daemon thread that pushes frames into a list; the
calling thread POSTs and then polls that list against a deadline. The session is
per-call rather than pooled, because these calls are user-facing and infrequent,
and a long-lived SSE reader per replica would be a background task to supervise
and a sticky-session problem.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.ai.aimi.redaction import scrub_outbound
from app.config import settings
from app.monitoring import egress

logger = logging.getLogger(__name__)

#: The egress register entry this gateway is permitted to use. Checked before
#: every call, not once at import: the register is a compliance control, and a
#: control that runs once at startup is one a later config reload can bypass.
EGRESS_DESTINATION_ID = "aimi"

#: AIMI tool names this platform is permitted to invoke, and nothing else.
ALLOWED_TOOLS = frozenset({
    "tool_aimi_get_started",
    "tool_aimi_plan_investigation",
    "tool_aimi_detection_engineer",
    "tool_aimi_ioc_correlate",
    "tool_aimi_shortest_path",
    "tool_aimi_playbook_attack",
    "tool_aimi_playbook_defense",
    "tool_aimi_regulatory_guide",
    "tool_aimi_case_law_search",
    "tool_aimi_typology_match",
    "tool_aimi_web_search_news",
})

#: Tools the provider offers that this platform must never invoke. Kept beside
#: the allowlist so a reviewer widening one is reading the list that explains
#: the refusals, not a separate list they might not find.
REFUSED_TOOLS = frozenset({
    "tool_aimi_sandbox_execute",
    "tool_aimi_vpn_rotate",
    "tool_aimi_set_sovereign_override",
    "tool_aimi_iron_dome_block_ip",
    "tool_aimi_iron_dome_unblock_ip",
    "tool_aimi_pentest_vapt",
    "tool_aimi_engagement_create",
})

_SESSION_ENDPOINT_RE = re.compile(r"/mcp/sse/messages\?session_id=[^\s\"']+")


class AimiNotEnabled(RuntimeError):
    """A caller asked for enrichment with AIMI switched off."""


class AimiToolNotAllowed(PermissionError):
    """A caller asked for a tool that is not on the allowlist."""


@dataclass
class CircuitState:
    """A breaker that opens on consecutive failure and closes after a cooldown.

    Deliberately minimal and deliberately per-process. AIMI calls are
    user-facing and bursty, so a shared breaker would need Redis to be correct
    and would buy little; a per-process breaker stops one unhealthy replica
    from hammering a provider that is already down.
    """

    threshold: int
    cooldown_seconds: int
    consecutive_failures: int = 0
    opened_at: float = 0.0
    calls: int = 0
    failures: int = 0

    @property
    def is_open(self) -> bool:
        if self.consecutive_failures < self.threshold:
            return False
        return (time.monotonic() - self.opened_at) < self.cooldown_seconds

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.calls += 1

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.calls += 1
        self.failures += 1
        if self.consecutive_failures >= self.threshold:
            self.opened_at = time.monotonic()

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "failures": self.failures,
            "consecutive_failures": self.consecutive_failures,
            "state": "open" if self.is_open else "closed",
        }


_state = CircuitState(
    threshold=settings.aimi_circuit_threshold,
    cooldown_seconds=settings.aimi_circuit_cooldown_seconds,
)


def circuit() -> CircuitState:
    """The breaker, for tests and for an admin status endpoint."""
    return _state


def reset_circuit() -> None:
    """Close the breaker. Test affordance, and an operator runbook step."""
    _state.consecutive_failures = 0
    _state.opened_at = 0.0
    _state.calls = 0
    _state.failures = 0


def is_available() -> bool:
    """Whether a call would be attempted, without attempting one."""
    return bool(settings.aimi_enabled) and not _state.is_open


def _headers() -> dict[str, str]:
    return {
        "X-API-Key": settings.aimi_api_key.get_secret_value(),
        "Content-Type": "application/json",
    }


def _open_stream(base_url: str, headers: dict[str, str], seconds: float,
                 frames: list[str], stop: threading.Event) -> threading.Thread:
    """Start a daemon thread draining the SSE stream into ``frames``."""
    def _pump() -> None:
        try:
            with httpx.Client(timeout=seconds) as client:
                with client.stream("GET", f"{base_url}/mcp/sse", headers=headers) as response:
                    if response.status_code != 200:
                        logger.warning(
                            "AIMI SSE stream refused: HTTP %s", response.status_code
                        )
                        return
                    for line in response.iter_lines():
                        if stop.is_set():
                            return
                        if line and line.startswith("data:"):
                            frames.append(line[5:].strip())
        except Exception as exc:  # noqa: BLE001 - reader must never surface
            logger.warning("AIMI SSE reader stopped: %s", exc.__class__.__name__)

    thread = threading.Thread(target=_pump, daemon=True, name="aimi-sse")
    thread.start()
    return thread


def _await_endpoint(frames: list[str], deadline: float) -> str:
    """Poll collected frames for the postable session endpoint.

    AIMI announces the endpoint as the first ``data:`` frame rather than in a
    header, so the stream must be read to discover it.
    """
    while time.monotonic() < deadline:
        for frame in frames:
            match = _SESSION_ENDPOINT_RE.search(frame)
            if match:
                return match.group(0)
        time.sleep(0.05)
    raise TimeoutError("AIMI allocated no SSE session endpoint")


def _await_result(frames: list[str], request_id: int, deadline: float) -> dict[str, Any]:
    """Poll collected frames for the response carrying ``request_id``.

    Every pass re-scans the whole list rather than tracking a cursor: a reply can
    land between two sleeps, and a frame that is not JSON yet is common enough
    that dropping it silently would lose answers.
    """
    while time.monotonic() < deadline:
        for frame in frames:
            try:
                parsed = json.loads(frame)
            except (ValueError, TypeError):
                continue
            if isinstance(parsed, dict) and parsed.get("id") == request_id:
                return parsed
        time.sleep(0.05)
    raise TimeoutError(f"AIMI did not answer request {request_id} before the deadline")


def call_tool(
    tool: str,
    arguments: dict[str, Any],
    *,
    timeout: float | None = None,
) -> dict[str, Any] | None:
    """Invoke one allowlisted AIMI tool. Returns ``None`` on provider failure.

    ``None`` is a meaningful answer, not an error to propagate: the caller
    already holds a deterministic result and this only ever adds to it. Callers
    surface the absence as ``enriched_by_model: false``.

    Raises
    ------
    AimiToolNotAllowed
        The tool is not on :data:`ALLOWED_TOOLS`.
    AimiNotEnabled
        ``AIMI_ENABLED`` is false.
    OutboundPayloadRefused
        The payload carries a field with no egress path. This is a caller bug,
        so it propagates rather than degrading — and it is deliberately not
        counted against the breaker.

    Parameters
    ----------
    tool:
        An AIMI tool name.
    arguments:
        Tool arguments, scrubbed before egress.
    timeout:
        Override for the configured timeout, in seconds. Tests use this.
    """
    if tool in REFUSED_TOOLS:
        raise AimiToolNotAllowed(
            f"AIMI tool '{tool}' is not available to this platform"
        )
    if tool not in ALLOWED_TOOLS:
        raise AimiToolNotAllowed(
            f"AIMI tool '{tool}' is not on the allowlist. Permitted: "
            f"{sorted(ALLOWED_TOOLS)}"
        )
    if not settings.aimi_enabled:
        raise AimiNotEnabled(
            "AIMI_ENABLED is false; the deterministic path is authoritative"
        )
    if _state.is_open:
        logger.info("AIMI breaker is open; skipping %s", tool)
        return None

    # Fail closed: an unregistered destination raises rather than proceeding.
    destination = egress.check(EGRESS_DESTINATION_ID)

    outbound = scrub_outbound(arguments)

    base_url = settings.aimi_base_url.rstrip("/")
    headers = _headers()
    seconds = float(timeout if timeout is not None else settings.aimi_timeout_seconds)
    deadline = time.monotonic() + seconds
    frames: list[str] = []
    stop = threading.Event()

    started = time.monotonic()
    try:
        _open_stream(base_url, headers, seconds, frames, stop)
        path = _await_endpoint(frames, deadline)

        with httpx.Client(timeout=seconds) as client:
            for payload in (
                {
                    "jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "sita-platform", "version": "1.0"},
                    },
                },
                {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                {
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": tool, "arguments": outbound},
                },
            ):
                response = client.post(
                    f"{base_url}{path}", json=payload, headers=headers
                )
                if response.status_code >= 400:
                    raise RuntimeError(
                        f"AIMI RPC {payload['method']} refused: "
                        f"HTTP {response.status_code}"
                    )

        envelope = _await_result(frames, 2, deadline)
        if "error" in envelope:
            _state.record_failure()
            logger.warning("AIMI call %s returned an error envelope", tool)
            return None

    except Exception as exc:  # noqa: BLE001 - degradation is the contract
        _state.record_failure()
        logger.warning(
            "AIMI call %s failed (%s); falling back to the deterministic result",
            tool, exc.__class__.__name__,
        )
        return None
    finally:
        stop.set()

    _state.record_success()
    logger.info(
        "AIMI call %s to %s completed in %dms",
        tool, destination.host, int((time.monotonic() - started) * 1000),
    )
    return envelope.get("result")


def text_of(result: Any) -> str:
    """Flatten an MCP tool result to plain text.

    AIMI returns ``{"content": [{"type": "text", "text": ...}]}`` with mixed
    shapes. Callers want a string; this is the one place that knows the shape.
    """
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    content = result.get("content") if isinstance(result, dict) else None
    if isinstance(content, list):
        parts = [
            block.get("text", "") for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if parts:
            return "\n".join(parts)
    if isinstance(result, dict):
        for key in ("report", "summary", "text", "output", "narrative"):
            value = result.get(key)
            if isinstance(value, str):
                return value
    return json.dumps(result, default=str)