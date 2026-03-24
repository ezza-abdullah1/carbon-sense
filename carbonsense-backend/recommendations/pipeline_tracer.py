"""
Pipeline tracer — provides real-time visibility into the RAG pipeline steps.

Emits structured trace events that can be:
  1. Streamed to the frontend via SSE (Server-Sent Events)
  2. Logged for debugging
  3. Collected and returned with the final response
"""

import json
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class TraceStep:
    """A single step in the pipeline trace."""
    step: int
    name: str
    status: str  # 'running', 'completed', 'error'
    started_at: str = ''
    completed_at: str = ''
    duration_ms: int = 0
    data: dict = field(default_factory=dict)
    error: str = ''

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v or k in ('step', 'data')}


class PipelineTracer:
    """Traces each step of the recommendation pipeline.

    Usage:
        tracer = PipelineTracer()

        with tracer.step(1, "Retrieving policies from vector DB") as t:
            results = retriever.retrieve(...)
            t.add_data({"query": query_text, "results_count": len(results), ...})

        # Get full trace
        trace = tracer.get_trace()

        # Or iterate events as SSE
        for event in tracer.iter_events():
            yield f"data: {json.dumps(event)}\\n\\n"
    """

    def __init__(self):
        self.steps: list[TraceStep] = []
        self.events: list[dict] = []
        self._start_time = time.time()

    class StepContext:
        """Context manager for tracing a pipeline step."""

        def __init__(self, tracer: 'PipelineTracer', step_num: int, name: str):
            self.tracer = tracer
            self.trace_step = TraceStep(
                step=step_num,
                name=name,
                status='running',
                started_at=datetime.now(timezone.utc).isoformat(),
            )
            self._start = None

        def __enter__(self):
            self._start = time.time()
            self.tracer.steps.append(self.trace_step)
            self.tracer._emit_event('step_start', self.trace_step.to_dict())
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed = int((time.time() - self._start) * 1000)
            self.trace_step.duration_ms = elapsed
            self.trace_step.completed_at = datetime.now(timezone.utc).isoformat()

            if exc_type:
                self.trace_step.status = 'error'
                self.trace_step.error = str(exc_val)
                self.tracer._emit_event('step_error', self.trace_step.to_dict())
                return False  # Re-raise the exception

            self.trace_step.status = 'completed'
            self.tracer._emit_event('step_complete', self.trace_step.to_dict())
            return False

        def add_data(self, data: dict):
            """Add observable data to this step."""
            self.trace_step.data.update(data)
            self.tracer._emit_event('step_data', {
                'step': self.trace_step.step,
                'data': data,
            })

    def step(self, step_num: int, name: str) -> StepContext:
        """Create a traced step context."""
        return self.StepContext(self, step_num, name)

    def _emit_event(self, event_type: str, payload: dict):
        """Record a trace event."""
        self.events.append({
            'type': event_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'elapsed_ms': int((time.time() - self._start_time) * 1000),
            **payload,
        })

    def get_trace(self) -> dict:
        """Return the complete pipeline trace."""
        total_ms = int((time.time() - self._start_time) * 1000)
        return {
            'total_duration_ms': total_ms,
            'steps': [s.to_dict() for s in self.steps],
            'step_count': len(self.steps),
        }

    def iter_sse_events(self):
        """Yield trace events as SSE-formatted strings."""
        for event in self.events:
            yield f"data: {json.dumps(event)}\n\n"
