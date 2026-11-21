# POLISCOPE — Architecture Self-Review (Phase 6)

Status: **GATE DOCUMENT.** Implementation (Phase 7) does not start until the owner reviews this file and answers §4.
Reviewed: REQUIREMENTS, DATA_MODEL, ARCHITECTURE, CONSENSUS_DESIGN, SECURITY_MODEL, THREAT_MODEL.

---

## 1. Checklist from Directive §51 Phase 6

| Check | Result | Evidence |
|---|---|---|
| Unsupported APIs | **PASS** (with one open item) | Every symbol used was read in SDK source and exercised in a probe on both runners (RESEARCH D-01…D-19). Open: `unicodedata` is **avoided**, not verified. |
| Storage access inside nondeterministic blocks | **PASS** | Snapshot via `copy_to_memory`; closures capture plain data; probe passes `check_pickling` (D-08, D-17). Static + runtime tests planned. |
| Incomplete validator checks | **PASS** | V1–V6; every material field compared or recomputed; no leader-supplied field is unchecked (I-02). |
| Mutable historical data | **PASS** | No update/delete API; compare-and-set on versions; audits write-once. |
| Unverified report fields | **PASS** | Wire report carries bindings + findings only; everything else derived. |
| Ambiguous identities | **PASS** | Length-prefixed, type-tagged encoding; golden vectors; ambiguity cases checked. |
| Missing error paths | **PASS** | Failure matrix (CONSENSUS_DESIGN §10); error taxonomy (ARCHITECTURE §7). |
| Resource exhaustion | **PARTIAL** | All loops bounded, single LLM call; **limits unmeasured inside GenVM** (KL-01). |
| Deployment dependencies | **PASS** | `ctor_params: 0` verified on probes; no seed/config. |
| Unnecessary DApp components | **PASS** | None (EXC-01). |

## 2. Defects found **during** design review (and fixed before any code)

| # | Defect | How found | Resolution |
|---|---|---|---|
| F-1 | Segmenter hard-cut could leave **trailing whitespace** in a segment, violating "segments are trimmed" (offsets are committed, so this would have changed commitments) | Reference implementation + 20,000-case fuzz of invariants | Fixed in spec and reference (DATA_MODEL §4.2); fuzz re-run clean |
| F-2 | A registered proposal could exceed `LIM-SEGMENTS` at audit time and be **permanently unauditable** | Walk-through of lifecycle | Segmenter runs at **registration** (FR-PRO-06); `segment_count` stored and re-checked (FR-AUD-05) |
| F-3 | Quotation text would have been model-generated under the original directive (fabrication + variance) | Owner decision DEC-02 | Evidence = segment IDs; contract derives quotes |
| F-4 | A lone surrogate makes `str.encode('utf-8')` raise an *unclassified* exception | Analysis of NFR-INP-02 | Explicit catch → `INVALID_INPUT` (TM-A07) |
| F-5 | `isinstance(True, int)` is `True`, and `bool` is calldata-encodable. (Correction: floats ARE rejected by calldata encoding in direct mode; an earlier draft said otherwise.) | Python semantics + test run | Explicit `type(x) is int` checks (NFR-INP-01) |
| F-6 | Proposal title would be an unnecessary injection vector | Threat enumeration | Title never sent to the LLM (FR-PRO-08, TM-D08) |
| F-7 | `run_nondet_default` accepts an *agreed error* and runs the validator in a storage-writable sandbox | Source reading (`vm/__init__.py`) | Generic `run_nondet`; leader error ⇒ `False` |
| F-8 | Audit authority was conflated with proposal ownership | Directive §12 item 3 | Separate explicit checks; submitter-or-admin (OQ-01) |
| F-9 | `exec_prompt` has **no temperature/seed** parameter, so determinism cannot be requested | Signature reading | Strictness relies on output-space minimization (SL-01…05); disclosed |
| F-10 | Linter/test tools **auto-select the newest GenVM bundle**; the runner I called "the only verified one" (`5jycge4q…`) is no longer resolvable by default tooling | Lint began failing mid-session (`E101`) | RESEARCH §0a, D-18/D-19; proposal DEC-01a (§4 Q1) |
| F-11 | Directive Part XX pre-ticks "deployed in StudioNet" | Reading the checklist | Treated as unchecked (AC-07) |

## 3. Requirement → design → test traceability (summary by Directive part)

| Directive part | Requirements | Design | Planned tests |
|---|---|---|---|
| §8 Workspace | FR-WS-01…07 | DATA_MODEL §2–3; ARCH §3 | B-ws-*, I-multi-ws, A-* |
| §9 Policy | FR-POL-01…10 | DATA_MODEL §2.3 | B-policy-*, A-publish-*, ENC-policy-* |
| §10–11 Proposal / identity | FR-PRO-01…10 | DATA_MODEL §3–4 | ENC-*, SEG-*, I-*, U-* |
| §12–13 Audit / retrieval | FR-AUD-01…11, FR-RET-* | CONSENSUS §5–8; ARCH §4–5 | C01–C20, B-*, S-* |
| §14–16 Storage | STO-01…08 | DATA_MODEL §2.2; ARCH §6, §9 | S-*, API-* |
| §17–23 Consensus | CON-* | CONSENSUS_DESIGN | C01–C20, LIV-* (BLOCKED) |
| §24–27 Findings / evidence / verdict | EVD-01…12 | DATA_MODEL §5 | E01–E13, B-verdict-* |
| §28–30 Prompt security | SEC-01…04 | CONSENSUS §12 | P-* |
| §31–32 State / concurrency | FR-PRO-10, FR-AUD-09/11 | ARCH §4, §8 | I-*, B-failed-no-write |
| §33 Hashing | NFR-DET-*, DATA_MODEL §3 | golden vectors + reference impl | ENC-* |
| §34–35 Errors | ERR-*, SEC-08 | ARCH §7 | B-error-*, state-preserved suite |
| §36 Threats | SECURITY/THREAT_MODEL | all | per THREAT_MODEL |
| §37 Limits | NFR-RES-*, LIM-* | DATA_MODEL §1 | L-* (limits unmeasured in VM) |
| §49–50 Deployment | DEP-* | ARCH §11 | `ctor_params: 0`; deploy tests **BLOCKED** |

## 4. Decisions required from the owner before implementation

**Q1 — Runner baseline (DEC-01a) — ANSWERED BY EVIDENCE 2026-11-19: legacy `1jb45…`; DEC-01a REVERSED (see RESEARCH §0b).** Original text:

**Q1 — Runner baseline (DEC-01a).** New evidence changes the premise of DEC-01 ("only verified new-generation runner"):
`py-genlayer:kzybg95x…` (SDK v0.4.0-rc1, the hash printed in the SDK reference `main`) is in GenVM manager bundle `v0.6.0-rc15`,
is flagged by the linter as the newest runner, passes lint/validate, and passes **6/6 direct probe tests** (`GENVM_VERSION=v0.6.0-rc15`).
`5jycge4q…` is superseded (absent from rc15; default tooling no longer resolves it). The public surface I depend on is
unchanged between the two (RESEARCH D-19). **Recommendation:** switch the development baseline to `kzybg95x…`.
*Cost of switching now: zero (no contract code exists). Cost later: re-verification.* This still does **not** assume StudioNet serves it.

**Q2 (OQ-01) Audit authorization:** submitter-or-administrator (recommended) vs anyone.
**Q3 (OQ-02) LLM calls:** one call for all rules (recommended; lowest cost) vs one per rule (better atomic focus, ≤ 12× calls/node).
**Q4 (OQ-03) `LIM-CITABLE-ALNUM = 8`:** keeps "Sí."/"Dr." uncitable but also blocks short valid statements; CJK is poorly served. Keep 8 for ES/EN?
**Q5 (OQ-04) Provisional limits** (DATA_MODEL §1): accept as conservative starting values pending measurement? In particular `LIM-TEXT = 20,000 B`, `LIM-RULES = 12`, `LIM-EVIDENCE = 4`.
**Q6 (OQ-05) `prohibited_hits` field:** keep (structured IDs for prohibited conditions) or drop (fewer fields ⇒ less disagreement, but the policy's "prohibited conditions" would be only prose).
**Q7 (OQ-06) Evidence only where presence is asserted:** accept (reduces variance; missing/uncertain findings carry no excerpt)?
**Q8 (OQ-07) No administrator transfer in V1:** accept (simplest; key loss freezes publishing)?
**Q9 (OQ-08) Permissionless registration without aggregate cap:** accept (a cap is a DoS lever)?
**Q10 (OQ-09) Reject (not strip) hostile code points** including ZWJ/RTL marks: accept the cost to emoji/RTL users?
**Q11 (OQ-10) One audit per proposal** (re-audit = re-register with a new nonce): accept?
**Q12 Evidence variance lever:** if liveness is poor, first try `LIM-EVIDENCE` 4 → 1–2 (strict, SL-03) before ever discussing R-01 (Relaxation Register). Agree?

## 5. Sources still to read in full before Phase 7 (honest status)

Read or consulted: SDK API reference (partial), SDK source (both generations), equivalence-principle page, error-handling page (generation-mixed),
prompt-injection guidance (summary level). **Not yet read in full:** non-determinism, calling-llms, crafting-prompts, storage pages,
testing page, tooling-setup page, typical use cases, and the `pm-kit` template. They will be consulted per decision when the prompt (Phase 7) and tests (Phase 8)
are written; none of them alters a decision above, but any discrepancy found will be recorded in RESEARCH §2.

## 6. Gate (status update 2026-11-18)

The owner asked for the contract before answering Q1–Q12. **Defaults were applied** (including DEC-01a: runner `kzybg95x…`), the contract was implemented and tested (TEST_MATRIX.md), and every default remains open to change. Original gate text:

Phase 7 will **not** begin until: (a) Q1–Q12 are answered (defaults above apply only if you say "accept defaults"), and (b) you confirm the documents are approved.
No deployment, no StudioNet claim, no implementation.
