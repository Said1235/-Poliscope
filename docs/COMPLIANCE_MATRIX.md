# POLISCOPE — Compliance Matrix against Directive v2

Audited contract: `contracts/poliscope.py` · legacy runner `py-genlayer:1jb45aa8…` · sha256 `28bf8e7eb0412fe2e3724d0f043d0a4e242a5e2d2b6c376420970fcd8811f31a` · 328 direct tests.

Legend: **OK** = implemented and tested (direct mode) · **DEV** = *design deviation* from the directive (an owner decision is needed; not an implementation bug) ·
**PART** = partially met · **BLOCKED** = needs a reachable network · **N/A** = not applicable to V1 · **UNMEAS** = not measured in the real runtime.

## Headline

The implementation is internally consistent and fails closed, **but the evaluation schema is a different (rule-level) design from the element-level design that
directive v2 §12–13 specifies** (DEV-1, DEV-2). Directive v2 §56 Phase 6 says a design of that size needs an explicit review gate before implementation; that
gate did not happen for the schema change, so the contract was **not** rewritten to element-level. This is the single most important decision left for the owner.

## Deviations from directive v2 (owner decision required)

| ID | Directive | What the contract does instead | Effect | Options |
|---|---|---|---|---|
| **DEV-1** | §12 element-level assessment: every required element gets `PRESENT / NOT_PRESENT / AMBIGUOUS`, with separate support and contradiction segment IDs, applicability with evidence | **Rule-level** finding: `status`, `reason_code`, one `evidence_segments` list, closed `missing_elements` / `prohibited_hits` IDs | Less information per audit; fewer fields for validators to disagree on (deliberate, DEC-03 liveness reasoning) | Accept as V1, or approve a V1.1 element-level schema through the design gate |
| **DEV-2** | §13 rule status **derived in code** from element assessments | Status is chosen by the model and **agreed by consensus**; code deterministically validates (status, reason, evidence cardinality, element IDs) compatibility, scope rule (A-4) and derives only the **global** verdict | The model has more authority per rule than the directive allows; still every field is exact-compared across independent evaluators | Same as DEV-1 (they are one design change) |
| DEV-3 | §8 reject rules with **no required elements** | Allowed (a rule may have only prohibited conditions or none) | Weaker rule structure guarantees | Enforce when DEV-1 is adopted |
| DEV-4 | §10.1 segmenter preserves **every source character**, no gaps | Line/sentence segmenter; gaps are **whitespace and line breaks only** (property fuzzed: lossless reconstruction from segments + gaps; nothing else dropped) | Equivalent for integrity of evidence; not a literal partition | A fixed-width code-point segmenter would be literal but would cut sentences |
| DEV-5 | §12.2 `AMBIGUOUS` must carry evidence | `INDETERMINATE` carries **no** evidence (reduces variance) | Less inspectable ambiguity | Revisit with DEV-1 |
| DEV-6 | §7/§9 "creation metadata supported by the runtime" | Omitted (no timestamps) | None for any invariant | Add if a verified runtime source exists |
| DEV-7 | §8 "policy schema version", "creation administrator" stored per version | Schema version is a contract constant bound into `audit_id`; administrator is immutable per workspace | None | Add fields if desired |

## Section-by-section

| Directive §| Requirement (short) | Status | Evidence |
|---|---|---|---|
| 1–2 | Single contract, no DApp/backend | **OK** | repo contains the contract, tests, docs, tooling only |
| 3 | Intended network: stable StudioNet; no silent switching | **BLOCKED** | sandbox cannot reach any network; **nothing deployed** |
| 4 | Zero-argument constructor, empty registries | **OK** | `ctor_params:0` in lint and schema |
| 5–6 | Refresh sources; register; resolve API discrepancy with a probe | **PART** | SOURCE_REGISTER (several doc pages **NOT READ**); legacy probe passed (leader, validator, identical accepted, different rejected, validator exception, leader error, pickling) |
| 6.3 | Pinned verified runner | **PART** | pinned `1jb45…`, verified locally (lint, schema, 328 tests); **not observed loading in the target Studio** |
| 7 | Workspace registry, one administrator, no overwrite | **OK** (DEV-6) | `test_workspace_policy.py` |
| 8 | Immutable versioned policy of atomic rules | **OK** except DEV-3/DEV-7 | CAS versions, immutability tests |
| 9, 9.1 | Exact source commitment; re-submit; **length and commitment** checked before any LLM | **OK** | finding A-1 closed; tests assert no LLM call on mismatch |
| 10 | Deterministic segmentation, IDs not quotes, contract-derived fragments | **OK** (DEV-4) | oracle parity, fuzz, hard-cut regression |
| 10.3 | Evidence relevance independently assessed | **OK** (shared-bias residual R-01) | exact agreement of independent runs |
| 11 | No scores / summaries / recommendations | **OK** | none exist (static + review) |
| 12–13 | Element-level assessment; derived rule status | **DEV-1, DEV-2** | see above |
| 12.1 | `NOT_APPLICABLE` forbidden without explicit applicability | **OK** | finding A-4 closed (deterministic + validator-side) |
| 14 | Global verdict derived in code with the stated precedence | **OK** | 10-combination test; empty/incomplete never `COMPLIANT` |
| 15–17 | Actual leader `Result`; full material check; independent evaluation; fail closed | **OK** (direct mode) | C01–C20; mutants M01–M03, M16 killed |
| 18 | Canonical representation; unambiguous encoding; reject floats/unknown/duplicates | **OK** | encoding oracle, golden vectors, ambiguity tests |
| 19 | No tolerance; liveness investigated | **PART** | strict equality; **liveness UNMEASURED**; relaxation register R-01 not approved |
| 20 | Protocol majority limitation documented | **OK** | CONSENSUS_DESIGN §2 (behaviors themselves **UNVERIFIED** on network) |
| 21–22 | Storage→memory boundary; supported storage types | **OK** | AST proof closures never touch `self`/storage; `check_pickling`; lint |
| 23 | Exact deterministic audit ID; exact lookup; no wallet diff / `latest` | **OK** | identity tests; **write methods now return their exact IDs** (A-2) |
| 24 | No write before consensus; partial records impossible | **OK** (direct mode) | byte-identical state on warmed storage; race test |
| 25 | Verified hashing; domain separation; known vectors | **OK** | EVM Keccak vectors; domains; one-byte sensitivity |
| 26 | Bounded input; **measure in real runtime** | **PART / UNMEAS** | bounds enforced and tested; native timings only (AUDIT §6); limits provisional |
| 26.1 | 300 KB hostile markup | **OK (rejected safely)** | rejected in 0.4 ms before any scan; 300 KB **not claimed supported** |
| 27 | Unicode integrity | **OK** | accents, mixed scripts, NFC/NFD, hostile code points rejected (not normalized) |
| 28–30 | Fixed prompt; injection; strict JSON | **OK** (mocked LLM) | 11 injections; pinned prompt fingerprints; strict fail-closed parser; **real-model behavior UNMEAS** |
| 31–32 | Semantic vs operational failure; error classes | **OK** | stable error codes; no swallowed exceptions (static test) |
| 33, 51 | No external retrieval in V1 | **N/A** | APPLICABILITY_MATRIX |
| 34 | Threat model | **OK** | THREAT_MODEL.md (+ SECURITY_AUDIT) |
| 35–37 | Architecture, diagrams, state machine | **OK** | ARCHITECTURE, STATE_MACHINE (Mermaid A–F) |
| 38–39 | Test layers; **Studio integration** | **Direct: OK · Studio: BLOCKED** | TEST_MATRIX §6, DEPLOYMENT §4 |
| 40 | Consensus matrix C01–C30 | **OK** (C01–C20 mandatory set of the first directive plus extras; the v2 table C01–C30 maps to the same validator checks) | `test_consensus.py` — v2 cases on elements/applicability/contradiction IDs are **N/A** until DEV-1 is resolved |
| 41 | Single-field mutation tests of every material field | **PART** | bindings (10 fields), findings fields, smuggled fields tested; element/applicability mutations N/A (DEV-1) |
| 42 | Exhaustive truth tables | **PART** | global verdict: 10 combinations incl. mixed; element/rule derivation tables N/A (DEV-2) |
| 43–50 | Evidence, source, hostile, injection, identity, authorization, storage, error tests | **OK** | `test_audit`, `test_proposals_commitments`, `test_security`, `test_identity_storage`, `test_workspace_policy` |
| 52 | Property tests | **PART** | segmenter and commitment properties fuzzed with deterministic randomness; no property-testing library used |
| 53–54 | Independent audit + checklist | **OK** | SECURITY_AUDIT.md |
| 56 | Phased workflow with a design-review gate before implementation | **PART** | phases 1–8 executed; the **gate was only partially honored** (owner asked for the contract before answering the open questions; defaults applied, recorded in ARCHITECTURE_REVIEW) |
| 59 | Release blockers | see SECURITY_AUDIT §4 | **not release-ready** |
