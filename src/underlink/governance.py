"""Who may move an output towards publication, written as a state machine.

The same pattern as the author's FairFix project. An output (a card, a region
table, a relay list) starts as DRAFT. Code can compute it. Only people can put
it in front of a community, and only the custodian the community chose can
approve it, publish it onward or withhold it. The rules live in one table so
they can be tested, not just described.

    DRAFT -> COMPUTED -> COMMUNITY_REVIEW -> CUSTODIAN_APPROVED -> PUBLISHED
                              any state  -> WITHHELD   (custodian only)
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class State(str, Enum):
    DRAFT = "DRAFT"
    COMPUTED = "COMPUTED"
    COMMUNITY_REVIEW = "COMMUNITY_REVIEW"
    CUSTODIAN_APPROVED = "CUSTODIAN_APPROVED"
    PUBLISHED = "PUBLISHED"
    WITHHELD = "WITHHELD"


class Actor(str, Enum):
    AUTOMATED = "AUTOMATED"   # the pipeline, or any AI tool
    TEAM = "TEAM"             # the Underlink team
    CUSTODIAN = "CUSTODIAN"   # the person or body the community chose


class IllegalTransition(Exception):
    """Raised when an actor tries a move the rules do not allow."""


S, A = State, Actor

# (from, to) -> actors allowed to make that move. Anything not listed is refused.
RULES: dict[tuple[State, State], frozenset[Actor]] = {
    (S.DRAFT, S.COMPUTED): frozenset({A.AUTOMATED, A.TEAM}),
    (S.COMPUTED, S.DRAFT): frozenset({A.TEAM}),                       # rework
    (S.COMPUTED, S.COMMUNITY_REVIEW): frozenset({A.TEAM}),
    (S.COMMUNITY_REVIEW, S.DRAFT): frozenset({A.TEAM, A.CUSTODIAN}),   # changes asked for
    (S.COMMUNITY_REVIEW, S.CUSTODIAN_APPROVED): frozenset({A.CUSTODIAN}),
    (S.CUSTODIAN_APPROVED, S.PUBLISHED): frozenset({A.TEAM, A.CUSTODIAN}),
    (S.WITHHELD, S.DRAFT): frozenset({A.CUSTODIAN}),                   # only the custodian reopens
}
# The custodian can withhold from any state, including after publication.
for _s in State:
    if _s is not S.WITHHELD:
        RULES[(_s, S.WITHHELD)] = frozenset({A.CUSTODIAN})


def allowed(src: State, dst: State, actor: Actor) -> bool:
    return actor in RULES.get((State(src), State(dst)), frozenset())


def reachable_states(actors: set[Actor], start: State = S.DRAFT) -> set[State]:
    """Every state a given set of actors can reach from `start` on their own."""
    seen, todo = {start}, deque([start])
    while todo:
        s = todo.popleft()
        for (a, b), who in RULES.items():
            if a is s and who & actors and b not in seen:
                seen.add(b)
                todo.append(b)
    return seen


def ai_reachable_states(start: State = S.DRAFT) -> set[State]:
    """What automation can do with no person involved. Expected: {DRAFT, COMPUTED}."""
    return reachable_states({A.AUTOMATED}, start)


@dataclass
class Output:
    """One publishable output and its audit trail."""
    name: str
    state: State = S.DRAFT
    history: list[tuple[str, str, str, str, str]] = field(default_factory=list)

    def move(self, dst: State, actor: Actor, note: str = "") -> "Output":
        dst, actor = State(dst), Actor(actor)
        if not allowed(self.state, dst, actor):
            raise IllegalTransition(f"{actor.value} cannot move {self.name} from {self.state.value} to {dst.value}")
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.history.append((stamp, actor.value, self.state.value, dst.value, note))
        self.state = dst
        return self


class NotReleased(Exception):
    """Raised when an output about a real community is written without a custodian's release."""


def require_release(output: "Output | None", community: str) -> None:
    """The gate every output about a real community passes before it is written.

    It must be PUBLISHED, and the step that got it there must have been taken by the
    custodian the community chose. Automated steps (the pipeline, any AI tool) cannot
    reach PUBLISHED, so code alone can never release one."""
    if output is None or output.state != S.PUBLISHED:
        raise NotReleased(f"No custodian release for {community}: nothing is written.")
    if not any(h[1] == Actor.CUSTODIAN.value and h[3] == S.CUSTODIAN_APPROVED.value for h in output.history):
        raise NotReleased(f"{community}: the release was not approved by the community's custodian.")


def suppress_count(n: float, floor: int) -> float | str:
    """Public counts below the floor are shown as '<floor'. Zero stays zero.

    Mirrors pipeline.suppress so other modules can use it without importing the
    whole pipeline.
    """
    return f"<{floor}" if 0 < n < floor else n
