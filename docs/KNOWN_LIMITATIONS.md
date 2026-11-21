# POLISCOPE — Known Limitations (living document)

Every compatibility gap and accepted residual risk is listed here (AC-08). Status: **BLOCKED**, **UNMEASURED**, **ACCEPTED**, **TOOLING**.

## Compatibility and environment

| ID | Status | Limitation |
|---|---|---|
| KL-00 | **BLOCKED** | StudioNet (and docs hosts) are unreachable from the development sandbox. Deployment, real consensus, liveness and cost measurements are **not done**. Direct-mode results are not consensus evidence. |
| KL-00a | **RESOLVED (owner evidence)** | The owner's Studio serves the legacy runner `1jb45…`; the new-generation build failed to load its schema there. Deployed baseline = legacy (DEC-07). **Still unobserved by me:** a successful load/deploy of the legacy build in that Studio. |
| KL-T8 | TOOLING | Legacy toolchain: `genlayer-test==0.29.2` only (0.30.0rc2 regresses on legacy contracts). In this sandbox its GenVM download 404s; link the cached rc7 bundle (RESEARCH §0b). Its mock layer returns a non-JSON mock as a raw `str`. `calldata.Decoded` has no `bool`/`Address`. |
| KL-T1 | TOOLING | `genvm-linter` PyPI 0.11.0 cannot load the new SDK layout; use GitHub `main` (0.11.1-rc.2). |
| KL-T2 | TOOLING | Linter false positive `E014` for `@gl.storage.allow`; mitigated by `allow_storage = gl.storage.allow` alias. |
| KL-T3 | TOOLING | `genlayer-test 0.30.0rc2` `mock_llm` + `response_format="json"` defect; test-only workaround in `tests/conftest.py`. Needs `cloudpickle`. |
| KL-T4 | TOOLING | Linter and `gltest` **auto-select the newest reachable GenVM bundle**; results are time-dependent. Pin with `GENVM_VERSION=v0.6.0-rc15` for tests and record the bundle version in every lint/test log. When the GitHub API is rate-limited (403) they silently fall back to the newest *cached* bundle. |
| KL-T5 | TOOLING | Official `write-contract` skill and boilerplate still use the legacy generation (`1jb45…`, `sender_account`); live Equivalence-Principle page uses removed names. SDK source is authoritative. |
| KL-T7 | UNVERIFIED | Direct mode lazily allocates storage slots for empty containers on first read (raw image grows even when nothing is written; logical state unchanged — RESEARCH D-21). Real-runtime behavior unverified; no correctness depends on it. |
| KL-T6 | UNVERIFIED | `unicodedata`, cross-contract call semantics, rollback-on-error semantics, validator-exception handling and transaction-size limits inside GenVM/StudioNet are unverified. The design does not depend on them. |

## Resource limits

| ID | Status | Limitation |
|---|---|---|
| KL-01 | **UNMEASURED** | All LIM-* values are provisional. Keccak-256 is pure Python (≈3.2 µs/B on native CPython; GenVM cost unknown). `LIM-TEXT = 20,000 B` is the least certain. |
| KL-02 | UNMEASURED | LLM prompt size/latency, validator cost and agreement rate (liveness) are unmeasured (LIV-*, BLOCKED). |

## Deviations from directive v2 (owner decision pending — details in COMPLIANCE_MATRIX.md)

| ID | Limitation |
|---|---|
| DEV-1/DEV-2 | **Rule-level evaluation schema** (status chosen by the model and agreed by consensus) instead of the directive's element-level assessments with rule status *derived in code*. Not implemented because it needs the design-review gate |
| DEV-3 | Rules with no required elements are allowed |
| DEV-4 | Segmenter drops only whitespace/line breaks between segments (lossless reconstruction proven by fuzz), not a literal character partition |
| DEV-5 | `INDETERMINATE` carries no evidence |
| DEV-6/DEV-7 | No creation timestamps; policy schema version and creator are not stored per version |

## Audit status (2026-11-20, SECURITY_AUDIT.md)

Not release-ready: runner not yet observed loading in the target Studio (blocker #17), costs unmeasured inside GenVM (#21), real consensus unverified (#11/#19). The audit was performed by the same agent that wrote the contract; an independent human review is still required.

## Design trade-offs (ACCEPTED, pending owner confirmation in ARCHITECTURE_REVIEW §4)

| ID | Limitation |
|---|---|
| KL-03 | **Consensus is not truth.** Shared model bias/injection passes consensus (THREAT R-01/TM-C14). |
| KL-04 | Strict exact equality may starve liveness on ambiguous text (R-02). Relaxation R-01 is *proposed, not approved*. |
| KL-05 | Permissionless registration has no aggregate cap; spam is bounded per record only. |
| KL-06 | No Unicode normalization: NFC and NFD forms of the same visible text are different proposals. |
| KL-07 | Segmenter is language-neutral and simple: abbreviations ("Dr.", "p. ej.") over-split; very short sentences are not citable (`LIM-CITABLE-ALNUM = 8`); CJK is accepted but poorly served (fewer alphanumerics per concept). Spanish and English are the supported-quality languages. |
| KL-08 | Hostile code points are **rejected**, including ZWJ (affects some emoji sequences) and bidi/RTL marks. |
| KL-09 | One audit per proposal; no administrator transfer; no policy deletion/editing (new versions only). |
| KL-10 | A proposal's text must be re-supplied for every audit (commitment-only storage). |
| KL-11 | Evidence is cited only for findings asserting presence (`SATISFIED`, `REQUIREMENT_CONTRADICTED`, `PROHIBITED_CONDITION_PRESENT`). |
| KL-12 | `exec_prompt` exposes no temperature/seed; reproducibility depends on the constrained output space. |
| KL-13 | Policy quality bounds audit quality; authoring guidance (atomic rules, closed element IDs) is required reading. |
