# Design evidence

- `reference_encoding.py`, `reference_segmenter.py` — independent reference implementations of the canonical encoding and the segmenter, validated during design
  (golden vectors; 20,000-case segmenter fuzz) and reused by `tests/ref.py` as the oracle.
- `probes/` — small contracts + tests used to verify SDK behavior **before** designing around it. They use the **new-generation** syntax
  (`import genlayer as gl`, runner `kzybg95x…`/`5jycge4q…`) and `genlayer-test 0.30.0rc2`; they are historical evidence, are **not** collected by `pytest.ini`
  and will not load on the legacy runner. The legacy-generation probe result is summarized in `docs/RESEARCH_AND_COMPATIBILITY.md` §0b.
