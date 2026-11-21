# POLISCOPE — Applicability Matrix (V1)

Directive v2 Part X: V1 evaluates **caller-submitted text only**. It does not fetch websites or APIs, crawl, verify third-party events or depend on source availability.
No artificial web-fetch functionality was added to "cover" these cases. A test (`test_api_compat.py::test_no_nondeterminism_sources…`) asserts the contract contains no
`gl.nondet.web`, `gl.evm`, cross-contract call or payable path.

| Case | Status in V1 | Technical reason | Future requirement (if retrieval is ever added) |
|---|---|---|---|
| Identical content across different hosts | **Not applicable** | no host is ever contacted | Different hostnames serving identical content must not count as independent corroboration; content identity is computed on canonicalized retrieved content and kept distinct from source identity |
| Independent corroboration across several sites | **Not applicable** | single caller-supplied source | Require genuinely independent sources, with provenance preserved |
| All-source HTTP 5xx | **Not applicable** | no fetch | An outage must stay retryable/unresolved and must never be read as "the event did not happen" |
| External request timeouts | **Not applicable** | no fetch | Timeouts are technical failures, not findings; must not finalize anything |
| Premature third-party event resolution | **Not applicable** | no event resolution | A third party's early answer must not override a configured deadline or challenge period |
| Source provenance / host reputation | **Not applicable** | no external source | Persist provenance if retrieval is added |
| Hostile HTML processing | **Implemented as "do not parse"** | text is evaluated as text; no tag stripping, no regex over user data | If parsing is ever added it must be demonstrably linear and tested on hostile 300 KB markup |
| Caller-controlled retrieval instructions | **Not applicable** | prompt is contract-owned; no retrieval | Never let caller text drive retrieval |
| Irrelevant excerpts counted as corroboration | **Implemented for V1 evidence** | evidence = deterministic segment IDs, citable floor, independent re-evaluation with exact agreement (shared-model blind spot remains: THREAT R-01) | Same, plus relevance check per source |

Other V1 exclusions (REQUIREMENTS EXC-*): no frontend/backend/API, no multisig, delegation, voting, treasury execution, administrator transfer, scores, free-text recommendations, or payable methods.
