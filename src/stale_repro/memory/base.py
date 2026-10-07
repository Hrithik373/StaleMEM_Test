"""Common interface for every memory system under test (B0..B3, M, M+).

Lifecycle per STALE instance:
    system.reset()
    for session in instance.sessions: system.ingest(session)
    for probe in instance.probes.values(): system.answer(probe)

``Answer.trace`` carries whatever intermediate state a system wants to expose;
CUPMem uses it for stage-wise failure attribution.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..data.loader import Instance, Probe, Session

# Response-generation prompts, verbatim from the paper (App. E.1) and the
# official STALE/Evaluation/run_target_model.py.
SYSTEM_QA = ("You are a helpful assistant. Review the following conversation history "
             "with the user, then accurately answer the question.")
SYSTEM_TASK = ("You are a helpful assistant. Review the following conversation history "
               "with the user, then respond to the user's latest query directly.")


def build_answer_prompt(history_text: str, probe: Probe) -> tuple[str, str]:
    if probe.is_task:
        return SYSTEM_TASK, f"[Conversation History]\n{history_text}\n\n[Latest Query]\n{probe.text}"
    return SYSTEM_QA, f"[Conversation History]\n{history_text}\n\n[Question]\n{probe.text}"


@dataclass
class Answer:
    text: str
    trace: dict[str, Any] = field(default_factory=dict)


class MemorySystem(ABC):
    name: str = "base"

    def reset(self) -> None:  # noqa: B027 - optional hook
        """Clear all state before a new instance."""

    def begin_instance(self, instance: Instance) -> None:
        """Optional hook. Systems must NOT read labels (M_old/M_new/evidence
        indices) from here; the runner only calls it so B0 can apply the
        paper's evidence-preserving truncation, which the paper also grants."""

    @abstractmethod
    def ingest(self, session: Session) -> None: ...

    @abstractmethod
    def answer(self, probe: Probe) -> Answer: ...

    def ingest_many(self, sessions: list[Session]) -> None:
        for s in sessions:
            self.ingest(s)
