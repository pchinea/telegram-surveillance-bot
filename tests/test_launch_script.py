"""
Test suite for launch script testing.
"""
import logging
import runpy

import _pytest.logging
import pytest


def test_launch_script(caplog: _pytest.logging.caplog):
    """
    Tests launch script invocation.

    Args:
        caplog: Fixture for log messages capturing.
    """
    with pytest.raises(SystemExit) as error:
        runpy.run_path('start.py')

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.CRITICAL
    assert 'BOT_API_KEY' in record.message
    assert error.type == SystemExit
    assert error.value.code == 1
