#!/usr/bin/env python3
"""Mutation testing for contracts/poliscope.py.

Injects one deliberate defect at a time into a COPY of the repository and runs the direct-mode suite with `-x`.
A mutant is KILLED if the suite fails, SURVIVED if it still passes. Survivors must be either closed with a new test
or justified as equivalent (see docs/TEST_MATRIX.md section 4).

Usage:  python tools/mutation_test.py [--python /path/to/venv/bin/python] [M01 M07 ...]
The interpreter must have genlayer-test==0.29.2 installed (legacy runner, see README).
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = open(os.path.join(ROOT, "contracts", "poliscope.py"), encoding="utf-8").read()
M = [
 ("M01 validator always True", 'return own == report["findings"]  # exact canonical equality of every material field', "return True"),
 ("M02 validator reuses leader findings (no independent run)", "own = _evaluate(snap)  # independent evaluation; leader findings are NOT shown to it", 'own = report["findings"]'),
 ("M03 skip binding comparison", "if type(report[k]) is not type(snap[k]) or report[k] != snap[k]:", "if False:"),
 ("M04 skip source commitment check", "if source != prop.source_commitment:", "if False:"),
 ("M05 audit uses LATEST policy version", "version = int(prop.policy_version)  # the version BOUND", "version = int(ws.current_policy_version)  # the version BOUND"),
 ("M06 remove pre-phase duplicate-audit check", 'if audit_id in self.audits:\n            _fail("AUDIT_EXISTS")\n\n        citable', "citable"),
 ("M07 remove post-consensus duplicate re-check", "if audit_id in self.audits or self.proposals[proposal_id].state != STATE_REGISTERED:", "if False:"),
 ("M08 bool accepted as evidence int", "def _is_int_list(v) -> bool:\n    if type(v) is not list:\n        return False\n    for x in v:\n        if type(x) is not int:", "def _is_int_list(v) -> bool:\n    if type(v) is not list:\n        return False\n    for x in v:\n        if not isinstance(x, int):"),
 ("M09 citable check removed", "or sid >= seg_count or not citable[sid]:", "or sid >= seg_count:"),
 ("M10 publish_policy admin check removed", 'if gl.message.sender_address != ws.administrator:\n            _fail("UNAUTHORIZED")', "pass"),
 ("M11 audit authorization removed", "if sender != prop.submitter and sender != ws.administrator:", "if False:"),
 ("M12 evidence not canonically sorted", '"evidence_segments": sorted(ev),', '"evidence_segments": ev,'),
 ("M13 VIOLATED no longer dominates verdict", 'if "VIOLATED" in sts:\n        return "NON_COMPLIANT"', 'if "VIOLATED" in sts and False:\n        return "NON_COMPLIANT"'),
 ("M14 report commitment omits evidence", "                evidence[i],\n                list(f[\"missing_elements\"]),", "                [],\n                list(f[\"missing_elements\"]),"),
 ("M15 policy commitment check removed", "if policy_commitment != pv.policy_set_commitment:", "if False:"),
 ("M16 leader error is accepted", "return False  # leader UserError/VMError can never be agreed upon", "return True"),
 ("M17 zero-width chars no longer rejected", "0x200B <= o <= 0x200F or ", ""),
 ("M18 version compare-and-set removed", "if new_version != int(ws.current_policy_version) + 1:", "if False:"),
 ("M19 status/reason compatibility removed", "if (st, rc) not in COMPAT:", "if False:"),
 ("M20 missing/prohibited cardinality removed", "if need_ms != (len(ms) > 0) or need_ph != (len(ph) > 0):", "if False:"),
 ("M21 element ID order/membership removed", "if not _ordered_subset(ms, eids):", "if False:"),
 ("M22 policy_version mismatch type check removed (bool==1)", "if type(report[k]) is not type(snap[k]) or report[k] != snap[k]:", "if report[k] != snap[k]:"),
 ("M23 proposal title sent to LLM", '    return _PREAMBLE + "\\nDATA DOCUMENT\\n" + doc', '    return _PREAMBLE + "TITLE_LEAK" + "\\nDATA DOCUMENT\\n" + doc'),
 ("M24 evidence quote taken from wrong span", "refs.append([sid, s, e, text[s:e]])", "refs.append([sid, s, e, text[s:e].upper()])"),
 ("M25 findings coverage length check removed", "if type(findings) is not list or len(findings) != len(rules):\n        raise EvaluationError(\"[LLM_ERROR] BAD_COVERAGE\")\n    seg_count", "seg_count"),
 ("M26 segment hard-cut trailing trim removed", "            while piece_end > s and text[piece_end - 1] in _WS:\n                piece_end -= 1\n", ""),
 ("M27 audit-time byte-length check removed (finding A-1)", 'if len(proposal_text.encode("utf-8")) != int(prop.text_length_bytes):', "if False:"),
 ("M28 oversized-list guard removed in canonical validation (finding A-3)", "        if not _lists_within_bounds(ev, ms, ph):\n            raise EvaluationError(\"[LLM_ERROR] BAD_OUTPUT_SIZE\")\n        if not _is_int_list(ev) or not _is_str_list(ms) or not _is_str_list(ph):\n            raise EvaluationError(\"[LLM_ERROR] BAD_SHAPE\")\n        ev_min", "        if not _is_int_list(ev) or not _is_str_list(ms) or not _is_str_list(ph):\n            raise EvaluationError(\"[LLM_ERROR] BAD_SHAPE\")\n        ev_min"),
 ("M29 oversized-list guard removed in LLM normalization (finding A-3)", "        if not _lists_within_bounds(ev, ms, ph):\n            raise EvaluationError(\"[LLM_ERROR] BAD_OUTPUT_SIZE\")\n        if not _is_int_list(ev) or not _is_str_list(ms) or not _is_str_list(ph):\n            raise EvaluationError(\"[LLM_ERROR] BAD_SHAPE\")\n        if len(set(ev))", "        if not _is_int_list(ev) or not _is_str_list(ms) or not _is_str_list(ph):\n            raise EvaluationError(\"[LLM_ERROR] BAD_SHAPE\")\n        if len(set(ev))"),
 ("M30 NOT_APPLICABLE allowed for rules without scope (finding A-4)", '        if st == "NOT_APPLICABLE" and not has_scope:\n            raise EvaluationError("[LLM_ERROR] BAD_APPLICABILITY")\n', ""),
]


ap = argparse.ArgumentParser()
ap.add_argument("--python", default=sys.executable)
ap.add_argument("only", nargs="*")
args = ap.parse_args()
results = {}
work = tempfile.mkdtemp(prefix="poliscope_mut_")
for name, old, new in M:
    key = name.split()[0]
    if args.only and key not in args.only:
        continue
    if SRC.count(old) < 1:
        results[name] = "NOT_APPLIED"; print(name, "-> NOT_APPLIED", flush=True); continue
    d = os.path.join(work, key)
    shutil.copytree(ROOT, d, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git", "variants"))
    open(os.path.join(d, "contracts", "poliscope.py"), "w", encoding="utf-8").write(SRC.replace(old, new, 1))
    t = time.time()
    p = subprocess.run([args.python, "-m", "pytest", "tests/direct", "-x", "-q", "-p", "no:cacheprovider"],
                       cwd=d, capture_output=True, text=True)
    failed = [l for l in p.stdout.splitlines() if l.startswith("FAILED")]
    results[name] = "KILLED" if p.returncode != 0 else "SURVIVED"
    print(f"{name} -> {results[name]} ({time.time()-t:.0f}s) {failed[0][:100] if failed else ''}", flush=True)
    shutil.rmtree(d, ignore_errors=True)
shutil.rmtree(work, ignore_errors=True)
killed = sum(v == "KILLED" for v in results.values())
print(f"DONE {killed} killed / {len(results)}  survivors: {[k for k, v in results.items() if v != 'KILLED']}")
