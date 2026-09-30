"""Automation can compute an output. Only people can review or publish it."""
import pytest

from underlink.governance import (Actor, IllegalTransition, Output, RULES, State,
                                  ai_reachable_states, allowed, reachable_states)


def test_ai_can_only_draft_and_compute():
    assert ai_reachable_states() == {State.DRAFT, State.COMPUTED}


def test_automated_cannot_publish():
    assert State.PUBLISHED not in reachable_states({Actor.AUTOMATED})
    o = Output("region table").move(State.COMPUTED, Actor.AUTOMATED)
    with pytest.raises(IllegalTransition):
        o.move(State.COMMUNITY_REVIEW, Actor.AUTOMATED)


def test_team_alone_cannot_publish():
    assert State.PUBLISHED not in reachable_states({Actor.AUTOMATED, Actor.TEAM})


def test_withheld_only_by_custodian():
    for (src, dst), who in RULES.items():
        if dst is State.WITHHELD:
            assert who == {Actor.CUSTODIAN}, src


def test_published_only_from_custodian_approved():
    assert {src for (src, dst) in RULES if dst is State.PUBLISHED} == {State.CUSTODIAN_APPROVED}


def test_only_custodian_approves():
    assert allowed(State.COMMUNITY_REVIEW, State.CUSTODIAN_APPROVED, Actor.CUSTODIAN)
    assert not allowed(State.COMMUNITY_REVIEW, State.CUSTODIAN_APPROVED, Actor.TEAM)


def test_full_path_with_audit_trail():
    o = Output("community card")
    o.move(State.COMPUTED, Actor.AUTOMATED).move(State.COMMUNITY_REVIEW, Actor.TEAM)
    o.move(State.CUSTODIAN_APPROVED, Actor.CUSTODIAN).move(State.PUBLISHED, Actor.TEAM)
    o.move(State.WITHHELD, Actor.CUSTODIAN, "community asked to take it down")
    assert o.state is State.WITHHELD
    assert [h[3] for h in o.history] == ["COMPUTED", "COMMUNITY_REVIEW", "CUSTODIAN_APPROVED", "PUBLISHED", "WITHHELD"]


def test_skipping_review_is_refused():
    with pytest.raises(IllegalTransition):
        Output("x").move(State.COMPUTED, Actor.TEAM).move(State.PUBLISHED, Actor.TEAM)
