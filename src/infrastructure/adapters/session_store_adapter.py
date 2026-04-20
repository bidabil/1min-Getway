from ...domain.ports import SessionStorePort
from ..session_store import session_store as _global_store


class InMemorySessionStoreAdapter(SessionStorePort):
    def get(self, key: str) -> str | None:
        return _global_store.get(key)

    def set(self, key: str, conversation_id: str) -> None:
        _global_store.set(key, conversation_id)

    def make_key(self, api_key: str, model: str, first_user_message: str) -> str:
        return _global_store.make_key(api_key, model, first_user_message)
