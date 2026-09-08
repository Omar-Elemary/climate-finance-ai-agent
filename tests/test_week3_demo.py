"""
Test suite for week3_demo script execution.
"""

from week3_demo import run_week3_demo


def test_demo_execution_runs_without_exceptions():
    """Verify that the full week3_demo executes end-to-end without unhandled errors."""
    try:
        run_week3_demo()
    except Exception as exc:
        assert False, f"week3_demo raised an unexpected exception: {exc}"
        