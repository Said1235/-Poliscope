# DO NOT DEPLOY — archived build for a different runner generation

`poliscope_v04.py` is the first build of POLISCOPE, written for the **new SDK generation** (`import genlayer as gl`, `gl.contract.Contract`,
runner `py-genlayer:kzybg95x…`). It **failed to load its schema in the target Studio** ("Could not load contract schema") because that Studio
serves the legacy runner `py-genlayer:1jb45aa8…`.

- It passed 307 direct tests with `genlayer-test 0.30.0rc2` at the time, but it is **not maintained**: later audit fixes (A-1 … A-4) were applied
  **only** to `contracts/poliscope.py`.
- It is kept solely as a reference for a future migration to the new generation. See `docs/RESEARCH_AND_COMPATIBILITY.md` §0b.
