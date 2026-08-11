"""Pure domain tests: no DB, no app import, no fixtures beyond stdlib."""

import pytest

from app.domain.enums import ALLOWED_TRANSITIONS, ApplicationStage


def test_every_stage_has_a_transition_entry():
    # Guards against the class of bug where a new ApplicationStage is added
    # but nobody updates ALLOWED_TRANSITIONS - that would raise a bare
    # KeyError deep in ApplicationService.change_stage() instead of a clean
    # InvalidTransition/404.
    assert set(ALLOWED_TRANSITIONS.keys()) == set(ApplicationStage)


def test_terminal_stages_allow_no_further_transitions():
    for stage in (
        ApplicationStage.REJECTED,
        ApplicationStage.WITHDRAWN,
        ApplicationStage.ACCEPTED,
        ApplicationStage.GHOSTED,
    ):
        assert ALLOWED_TRANSITIONS[stage] == set()


@pytest.mark.parametrize(
    ("from_stage", "to_stage"),
    [
        (ApplicationStage.SAVED, ApplicationStage.APPLIED),
        (ApplicationStage.SAVED, ApplicationStage.WITHDRAWN),
        (ApplicationStage.APPLIED, ApplicationStage.INTERVIEW),
        (ApplicationStage.APPLIED, ApplicationStage.GHOSTED),
        (ApplicationStage.INTERVIEW, ApplicationStage.OFFER),
        (ApplicationStage.OFFER, ApplicationStage.ACCEPTED),
    ],
)
def test_allowed_transitions(from_stage, to_stage):
    assert to_stage in ALLOWED_TRANSITIONS[from_stage]


@pytest.mark.parametrize(
    ("from_stage", "to_stage"),
    [
        (ApplicationStage.SAVED, ApplicationStage.INTERVIEW),
        (ApplicationStage.SAVED, ApplicationStage.OFFER),
        (ApplicationStage.APPLIED, ApplicationStage.ACCEPTED),
        (ApplicationStage.INTERVIEW, ApplicationStage.SAVED),
    ],
)
def test_disallowed_transitions(from_stage, to_stage):
    assert to_stage not in ALLOWED_TRANSITIONS[from_stage]
