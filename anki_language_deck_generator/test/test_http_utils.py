from types import SimpleNamespace
from unittest.mock import patch

import pytest
import requests

from anki_language_deck_generator.http_utils import USER_AGENT, get_with_retry, make_session


class FakeSession:
    """Returns (or raises) the given outcomes, one per GET call."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.kwargs = None

    def get(self, url, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def response(status, headers=None):
    return SimpleNamespace(status_code=status, headers=headers or {})


@pytest.fixture
def sleep():
    with patch('anki_language_deck_generator.http_utils.time.sleep') as mock:
        yield mock


def test_success_is_returned_without_sleeping(sleep):
    session = FakeSession([response(200)])
    assert get_with_retry(session, 'http://x').status_code == 200
    assert session.calls == 1
    sleep.assert_not_called()


def test_429_is_retried_after_retry_after_seconds(sleep):
    session = FakeSession([response(429, {'Retry-After': '48'}), response(200)])
    assert get_with_retry(session, 'http://x').status_code == 200
    assert session.calls == 2
    sleep.assert_called_once_with(48.0)


def test_retry_after_is_capped(sleep):
    session = FakeSession([response(429, {'Retry-After': '3600'}), response(200)])
    get_with_retry(session, 'http://x', max_wait=90)
    sleep.assert_called_once_with(90)


def test_exponential_backoff_without_retry_after(sleep):
    session = FakeSession([response(503), response(503), response(200)])
    assert get_with_retry(session, 'http://x').status_code == 200
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]


def test_gives_up_after_attempts(sleep):
    session = FakeSession([response(429)] * 3)
    assert get_with_retry(session, 'http://x', attempts=3).status_code == 429
    assert session.calls == 3


def test_404_is_not_retried(sleep):
    session = FakeSession([response(404)])
    assert get_with_retry(session, 'http://x').status_code == 404
    assert session.calls == 1
    sleep.assert_not_called()


def test_connection_error_is_retried_then_raised(sleep):
    session = FakeSession([requests.ConnectionError('boom'), response(200)])
    assert get_with_retry(session, 'http://x').status_code == 200

    session = FakeSession([requests.ConnectionError('boom')] * 2)
    with pytest.raises(requests.ConnectionError):
        get_with_retry(session, 'http://x', attempts=2)


def test_default_timeout_is_passed_to_the_session():
    session = FakeSession([response(200)])
    get_with_retry(session, 'http://x')
    assert session.kwargs['timeout'] == 30


def test_session_has_descriptive_user_agent():
    assert make_session().headers['User-Agent'] == USER_AGENT
    assert 'github.com/impugachev' in USER_AGENT
