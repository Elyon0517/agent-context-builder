# Behavior contracts

## Observation outcomes

| Outcome | Memory change |
| --- | --- |
| `created` | First observation for the scoped source key |
| `updated` | Higher source version replaces current content and evidence |
| `unchanged` | New event ID carries the same source version and payload |
| `stale_source` | Older source version ignored |
| `protected_by_user` | User override retained |
| `blocked_by_forget` | Tombstone retained |

An exact event replay sets `replayed=True` and does not advance the revision. A different new event that is blocked or stale still commits a receipt and operation record, advancing the subject revision without changing the memory version. Automatic updates do not expire over time.

## Control operations

`correct` and `forget` require `expected_version` and a stable `operation_id`. Operation IDs share the scope's receipt namespace with observation event IDs. Reusing an identity for a different action or payload raises `EventConflict`.

Use the memory version displayed to the user, not a newly fetched version hidden from them. If it changed, a `RevisionConflict` asks the application to reload and present the change. Supplying a foreign scope raises `MemoryNotFound`; scope construction itself is the application's responsibility.

A user correction requires explicit evidence references. Forgetting retains the source key, versions, kind, confidence, override flag, compact operation metadata, and hashed receipts; it clears the canonical content and evidence. It does not clear the caller's existing objects, transport logs, external providers, caches, or backups.

## Evidence semantics

An evidence reference is an application-defined string, such as a record ID or authorized deep link. The library validates that a reference is nonempty, but does not fetch it, judge its truth, or authenticate it. Corrected memory retains prior lineage and the correction reference. Source refresh replaces evidence to correspond to the new content.

## Provider semantics

Providers declare keys before reading, which allows failures to block unsafe fallback. A successful provider must supply a nonempty revision and cannot emit undeclared or duplicate keys. An absent or failed result cannot carry facts. Required means read failure prevents compilation; required does not mean the source must contain a row.

Large requests or provider metadata can exceed the envelope budget; no hidden truncation occurs. Omission counters distinguish budget exclusion from an empty memory store.

## Validation coverage

The suite checks identity conflicts, source ordering, evidence refresh, protected corrections, forget replay, stale user edits, scope isolation, atomic commit races, snapshot invalidation, final-memory removal, provider absence versus failure, delimiter escaping, complete-record budgeting, cache failure, stale vector entries, and projection ordering.

The memory behavior suite runs against `InMemoryStore` and a MongoDB emulator. Optional live tests exercise MongoDB persistence and concurrent CAS, plus Redis namespace and TTL behavior. Emulator tests do not substitute for server-level integration checks.
