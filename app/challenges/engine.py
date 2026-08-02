"""Challenge sequencing and response evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic


class ChallengeKind(StrEnum):
    LOOK_LEFT = "look_left"
    LOOK_RIGHT = "look_right"
    LOOK_UP = "look_up"
    LOOK_DOWN = "look_down"
    BLINK = "blink"
    SMILE = "smile"
    OPEN_MOUTH = "open_mouth"
    MOVE_CLOSER = "move_closer"
    MOVE_AWAY = "move_away"


@dataclass(frozen=True, slots=True)
class Challenge:
    kind: ChallengeKind
    instruction: str
    timeout_seconds: float = 5.0
    repetitions: int = 1


@dataclass(slots=True)
class ChallengeResult:
    challenge: Challenge
    passed: bool
    response_seconds: float
    confidence: float
    note: str = ""


@dataclass(slots=True)
class ChallengeEngine:
    """State machine used by local and authorized test adapters."""

    challenges: list[Challenge]
    current_index: int = 0
    results: list[ChallengeResult] = field(default_factory=list)
    _started_at: float | None = None

    @property
    def current(self) -> Challenge | None:
        if self.current_index >= len(self.challenges):
            return None
        return self.challenges[self.current_index]

    @property
    def finished(self) -> bool:
        return self.current is None

    def start_current(self) -> Challenge:
        challenge = self.current
        if challenge is None:
            raise RuntimeError("Challenge sequence is complete")
        self._started_at = monotonic()
        return challenge

    def submit(self, passed: bool, confidence: float, note: str = "") -> ChallengeResult:
        challenge = self.current
        if challenge is None or self._started_at is None:
            raise RuntimeError("No active challenge")
        elapsed = monotonic() - self._started_at
        timed_out = elapsed > challenge.timeout_seconds
        result = ChallengeResult(
            challenge=challenge,
            passed=bool(passed and not timed_out),
            response_seconds=elapsed,
            confidence=max(0.0, min(float(confidence), 1.0)),
            note="Timed out" if timed_out else note,
        )
        self.results.append(result)
        self.current_index += 1
        self._started_at = None
        return result

    def completion_rate(self) -> float:
        if not self.challenges:
            return 1.0
        return sum(result.passed for result in self.results) / len(self.challenges)


def default_sequence() -> list[Challenge]:
    return [
        Challenge(ChallengeKind.LOOK_LEFT, "Turn your head left"),
        Challenge(ChallengeKind.LOOK_RIGHT, "Turn your head right"),
        Challenge(ChallengeKind.BLINK, "Blink twice", repetitions=2),
        Challenge(ChallengeKind.SMILE, "Smile"),
    ]
