# POLISCOPE — Source Register

Directive v2 §6 requires, for each important decision: question, source, date accessed, version, symbol/behavior, **how it was verified**, and the decision.
Method legend: **SRC** = source code read/inspected · **RUN** = executed (probe or test) · **DOC** = documentation page read · **SNIP** = search snippet only (weak) · **OWNER** = evidence supplied by the project owner · **NOT READ**.
Never read "verified" where only **DOC/SNIP** is listed.

## 1. What was actually consulted

| # | Question | Source | Accessed | Version | Method | Result → decision |
|---|---|---|---|---|---|---|
| S-01 | Which runner/SDK generation does the target Studio load? | Owner's Studio failure report + owner's reference contract (`# v0.2.16`, `py-genlayer:1jb45aa8…`, `from genlayer import *`) | 2026-11-19 | legacy | **OWNER** | The new-generation build failed with "Could not load contract schema"; deployed baseline = legacy `1jb45…` (RESEARCH §0b) |
| S-02 | Legacy SDK symbols (`run_nondet_unsafe`, `exec_prompt`, `Keccak256`, `copy_to_memory`, `sender_address`, `calldata.Decoded`, `UserError.message`) | std lib `11rhn002…` extracted from GenVM bundles | 2026-11-19 | runner `1jb45…` | **SRC + RUN** (probe, then 324 tests) | All used; no `bool`/`Address` in `Decoded` (API_COMPATIBILITY) |
| S-03 | New-generation SDK symbols | std libs `kzr02ndm…`, `0v3kzt…`; `sdk.genlayer.com/main/_static/ai/api.txt` | 2026-11-17/18 | v0.4.0-rc1 / manager rc3, rc15 | **SRC + RUN**; api.txt **DOC** (fetched truncated at 60k tokens: storage/calldata/eq_principle sections not seen there, read in source instead) | Archived variant only |
| S-04 | Generic vs sandboxed consensus API semantics | legacy `gl/vm.py` source (`run_nondet_unsafe`, `run_nondet`) | 2026-11-20 | legacy | **SRC** | `run_nondet_unsafe`: validator un-sandboxed, validator error ⇒ Disagree. **Discrepancy:** the legacy docstring recommends `run_nondet` (sandboxed; leader-error + validator-error ⇒ error propagates); the web docs recommend `run_nondet_unsafe`. Decision: `run_nondet_unsafe` (both are fail-closed for this validator, which returns `False` on any non-`Return`) |
| S-05 | Equivalence-principle semantics, undetermined transactions | docs.genlayer.com `…/equivalence-principle` | 2026-11-17 | page uses **old names** (`run_nondet_unsafe` generic, `e.message`) | **DOC** | Consistent with the *legacy* names; stale for the new generation. Undetermined ⇒ no state change is stated **by docs only**, not observed (UNVERIFIED on network) |
| S-06 | Error handling / rollback semantics | docs error-handling pages | 2026-11-17 | generation-mixed | **SNIP/DOC** | Not relied on: design validates before writing (STO-06) |
| S-07 | Prompt-injection guidance | docs prompt-injection page, community write-up | 2026-11-17 | — | **SNIP** (summary level) | Informed SEC-02; consensus does not detect shared injection (R-01) |
| S-08 | Official skill `write-contract` and boilerplate patterns | `genlayerlabs/skills`, `genlayer-project-boilerplate` (cloned) | 2026-11-17 | legacy generation | **SRC** | Legacy; boilerplate `football_bets.py` pattern for `gl.Contract`, `TreeMap`, `@allow_storage @dataclass` matched in probes |
| S-09 | Linter / test-tool compatibility per generation | `genvm-linter` (PyPI 0.11.0, GitHub main 0.11.1-rc.2), `genlayer-test` 0.29.2 / 0.30.0rc2 | 2026-11-17…20 | — | **RUN** | Legacy ⇒ `genlayer-test==0.29.2` (+ linter `main`); see KNOWN_LIMITATIONS KL-T* |
| S-10 | CLI command syntax | npm `genlayer@0.39.2` `--help` | 2026-11-18 | 0.39.2 | **RUN** (help only; no network call) | DEPLOYMENT.md |
| S-11 | EVM Keccak-256 correctness | known vectors `keccak256("")`, `keccak256("abc")` | 2026-11-17/19 | — | **RUN** | Both generations' `Keccak256` match |
| S-12 | Owner playbook (project rules) | `GENLAYER_INTELLIGENT_CONTRACT_PLAYBOOK*.md` | 2026-11-17/19 | — | **OWNER** | Method followed (probe first, same-file chain, generation mismatch diagnosis) |

## 2. Referenced by the directive but NOT read in this project

State plainly so no one assumes coverage: GenVM / non-deterministic-operations / optimistic-democracy concept pages; `features/non-determinism`; `features/calling-llms`; `crafting-prompts`; both **storage** pages; **testing** page and `api-references/genlayer-test`; `tooling-setup`; **Studio page (chain IDs 61999/61997/61127 are taken from the directive text and were NOT verified)**; **deployment / CLI-deployment** pages; typical-use-cases; when-to-use-genlayer; `courtofinternet/pm-kit`. Their subject matter was covered through SDK source and probes instead (S-02…S-04), but the *documented* statements remain unchecked.

## 3. Network
StudioNet / `docs.genlayer.com` were unreachable from the development sandbox for direct access (only search/fetch tools worked for some docs pages). **No request to any GenLayer network was made.**
