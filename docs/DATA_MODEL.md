# POLISCOPE — Data Model (Phase 4)

Status: **DRAFT FOR REVIEW.** Python snippets are *specification*, not implementation.
Reference implementations of the encoding and segmenter that were executed to validate this
document live in `docs/evidence/reference_encoding.py` and `reference_segmenter.py`.

---

## 1. Limits (LIM-*) — PROVISIONAL AND UNMEASURED

All limits are centralized constants. **None has been measured inside GenVM** (StudioNet is
unreachable; direct mode runs native CPython and cannot measure WASM cost). They are
deliberately conservative and MUST be confirmed before release (NFR-RES-01).
Sizes are UTF-8 **bytes** unless stated; "chars" means Unicode code points.

| ID | Limit | Provisional value | Rationale / measurement needed |
|---|---|---|---|
| LIM-WS-NAME | Workspace name | 80 B | Metadata only. |
| LIM-NONCE | `client_nonce` | 64 B, charset `A-Z a-z 0-9 . _ : -` | Caller-chosen uniqueness salt; restricted charset avoids display/spoofing issues. |
| LIM-RULES | Rules per policy version | 12 | One LLM call evaluates all rules; prompt size and disagreement grow with rule count. Measure on real LLMs. |
| LIM-RULE-ID | Rule ID | 24 chars, charset `A-Z a-z 0-9 . _ -` | Stable machine identifier. |
| LIM-RULE-TITLE | Rule title | 120 B | |
| LIM-RULE-REQ | Requirement text | 800 B | Rules must be atomic. |
| LIM-RULE-SCOPE | Applicability scope | 400 B (may be empty = "applies to all proposals") | |
| LIM-RULE-GUIDE | Evaluation guidance | 600 B (may be empty) | |
| LIM-ELEMS | Required elements per rule; prohibited conditions per rule | 6 each | Closed ID vocabulary. |
| LIM-ELEM-ID | Element/condition ID | 16 chars, same charset as rule IDs | |
| LIM-ELEM-DESC | Element/condition description | 200 B | |
| LIM-VERSIONS | Policy versions per workspace | 1000 | Bounds `u32` growth. |
| LIM-TITLE | Proposal title | 160 B | |
| LIM-TEXT | Proposal text | **20,000 B** | Keccak-256 is pure Python (measured natively ≈ 3.2 µs/B); WASM cost unknown; transaction-size limits unknown. Most uncertain limit. |
| LIM-SEG-CHARS | Max segment length | 500 chars | Hard cut (§4). |
| LIM-SEGMENTS | Segments per proposal | 400 | Bounds prompt size and loops. |
| LIM-CITABLE-ALNUM | Min alphanumeric chars for a *citable* segment | 8 | Deterministic floor against trivial evidence ("Sí.", "Dr."). Tunable; see KL-07. |
| LIM-EVIDENCE | Evidence segments per finding | 4 | Bounds report size. |

Derived bound (NFR-RES-03): worst-case persisted audit ≈ LIM-RULES × LIM-EVIDENCE ×
(max segment bytes). With ≤ 500 chars/segment (≤ 2,000 B in the worst script) this is ≤ ~96 KB;
typical ES/EN audits are far smaller. To be re-derived after measurement.

---

## 2. Records

### 2.1 Conceptual model

```text
Workspace 1─* PolicyVersion 1─* PolicyRule 1─* RuleElement (required | prohibited)
Workspace 1─* Proposal ──binds──► (Workspace, PolicyVersion, source_commitment)
Proposal  1─0..1 AuditRecord 1─* Finding 1─* EvidenceRef
```

### 2.2 Storage declarations (specification)

> Shown in new-generation syntax for readability. The **deployed legacy** contract writes the same declarations as `from genlayer import *` → `@allow_storage @dataclass`,
> `DynArray[...]`, `TreeMap[...]`, base class `gl.Contract`, and needs no `allow_storage = gl.storage.allow` alias.

```python
allow_storage = gl.storage.allow        # alias so genvm-lint's textual E014 rule recognises it

@allow_storage
@dataclass
class RuleElement:
    element_id: str
    description: str

@allow_storage
@dataclass
class PolicyRule:
    rule_id: str
    title: str
    requirement_text: str
    scope: str
    evaluation_guidance: str
    required_elements: gl.storage.DynArray[RuleElement]
    prohibited_conditions: gl.storage.DynArray[RuleElement]

@allow_storage
@dataclass
class PolicyVersion:
    workspace_id: str
    version: u32
    policy_set_commitment: str
    rule_count: u32
    rules: gl.storage.DynArray[PolicyRule]          # insertion order == canonical rule order

@allow_storage
@dataclass
class Workspace:
    workspace_id: str
    administrator: Address
    name: str
    current_policy_version: u32                      # 0 = none published
    proposal_counter: u32                            # informational; NEVER used for identity

@allow_storage
@dataclass
class Proposal:
    proposal_id: str
    workspace_id: str
    submitter: Address
    policy_version: u32
    source_commitment: str
    text_length_bytes: u32
    segment_count: u32
    title: str
    state: str                                       # "REGISTERED" | "AUDITED"
    audit_id: str                                    # "" until AUDITED

@allow_storage
@dataclass
class EvidenceRef:
    segment_id: u32
    start: u32                                       # code-point offset, inclusive
    end: u32                                         # code-point offset, exclusive
    quote: str                                       # derived by contract code, never by the LLM

@allow_storage
@dataclass
class Finding:
    rule_id: str
    status: str
    reason_code: str
    evidence: gl.storage.DynArray[EvidenceRef]
    missing_elements: gl.storage.DynArray[str]       # element_ids declared by the rule
    prohibited_hits: gl.storage.DynArray[str]        # condition_ids declared by the rule

@allow_storage
@dataclass
class AuditRecord:
    audit_id: str
    workspace_id: str
    proposal_id: str
    policy_version: u32
    source_commitment: str
    policy_set_commitment: str
    schema_version: str
    prompt_version: str
    segmentation_version: str
    global_verdict: str
    report_commitment: str
    finding_count: u32
    findings: gl.storage.DynArray[Finding]

class Poliscope(gl.contract.Contract):
    workspaces:       gl.storage.TreeMap[str, Workspace]       # key = workspace_id
    policy_versions:  gl.storage.TreeMap[str, PolicyVersion]   # key = f"{workspace_id}:{version}"
    proposals:        gl.storage.TreeMap[str, Proposal]        # key = proposal_id
    audits:           gl.storage.TreeMap[str, AuditRecord]     # key = audit_id

    def __init__(self):
        pass
```

Notes
- `workspace_id` is fixed-width (64 hex chars), so `f"{workspace_id}:{version}"` is unambiguous.
- Verified in RESEARCH probes: nested dataclass → `DynArray` → dataclass → `DynArray[str]` storage and
  `list[dict[str, typing.Any]]` method parameters pass lint and direct tests.
- Enumerations are stored as `str` and validated against closed constant sets on every write path.
- Fields are append-only across future versions (STO-03).
- **Intentionally absent:** full proposal text, free-text reasoning, scores, `latest_*`, wallet-indexed lists.

### 2.3 Policy rule input schema (`publish_policy` → `rules`)

```text
rules: list[dict]   (1 ≤ len ≤ LIM-RULES)
rule  = {
  "rule_id": str,                      required, unique in version
  "title": str,                        required, non-empty
  "requirement_text": str,             required, non-empty after whitespace check
  "scope": str,                        required (may be "")
  "evaluation_guidance": str,          required (may be "")
  "required_elements":      list[{"id": str, "description": str}],   required (may be [])
  "prohibited_conditions":  list[{"id": str, "description": str}],   required (may be [])
}
```
Exact key sets (no unknown keys, no missing keys), exact types (`bool` is not `int`; no `float`),
IDs unique within their list, all text passes NFR-INP-03. Reason code `MANDATORY_ELEMENT_MISSING`
is only usable for rules declaring ≥ 1 required element; `PROHIBITED_CONDITION_PRESENT` only for rules
declaring ≥ 1 prohibited condition (§5.2).

---

## 3. Commitments and identifiers

### 3.1 Canonical encoding `ENC`

Every value is self-describing and length-prefixed so that no two distinct field sequences encode
identically:

| Type | Encoding |
|---|---|
| `str` | `0x53 ("S")` ‖ `u32be(len(utf8))` ‖ `utf8` |
| `uint` (0 ≤ v < 2⁶⁴) | `0x55 ("U")` ‖ `u32be(8)` ‖ `u64be(v)` |
| `bytes` | `0x42 ("B")` ‖ `u32be(len)` ‖ bytes |
| `list` | `0x4C ("L")` ‖ `u32be(count)` ‖ `ENC(e₁)` ‖ … ‖ `ENC(eₙ)` |

`bool` and `float` are not encodable (error). Addresses are encoded as `bytes` via
`Address.as_bytes` (20 bytes, verified in SDK source).

`H(domain, f₁…fₙ) = lowercase_hex( Keccak256( ENC(domain) ‖ ENC(f₁) ‖ … ‖ ENC(fₙ) ) )` using the SDK
`gl.Keccak256` (EVM Keccak-256; vector-validated). 64 lowercase hex chars. No `hash()`, no `hashlib`.

### 3.2 Domains

`POLISCOPE:WORKSPACE:V1`, `POLISCOPE:POLICY:V1`, `POLISCOPE:SOURCE:V1`,
`POLISCOPE:PROPOSAL:V1`, `POLISCOPE:AUDIT:V1`, `POLISCOPE:REPORT:V1`.

### 3.3 Identifier and commitment definitions

```text
workspace_id          = H(WORKSPACE, creator:bytes, client_nonce:str)
source_commitment     = H(SOURCE,    proposal_text:str)                       # exact text, no normalization
proposal_id           = H(PROPOSAL,  workspace_id, policy_version:uint, submitter:bytes,
                                     source_commitment, client_nonce:str)
policy_set_commitment = H(POLICY,    workspace_id, version:uint, rule_count:uint, [rule₁ … ruleₙ])
   rule               = [rule_id, title, requirement_text, scope, evaluation_guidance,
                         [[element_id, description] …],      # required_elements, in published order
                         [[condition_id, description] …]]    # prohibited_conditions, in published order
audit_id              = H(AUDIT,     workspace_id, proposal_id, source_commitment, policy_version:uint,
                                     policy_set_commitment, SCHEMA_VERSION, PROMPT_VERSION,
                                     SEGMENTATION_VERSION)
report_commitment     = H(REPORT,    audit_id, workspace_id, proposal_id, policy_version:uint,
                                     source_commitment, policy_set_commitment, SCHEMA_VERSION,
                                     PROMPT_VERSION, SEGMENTATION_VERSION, global_verdict, [finding₁ … findingₙ])
   finding            = [rule_id, status, reason_code,
                         [[segment_id:uint, start:uint, end:uint, quote:str] …],
                         [missing_element_id …], [prohibited_hit_id …]]
```

Constants: `SCHEMA_VERSION = "POLISCOPE-REPORT-1"`, `PROMPT_VERSION = "POLISCOPE-PROMPT-1"`,
`SEGMENTATION_VERSION = "POLISCOPE-SEG-1"`. Changing any of them changes every `audit_id`.

The report commitment covers **every** persisted material field (identifiers, versions, verdict, every finding,
every evidence reference **including offsets and derived quotation**). A one-field change in any of them changes it.

### 3.4 Golden vectors (computed 2026-11-17 with SDK `Keccak256`, see `docs/evidence/reference_encoding.py`)

```text
creator            = 0x5b38da6a701c568545dcfcb03fcb875f56beddc4
workspace_id       = H(WORKSPACE, creator, "ws-1")
                   = 6dececaef0018ace711ab3937cd3c80f808b60e17f17fe78aca20840212b6ce2
text               = "Solicitamos 50.000 USDC para el proveedor Acme. ¿Cómo apoya esto al protocolo?"   (80 UTF-8 bytes)
source_commitment  = 89046a99097767de9bf00cf50d1d48d4a90b5286303767c092e011530a33be94
source (NFD form)  = 377a2ad3aebf7436381e926714a96c78f4b885dd6d5b0efbf01a7d778d36e702   ← differs (NFR-LANG-03)
proposal_id        = H(PROPOSAL, workspace_id, 1, creator, source_commitment, "n-1")
                   = 724b3e4c6e5db3762be2acbfc9a6b327ecee6b2af379d2053b7a47e96c47a0a2
ENC("a")           = 530000000161
ENC(7)             = 55000000080000000000000007
ENC(["a",[1]])     = 4c000000025300000001614c0000000155000000080000000000000001
```
Checked: `("ab","c")` ≠ `("a","bc")`; `"a"` ≠ `b"a"`; `"1"` ≠ `1`.

---

## 4. Segmentation (`POLISCOPE-SEG-1`)

Purpose (DEC-02): give validators a **deterministic, language-neutral, bounded** vocabulary for evidence so
that the LLM never produces quotations. Offsets are code-point offsets into the **exact** submitted text.

### 4.1 Input validation (before segmentation, at registration and audit)

Reject (never strip) a proposal if it: is empty or all whitespace; exceeds LIM-TEXT bytes; fails UTF-8 encoding
(lone surrogates); or contains any code point in:

```text
U+0000–U+0008, U+000B, U+000C, U+000E–U+001F   (C0 controls except TAB, LF, CR)
U+007F–U+009F                                   (DEL, C1 controls)
U+00AD                                          (soft hyphen)
U+200B–U+200F                                   (zero-width, ZWNJ, ZWJ, LRM, RLM)
U+2028–U+202E                                   (line/paragraph separators, bidi embeddings/overrides)
U+2060–U+206F                                   (word joiner, invisible operators, bidi isolates)
U+D800–U+DFFF                                   (surrogates)
U+E000–U+F8FF                                   (private use)
U+FEFF                                          (BOM / zero-width no-break space)
U+FFF0–U+FFFF                                   (specials)
U+E0000–U+E007F                                 (tag characters)
```
Explicit ranges are used because `unicodedata` availability inside GenVM is unverified (NFR-DET-04).
Known cost: ZWJ-joined emoji and RTL marks are rejected (KL-08). Spanish characters `á é í ó ú ü ñ Ñ ¿ ¡ «» —` are
unaffected. The same check applies to policy text fields and `title`.

### 4.2 Algorithm (single pass, O(n), no regular expressions)

Definitions:
`WS` = `{U+0020, U+0009, U+00A0, U+2000–U+200A, U+202F, U+205F, U+3000}`;
`ASCII_TERMS` = `{ . ! ? … }` (split only if followed by `WS` or end of line);
`CJK_TERMS` = `{ 。 ！ ？ }` (split immediately).

1. Scan the text line by line; a line break is `\r\n`, `\n` or `\r` (never part of a segment).
2. Within a line, cut after each terminator as defined above.
3. Trim `WS` at both ends of every piece; drop empty pieces.
4. If a piece exceeds LIM-SEG-CHARS, **hard-cut** at exactly LIM-SEG-CHARS code points (no whitespace search,
   hence O(n)); re-trim each resulting piece; repeat on the remainder.
5. Assign IDs `0 … n−1` in text order; `segment = (id, start, end)`, `quote = text[start:end]`.
6. If `n > LIM-SEGMENTS` → reject (`LIMIT_EXCEEDED`). `n = 0` cannot happen for a valid non-empty proposal.
7. A segment is **citable** iff it has ≥ LIM-CITABLE-ALNUM characters for which `str.isalnum()` is true.

Validated invariants (fuzzed over 20,000 random inputs including `\r`, `\n`, tabs, NBSP, `…`, `¿¡`, `。`, with
`seg_max ∈ {1,2,3,7,500}`): spans are ordered, disjoint, within bounds, ≤ `seg_max`, trimmed, contain no line break,
**cover every non-whitespace character** (nothing silently dropped), and are deterministic.
This fuzz found and fixed a real defect in the first draft (a hard cut could leave trailing whitespace).

Worked example (reference implementation output):

```text
text = "Propuesta de gasto\r\nSolicitamos 50.000 USDC para Acme. ¿Cómo apoya esto al protocolo? Dr. Pérez lo revisó.\nSí."
[0] (0,18)    'Propuesta de gasto'                        citable
[1] (20,54)   'Solicitamos 50.000 USDC para Acme.'        citable      ← "50.000" is not split ('.' not followed by WS)
[2] (55,85)   '¿Cómo apoya esto al protocolo?'             citable
[3] (86,89)   'Dr.'                                        not citable  ← abbreviation over-split (accepted, NFR-LANG-04)
[4] (90,106)  'Pérez lo revisó.'                           citable
[5] (107,110) 'Sí.'                                        not citable
```

### 4.3 Segmentation versioning

Any change to §4.1–4.2 requires a new `SEGMENTATION_VERSION`; it is bound into `audit_id` and `report_commitment`.

---

## 5. Findings

### 5.1 Canonical finding (wire and storage form)

```text
finding = {
  "rule_id": str,
  "status": "SATISFIED" | "VIOLATED" | "INDETERMINATE" | "NOT_APPLICABLE",
  "reason_code": <closed enum, §5.2>,
  "evidence_segments": [u32 …]       # strictly ascending, unique, citable, < segment_count
  "missing_elements": [str …]        # declared required-element IDs, in published order, unique
  "prohibited_hits":  [str …]        # declared prohibited-condition IDs, in published order, unique
}
```
Exactly these six keys; findings listed in the **policy's rule order**, one per rule.

### 5.2 Status × reason × cardinality compatibility (enforced deterministically — EVD-03)

| Status | Reason code | Evidence segments | `missing_elements` | `prohibited_hits` | Extra condition |
|---|---|---|---|---|---|
| `SATISFIED` | `REQUIREMENT_SATISFIED` | 1…LIM-EVIDENCE | ∅ | ∅ | — |
| `VIOLATED` | `REQUIREMENT_CONTRADICTED` | 1…LIM-EVIDENCE | ∅ | ∅ | — |
| `VIOLATED` | `MANDATORY_ELEMENT_MISSING` | ∅ | ≥ 1 | ∅ | rule declares ≥ 1 required element |
| `VIOLATED` | `PROHIBITED_CONDITION_PRESENT` | 1…LIM-EVIDENCE | ∅ | ≥ 1 | rule declares ≥ 1 prohibited condition |
| `INDETERMINATE` | `INSUFFICIENT_EVIDENCE` | ∅ | ∅ | ∅ | — |
| `INDETERMINATE` | `AMBIGUOUS_REQUIREMENT` | ∅ | ∅ | ∅ | — |
| `NOT_APPLICABLE` | `OUT_OF_SCOPE` | ∅ | ∅ | ∅ | — |

Every other combination is invalid (e.g. `SATISFIED`+`MANDATORY_ELEMENT_MISSING`, `NOT_APPLICABLE`+`REQUIREMENT_CONTRADICTED`,
`INDETERMINATE` that carries a verdict-like reason). The table deliberately **removes degrees of freedom**: evidence exists
only where a statement is *asserted to be present*; absent/uncertain/inapplicable cases carry no evidence, so two evaluators
cannot disagree merely on "which supporting excerpt to attach" where none is needed.

### 5.3 Global verdict (EVD-12)

```text
if any finding.status == VIOLATED          → NON_COMPLIANT
elif any finding.status == INDETERMINATE   → INDETERMINATE
elif all finding.status == NOT_APPLICABLE  → NOT_APPLICABLE
else                                       → COMPLIANT
```
Empty finding set, unknown status, or count ≠ rule_count → invalid report (never a verdict).

### 5.4 Leader wire report (what `leader_fn` returns)

```text
{ "workspace_id": str, "proposal_id": str, "source_commitment": str, "policy_version": int,
  "policy_set_commitment": str, "schema_version": str, "prompt_version": str,
  "segmentation_version": str, "findings": [finding …] }
```
Contains **no** quotation text, offsets, verdict, commitment or free text. Only `str / int / list / dict[str,…]`
(the calldata-safe subset; `float`/tuple do not exist in `calldata.Decoded`).

### 5.5 Derived fields (computed after consensus by contract code)

`quote`/`start`/`end` per evidence ID (from the recomputed segmentation), `global_verdict`, `audit_id`,
`report_commitment`, `finding_count`.

---

## 6. View payloads (read-only)

| View | Returns |
|---|---|
| `get_workspace(workspace_id)` | `{workspace_id, administrator, name, current_policy_version, proposal_counter}` |
| `get_policy_version(workspace_id, version)` | `{workspace_id, version, policy_set_commitment, rule_count}` |
| `get_policy_rule(workspace_id, version, rule_index)` | rule incl. element/condition lists |
| `get_proposal(proposal_id)` | all `Proposal` fields (incl. `state`, `audit_id`) |
| `get_audit(audit_id)` | all `AuditRecord` fields; findings with `evidence: [{segment_id,start,end,quote}]`, `missing_elements`, `prohibited_hits` |

`Address` values are returned as hex strings. All lookups are direct key lookups.
