# POLISCOPE — Independent Security Audit (final pass)

| | |
|---|---|
| Audited artifact | `contracts/poliscope.py` · **sha256 `28bf8e7eb0412fe2e3724d0f043d0a4e242a5e2d2b6c376420970fcd8811f31a`** · 1143 lines |
| Runner | legacy `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` (header `# v0.2.16`) |
| Against | Directive v2 Parts XV (checklist) and XVIII (release blockers), plus the project threat model |
| Date | 2026-11-20 |
| Evidence base | adversarial re-read of every public method and helper · SDK source inspection · 328 direct tests · mutation testing (28 of 30 injected defects killed; the 2 survivors are equivalent by design) · native timing probes |

## 0. Limits of this audit — read before trusting it

1. **The auditor is the same agent that wrote the code.** Independence is simulated by: an independent oracle implementation (encoding, segmenter, commitments) that never imports the contract,
   automated mutation testing, and reading the *SDK* source rather than my own comments. It is **not** a substitute for a human or third-party review before production use.
2. **No real-network evidence.** Nothing was deployed; real validator consensus, protocol behavior on disagreement/undetermined, transaction ordering, real LLM behavior and in-GenVM costs are **unobserved**.
3. All LLM answers in tests are mocks.
4. No formal verification. "No Critical/High defect found" means *none found by these methods*, not *none exist*.

## 1. Verdict

| Question | Answer |
|---|---|
| Open Critical or High **implementation** defects found? | **None found.** |
| Implementation defects found and fixed during this audit | **4** (A-1 … A-4, all with regression tests and mutants) |
| Design deviations from directive v2 needing an owner decision | **7** (DEV-1 … DEV-7, two of them High relative to the directive) — see `COMPLIANCE_MATRIX.md` |
| Release blockers under directive §59 | **3 present** (#17, #21, and the unverifiable-until-networked pair #11/#19), **plus** the DEV-1/DEV-2 design decision |
| **Overall** | **Not release-ready.** It is a *release candidate for network validation*: it can responsibly proceed to a StudioNet deployment test **only as a test**, not as a production audit authority. |

## 2. Findings fixed during this audit

| ID | Severity | Where | Behavior found | Exploit / impact | Correction | Regression test | Mutant |
|---|---|---|---|---|---|---|---|
| **A-1** | Low | `audit_proposal` | The registered **byte length** was stored but never compared at audit time (directive §9.1 requires it); only the Keccak commitment was checked | None practical (equal commitment implies equal bytes) — a spec-conformance and defence-in-depth gap; also saves hashing work on obviously wrong input | Compare exact UTF-8 length first, then the commitment | `test_audit_checks_exact_byte_length_before_hashing…` (only the stored length is corrupted, so only this check can fire; asserts no LLM call), `…uses_bytes_not_characters` | M27 killed |
| **A-2** | Low (conformance) | all 4 write methods | Returned `None`; directive §23.2/§24 require the transaction to return the **exact record ID** | Forces clients to reconstruct IDs or read `get_proposal`; invites "latest record" workarounds | `create_workspace`, `publish_policy`, `register_proposal`, `audit_proposal` now return their exact ID / commitment | `test_write_methods_return_their_exact_ids…` (equals the independent oracle) | — (behavioral test) |
| **A-3** | Medium (resource) | `_normalize_llm`, `_validate_canonical`, `_check_report` | Length of lists/dicts was compared **after** scanning them (`_is_int_list`, `set(...)`, `set(keys)`). A model answer or a malicious leader report with millions of elements would be processed in full before being rejected | Validator/leader CPU burn bounded only by transport size; amplifies a griefing leader | Size guards (`_lists_within_bounds`, `len(dict)` checks) run **before** any scan; new error `BAD_OUTPUT_SIZE` | 4 bad-output cases; `test_oversized_leader_report_is_rejected_before_any_scan` (1,000,000-element list and 100,000-key dict rejected, < 1 s) | M28, M29 killed |
| **A-4** | Medium | `_validate_canonical` | `NOT_APPLICABLE` was only discouraged in the prompt. A rule with **no applicability scope** could still be marked `OUT_OF_SCOPE` (directive §12.1 forbids it) | A biased model — or an injection that moves *every* node alike — could mark all rules `NOT_APPLICABLE`, yielding the vacuous verdict `NOT_APPLICABLE` with full consensus | Deterministic rule: a rule whose scope is empty/whitespace can never be `NOT_APPLICABLE`; enforced for LLM output, leader reports (validator V4) and post-consensus | `test_not_applicable_is_forbidden_for_a_rule_without_scope…`, `…all_rules_not_applicable_requires_every_rule_to_declare_a_scope`, `test_leader_claiming_not_applicable_for_an_unscoped_rule_disagrees` | M30 killed |

Side effect recorded honestly: the existing test `too_many_evidence` changed its expected code from `BAD_COMBINATION` to `BAD_OUTPUT_SIZE` (still rejected, rejected earlier). Test fixtures' rules now declare an explicit scope so `NOT_APPLICABLE` stays testable.

## 3. Observations and residual risks (not fixed — by design or out of reach)

| ID | Severity | Observation | Disposition |
|---|---|---|---|
| O-1 | Medium (inherent) | **Consensus is not truth.** A bias/injection shared by all nodes passes. Pinned in a test (`test_residual_risk_R01…`) so nobody assumes otherwise | Accepted; mitigated by fixed prompt, deterministic structural checks (incl. A-4), minimal output space. Needs real-model red-teaming |
| O-2 | Medium (unmeasured) | **Liveness**: exact agreement across independent LLMs may rarely succeed on ambiguous text | Unmeasured (needs network). Relaxation R-01 *proposed, not approved* |
| O-3 | Low | Permissionless registration, no aggregate cap → storage-growth spam bounded only per record | Accepted (a cap would be a DoS lever); depends on network fees (unverified) |
| O-4 | Low | The administrator is trusted for policy *content*; can author rules that bias results (cannot forge or alter audits) | By design; policy and commitments are public |
| O-5 | Low | `INDETERMINATE` is permanent for a proposal (one audit per proposal); re-audit = re-register | By design; documented |
| O-6 | Low | Hostile-code-point **rejection** blocks legitimate RTL marks / ZWJ emoji; `citable` floor is poor for CJK | Accepted trade-off (KL-07/08) |
| O-7 | Info | SDK docstring recommends the sandboxed `gl.vm.run_nondet`, web docs recommend `run_nondet_unsafe` | Chose `run_nondet_unsafe`; both fail closed for this validator (SOURCE_REGISTER S-04) |
| O-8 | Info | Runtime lazily allocates storage for empty containers on first read (raw image grows; logical state unchanged) | Proven layout-only; byte-identity asserted on warmed state |
| O-9 | Info | Mutants **M06** (pre-phase `audit_id` duplicate check) and **M21** (element-ID order inside `_validate_canonical`) survive | Equivalent by design: redundant with the `AUDITED` state check and with `_normalize_llm` + exact equality respectively (defence in depth) |
| O-10 | Info | `str.isalnum`/whitespace behavior depends on the runner's Unicode tables; identical on all nodes of one runner. The test oracle runs on a host Python that may differ for exotic code points | Acceptable; affects only citable acceptance, not commitments (segmentation whitespace is an explicit set) |

## 4. Release blockers — directive §59

| # | Blocker | Present? | Evidence / note |
|---|---|---|---|
| 1 | Validator does not receive the actual leader result | No (direct mode) | `validator_fn(leader_result)`; V1–V6; C14/C16; mutant M16 killed. **Real network: unverified** |
| 2 | Validator does not inspect the leader's calldata | No | `.calldata` read only after the `Return` check |
| 3 | Validator checks only the global verdict | No | field-by-field equality; M01/M02 killed |
| 4 | Checks only a score/bucket | No | no scores exist |
| 5 | Material findings can differ yet be accepted | No | C03–C09, C17 |
| 6 | Missing-element results can differ yet be accepted | No | C09 |
| 7 | Evidence invented or from another source | No | IDs verified against this node's own segmentation; no LLM text stored |
| 8 | Source commitment not checked at audit | No | A-1 + commitment; M04, M27 killed |
| 9 | Policy version can change during evaluation | No | bound version, commitment recomputed; M05, M15 killed |
| 10 | Technical failure stored as a successful audit | No | 40+ invalid-output cases leave state byte-identical |
| 11 | Failed consensus can leave a finalized record | **Unverified on a network** | writes only after `run_nondet_unsafe` returns; protocol *undetermined* behavior is documented-only |
| 12 | Audit identity depends on a wallet-list diff | No | client-computable domain-separated IDs; IDs returned (A-2) |
| 13 | Overlapping submissions can retrieve the wrong record | No | identity/concurrency tests; race simulated inside the LLM call; M07 killed |
| 14 | Shared latest result overwrites history | No | no `latest_*`; static test |
| 15 | Closure captures storage / unsupported state | No | AST proof + `check_pickling` |
| 16 | Unsupported storage types | No | lint + schema + static test |
| 17 | Selected runner not verified | **Yes (partial)** | verified locally (lint, schema, 328 tests) and by owner evidence of the Studio's generation; **a successful load/deploy in the target Studio has not been observed** |
| 18 | Suite does not exercise validator disagreement | No | 68 consensus tests via the real `validator_fn` |
| 19 | Real Studio consensus untested but claimed complete | **Untested; NOT claimed** | all documents label it BLOCKED |
| 20 | Deployment needs business constructor args | No | `ctor_params: 0` |
| 21 | Unbounded or unmeasured critical processing path | **Yes (unmeasured)** | bounds enforced and tested; cost inside GenVM (pure-Python Keccak, segmentation, prompt) not measured; limits provisional |
| 22 | Critical/high findings unresolved | No implementation findings; **DEV-1/DEV-2 open as owner decisions** | `COMPLIANCE_MATRIX.md` |

## 5. Part XV checklist

**Consensus** — validator receives actual `Result` ✔ · extracts calldata ✔ · leader output not ignored ✔ · every material field validated ✔ (*for the implemented rule-level schema*) · every finding independently checked ✔ · every missing element checked ✔ ·
every evidence reference checked ✔ · contradictory findings cannot pass on a matching verdict ✔ · no score tolerance ✔ · no unverified summary ✔ · no stored recommendations ✔ · validator errors fail closed ✔ · malformed leader results fail closed ✔ · no partial result persisted ✔ (direct mode).

**Source integrity** — exact commitment ✔ · re-submitted source must match ✔ · length checked ✔ (A-1) · policy immutable ✔ · audit binds source + policy commitments ✔ · segment IDs deterministic ✔ · quotations derived by the contract ✔ · evidence references valid ✔ · relevance independently assessed ✔ (shared-bias residual O-1).

**Identity** — deterministic unambiguous IDs ✔ · exact lookup ✔ · no wallet-list diff ✔ · no authoritative latest ✔ · concurrent submissions cannot pick the wrong record ✔ · duplicate behavior explicit (`*_EXISTS`) ✔ · history cannot be overwritten ✔.

**Runtime** — runner hash verified ◐ (locally; not on the target network) · API signatures verified ✔ (legacy SDK source) · linter compatible ✔ · test framework compatible ✔ (`genlayer-test==0.29.2`) · storage types verified ✔ · storage-to-memory boundary ✔ · closures pass pickling ✔ · no unsupported imports ✔ (`json`, `typing`, `dataclasses` only) · no non-deterministic calls outside the block ✔ (static) · no storage writes inside the non-deterministic path ✔ (static AST; the runtime sandbox property itself is unverified).

**Resource safety** — source/policy/segment/evidence bounded ✔ · LLM/leader output size bounded ✔ (A-3) · processing bounded ✔ (O(n) single pass, no regex, no HTML stripping) · cost measured ◐ (native only, see §6) .

**Deployment** — zero-argument constructor ✔ · no mandatory business data ✔ · empty registries ✔ · target network explicit ✔ (documented; **not reached**) · runner matches target ◐ · **not falsely marked complete ✔** · no frontend/backend ✔ · no secrets embedded ✔.

## 6. Measurements (native CPython — **not GenVM**; reported because directive §26.1 asks for timings)

| Operation | Size | Time |
|---|---:|---:|
| Reject 300 KB hostile markup (size check, before any scan) | 297,000 B | 0.4 ms |
| Reject 300 KB deeply nested markup | 300,000 B | 0.8 ms |
| Register, single 20,000 B line (40 hard cuts) | 20,000 B | 95 ms |
| Register, 400 segments | 17,489 B | 84 ms |
| Audit leader path, 400 segments × 12 rules (mock LLM) | 17,489 B | 60 ms |
| Prompt length for that audit | 38,789 chars | — |
| Keccak-256 (SDK pure-Python source) | 20,000 B | 45 ms |

Reading these as GenVM costs would be wrong: the SDK's Keccak is pure Python and the WASM runtime is expected to be substantially slower. The 300 KB input is **rejected, not supported**.

## 7. What an attacker can still do (summary)

- Craft proposals that make *all* models behave the same wrong way (O-1) — needs real-model red-teaming.
- Spam registrations (O-3) at the cost of fees.
- Cause repeated disagreement on ambiguous text (O-2), delaying but never forging an audit.
- As administrator, bias outcomes through rule wording (O-4) — visibly and verifiably, because policy and commitments are public.

## 8. Required before any production claim

1. Observe a successful load/deploy of **this exact file** in the target Studio (`DEPLOYMENT.md` §3).
2. Execute the real-network suite NET-1…NET-8 (`DEPLOYMENT.md` §4), including liveness (LIV-*) and real-model injection tests.
3. Measure costs inside GenVM and confirm or lower the provisional limits.
4. Owner decision on DEV-1/DEV-2 (element-level assessment with derived rule status) through the design-review gate.
5. Independent human review.
