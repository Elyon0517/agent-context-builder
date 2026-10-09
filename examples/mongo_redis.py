"""Use explicitly configured local services for persistent memory and a cache."""

import os
from uuid import uuid4

from contextkit import ContextCompiler, MemoryEngine, Observation, Scope
from contextkit.adapters.mongo import MongoStore
from contextkit.adapters.redis import RedisCache


def main() -> None:
    from pymongo import MongoClient
    from redis import Redis

    mongo_uri = os.environ.get("CONTEXTKIT_MONGO_URI")
    redis_url = os.environ.get("CONTEXTKIT_REDIS_URL")
    if not mongo_uri or not redis_url:
        raise SystemExit(
            "Set CONTEXTKIT_MONGO_URI and CONTEXTKIT_REDIS_URL to local demo services."
        )
    mongo = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    redis = Redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
    try:
        store = MongoStore(mongo.contextkit_demo.subjects)
        scope = Scope("demo", f"customer-{uuid4().hex}")
        MemoryEngine(store).observe(
            scope,
            Observation(
                "demo:1",
                "response-preference",
                1,
                "Prefers detailed explanations",
                ("demo:message:1",),
            ),
        )
        compiler = ContextCompiler(store, cache=RedisCache(redis, namespace="contextkit-demo"))
        first = compiler.compile(scope)
        assert compiler.compile(scope).id == first.id
        print(first.render())
        print("Demo state remains in the contextkit_demo database for inspection.")
    finally:
        mongo.close()
        redis.close()


if __name__ == "__main__":
    main()
