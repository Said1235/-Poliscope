# POLISCOPE — Architecture (Phase 4)

Status: **DRAFT FOR REVIEW — no contract code exists.** Companion documents: DATA_MODEL.md (records,
encodings, segmenter), CONSENSUS_DESIGN.md (leader/validator procedure), SECURITY_MODEL.md, THREAT_MODEL.md.

---

## 1. System shape

A **single-file** GenLayer Intelligent Contract (`contracts/poliscope.py`) on the standard `py-genlayer`
runner. No frontend, backend, API, indexer, external storage, web access or cross-contract calls
(EXC-01…EXC-07). Developer tooling (lint, pytest) is outside the contract.

```text
                ┌────────────────────────── Poliscope (one contract) ──────────────────────────┐
 caller ──tx──► │ create_workspace · publish_policy · register_proposal · audit_proposal        │
 caller ──view─►│ get_workspace · get_policy_version · get_policy_rule · get_proposal · get_audit│
                │                                                                              │
                │  DETERMINISTIC CORE (pure module-level functions, unit-testable)             │
                │   input validation · canonical encoding · Keccak commitments · segmenter     │
                │   finding validation/canonicalization · verdict · report commitment          │
                │                                                                              │
                │  STORAGE: workspaces · policy_versions · proposals · audits (TreeMaps)       │
                │                                                                              │
                │  NONDETERMINISTIC BLOCK (one per audit): leader_fn / validator_fn            │
                │   closes over an immutable plain-data Snapshot; exactly one exec_prompt      │
                └──────────────────────────────────────────────────────────────────────────────┘
```

## 2. Single-file layout (specification)

1. Runner header (pinned `Depends`, **first line**) and imports (`from genlayer import *`, `json`, `dataclasses`, `typing`). Header: `# v0.2.16` then the pinned legacy `Depends` line.
2. Constants: versions (`SCHEMA_VERSION`, `PROMPT_VERSION`, `SEGMENTATION_VERSION`), limits (LIM-*), enums (`STATUS`, `REASON`, `VERDICT`, `STATE`), the compatibility table, the trusted prompt parts.
3. Pure module-level helpers (no storage access, no `gl.nondet`): `validate_*`, `enc`, `H`, `segment`, `is_citable`, `validate_findings`, `aggregate_verdict`, `report_commitment`, `build_prompt`.
4. `EvaluationError` (internal exception carrying a stable code).
5. `allow_storage = gl.storage.allow` alias; storage dataclasses (DATA_MODEL §2.2).
6. `class Poliscope(gl.contract.Contract)`: storage fields, `__init__`, public views/writes, private helpers.

Rationale: pure helpers are testable without a VM, and the *same* functions run in leader, validator and post-consensus phases,
eliminating drift between the three. Closures referencing module-level helpers/constants/exception classes were probed and
pickle correctly with `check_pickling = True` (RESEARCH D-17). Not split into modules: single-file runner (EXC-06).

## 3. Public interface

### 3.1 Writes (state-changing)

| Method | Authorization | Effect |
|---|---|---|
| `create_workspace(name: str, client_nonce: str)` | anyone | creates workspace; sender becomes administrator |
| `publish_policy(workspace_id: str, new_version: int, rules: list[dict[str, typing.Any]])` | administrator | appends immutable version `current+1` |
| `register_proposal(workspace_id: str, policy_version: int, title: str, client_nonce: str, proposal_text: str)` | anyone | commits to text, stores metadata; no text stored |
| `audit_proposal(proposal_id: str, proposal_text: str)` | proposal submitter **or** administrator | consensus audit; persists report |

No payable methods. No other writes exist: **no update, delete, transfer or admin-change method.**

### 3.2 Views (read-only)

`get_workspace`, `get_policy_version`, `get_policy_rule`, `get_proposal`, `get_audit` (payloads: DATA_MODEL §6).
All use direct key lookup. Views never mutate state, never use `latest_*`.

### 3.3 Identity derivation is client-reproducible

Clients compute `workspace_id`, `source_commitment`, `proposal_id` and `audit_id` **off-chain** from the normative encoding
(DATA_MODEL §3) before sending transactions, so no wallet-activity diffing or "latest record" lookup is ever needed
(Pattern D). Golden vectors and a reference implementation ship with the docs/tests.

## 4. Lifecycle and state transitions

```text
Workspace:  (none) ──create_workspace──► exists (current_policy_version = 0)
PolicyVer:  v(n) ──publish_policy(new_version = n+1)──► v(n+1)        (v(n) never changes)
Proposal:   (none) ──register_proposal──► REGISTERED ──audit_proposal (consensus OK)──► AUDITED   (terminal)
Audit:      (none) ──written once, after consensus──► exists          (never overwritten, never deleted)
```
There is no transition out of `AUDITED` and none that re-opens a proposal. A corrected proposal is a **new** proposal.

## 5. Control flow of the audit (summary; details in CONSENSUS_DESIGN §5–§8)

```text
 deterministic pre-phase (validate, authorize, recompute commitments, segment, derive audit_id, build Snapshot)
        │                                  nothing written
        ▼
 gl.vm.run_nondet(leader_fn, validator_fn)   ← one LLM call per node; closures over Snapshot only
        │  fail / disagree ⇒ no state change
        ▼
 deterministic post-phase (re-validate, derive quotes/verdict/commitment, re-check audit_id, WRITE)
```

## 6. Storage-to-memory transition (STO-07, Directive §16)

1. Read the bound `PolicyVersion` by key `f"{workspace_id}:{version}"`.
2. `pv = gl.storage.copy_to_memory(self.policy_versions[key])`.
3. Convert to plain tuples (`rules`), build `segments` from the supplied text, assemble `Snapshot`.
4. `leader_fn`/`validator_fn` capture only the Snapshot (and module-level constants/functions). A static test greps both closures'
   source for `self` and a runtime test uses `check_pickling = True`.

## 7. Errors

| Class | Raised as | Examples |
|---|---|---|
| Business | `gl.vm.UserError("[EXPECTED] CODE[: field]")` before any write | `WORKSPACE_NOT_FOUND`, `NOT_FOUND`, `UNAUTHORIZED`, `INVALID_INPUT`, `LIMIT_EXCEEDED`, `VERSION_CONFLICT`, `RULE_DUPLICATE`, `WORKSPACE_EXISTS`, `PROPOSAL_EXISTS`, `AUDIT_EXISTS`, `SOURCE_COMMITMENT_MISMATCH`, `POLICY_COMMITMENT_MISMATCH` |
| Evaluation | `EvaluationError` → leader: `UserError("[LLM_ERROR] CODE")`; validator: `False` | `BAD_SHAPE`, `BAD_STATUS`, `BAD_REASON`, `BAD_COMBINATION`, `MISSING_FINDING`, `DUPLICATE_FINDING`, `BAD_EVIDENCE`, `BAD_ELEMENT_ID` |
| Transient | `UserError("[TRANSIENT] LLM_UNAVAILABLE")` (leader) / `False` (validator) | `NondetException` from `exec_prompt` |
| Consensus | protocol-level (leader rotation, *undetermined*) | validator disagreement, leader failure |
| Runtime | VM-generated (`VMError`) | resource exhaustion, serialization |

Rules: codes are stable strings with deterministic detail only (the platform compares error messages strictly); no stack traces;
no `except Exception: pass`; no exception becomes a default or compliant value (ERR-03).

## 8. Concurrency and idempotence (Directive §32)

POLISCOPE assumes **nothing** about transaction ordering or locking and instead makes every operation order-independent where it matters:

| Scenario | Behavior |
|---|---|
| Two users audit different proposals | Disjoint keys (`audit_id` differ); both can succeed independently |
| Two users audit the **same** proposal concurrently | Same `audit_id`; first successful write wins; the other fails `AUDIT_EXISTS` (checked in P7 **and again** in P13 after consensus) |
| Duplicate transaction submission / repeated call | `AUDIT_EXISTS` / `PROPOSAL_EXISTS` / `WORKSPACE_EXISTS`; no overwrite |
| Retry after undetermined/failed consensus | Allowed; nothing was written |
| New policy version published during an audit | The audit uses the version **bound** at registration; the new version cannot affect it |
| Same wallet submits several proposals | Distinct `client_nonce` ⇒ distinct IDs; client knows each ID in advance |
| Overlapping `publish_policy` | Compare-and-set on `new_version`; the loser fails `VERSION_CONFLICT` |
| Retrieval during overlapping writes | Views are keyed lookups; no shared "latest" state |

Only shared mutable scalars: `Workspace.current_policy_version` (guarded by compare-and-set) and `Workspace.proposal_counter`
(informational, never used for identity). Real StudioNet ordering behavior is **UNVERIFIED** and is to be tested, not assumed (BLOCKED).

## 9. Atomicity discipline (STO-06)

Every write method follows **validate → derive → check → write**. No method writes anything before its last possible failure.
Correctness never depends on platform rollback of a partial write (rollback semantics are described only in
generation-mixed documentation pages; a direct-mode test will assert byte-identical state after each failure class).

## 10. Resource boundaries (NFR-INP-05, NFR-RES-*)

Every loop is bounded by a constant: rules ≤ LIM-RULES; elements ≤ LIM-ELEMS; segments ≤ LIM-SEGMENTS; evidence ≤ LIM-EVIDENCE;
text ≤ LIM-TEXT. The segmenter is single-pass O(n) with no regex and no whitespace back-scan. Hashing is O(n) over ≤ LIM-TEXT.
Per audit and per node: 1 LLM call, 1 text hash, 1 policy hash, 1 segmentation, 1 report hash. Costs are **UNMEASURED inside GenVM** (DATA_MODEL §1).

## 10a. Cost note on commitments

Keccak-256 here is pure Python. The text is hashed at registration and again at every audit on **every** validating node; the
proposal size limit is therefore the dominant resource parameter and is intentionally conservative until measured.

## 11. Deployment shape

`__init__(self): pass`; `ctor_params: 0`; empty storage. First workspace is created by the first user. No seed data, no keys, no
addresses (DEP-01/02). Deployment itself is **not performed** (DEC-06).

## 12. Explicitly rejected architectural alternatives

| Alternative | Reason rejected |
|---|---|
| LLM writes quotations/offsets | Fabrication risk, unbounded text variance, forces fuzzy matching (DEC-02 solves it) |
| Store full proposal text | Storage cost; commitment + re-supply already gives integrity (FR-PRO-07) |
| Global counters / `latest_*` for IDs | Pattern D (wrong-record association) |
| `prompt_comparative`/`non_comparative` wrappers | LLM-judged equivalence over material fields (§9.3 CONSENSUS_DESIGN) |
| `run_nondet_default` | Sandbox with storage-write permission; error-agreement path (CONSENSUS_DESIGN §3) |
| Score or free-text recommendations | Cross threshold with broad-category agreement (Pattern B) |
| One contract per workspace / factory | Not required; adds cross-contract surface |
| Legacy-runner parallel variant | DEC-01/EXC-07: no evidence two variants are necessary |
