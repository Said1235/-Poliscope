import unicodedata

import pytest

import ref
from helpers import TEXT_ES, TEXT_EN, RULES

GOLDEN_CREATOR = bytes.fromhex("5b38da6a701c568545dcfcb03fcb875f56beddc4")
GOLDEN_TEXT = "Solicitamos 50.000 USDC para el proveedor Acme. ¿Cómo apoya esto al protocolo?"


# ----------------------------------------------------------------------------------------------- encoding oracle
def test_keccak_reference_matches_evm_vector():
    assert ref.Keccak256(b"").hexdigest() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def test_golden_vectors_from_spec():
    ws = ref.workspace_id(GOLDEN_CREATOR, "ws-1")
    assert ws == "6dececaef0018ace711ab3937cd3c80f808b60e17f17fe78aca20840212b6ce2"
    src = ref.source_commitment(GOLDEN_TEXT)
    assert src == "89046a99097767de9bf00cf50d1d48d4a90b5286303767c092e011530a33be94"
    assert ref.source_commitment(unicodedata.normalize("NFD", GOLDEN_TEXT)) == "377a2ad3aebf7436381e926714a96c78f4b885dd6d5b0efbf01a7d778d36e702"
    assert ref.proposal_id(ws, 1, GOLDEN_CREATOR, src, "n-1") == "724b3e4c6e5db3762be2acbfc9a6b327ecee6b2af379d2053b7a47e96c47a0a2"
    assert ref.enc("a").hex() == "530000000161"
    assert ref.enc(7).hex() == "55000000080000000000000007"
    assert ref.enc(["a", [1]]).hex() == "4c000000025300000001614c0000000155000000080000000000000001"


def test_encoding_is_unambiguous():
    K = ref.Keccak256
    assert ref.H("D", "ab", "c") != ref.H("D", "a", "bc")
    assert ref.H("D", "a") != ref.H("D", b"a")
    assert ref.H("D", "1") != ref.H("D", 1)
    assert ref.H("D", ["a", "b"]) != ref.H("D", "a", "b")
    with pytest.raises(TypeError):
        ref.enc(True)
    with pytest.raises(TypeError):
        ref.enc(1.5)


def test_contract_matches_golden_workspace_and_proposal_ids(env, direct_vm):
    direct_vm.sender = GOLDEN_CREATOR
    env.c.create_workspace("Golden", "ws-1")
    ws = "6dececaef0018ace711ab3937cd3c80f808b60e17f17fe78aca20840212b6ce2"
    assert env.c.get_workspace(ws)["workspace_id"] == ws
    env.c.publish_policy(ws, 1, [dict(RULES[0])])
    env.c.register_proposal(ws, 1, "t", "n-1", GOLDEN_TEXT)
    pid = "724b3e4c6e5db3762be2acbfc9a6b327ecee6b2af379d2053b7a47e96c47a0a2"
    p = env.c.get_proposal(pid)
    assert p["source_commitment"] == "89046a99097767de9bf00cf50d1d48d4a90b5286303767c092e011530a33be94"


# ----------------------------------------------------------------------------------------------- registration
def test_register_stores_commitment_not_text(env):
    wid = env.workspace(); env.publish(wid, 1)
    pid = env.register(wid, 1, TEXT_ES, "p1", title="Gasto Acme")
    p = env.c.get_proposal(pid)
    assert p["source_commitment"] == ref.source_commitment(TEXT_ES)
    assert p["text_length_bytes"] == len(TEXT_ES.encode("utf-8"))
    assert p["segment_count"] == len(ref.ref_segment(TEXT_ES)) == 5
    assert p["state"] == "REGISTERED" and p["audit_id"] == ""
    assert p["policy_version"] == 1 and p["title"] == "Gasto Acme"
    assert p["submitter"].lower() == "0x" + env.alice.hex()
    assert not any("Solicitamos" in str(v) for v in p.values())      # the text itself is never stored
    assert env.c.get_workspace(wid)["proposal_counter"] == 1


def test_duplicate_proposal_rejected_state_unchanged(env):
    wid = env.workspace(); env.publish(wid, 1)
    env.register(wid, 1, TEXT_ES, "p1")
    before = env.storage()
    with env.vm.expect_revert("PROPOSAL_EXISTS"):
        env.register(wid, 1, TEXT_ES, "p1")
    assert env.storage() == before


def test_same_text_distinct_nonce_or_submitter_are_distinct_proposals(env):
    wid = env.workspace(); env.publish(wid, 1)
    a = env.register(wid, 1, TEXT_ES, "p1", who=env.alice)
    b = env.register(wid, 1, TEXT_ES, "p2", who=env.alice)
    c = env.register(wid, 1, TEXT_ES, "p1", who=env.bob)
    assert len({a, b, c}) == 3
    assert env.c.get_proposal(c)["submitter"].lower() == "0x" + env.bob.hex()
    assert env.c.get_workspace(wid)["proposal_counter"] == 3


def test_proposal_binds_selected_version_even_if_newer_exists(env):
    wid = env.workspace(); env.publish(wid, 1); env.publish(wid, 2)
    p1 = env.register(wid, 1, TEXT_ES, "a")
    p2 = env.register(wid, 2, TEXT_ES, "a")
    assert p1 != p2
    assert env.c.get_proposal(p1)["policy_version"] == 1 and env.c.get_proposal(p2)["policy_version"] == 2


@pytest.mark.parametrize("ws,ver,code", [("0" * 64, 1, "NOT_FOUND"), ("OK", 2, "NOT_FOUND"),
                                         ("OK", 0, "INVALID_INPUT"), ("OK", True, "INVALID_INPUT")])
def test_register_requires_existing_workspace_and_version(env, ws, ver, code):
    wid = env.workspace(); env.publish(wid, 1)
    ws = wid if ws == "OK" else ws
    before = env.storage()
    with env.vm.expect_revert(code):
        env.c.register_proposal(ws, ver, "t", "n", TEXT_ES)
    assert env.storage() == before


def test_register_in_workspace_without_policy(env):
    wid = env.workspace()
    with env.vm.expect_revert("NOT_FOUND"):
        env.c.register_proposal(wid, 1, "t", "n", TEXT_ES)


# ----------------------------------------------------------------------------------------------- hostile / invalid text
HOSTILE = ["\x00", "\x07", "\x1b", "\x7f", "\x85", "\u00ad", "\u200b", "\u200d", "\u200f", "\u2028", "\u2029",
           "\u202a", "\u202e", "\u2060", "\u2066", "\u2069", "\ufeff", "\ue000", "\ufff9", "\U000e0001", "\ud800"]


@pytest.mark.parametrize("ch", HOSTILE, ids=lambda c: f"U+{ord(c):04X}")
def test_hostile_codepoints_rejected_not_stripped(env, ch):
    wid = env.workspace(); env.publish(wid, 1)
    before = env.storage()
    with env.vm.expect_revert():                      # INVALID_INPUT (or calldata encoding for lone surrogate)
        env.c.register_proposal(wid, 1, "t", "n", "Texto válido de la propuesta. " + ch + " Más texto.")
    assert env.storage() == before


def test_hostile_codepoint_in_title_rejected(env):
    wid = env.workspace(); env.publish(wid, 1)
    with env.vm.expect_revert("INVALID_INPUT"):
        env.c.register_proposal(wid, 1, "ti\u202etle", "n", TEXT_ES)
    with env.vm.expect_revert("INVALID_INPUT"):
        env.c.register_proposal(wid, 1, "ti\ntle", "n", TEXT_ES)


@pytest.mark.parametrize("text", ["", " ", "   \n\t \r\n  ", "\u00a0\u3000"])
def test_empty_and_whitespace_only_rejected(env, text):
    wid = env.workspace(); env.publish(wid, 1)
    with env.vm.expect_revert("INVALID_INPUT"):
        env.c.register_proposal(wid, 1, "t", "n", text)


@pytest.mark.parametrize("bad", [None, 5, b"bytes", ["x"], True])
def test_non_string_text_rejected(env, bad):
    wid = env.workspace(); env.publish(wid, 1)
    with env.vm.expect_revert():
        env.c.register_proposal(wid, 1, "t", "n", bad)


def test_tab_lf_cr_are_allowed_and_nfc_nfd_are_different_content(env):
    wid = env.workspace(); env.publish(wid, 1)
    nfc = "Propuesta: acción.\tSegunda línea.\r\nTercera."
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfc != nfd
    a = env.register(wid, 1, nfc, "a"); b = env.register(wid, 1, nfd, "a")
    assert env.c.get_proposal(a)["source_commitment"] != env.c.get_proposal(b)["source_commitment"]
    assert env.c.get_proposal(a)["source_commitment"] == ref.source_commitment(nfc)
    assert env.c.get_proposal(b)["source_commitment"] == ref.source_commitment(nfd)


# ----------------------------------------------------------------------------------------------- limits
def test_text_limit_boundaries(env):
    wid = env.workspace(); env.publish(wid, 1)
    env.register(wid, 1, "a" * 20000, "max")                      # exactly LIM_TEXT bytes -> 40 hard-cut segments
    assert env.c.get_proposal(ref.proposal_id(wid, 1, env.alice, ref.source_commitment("a" * 20000), "max"))["segment_count"] == 40
    before = env.storage()
    with env.vm.expect_revert("LIMIT_EXCEEDED"):
        env.register(wid, 1, "a" * 20001, "over")
    with env.vm.expect_revert("LIMIT_EXCEEDED"):
        env.register(wid, 1, "<div>" * 60000, "markup300kb")      # ~300 KB hostile markup
    assert env.storage() == before


def test_multibyte_limit_is_in_bytes_not_chars(env):
    wid = env.workspace(); env.publish(wid, 1)
    with env.vm.expect_revert("LIMIT_EXCEEDED"):
        env.register(wid, 1, "ñ" * 10001, "x")                    # 20,002 bytes
    env.register(wid, 1, "ñ" * 10000, "y")                        # 20,000 bytes


def test_segment_count_limit_enforced_at_registration(env):
    wid = env.workspace(); env.publish(wid, 1)
    env.register(wid, 1, " ".join(["A."] * 400), "ok400")
    before = env.storage()
    with env.vm.expect_revert("LIMIT_EXCEEDED"):
        env.register(wid, 1, " ".join(["A."] * 401), "boom")      # would be un-auditable -> rejected up front
    assert env.storage() == before


# ----------------------------------------------------------------------------------------------- segmentation parity with oracle
SEG_CASES = [
    TEXT_ES, TEXT_EN,
    "Línea uno\r\nLínea dos. ¿Tercera? ¡Cuarta!\rQuinta…  Sexta",
    "El valor es 1.5 ETH. Ver p. ej. la tabla… Listo!",
    "提案已提交。请审核！这是第二句。",
    "Dr. Pérez firmó. Sr. López no.",
    "x" * 1234 + " fin.",
    "  \t espacios al inicio y final \u00a0 ",
    "a. b. c.\n\n\nd?",
]


@pytest.mark.parametrize("text", SEG_CASES)
def test_segment_count_matches_independent_segmenter(env, text):
    wid = env.workspace(); env.publish(wid, 1)
    pid = env.register(wid, 1, text, "s")
    assert env.c.get_proposal(pid)["segment_count"] == len(ref.ref_segment(text))


def test_registration_ids_and_commitments_match_reference_in_english(env):
    wid = env.workspace(); env.publish(wid, 1)
    pid = env.register(wid, 1, TEXT_EN, "en-1", who=env.bob)
    assert env.c.get_proposal(pid)["source_commitment"] == ref.source_commitment(TEXT_EN)


def test_segments_partition_the_source_up_to_whitespace_only():
    """Directive 10.1 audit note: segments do not cover whitespace/line breaks between them, and NOTHING else is dropped.

    Reconstructing the source from segments + the gaps must be possible, and every gap must be pure whitespace / line breaks.
    """
    import random
    random.seed(11)
    alphabet = list("ab .!?\n\r\u2026\u00bf\u00a1\u00e9\t\u00a0\u3002")
    ws = set(ref.sys.modules["reference_segmenter"].WS) | {"\n", "\r"}
    for _ in range(3000):
        text = "".join(random.choice(alphabet) for _ in range(random.randint(0, 70)))
        spans = ref.ref_segment(text)
        pos = 0
        rebuilt = []
        for a, b in spans:
            assert a >= pos and set(text[pos:a]) <= ws, (text, spans)      # the gap is whitespace/line breaks only
            rebuilt.append(text[pos:a]); rebuilt.append(text[a:b]); pos = b
        assert set(text[pos:]) <= ws
        rebuilt.append(text[pos:])
        assert "".join(rebuilt) == text                                     # lossless reconstruction from segments + gaps
