import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from contextkit import ContextCompiler, MemoryEngine, Scope
from contextkit.adapters.redis import RedisCache

from .conftest import observation


def test_redis_cache_namespace_and_ttl():
    import fakeredis

    client = fakeredis.FakeRedis()
    first = RedisCache(client, namespace="first", ttl=10)
    second = RedisCache(client, namespace="second", ttl=10)
    first.put("snapshot", "payload")
    assert first.get("snapshot") == "payload"
    assert second.get("snapshot") is None
    assert 0 < client.ttl("first:snapshot:snapshot") <= 10


@pytest.mark.parametrize("ttl", [0, -1, True, 1.5])
def test_redis_ttl_is_validated(ttl):
    with pytest.raises(ValueError):
        RedisCache(object(), ttl=ttl)


@pytest.mark.integration
def test_live_mongo_replay_correction_and_forget(live_store):
    engine = MemoryEngine(live_store)
    scope = Scope("integration", "user")
    memory = engine.observe(scope, observation(event_id="event.$1")).memory
    assert engine.observe(scope, observation(event_id="event.$1")).replayed
    corrected = engine.correct(
        scope,
        memory.id,
        "Detailed",
        evidence=("user:1",),
        expected_version=1,
        operation_id="edit",
    ).memory
    assert engine.observe(scope, observation(2)).outcome == "protected_by_user"
    engine.forget(scope, memory.id, expected_version=corrected.version, operation_id="forget")
    assert ContextCompiler(live_store).compile(scope).to_dict()["memories"] == []


@pytest.mark.integration
def test_live_mongo_concurrent_source_updates(live_store):
    engine = MemoryEngine(live_store, max_retries=100)
    scope = Scope("integration", "race")
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(
            pool.map(
                lambda version: engine.observe(
                    scope, observation(version, content=str(version))
                ),
                range(1, 31),
            )
        )
    (memory,) = engine.active(scope)
    assert memory.source_version == 30
    assert len(live_store.load(scope).receipts) == 30


@pytest.mark.integration
def test_live_redis_cache():
    uri = os.environ.get("CONTEXTKIT_TEST_REDIS_URL")
    if not uri:
        pytest.skip("set CONTEXTKIT_TEST_REDIS_URL to an isolated test server")
    from uuid import uuid4

    from redis import Redis

    client = Redis.from_url(uri, socket_connect_timeout=3, socket_timeout=3)
    cache = RedisCache(client, namespace=f"contextkit-test-{uuid4().hex}", ttl=10)
    try:
        cache.put("one", "payload")
        assert cache.get("one") == "payload"
        assert 0 < client.ttl(f"{cache.namespace}:snapshot:one") <= 10
    finally:
        client.delete(f"{cache.namespace}:snapshot:one")
        client.close()
