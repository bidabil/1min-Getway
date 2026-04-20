"""
Session store en mémoire : mappe session_key → conversationId 1min.AI.
Thread-safe via threading.Lock.
Non-persistant : redémarre vide à chaque restart du process.

Avec WORKERS > 1, chaque worker a son propre store (pas de partage inter-process).
Pour un déploiement multi-worker, remplacer par un backend Redis.
"""

import hashlib
import threading
from typing import Optional


class InMemorySessionStore:
    """
    Clé de session : sha256(api_key:model:premier_message_user).
    Détection nouvelle conversation : len(messages) == 1 côté ChatService.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            return self._store.get(key)

    def set(self, key: str, conversation_id: str) -> None:
        with self._lock:
            self._store[key] = conversation_id

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def make_key(self, api_key: str, model: str, first_user_message: str) -> str:
        raw = f"{api_key}:{model}:{first_user_message}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


session_store = InMemorySessionStore()
