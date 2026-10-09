"""A customer changes a preference, then asks the application to forget it."""

from contextkit import ContextCompiler, MemoryEngine, Observation, Scope
from contextkit.adapters import InMemoryStore


def main() -> None:
    store = InMemoryStore()
    engine = MemoryEngine(store)
    compiler = ContextCompiler(store)
    scope = Scope("helpdesk", "customer-42")
    event = Observation(
        "message-17:preference",
        "response-preference",
        1,
        "Prefers short explanations",
        ("message:17",),
        kind="preference",
        confidence=0.7,
    )
    memory = engine.observe(scope, event).memory
    corrected = engine.correct(
        scope,
        memory.id,
        "Prefers detailed explanations",
        evidence=("message:18",),
        expected_version=memory.version,
        operation_id="correction:18",
    ).memory
    replay = engine.observe(scope, event)
    assert replay.replayed and replay.memory.content == corrected.content
    automatic = engine.observe(
        scope,
        Observation(
            "message-20:preference",
            "response-preference",
            2,
            "Prefers short explanations",
            ("message:20",),
        ),
    )
    assert automatic.outcome == "protected_by_user"
    before = compiler.compile(
        scope, resource="ticket:101", request="Explain the refund process"
    )
    print("After correction:", before.to_dict()["memories"][0]["content"])
    engine.forget(
        scope, memory.id, expected_version=corrected.version, operation_id="forget:21"
    )
    after = compiler.compile(scope, resource="ticket:101", request="Explain the refund process")
    assert after.id != before.id and after.to_dict()["memories"] == []
    assert engine.observe(scope, event).memory.content == ""
    print("After forgetting:", after.to_dict()["memories"])
    print("The next interaction receives a new snapshot:", after.id[:12])


if __name__ == "__main__":
    main()
