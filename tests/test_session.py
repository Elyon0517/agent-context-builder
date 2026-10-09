import pytest
from agent_memory_kit import Message, SessionMemory

from contextkit import ContextBudgetExceeded, ContextCompiler, ContextManager, Scope
from contextkit.adapters import InMemoryStore


def setup_manager(counter=len):
    sessions = SessionMemory()
    manager = ContextManager(ContextCompiler(InMemoryStore()), sessions, count_tokens=counter)
    return manager, sessions, Scope("t", "u")


def test_summary_and_recent_history_and_isolation():
    manager, sessions, scope = setup_manager()
    sessions.append(scope, "a", Message("1", "user", "old"))
    sessions.summarize(scope, "a", lambda messages: "summary")
    sessions.append(scope, "a", Message("2", "assistant", "recent"))
    result = manager.build(scope, session_id="a", query="question", max_tokens=5000)
    data = result.to_dict()
    assert data["current_request"] == "question"
    assert data["session"]["summary"] == "summary"
    assert [m["id"] for m in data["session"]["history"]] == ["2"]
    other = manager.build(scope, session_id="b", query="question", max_tokens=5000)
    assert other.to_dict()["session"]["history"] == []
    assert other.id != result.id


def test_budget_drops_whole_messages():
    manager, sessions, scope = setup_manager()
    sessions.append(scope, "s", Message("1", "user", "x" * 1000))
    sessions.append(scope, "s", Message("2", "assistant", "y" * 1000))
    snapshot = manager.build(
        scope, session_id="s", query="keep", max_tokens=1100, reserved_tokens=100
    )
    assert len(snapshot.payload) <= 1000
    assert snapshot.to_dict()["current_request"] == "keep"
    assert snapshot.to_dict()["omitted_messages"] == 2


def test_envelope_too_large():
    manager, _, scope = setup_manager()
    with pytest.raises(ContextBudgetExceeded):
        manager.build(
            scope, session_id="s", query="x" * 1000, max_tokens=100, reserved_tokens=0
        )


@pytest.mark.parametrize("count", [-1, True, 1.5])
def test_invalid_token_counter(count):
    manager, _, scope = setup_manager(lambda payload: count)
    with pytest.raises(ValueError):
        manager.build(scope, session_id="s", query="q")


def test_session_character_budget():
    manager, sessions, scope = setup_manager(lambda payload: 1)
    sessions.append(scope, "s", Message("1", "user", "x" * 2000))
    result = manager.build(scope, session_id="s", query="q", max_chars=1000)
    assert len(result.payload) <= 1000
    assert result.to_dict()["omitted_messages"] == 1


def test_oversized_summary_does_not_discard_recent_history():
    manager, sessions, scope = setup_manager()
    sessions.append(scope, "s", Message("1", "user", "old"))
    sessions.summarize(scope, "s", lambda messages: "s" * 5000)
    sessions.append(scope, "s", Message("2", "user", "recent"))
    result = manager.build(
        scope, session_id="s", query="q", max_tokens=2000, reserved_tokens=0, max_chars=10000
    )
    data = result.to_dict()
    assert data["omitted_summary"] is True
    assert data["omitted_messages"] == 0
    assert data["session"]["history"][0]["content"] == "recent"


def test_retrieval_selection_revalidates_scope_and_active_records():
    from contextkit import MemoryEngine, Observation

    store = InMemoryStore()
    engine = MemoryEngine(store)
    scope = Scope("t", "u")
    first = engine.observe(scope, Observation("e1", "one", 1, "keep", ("source:1",)))
    engine.observe(scope, Observation("e2", "two", 1, "omit", ("source:2",)))
    other = engine.observe(
        Scope("other", "u"), Observation("e3", "three", 1, "private", ("source:3",))
    )
    manager = ContextManager(
        ContextCompiler(store),
        SessionMemory(),
        count_tokens=len,
        retrieve_memory_ids=lambda s, q: (first.memory.id, other.memory.id),
    )
    result = manager.build(scope, session_id="s", query="q", max_tokens=5000)
    assert [m["content"] for m in result.to_dict()["memories"]] == ["keep"]
    engine.forget(
        scope, first.memory.id, operation_id="forget", expected_version=first.memory.version
    )
    result = manager.build(scope, session_id="s", query="q", max_tokens=5000)
    assert result.to_dict()["memories"] == []
