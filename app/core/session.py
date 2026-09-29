"""Session models for authorized FacePilot test runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class SessionStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class SignalResult:
    """One detector signal recorded during a test session."""

    name: str
    score: float
    detail: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        self.score = max(0.0, min(float(self.score), 1.0))


@dataclass(slots=True)
class TestSession:
    """Local-only authorized simulation session."""

    input_name: str
    id: str = field(default_factory=lambda: uuid4().hex)
    status: SessionStatus = SessionStatus.CREATED
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    ended_at: str | None = None
    signals: list[SignalResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def start(self) -> None:
        if self.status is not SessionStatus.CREATED:
            raise RuntimeError("Only a newly created session can be started")
        self.status = SessionStatus.RUNNING
        self.started_at = datetime.now(UTC).isoformat()

    def add_signal(self, result: SignalResult) -> None:
        if self.status is not SessionStatus.RUNNING:
            raise RuntimeError("Signals can only be added to a running session")
        self.signals.append(result)

    def complete(self) -> None:
        if self.status is not SessionStatus.RUNNING:
            raise RuntimeError("Only a running session can be completed")
        self.status = SessionStatus.COMPLETED
        self.ended_at = datetime.now(UTC).isoformat()

    def cancel(self, reason: str = "Cancelled by operator") -> None:
        if self.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
            return
        self.status = SessionStatus.CANCELLED
        self.notes.append(reason)
        self.ended_at = datetime.now(UTC).isoformat()

    def _risk_signals(self) -> list[SignalResult]:
        """Return signals intended to contribute to the anomaly score."""
        return [
            signal
            for signal in self.signals
            if signal.name.startswith("challenge:")
            or signal.name in {"frame:duplicate", "frame:challenge_motion"}
        ]

    @staticmethod
    def _average(signals: list[SignalResult]) -> float:
        if not signals:
            return 0.0
        return sum(item.score for item in signals) / len(signals)

    def risk_score(self) -> float:
        """Calculate anomaly score from outcome and automated frame heuristics."""
        return self._average(self._risk_signals())

    def risk_breakdown(self) -> dict[str, float]:
        """Return transparent category averages for the session summary."""
        challenge_signals = [
            signal for signal in self.signals if signal.name.startswith("challenge:")
        ]
        frame_signals = [
            signal
            for signal in self.signals
            if signal.name in {"frame:duplicate", "frame:challenge_motion"}
        ]
        return {
            "challenge_outcomes": round(self._average(challenge_signals), 4),
            "frame_analysis": round(self._average(frame_signals), 4),
            "overall": round(self.risk_score(), 4),
        }

    def classification(self) -> str:
        score = self.risk_score()
        if score >= 0.75:
            return "high anomaly likelihood"
        if score >= 0.45:
            return "review recommended"
        return "low anomaly likelihood"

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["risk_score"] = round(self.risk_score(), 4)
        payload["risk_breakdown"] = self.risk_breakdown()
        payload["classification"] = self.classification()
        return payload
