import pytest
from fastapi import HTTPException

from app.core.rate_limit import _attempts, limit_public_report


def test_public_report_limit_blocks_excess_attempts() -> None:
    _attempts.clear()
    limit_public_report("test-ip", limit=2, window_seconds=60)
    limit_public_report("test-ip", limit=2, window_seconds=60)
    with pytest.raises(HTTPException) as error:
        limit_public_report("test-ip", limit=2, window_seconds=60)
    assert error.value.status_code == 429
