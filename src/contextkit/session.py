"""Assemble session history, canonical memory and application sources under a budget."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent_memory_kit import Scope, SessionMemory
from agent_memory_kit.models import fingerprint, require_revision

from contextkit.context import ContextBudgetExceeded, ContextCompiler, ContextSnapshot, _render


class ContextManager:
    """Tokenizer-independent orchestration. Caller supplies the exact token counter."""

    def __init__(
        self,
        compiler: ContextCompiler,
        sessions: SessionMemory,
        *,
        count_tokens: Callable[[str], int],
        retrieve_memory_ids: Callable[[Scope, str], tuple[str, ...]] | None = None,
    ) -> None:
        self.compiler = compiler
        self.sessions = sessions
        self.count_tokens = count_tokens
        self.retrieve_memory_ids = retrieve_memory_ids

    def build(
        self,
        scope: Scope,
        *,
        session_id: str,
        query: str,
        max_tokens: int = 4096,
        reserved_tokens: int = 512,
        max_chars: int = 32000,
    ) -> ContextSnapshot:
        require_revision(max_tokens, "max_tokens", 1)
        require_revision(reserved_tokens, "reserved_tokens")
        if reserved_tokens >= max_tokens:
            raise ValueError("reserved_tokens must be less than max_tokens")
        memory_ids = (
            None if self.retrieve_memory_ids is None else self.retrieve_memory_ids(scope, query)
        )
        snapshot = self.compiler.compile(
            scope, request=query, max_chars=max_chars, memory_ids=memory_ids
        )
        session = self.sessions.load(scope, session_id)
        history = list(session.messages)
        summary = session.summary
        if summary is not None:
            covered = next(
                (
                    i
                    for i, message in enumerate(history)
                    if message.id == summary.through_message_id
                ),
                None,
            )
            if covered is not None:
                history = history[covered + 1 :]
        envelope: dict[str, Any] = snapshot.to_dict()
        envelope["session"] = {
            "id": session_id,
            "revision": session.revision,
            "summary": None if summary is None else summary.content,
            "history": [{"id": m.id, "role": m.role, "content": m.content} for m in history],
        }
        envelope["omitted_messages"] = 0
        envelope["omitted_summary"] = False
        budget = max_tokens - reserved_tokens
        while True:
            payload = _render(envelope)
            tokens = self.count_tokens(payload)
            require_revision(tokens, "token count")
            if tokens <= budget and len(payload) <= max_chars:
                return ContextSnapshot(fingerprint(payload), snapshot.memory_revision, payload)
            if envelope["session"]["summary"] is not None:
                envelope["session"]["summary"] = None
                envelope["omitted_summary"] = True
            elif envelope["session"]["history"]:
                envelope["session"]["history"].pop(0)
                envelope["omitted_messages"] += 1
            elif envelope["memories"]:
                envelope["memories"].pop()
                envelope["omitted_memories"] += 1
            elif envelope["facts"]:
                envelope["facts"].pop()
                envelope["omitted_facts"] += 1
            else:
                raise ContextBudgetExceeded("request and envelope exceed the available budget")
