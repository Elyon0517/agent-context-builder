# Adapter guide

## MongoDB

```python
from pymongo import MongoClient
from contextkit import MemoryEngine
from contextkit.adapters.mongo import MongoStore

client = MongoClient("mongodb://127.0.0.1:27017")
store = MongoStore(client.contextkit.subjects)
engine = MemoryEngine(store)
```

The driver is installed through the `mongo` extra. The adapter selects primary reads and majority write concern. Initialization uses a unique `_id`; later commits use `replace_one` with both `_id` and expected revision. A racing first insert returns false on duplicate key, letting the engine retry. Driver errors propagate; a timeout after a server commit can be resolved by retrying the same operation identity.

One aggregate includes memory and operation receipts, keeping commits atomic on a standalone server as well as a replica set. This trades document growth and subject-level contention for a straightforward initial consistency contract. Use bounded subject profiles. Do not prune receipts or tombstones casually: doing so weakens replay and revocation guarantees. Sharded multi-document storage and retention-aware compaction need a separate adapter design.

Driver operations follow the [PyMongo collection API](https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html).

## Redis

```python
from redis import Redis
from contextkit import ContextCompiler
from contextkit.adapters.redis import RedisCache

cache = RedisCache(Redis.from_url("redis://127.0.0.1:6379/0"), ttl=300)
compiler = ContextCompiler(store, cache=cache)
```

The `redis` extra installs the client. Namespaces are configurable; keys contain a digest rather than raw user IDs. Payloads contain context data, so configure Redis access control and retention appropriately. TTL is a positive integer. Compilation never serves stale data solely because a cached payload exists; provider reads and canonical reads still happen.

Forget does not eagerly erase all historical cache keys. They become unreachable from fresh compilation and expire at TTL. A deployment requiring physical erasure must manage those keys, backups, and previously returned payloads explicitly.

Cache commands follow the [redis-py command API](https://redis.readthedocs.io/en/stable/commands.html).

## Vector index

`contextkit.ports.VectorIndex` declares two operations:

```python
def replace(scope, revision, entries) -> bool: ...
def search(scope, query, limit) -> list[VectorHit]: ...
```

`replace` must atomically swap the entire scoped projection and reject lower revisions. Each entry includes a canonical memory ID and memory version. Equal revisions must not accept different entries. `search` returns scoped identities and scores, never canonical content.

The reference adapter requires immutable tuples for the entries collection, each vector, and the query vector. `VectorEntry` validates a nonempty memory ID, a positive integer memory version, and finite numeric coordinates. Mutable lists are rejected so an external edit cannot change a committed projection without a new revision.

A remote adapter can stage entries under a generation and update a generation pointer with compare-and-swap. Query only the active generation and garbage-collect old generations separately. A sequence of unguarded deletes and upserts is not an atomic replacement. Include embedding model/version in the index namespace; changing it requires a separate projection.

`MemoryEngine.recall` treats the index as a candidate generator and revalidates its output against the store. Even a buggy adapter returning another tenant's hit cannot bypass this check, although it can cause missing results. Candidate oversampling is configurable through `candidate_limit`.

## Application sources and runtimes

Implement `ContextSource.read(scope)` using your application's authorized records. Use declared keys and revisions; do not include database credentials or exception details. Source providers can read PostgreSQL, MongoDB, an API, or application memory. ContextKit does not assume their underlying technology.

Compile once at the start of each turn. Store the snapshot ID beside the interaction record if you need to explain which state was consumed. Pass `snapshot.render()` as explicitly marked data to your runtime, retaining system rules separately. The library does not authenticate users, open network tools, or authorize current-resource access.
