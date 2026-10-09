# Changelog

## 0.2.0

- Delegate canonical memory and storage to independent Agent Memory Kit, preserving imports.
- Add ContextManager for session summaries, recent history, optional retrieval selection and tokenizer-driven budgets.
- Keep FlowEval as an independent evaluation component.


## 0.1.1

- Reject mutable projection entries and vectors so callers cannot alter an index outside a revision-guarded replacement.
- Validate vector memory identifiers, versions, and finite numeric values before indexing.
- Add regression coverage for mutable inputs and invalid vector values.

## 0.1.0

- Versioned, scoped memory with evidence references and replay receipts.
- User corrections, forget tombstones, and optimistic concurrency.
- Context snapshots with source authority, failure semantics, and character budgeting.
- In-memory and MongoDB state stores; in-memory and Redis snapshot caches.
- Vector index contract, reference cosine index, and canonical recall validation.
- Synthetic examples and behavioral tests, with optional live storage checks.
