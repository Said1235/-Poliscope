# POLISCOPE — Deployment Instructions

**STATUS: NOT EXECUTED BY ME.** Nothing was deployed from the development sandbox (DEC-06; StudioNet unreachable). The deployed runner is the **legacy
`1jb45…`**, chosen because the owner's Studio failed to load the new-generation build (RESEARCH §0b). Do not report "deployed" until a receipt and a successful read exist.
CLI syntax below was read from `genlayer --help` of npm package `genlayer@0.39.2`; the *behavior* against a live network is unverified.

## 0. Go/no-go checks (all must hold)

1. `genvm-lint check contracts/poliscope.py --json` → `"ok":true`, `"ctor_params":0`.
2. In the legacy venv (`genlayer-test==0.29.2`): `python -m pytest tests/direct -q` → 328 pass.
3. The first two lines of the contract are exactly:
   `# v0.2.16` and `# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }`
   and `sha256sum contracts/poliscope.py` equals `28bf8e7eb0412fe2e3724d0f043d0a4e242a5e2d2b6c376420970fcd8811f31a` (the audited, tested file is the deployed file).
4. If the Studio still reports "Could not load contract schema", run `genvm-lint check` and `genvm-lint schema … --json` on the exact deployed file
   and send the output plus the Studio's runner list; do not guess another hash. (The new-generation build is archived and unsupported.)
5. Explicit owner authorization to deploy.

## 1. Tooling

```bash
npm install -g genlayer            # verified version: 0.39.2
genlayer network list              # shows built-in networks
genlayer network set studionet     # use the built-in network; never override the RPC manually
genlayer account list              # StudioNet is gasless; 0 GEN is expected and fine
```

## 2. Deploy (no constructor arguments, no configuration)

```bash
genlayer deploy --contract contracts/poliscope.py
```
Record the transaction hash and the contract address. Then verify:

```bash
genlayer receipt <txHash> --stdout --stderr      # status must be finalized/accepted, no error
genlayer schema <contractAddress>                # must list: 4 writes, 5 views, constructor with 0 params
genlayer code <contractAddress>                  # must show the same source as contracts/poliscope.py
```
The schema must match `docs/ARCHITECTURE.md` §3 exactly. If it does not, the deployed source is not the tested source.

## 3. Smoke sequence (writes use `--args`; views use `call`)

IDs are **computed by the client** (docs/DATA_MODEL.md §3 and `docs/evidence/reference_encoding.py`), never discovered by diffing wallets.

```bash
# 1) workspace (creator becomes administrator)
genlayer write <addr> create_workspace --args "My DAO" "ws-1"
# 2) policy v1 (administrator only); rules is a JSON array — see tests/helpers.py::RULES for a valid example
genlayer write <addr> publish_policy --args <workspaceId> 1 '[{"rule_id":"POL-001", ... }]'
# 3) proposal registration (stores only a commitment to the text)
genlayer write <addr> register_proposal --args <workspaceId> 1 "Title" "p-1" "<exact proposal text>"
# 4) audit: the SAME exact text must be re-supplied; submitter or administrator only
genlayer write <addr> audit_proposal --args <proposalId> "<exact proposal text>"
# 5) read back
genlayer call <addr> get_proposal --args <proposalId>
genlayer call <addr> get_audit    --args <auditId>
```
Check after step 5: `state == "AUDITED"`, `report_commitment` equals the value recomputed by the reference implementation,
every `quote` equals the corresponding slice of your text.

## 4. Real-network tests still to perform (none done)

| ID | What | Why it cannot be replaced by direct mode |
|---|---|---|
| NET-1 | Deploy with no constructor args; successful read | runner/compat |
| NET-2 | Full flow (workspace → policy → proposal → audit → retrieval) | real GenVM, real storage |
| NET-3 | Real leader + validators agree; record rounds-to-acceptance | consensus |
| NET-4 | Mock/forced contradictory validator rejects | consensus (use supported mock validators; label them as mocks) |
| NET-5 | Duplicate audit, overlapping audits of one proposal, state after failure/undetermined | ordering/rollback semantics unverified |
| NET-6 | **Liveness (LIV-*)**: agreement rate over the bilingual corpus, by language / rule count / length; classify each disagreement (M1–M7) | strict equality across real LLMs is unmeasured |
| NET-7 | Cost/time of max-size proposals (20,000 B, 400 segments, 12 rules); confirm or lower LIM-* | WASM cost of pure-Python Keccak unmeasured |
| NET-8 | Real LLM follows the trusted prompt (decision procedure, evidence rules, bilingual) | all LLM answers in tests are mocks |

## 5. Rollback / safety

There is no upgrade or admin-override path by design. A bad deployment is replaced by deploying a new contract; audits and policies of the
old one remain readable and are not migrated.
