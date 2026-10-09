# Architecture

## Canonical state

A `Scope(tenant, subject)` selects one subject aggregate. The aggregate contains the current memory records, idempotency receipts, compact operation metadata, and a monotonic revision. Its storage key is a SHA-256 digest of the structured scope, so delimiter collisions in user identifiers do not create shared namespaces.

`MemoryEngine` loads a detached aggregate, applies a mutation, and commits the whole result with compare-and-swap. A successful commit advances the subject revision by exactly one. A losing writer reloads and reevaluates the operation. Corrections and forgetting also check the memory version the user edited, so retries of an unrelated write are safe while concurrent edits to the same memory fail explicitly.

Both memory changes and their receipts commit together. A process failure before commit has no effect; a retry after a successful commit finds the receipt. Reusing an event ID with different arguments raises `EventConflict`. A replay returns the original outcome with the **current** memory and subject revision, so replay cannot return old content after forgetting.

Event receipts are keyed by a digest of the event ID, avoiding user-controlled MongoDB field names. Raw event IDs appear only as values in operation records. Operation records omit content; this version does not retain historical memory bodies.

## Source updates and user control

Each observation identifies a stable `source_key`, a positive `source_version`, and one or more evidence references. A memory ID is deterministic for a scope and source key. The source key represents one logical claim, not an entire document that contains unrelated claims.

For active, uncorrected memory, a higher source version atomically replaces content, evidence, kind, and confidence. An older version records a `stale_source` outcome without changing the memory. An equal version with a different payload is a conflict. Sources are responsible for assigning monotonic versions; clocks are not used to choose a winner.

A correction marks the memory as a user override, increments its memory version, and appends the correction's evidence references. It preserves the previous confidence rather than treating a correction as certainty. Automatic observations cannot overwrite a user override, even with a newer source version. There is no unlock operation in this release.

Forgetting increments the memory version, clears its canonical body and evidence, and retains a tombstone for the source key. Later observations for that source key are blocked. A caller could use a new source key to represent a new claim; applications must enforce consent across semantically related claims when that is required.

## Context assembly

Every compile reads canonical memory and calls each application provider. Provider results distinguish `available`, `absent`, and `failed`. Absence permits a lower-authority fallback. Failure blocks equal or lower-authority values for that provider's declared keys; required-source failure aborts the snapshot. Reader exceptions are converted to failed status without embedding exception messages in context.

Fact conflicts are recorded by key. Higher authority wins; equal authority uses source name order deterministically, so callers should assign distinct authorities when the winner matters. A fact's kind is preserved. Intent, preference, and measured observation should use separate keys instead of competing for the same fact slot.

The snapshot includes memory revision, source revisions and status, current request, current resource, winning facts, active memories, conflicts, and omission counts. JSON uses deterministic ordering and escapes `<`, `>`, and `&`. The snapshot ID is a hash of the exact rendered payload. Provider data is supplied by trusted integration code but remains untrusted input to a consuming runtime.

The character budget preserves the envelope and request. It drops complete memory records, with user overrides ahead of inferred records and higher confidence ahead of lower confidence. It then drops lower-authority facts. If the envelope itself cannot fit, compilation raises `ContextBudgetExceeded`.

## Derived state

Redis caching uses the exact snapshot hash as a key. Compilation still reads the store and providers; the cache is a reusable rendered payload, not a shortcut around freshness. Cached content must match the freshly compiled payload. Corrupt or unavailable cache entries cannot change the snapshot. This deliberately offers limited performance benefit in exchange for simple correctness.

Projection rebuilding reads the canonical state, embeds active memories, and atomically replaces the index for that scope and revision. An older rebuild cannot replace a newer projection. A same-revision rebuild with different entries is rejected by the reference index; use a separate index when changing embedding configuration.

Recall queries the vector index first, then loads canonical state. Each hit must match the requested scope, exist in the canonical store, be active, and reference its current memory version. Duplicate IDs are removed. The result can contain fewer than the requested number when stale candidates are filtered; it does not silently fall back to unchecked index content.

## Consistency boundary

CAS gives atomic subject mutations, not a transaction across providers, caches, vector stores, or running interactions. Canonical reads define the freshness boundary. A mutation after that read can make an already-returned snapshot stale. Applications needing stronger interaction guarantees must coordinate turn admission, cancellation, or revalidation before side effects.

This release has no lease worker and makes no exactly-once claim about external side effects. It supplies replay-safe canonical mutations, not an event transport. A queue consumer can call `observe` with a stable event ID and retry failures.


## Component boundary in 0.2

Memory implementation lives in Agent Memory Kit. Compatibility imports preserve class identity; ContextKit does not maintain a second memory kernel. ContextManager reads session summary/history and compiles canonical memory plus ContextSource facts (including RAG/profile providers). A caller-supplied retrieval callback returns IDs, then the compiler reads canonical active records. Token counting includes the serialized envelope and reserved response/tool space. Budget trimming removes summary, oldest recent messages, memories, then facts. Model execution and evaluation are separate concerns.
