# POLISCOPE — Requirements Specification (Phase 3)

Status: **DRAFT FOR REVIEW — no implementation has started.**
Runner baseline: **legacy `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`** (DEC-07, header `# v0.2.16`), because the owner's Studio failed to
load the new-generation build (RESEARCH §0b). Deployment and StudioNet integration remain **blocked in this sandbox**; nothing was deployed by me.

Requirement language: MUST / MUST NOT / SHOULD. Every requirement has a stable ID and is
traced to design (ARCHITECTURE.md, CONSENSUS_DESIGN.md, DATA_MODEL.md) and to tests
(TEST_MATRIX.md, created in Phase 8 from the IDs below).

---

## 0. Binding decisions from the project owner (2026-11-17)

| ID | Decision |
|---|---|
| DEC-01 | Develop on runner `5jycge4q…`. Do **not** assume StudioNet serves it. Deployment and real-network integration stay **blocked/unmarked** until confirmed. **No legacy-generation implementation** is created preemptively. |
| DEC-01a | **PROPOSED, NOT APPROVED.** Switch the baseline to `kzybg95x…` (bundle `v0.6.0-rc15`): it is the hash in the SDK reference `main`, is flagged by the linter as the newest runner, and passes lint/validate and 6/6 direct probe tests; `5jycge4q…` is no longer resolvable by default tooling. Until approved, DEC-01 stands. |
| DEC-01a-status | **REVERSED (2026-11-19).** It was applied provisionally and was wrong for the owner's Studio: the new-generation build failed there with "Could not load contract schema". |
| DEC-07 | **The deployed runner is the LEGACY `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`** (header `# v0.2.16`), with `from genlayer import *` syntax, `genlayer-test==0.29.2`. Evidence: owner's Studio and reference example. See RESEARCH §0b. |
| DEC-02 | Evidence is represented by **deterministic, numbered proposal segments**. The LLM references segment IDs; it never writes quotations. The contract derives exact quotations from the original source. |
| DEC-03 | The consensus design MUST NOT be weakened to improve liveness: no approximate matching, no score-based acceptance, no relaxed validation. The strict design is evaluated first by adversarial and liveness tests. Any relaxation is **proposed in writing and reviewed before implementation** (see CONSENSUS_DESIGN.md §9, Relaxation Register). |
| DEC-04 | Engineering documentation, requirements, architecture, test specs and code comments are in **English**. Communication with the owner is in Spanish. |
| DEC-05 | POLISCOPE MUST accept proposals and policies written in **Spanish and English** (and not artificially restrict language). |
| DEC-06 | Do not deploy anything; do not begin contract implementation until requirements and architecture are reviewed. |

---

## 1. Explicit exclusions (EXC)

| ID | Requirement |
|---|---|
| EXC-01 | The repository MUST NOT contain a frontend, backend, REST API, dashboard, GenLayerJS/TypeScript application code, external database, indexer, auth service or third-party document storage. |
| EXC-02 | V1 MUST NOT parse HTML, scrape web pages, extract PDFs, fetch external documents or call `gl.nondet.web`. Input is caller-supplied plain text only. |
| EXC-03 | V1 MUST NOT include multi-signature governance, delegation, voting, treasury execution, administrator transfer, or recommendations/numeric scores. |
| EXC-04 | The contract MUST NOT claim a workspace is a "verified DAO". |
| EXC-05 | The contract MUST NOT be payable and MUST NOT hold funds. |
| EXC-06 | No contract dependency beyond the single-file `py-genlayer` runner and the Python standard-library modules proven available in GenVM (see NFR-DET-04). |
| EXC-07 | Exactly **one** supported contract exists: the legacy-generation `contracts/poliscope.py` (DEC-07). The archived new-generation build under `variants/` is unsupported and must not be deployed or extended. |

---

## 2. Functional requirements

### 2.1 Workspace registry (FR-WS)

| ID | Requirement |
|---|---|
| FR-WS-01 | `create_workspace(name, client_nonce)` MUST create a workspace whose ID is `workspace_id = H(WORKSPACE, creator, client_nonce)` (DATA_MODEL §3). |
| FR-WS-02 | The creator (`gl.message.sender_address`) MUST become the sole administrator. The administrator is immutable in V1. |
| FR-WS-03 | Creating a workspace whose ID already exists MUST fail with `[EXPECTED] WORKSPACE_EXISTS` and change nothing. |
| FR-WS-04 | Workspace creation MUST NOT depend on any other workspace's state and MUST NOT use a global counter or "latest" pointer for identity. |
| FR-WS-05 | `name` MUST be non-empty after validation and ≤ LIM-WS-NAME bytes. |
| FR-WS-06 | A workspace record MUST store: `workspace_id, administrator, name, current_policy_version (u32, 0 = none), proposal_counter (u32, informational only)`. Creation timestamps are **omitted** (no invariant needs them; timestamp consensus semantics unverified). |
| FR-WS-07 | An administrator MAY be a contract address; the authority check is on `gl.message.sender_address` only. (Cross-contract calling behavior is UNVERIFIED and is not required for correctness.) |

### 2.2 Policy registry (FR-POL)

| ID | Requirement |
|---|---|
| FR-POL-01 | `publish_policy(workspace_id, new_version, rules)` MUST be callable only by the workspace administrator, else `[EXPECTED] UNAUTHORIZED`. |
| FR-POL-02 | `new_version` MUST equal `current_policy_version + 1`, else `[EXPECTED] VERSION_CONFLICT`. (Compare-and-set; removes ambiguous version transitions under overlapping publishes.) Versions start at 1. |
| FR-POL-03 | A published version is **immutable**: no method may modify or delete a stored policy version or its rules. |
| FR-POL-04 | Each rule MUST be an atomic, independently evaluable obligation with the schema in DATA_MODEL §2.2: `rule_id, title, requirement_text, scope, evaluation_guidance, required_elements[], prohibited_conditions[]`. |
| FR-POL-05 | Rule IDs MUST be unique within a version, match the charset in LIM-RULE-ID, and be stable for the version. Duplicates → `[EXPECTED] RULE_DUPLICATE`. |
| FR-POL-06 | `required_elements` and `prohibited_conditions` entries are `{id, description}` with IDs unique **within their rule** (charset LIM-ELEM-ID). These IDs are the only vocabulary the evaluator may use for missing elements / prohibited hits (CON-SCHEMA-05). |
| FR-POL-07 | The publisher MUST reject: empty/whitespace-only `requirement_text`; zero rules; more than LIM-RULES rules; any field exceeding its limit; unknown keys; wrong types (including `bool` for ints, `float` anywhere); hostile characters (NFR-INP-03). Reject, never silently repair. |
| FR-POL-08 | `policy_set_commitment` MUST be computed over the complete canonical encoding of all rules (DATA_MODEL §3.4) and stored with the version. |
| FR-POL-09 | Publishing a new version MUST NOT alter any existing proposal or audit. Proposals stay bound to the version chosen at registration. |
| FR-POL-10 | Policy authoring guidance (atomicity, closed element IDs) MUST be documented in README/KNOWN_LIMITATIONS because rule quality bounds consensus liveness. |

### 2.3 Proposal registration (FR-PRO)

| ID | Requirement |
|---|---|
| FR-PRO-01 | `register_proposal(workspace_id, policy_version, title, client_nonce, proposal_text)` MUST validate all inputs (NFR-INP) before any write. |
| FR-PRO-02 | The referenced workspace and policy version MUST exist (any published version ≤ current is selectable). |
| FR-PRO-03 | The contract MUST compute `source_commitment = H(SOURCE, proposal_text)` over the **exact** UTF-8 bytes, with **no normalization** (no NFC/NFD, no whitespace trimming, no line-ending changes). |
| FR-PRO-04 | `proposal_id = H(PROPOSAL, workspace_id, policy_version, submitter, source_commitment, client_nonce)`. The caller can compute it off-chain **before** submitting. |
| FR-PRO-05 | A duplicate `proposal_id` MUST fail `[EXPECTED] PROPOSAL_EXISTS`. A corrected proposal MUST be registered as a new proposal (new nonce and/or new text); nothing is ever replaced. |
| FR-PRO-06 | Registration MUST run the segmenter (DATA_MODEL §4) and reject proposals that would exceed LIM-SEGMENTS, so every registered proposal is auditable. It stores `segment_count`. |
| FR-PRO-07 | The full proposal text MUST NOT be persisted. Stored: `proposal_id, workspace_id, submitter, policy_version, source_commitment, text_length_bytes, segment_count, title, state, audit_id`. |
| FR-PRO-08 | The proposal `title` is stored but MUST NOT be sent to any LLM (reduces injection surface; not needed for evaluation). |
| FR-PRO-09 | Registration is permissionless (any address may register in any workspace). Spam is bounded per record (LIM-*) but not by aggregate cap (accepted; see KNOWN_LIMITATIONS KL-05). |
| FR-PRO-10 | Proposal state is a closed enumeration: `REGISTERED` → `AUDITED`. No other transition exists. |

### 2.4 Audit execution (FR-AUD)

| ID | Requirement |
|---|---|
| FR-AUD-01 | `audit_proposal(proposal_id, proposal_text)` MUST resolve the exact proposal and its **bound** policy version (never the latest). |
| FR-AUD-02 | Authorization: the caller MUST be the proposal's submitter **or** the workspace administrator, else `[EXPECTED] UNAUTHORIZED`. Submitter-ownership is not otherwise treated as audit authority; reading is public. (Open question OQ-01.) |
| FR-AUD-03 | The contract MUST recompute `source_commitment` from the supplied text and compare to the stored value; any byte difference → `[EXPECTED] SOURCE_COMMITMENT_MISMATCH`. |
| FR-AUD-04 | The contract MUST recompute `policy_set_commitment` from the stored rules and compare to the stored value → else `[EXPECTED] POLICY_COMMITMENT_MISMATCH`. |
| FR-AUD-05 | The contract MUST recompute segments; `len(segments)` MUST equal stored `segment_count`. |
| FR-AUD-06 | `audit_id = H(AUDIT, workspace_id, proposal_id, source_commitment, policy_version, policy_set_commitment, SCHEMA_VERSION, PROMPT_VERSION, SEGMENTATION_VERSION)`. If it already exists → `[EXPECTED] AUDIT_EXISTS` (deterministic duplicate handling; **no overwrite, ever**). |
| FR-AUD-07 | The audit MUST build an immutable in-memory snapshot (CON-BND-*) **before** the nondeterministic block. |
| FR-AUD-08 | Consensus uses exactly one `gl.vm.run_nondet` per audit (CON-PROC-*). |
| FR-AUD-09 | **No state change** associated with a successful audit may occur before consensus succeeds; a failed/undetermined/rejected audit MUST leave all state byte-identical (STO-06). |
| FR-AUD-10 | After consensus the contract MUST: re-validate the result; derive quotations from segments; derive the global verdict; compute the report commitment; re-check `audit_id` absence; then persist the audit and mark the proposal `AUDITED`. |
| FR-AUD-11 | A proposal MUST have at most one audit per deployed contract (its `audit_id`). Re-evaluating the same text requires registering a new proposal (new ID). |

### 2.5 Retrieval (FR-RET)

| ID | Requirement |
|---|---|
| FR-RET-01 | Read-only views MUST exist for: workspace, policy-version metadata, individual policy rule (by index), proposal, audit (including all findings, evidence references with derived quotations, and the report commitment). |
| FR-RET-02 | Every view MUST resolve by exact ID/key via direct map lookup. No view may use "latest", wallet-keyed lists or insertion order to choose a record. |
| FR-RET-03 | Unknown IDs → `[EXPECTED] NOT_FOUND`. Views MUST NOT mutate state. |
| FR-RET-04 | Retrieval MUST allow an independent verifier holding the original text to recompute `source_commitment`, every quotation, the verdict and `report_commitment` and compare them with stored values. |

---

## 3. Findings and evidence model (EVD / CON-SCHEMA)

| ID | Requirement |
|---|---|
| EVD-01 | Status is a closed enum: `SATISFIED, VIOLATED, INDETERMINATE, NOT_APPLICABLE`. |
| EVD-02 | Reason code is a closed enum: `REQUIREMENT_SATISFIED, REQUIREMENT_CONTRADICTED, MANDATORY_ELEMENT_MISSING, PROHIBITED_CONDITION_PRESENT, INSUFFICIENT_EVIDENCE, AMBIGUOUS_REQUIREMENT, OUT_OF_SCOPE`. |
| EVD-03 | The status × reason × cardinality compatibility table in DATA_MODEL §5.2 MUST be enforced **deterministically** on every finding (leader, validator-local and post-consensus). |
| EVD-04 | Every rule has **exactly one** finding; none omitted, none duplicated, none unknown. |
| EVD-05 | Evidence is a list of **segment IDs** (u32). The contract derives `{segment_id, start, end, quote}` from the segmentation of the exact source. The LLM MUST NOT supply any text that is persisted. |
| EVD-06 | Evidence IDs MUST be integers (not bool/float/str), unique, in `[0, segment_count)`, and refer to **citable** segments (≥ LIM-CITABLE-ALNUM alphanumeric characters). Violations reject the whole report. |
| EVD-07 | Evidence is required (≥ 1) only for statuses asserting presence in the text (`SATISFIED`, `REQUIREMENT_CONTRADICTED`, `PROHIBITED_CONDITION_PRESENT`) and MUST be empty otherwise (minimizes free variation between evaluators). |
| EVD-08 | `missing_elements` / `prohibited_hits` entries MUST be IDs declared by that rule in the bound policy version. No free text. |
| EVD-09 | Evidence offsets/quotations are derived and verified deterministically; model-generated offsets are never accepted. |
| EVD-10 | Whether a cited segment actually **supports** the finding is verified by validators through independent re-evaluation and exact agreement on the cited IDs (CON-MAT-03). |
| EVD-11 | Free-form reasoning, recommendations, summaries and numeric scores MUST NOT be requested, accepted or persisted in V1. |
| EVD-12 | The global verdict MUST be computed by contract code with the rules: any `VIOLATED` → `NON_COMPLIANT`; else any `INDETERMINATE` → `INDETERMINATE`; else all `NOT_APPLICABLE` → `NOT_APPLICABLE`; else `COMPLIANT`. An empty finding set is invalid. |

---

## 4. Consensus requirements (CON)

| ID | Requirement |
|---|---|
| CON-PROC-01 | Use the **generic** consensus API of the deployed generation: in the legacy runner that is `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`. In this generation `gl.vm.run_nondet` is the *sandboxed* variant (opposite meaning) and MUST NOT be used. (In the new generation the names are swapped: generic = `run_nondet`, sandboxed = `run_nondet_default`.) |
| CON-PROC-02 | `leader_fn`/`validator_fn` MUST close over plain in-memory data only. They MUST NOT reference `self`, storage views or storage-backed objects. |
| CON-PROC-03 | `leader_fn` performs exactly one `gl.nondet.exec_prompt(..., response_format="json")`, strictly parses and canonicalizes the output, and returns `{bindings…, findings}` — no free text. |
| CON-PROC-04 | `validator_fn` MUST receive the actual leader `Result`; if it is not `gl.vm.Return` it MUST return `False` **before** touching `.calldata`. |
| CON-PROC-05 | `validator_fn` MUST (a) strictly validate the leader report schema and canonical form, (b) compare every binding to its **own** snapshot, (c) re-apply all deterministic finding rules, (d) independently run the evaluation on the same snapshot **without seeing the leader's findings**, (e) compare the two canonical finding lists for exact equality, (f) return `True` only if all pass. |
| CON-PROC-06 | A leader error (`UserError`/`VMError`) MUST NOT finalize an audit (validator returns `False`). A validator evaluation failure MUST NOT be an agreement. An unclassified validator exception MUST NOT become agreement. |
| CON-BND-01 | Bindings compared exactly: `workspace_id, proposal_id, source_commitment, policy_version, policy_set_commitment, schema_version, prompt_version, segmentation_version`. |
| CON-MAT-01 | Material (decision-bearing) fields are compared **exactly**: rule coverage and order, rule IDs, status, reason code, evidence segment IDs, missing-element IDs, prohibited-hit IDs. |
| CON-MAT-02 | Fields **derived** deterministically from agreed material fields and the snapshot (quotations, offsets, verdict, report commitment, audit ID) are recomputed by contract code, never taken from the leader, and need no vote. |
| CON-MAT-03 | **Invariant I-02:** every persisted audit field is either agreed by exact comparison or derived by deterministic code from agreed fields. No third category exists. |
| CON-MAT-04 | No tolerance, fuzzy matching, category-level matching, score threshold or summary-only comparison is permitted (DEC-03). |
| CON-LIM-01 | The contract controls each validator's vote, not the protocol quorum. Documentation MUST NOT claim that a minority disagreement blocks acceptance, nor that validators' intermediate outputs are persisted. |
| CON-LIM-02 | Consensus is not truth: a prompt injection or model bias shared by all nodes passes consensus. Integrity therefore relies on deterministic checks (EVD-03/06/08) plus fixed trusted prompts. Documented as residual risk (THREAT_MODEL R-01). |
| CON-LIV-01 | Liveness MUST be **measured** (agreement rate over a bilingual fixture corpus) before any relaxation is considered (DEC-03, TEST LIV-*). |

---

## 5. Input, language and resource requirements (NFR-INP / NFR-LANG / NFR-RES)

| ID | Requirement |
|---|---|
| NFR-INP-01 | All public-method arguments are type-checked explicitly (`str`, `int` not `bool`, `list`, `dict`) with exact key sets. `float` cannot be encoded as calldata (rejected by the framework before contract code); `bool` can, so the contract MUST validate it itself. |
| NFR-INP-02 | Size limits are measured in **UTF-8 bytes** (LIM-*); a string that cannot be UTF-8-encoded (e.g. lone surrogate) is rejected as `INVALID_INPUT`. |
| NFR-INP-03 | Reject (not strip) hostile characters in all text inputs: C0 controls other than `\t \n \r`, DEL and C1 controls, NUL, soft hyphen, zero-width and bidi-control characters, line/paragraph separators, BOM, private-use, tag characters, surrogates (explicit codepoint ranges in DATA_MODEL §4.1; no dependency on `unicodedata`). |
| NFR-INP-04 | Whitespace-only and empty proposals are rejected. |
| NFR-INP-05 | Every loop over user-influenced data has a constant upper bound; no recursion over user data; no regular expressions over user data; no quadratic string algorithms. |
| NFR-LANG-01 | Proposals and policy text may be Spanish, English or mixed. The contract MUST NOT filter by language or script. Spanish characters (`á é í ó ú ü ñ ¿ ¡`) MUST round-trip exactly. |
| NFR-LANG-02 | The trusted prompt MUST state that data may be Spanish and/or English and that output vocabularies are language-neutral enums/IDs. |
| NFR-LANG-03 | Normalization differences (NFC vs NFD) are treated as **different content** (different commitment). Documented limitation. |
| NFR-LANG-04 | The segmenter is language-neutral (DATA_MODEL §4). Abbreviation-induced over-splitting (e.g. "Dr.", "Sr.", "etc.") is accepted; evidence may cite several segments. |
| NFR-RES-01 | Limits (LIM-*) are centralized constants. Values in DATA_MODEL §1 are **PROVISIONAL and UNMEASURED**; they MUST be confirmed by measurement (Keccak cost, prompt size, serialization, validator cost) before release and any change MUST update the docs and tests. |
| NFR-RES-02 | The audit performs exactly **one** LLM call per node (leader and each validator). Tests assert the call count. |
| NFR-RES-03 | Worst-case persisted size per audit is bounded by constants (LIM-RULES × LIM-EVIDENCE × LIM-SEG-CHARS) and documented. |
| NFR-DET-01 | No `hash()`, `hashlib`, floats, wall-clock time, randomness or iteration over unordered containers in any decision/commitment path. |
| NFR-DET-02 | Commitments use the SDK `gl.Keccak256` with the length-prefixed, type-tagged canonical encoding of DATA_MODEL §3, with golden test vectors and an **independent pure-Python reference implementation in tests**. |
| NFR-DET-03 | Domain separation: `WORKSPACE, POLICY, SOURCE, PROPOSAL, AUDIT, REPORT` (all `:V1`). |
| NFR-DET-04 | Any standard-library module used in contract code MUST be verified to exist in the GenVM runner (not merely on the host). `unicodedata` is **not** assumed (UNVERIFIED) and is avoided. |

---

## 6. Storage requirements (STO)

| ID | Requirement |
|---|---|
| STO-01 | All persistent fields are declared in the contract class body with explicit storage types: `TreeMap`, `DynArray`, `@allow_storage @dataclass`, sized ints (`u8/u32/u64`). No `dict`, `list`, `float` or unbounded `int` is persisted. |
| STO-02 | Storage dataclasses use `@allow_storage @dataclass` from `from genlayer import *`; no alias is needed in the legacy generation (the E014 linter false positive only affects `gl.storage.allow`). |
| STO-03 | New dataclass fields are only ever **appended** (upgrade safety). |
| STO-04 | Records are keyed by deterministic ID strings; composite keys use fixed-width hex IDs so concatenation is unambiguous. |
| STO-05 | No `latest_*` or wallet-indexed list is persisted. |
| STO-06 | **Atomicity discipline:** all validation and derivation happen before the first write of any method; correctness MUST NOT rely on platform rollback of a half-written state (rollback semantics are documented only in generation-mixed pages). |
| STO-07 | Nondeterministic blocks never read or write storage (CON-PROC-02); the storage→memory step uses `gl.storage.copy_to_memory`. |
| STO-08 | Initial state after deployment is empty; the constructor is `def __init__(self): pass`. |

---

## 7. Security requirements (SEC)

| ID | Requirement |
|---|---|
| SEC-01 | Trusted instructions are constants inside the contract; no caller-supplied instruction text. |
| SEC-02 | All untrusted data (policy text, segments) enters the prompt only as JSON-encoded string values inside one data document (quotes, newlines and control characters escaped), bracketed by trusted instructions before **and after** the data. Delimiters alone are not relied upon. |
| SEC-03 | LLM output is validated strictly (exact keys, exact types, closed enums, closed ID sets); malformed output fails closed: **no** key aliases, **no** coercion, **no** regex extraction, **no** repair. |
| SEC-04 | `PROMPT_VERSION`, `SCHEMA_VERSION`, `SEGMENTATION_VERSION` are constants; a test pins a fingerprint of the prompt template so unintended prompt edits fail tests. |
| SEC-05 | Authorization failures never reveal or modify state. |
| SEC-06 | Identifier collisions are cryptographically negligible and, if they occur, are rejected as `*_EXISTS`. |
| SEC-07 | No external calls, no web access, no cross-contract calls. |
| SEC-08 | Error messages are stable codes (`[EXPECTED] CODE`, `[LLM_ERROR] CODE`, `[TRANSIENT] CODE`) with deterministic detail only (error messages are compared strictly by the platform). |

---

## 8. Error requirements (ERR)

| ID | Requirement |
|---|---|
| ERR-01 | Business errors raise `gl.vm.UserError("[EXPECTED] CODE[: detail]")` before any write. |
| ERR-02 | Evaluation errors (malformed/invalid model output) raise `[LLM_ERROR] CODE`; LLM unavailability `[TRANSIENT] CODE`. |
| ERR-03 | Exceptions MUST NOT be converted into compliance or default results; no `except Exception: pass`. |
| ERR-04 | Every failure class has a "state preserved" test (STO-06). |

---

## 9. Deployment requirements (DEP)

| ID | Requirement |
|---|---|
| DEP-01 | Deployable with **no constructor arguments** and no external configuration (`ctor_params: 0`, verified by lint). |
| DEP-02 | The first workspace is created by the first user after deployment; no seed data. |
| DEP-03 | Deployment instructions (docs/DEPLOYMENT.md) are written but **no deployment is executed** without explicit authorization (DEC-06). |
| DEP-04 | StudioNet integration is reported as **BLOCKED** until (a) the network is reachable and (b) the served runner is confirmed compatible. Direct-mode tests MUST NOT be reported as consensus verification. |

---

## 10. Testing requirements (TST)

| ID | Requirement |
|---|---|
| TST-01 | Direct tests run with `direct_vm.check_pickling = True` and `strict_mocks = True` (verified available in 0.30.0rc2 during Phase 8). |
| TST-02 | Consensus tests execute the real `validator_fn` through `direct_vm.run_validator()` with fabricated leader results (matrix C01–C20, extended in TEST_MATRIX). |
| TST-03 | A pure-Python **reference implementation** of encoding, segmentation and verdict aggregation lives in tests and is cross-checked against the contract (golden vectors). |
| TST-04 | Bilingual fixtures (Spanish, English, mixed, accented, NFC/NFD, `¿¡`) cover segmentation, commitments, injection and evaluation flows. |
| TST-05 | A liveness protocol (LIV-*) defines how agreement rate is measured on a real network; results are reported as measurements, with no pre-set pass threshold invented in advance. |
| TST-06 | Test results are reported exactly as executed; blocked suites are labelled BLOCKED. |
| TST-07 | The `tests/conftest.py` workaround for the `mock_llm` JSON defect (RESEARCH D-13) is test-only and documented. |

---

## 11. Acceptance criteria (AC)

| ID | Criterion |
|---|---|
| AC-01 | `genvm-lint check contracts/poliscope.py --json` → `ok:true`, `ctor_params: 0`. |
| AC-02 | All direct tests pass; counts reported by suite. |
| AC-03 | Matrix C01–C20, E01–E13, P*, B*, I*, S*, SEG*, ENC*, U*, L* each have ≥ 1 executed test, none skipped without justification. |
| AC-04 | For each Pattern A–J in the Directive §54, a test shows the failure cannot produce a finalized compliant report. |
| AC-05 | Invariants I-01…I-15 (SECURITY_MODEL §3) each map to ≥ 1 test. |
| AC-06 | Source header pins the runner approved under DEC-01/DEC-01a; static test rejects legacy names and unpinned aliases. |
| AC-07 | Integration/StudioNet items remain **unchecked** until real evidence exists; the Directive's pre-ticked "deployed in StudioNet" box is treated as unchecked. |
| AC-08 | `KNOWN_LIMITATIONS.md` lists every unverified compatibility item and every accepted residual risk. |
