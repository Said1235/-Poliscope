# POLISCOPE — Security Model (Phase 5)

Status: **DRAFT FOR REVIEW.** Attack-by-attack analysis is in THREAT_MODEL.md.

---

## 1. Assets

| Asset | Property to protect |
|---|---|
| Audit records | integrity (never forged, altered, overwritten, mis-associated) |
| Policy versions | immutability and exact binding to proposals |
| Proposal commitments | binding to the exact original bytes |
| Contract state | no partial/ghost writes from failed or undetermined operations |
| Validator/LLM budget | bounded work per transaction |

## 2. Actors and trust

| Actor | Trusted for | Not trusted for |
|---|---|---|
| Workspace administrator | choosing policy **content** and publishing versions | forging audits, editing published versions, auditing other workspaces |
| Proposal submitter | nothing | proposal text/title, identity claims, any instruction embedded in text |
| Third party | nothing | everything (read-only access only; cannot register-in-name-of, audit, or publish) |
| Leader node | proposing a candidate | the correctness of its result — every material field is independently reproduced |
| Validator node | independent evaluation | being identical to the leader (different model/provider allowed) |
| LLM provider(s) | producing candidate judgments | determinism, honesty, injection resistance |
| GenLayer protocol | majority consensus, leader rotation, *undetermined* on failure ([DOC]) | contract-specific correctness |

Out of scope for V1: DAO identity verification, validator collusion beyond the protocol's assumptions, cryptographic breaks of Keccak-256,
compromise of an administrator's key.

## 3. Invariants (each must map to ≥ 1 test — AC-05)

| ID | Invariant |
|---|---|
| I-01 | An `AuditRecord` exists only if `run_nondet` returned successfully; every write occurs after it. |
| I-02 | Every persisted audit field is either **agreed** (bindings, findings: exact equality of independent evaluations) or **derived** by deterministic code from agreed fields + the snapshot. |
| I-03 | A published policy version is never modified; every audit uses the version **bound** at registration, with its commitment recomputed. |
| I-04 | `source_commitment` is recomputed from the exact supplied bytes on every audit; the full text is never stored; one differing byte ⇒ rejection. |
| I-05 | All identifiers derive from content/identity via domain-separated Keccak; no record is ever overwritten; no `latest_*`/wallet-indexed lookup exists. |
| I-06 | `global_verdict` is a pure function of a complete, valid finding set, computed by contract code only. |
| I-07 | Every persisted quotation is an exact substring of the committed source, derived by code from a verified segment ID; the LLM never supplies persisted text. |
| I-08 | Nondeterministic functions never access `self`, storage proxies or storage-backed objects. |
| I-09 | Every loop and every input size is bounded by a constant (LIM-*). |
| I-10 | Fail-closed: any invalid, unknown, missing or erroring input/output yields rejection with no state change — never a default, never compliance. |
| I-11 | A report has exactly one finding per rule, in policy order, with a (status, reason, cardinality) combination allowed by DATA_MODEL §5.2. |
| I-12 | No `float`, `hash()`, `hashlib`, wall-clock time, randomness or unordered iteration influences any decision or commitment. |
| I-13 | Every write method validates and derives first and writes last; a failure leaves state byte-identical. |
| I-14 | Each state-changing method enforces its authorization (matrix §4); the administrator is immutable in V1. |
| I-15 | Untrusted text reaches the LLM only as JSON-escaped data inside one data document, between fixed trusted instructions; the proposal title never reaches the LLM. |

## 4. Authorization matrix

| Method | Anyone | Submitter | Administrator |
|---|---|---|---|
| `create_workspace` | ✔ (becomes administrator of the **new** workspace) | — | — |
| `publish_policy` | ✘ | ✘ | ✔ (own workspace only) |
| `register_proposal` | ✔ | ✔ | ✔ |
| `audit_proposal` | ✘ | ✔ (own proposal) | ✔ (any proposal in own workspace) |
| all `get_*` views | ✔ | ✔ | ✔ |

Rationale for `audit_proposal` (OQ-01): an audit is permanent (one per proposal, FR-AUD-11). Allowing any third party would let a griefer
burn a proposal's single audit slot at a moment of their choosing (e.g. during an LLM outage-induced undetermined streak is harmless, but
a lucky `INDETERMINATE` would be recorded permanently). Ownership of a proposal and authority to audit are kept **separate in code** (two explicit checks).

## 5. Security controls by layer

| Layer | Controls |
|---|---|
| Input | explicit type checks (`bool`≠`int`, no `float`), exact key sets, byte limits, hostile-code-point rejection (explicit ranges), whitespace-only rejection |
| Identity | domain-separated, length-prefixed, type-tagged Keccak encoding; caller-chosen nonces; duplicate ⇒ reject |
| Authorization | sender-based checks on every state-changing method; admin immutable |
| Integrity | source/policy commitments recomputed per audit; report commitment over every persisted material field |
| Prompting | fixed trusted constants; escaped JSON data document; instructions after the data; title never sent; fixed decision procedure with fail-safe tie-break ("uncertainty never resolves to `SATISFIED`") |
| Output | exact keys/types, closed enums, closed ID sets, evidence IDs verified deterministically, status×reason×cardinality table |
| Consensus | actual leader `Result` inspected; bindings vs own snapshot; deterministic rules re-applied; independent evaluation; exact equality |
| State | validate → derive → check → write; duplicate re-check after consensus; no `latest_*` |
| Resources | constant-bounded loops, single LLM call per node, O(n) segmenter, bounded report size |
| Errors | stable codes; no swallowed exceptions; no default-to-compliant |

## 6. Residual risks (accepted, documented, and **not** claimed solved)

| ID | Risk | Why it remains | Mitigation / disclosure |
|---|---|---|---|
| R-01 | **Shared bias or shared prompt injection**: all nodes (same/similar model) misjudge identically and agree. | Consensus verifies *agreement*, not truth. | Fixed trusted prompt, minimized output space, deterministic structural checks, public policy/commitments enabling independent re-audit; never claim injection is "solved" (Directive §29). |
| R-02 | **Liveness under strict equality**: ambiguous text/rules may repeatedly end *undetermined*. | Deliberate (DEC-03). | Measured by LIV-* before any relaxation; levers SL-01…SL-05; Relaxation Register R-01 (not approved). |
| R-03 | Platform behaviors unverified on the target network (rollback semantics, validator-exception handling, ordering, tx size, cost). | StudioNet unreachable; runner compatibility unconfirmed (DEC-01). | State-preserving design (I-13); explicit BLOCKED labelling; tests to run when reachable. |
| R-04 | Policy quality: non-atomic or ambiguous rules produce `INDETERMINATE` or disagreement. | Policy content is administrator-authored. | Rule schema, authoring guidance, closed element IDs. |
| R-05 | Registration spam grows storage. | No aggregate cap by design (a cap would be a denial-of-service lever). | Per-record bounds; fees (UNVERIFIED on StudioNet); KL-05. |
| R-06 | Administrator key loss or wrong administrator address freezes policy publishing. | No admin transfer in V1 (EXC-03). | Existing versions remain auditable; documented. |
| R-07 | NFC/NFD, hostile-code-point rejection and over-splitting change what is accepted or cited. | Exact-byte commitments; rejection instead of normalization. | Documented (KL-06/07/08); bilingual fixtures. |
| R-08 | A single colluding/compromised majority of validators. | Protocol-level assumption. | Out of scope; appeal process per protocol. |

## 7. Security testing obligations

Every threat in THREAT_MODEL.md has a planned test ID; every invariant has ≥ 1 test; direct-mode results are **never** reported as network-consensus
evidence; the adversarial review (Phase 10) must attempt to construct inputs and execution sequences that break I-01…I-15.
