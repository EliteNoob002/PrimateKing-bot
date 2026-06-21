"""ConfigCache unit tests."""

from unittest.mock import MagicMock, patch

from services.config_cache import DEFAULT_BOT_SETTINGS, DEFAULT_PREFIX, ConfigCache


def test_defaults_when_db_empty():
    cache = ConfigCache(ttl_seconds=3600)
    with patch("services.config_cache.get_session") as mock_session:
        session = MagicMock()
        session.query.return_value.all.return_value = []
        mock_session.return_value.__enter__.return_value = session
        cache.reload()

    assert cache.get_prefix(123) == DEFAULT_PREFIX
    assert cache.is_command_enabled(123, "slash", "help") is True
    assert cache.get_bot_setting("time_sleep") == DEFAULT_BOT_SETTINGS["time_sleep"]


def test_reload_keeps_stale_on_error():
    cache = ConfigCache(ttl_seconds=3600)
    with patch("services.config_cache.get_session") as mock_session:
        session = MagicMock()
        session.query.return_value.all.return_value = []
        mock_session.return_value.__enter__.return_value = session
        cache.reload()
        cache._config.bot_settings["time_sleep"] = 99

        mock_session.return_value.__enter__.side_effect = RuntimeError("db down")
        cache.reload()

    assert cache.get_bot_setting("time_sleep") == 99
    assert cache.last_error == "db down"


def test_command_precedence_global_over_default():
    cache = ConfigCache(ttl_seconds=3600)

    class Row:
        guild_id = None
        command_type = "slash"
        command_name = "ping"
        enabled = False

    with patch("services.config_cache.get_session") as mock_session:
        session = MagicMock()

        def query_side(model):
            q = MagicMock()
            if model.__name__ == "CommandSetting":
                q.all.return_value = [Row()]
            else:
                q.all.return_value = []
            return q

        session.query.side_effect = query_side
        mock_session.return_value.__enter__.return_value = session
        cache.reload()

    assert cache.is_command_enabled(1, "slash", "ping") is False
