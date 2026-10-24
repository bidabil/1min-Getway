import json
import logging

import pytest

from gateway.cli import main as cli_main
from gateway.infrastructure.observability.logging import (
    JsonFormatter,
    client_var,
    configure_logging,
    request_id_var,
)
from gateway.infrastructure.security.api_keys import hash_key, parse_key_entries


def test_cli_create_key_prints_a_usable_entry(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli_main(["create-key", "my-agent", "--rpm", "30"]) == 0
    output = capsys.readouterr().out
    key = next(line.strip() for line in output.splitlines() if line.strip().startswith("gw-"))
    entry_line = next(
        line.strip() for line in output.splitlines() if line.strip().startswith("my-agent:")
    )
    (entry,) = parse_key_entries(entry_line)
    assert (entry.name, entry.digest, entry.requests_per_minute) == ("my-agent", hash_key(key), 30)


def test_cli_hash_key(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli_main(["hash-key", "gw-abc"]) == 0
    assert capsys.readouterr().out.strip() == hash_key("gw-abc")


def test_json_log_format_includes_context_and_extras() -> None:
    token_request, token_client = request_id_var.set("req-1"), client_var.set("agent")
    try:
        record = logging.LogRecord(
            "gateway.test", logging.INFO, __file__, 1, "chat %s", ("ok",), None
        )
        record.model = "gpt-5"
        for log_filter in (
            logging.getLogger().handlers[0].filters if logging.getLogger().handlers else []
        ):
            log_filter.filter(record)
        record.request_id, record.client = "req-1", "agent"
        entry = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token_request)
        client_var.reset(token_client)
    assert entry["message"] == "chat ok"
    assert (
        entry["model"] == "gpt-5" and entry["request_id"] == "req-1" and entry["client"] == "agent"
    )


def test_configure_logging_replaces_handlers(capsys: pytest.CaptureFixture[str]) -> None:
    root = logging.getLogger()
    saved = list(root.handlers), root.level
    try:
        configure_logging("INFO", "json")
        logging.getLogger("gateway.test").info("hello", extra={"status": 200})
        line = capsys.readouterr().out.strip().splitlines()[-1]
        assert json.loads(line)["status"] == 200
        configure_logging("DEBUG", "text")
        assert root.level == logging.DEBUG
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
        for handler in saved[0]:
            root.addHandler(handler)
        root.setLevel(saved[1])
