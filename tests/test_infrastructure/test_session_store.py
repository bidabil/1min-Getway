# tests/test_infrastructure/test_session_store.py
"""Tests pour l'InMemorySessionStore."""

import threading

import pytest

from src.infrastructure.session_store import InMemorySessionStore


@pytest.fixture
def store():
    return InMemorySessionStore()


class TestInMemorySessionStore:
    def test_get_returns_none_for_unknown_key(self, store):
        assert store.get("nonexistent") is None

    def test_set_and_get_round_trip(self, store):
        store.set("key1", "conv-uuid-abc")
        assert store.get("key1") == "conv-uuid-abc"

    def test_delete_removes_key(self, store):
        store.set("key1", "conv-uuid-abc")
        store.delete("key1")
        assert store.get("key1") is None

    def test_delete_nonexistent_key_does_not_raise(self, store):
        store.delete("does-not-exist")

    def test_clear_empties_store(self, store):
        store.set("k1", "v1")
        store.set("k2", "v2")
        store.clear()
        assert store.size() == 0

    def test_size_reflects_entries(self, store):
        assert store.size() == 0
        store.set("k1", "v1")
        assert store.size() == 1
        store.set("k2", "v2")
        assert store.size() == 2

    def test_make_key_is_deterministic(self, store):
        key1 = store.make_key("api-key", "gpt-4o", "Hello")
        key2 = store.make_key("api-key", "gpt-4o", "Hello")
        assert key1 == key2

    def test_make_key_differs_for_different_api_keys(self, store):
        key1 = store.make_key("api-key-A", "gpt-4o", "Hello")
        key2 = store.make_key("api-key-B", "gpt-4o", "Hello")
        assert key1 != key2

    def test_make_key_differs_for_different_models(self, store):
        key1 = store.make_key("api-key", "gpt-4o", "Hello")
        key2 = store.make_key("api-key", "gpt-4o-mini", "Hello")
        assert key1 != key2

    def test_make_key_differs_for_different_messages(self, store):
        key1 = store.make_key("api-key", "gpt-4o", "Hello")
        key2 = store.make_key("api-key", "gpt-4o", "Bonjour")
        assert key1 != key2

    def test_thread_safety_concurrent_writes(self, store):
        errors = []

        def write(i):
            try:
                store.set(f"key-{i}", f"value-{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert store.size() == 50
