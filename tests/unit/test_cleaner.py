import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from Cleaner import cleaner


@pytest.mark.asyncio
async def test_periodic_expired_cleanup_triggers_once(mocker):
    # Мокаем delete_expired
    mock_delete = mocker.patch.object(cleaner.url_service, "delete_expired")

    mocker.patch("asyncio.sleep", new_callable=AsyncMock, side_effect=KeyboardInterrupt)

    mock_loop = mocker.Mock()
    mock_loop.run_in_executor = AsyncMock()
    mocker.patch("asyncio.get_event_loop", return_value=mock_loop)

    with pytest.raises(KeyboardInterrupt):
        await cleaner.periodic_expired_cleanup(interval_seconds=1, unused_days=5)

    mock_loop.run_in_executor.assert_called_once()
    assert mock_loop.run_in_executor.call_args[0][1].__name__ == "<lambda>"
