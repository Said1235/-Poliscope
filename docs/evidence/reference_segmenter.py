"""Independent reference implementation of the POLISCOPE segmenter (spec: DATA_MODEL §4).

Pure, language-neutral, O(n), no regex, no unicodedata. Offsets are CODEPOINT offsets
into the exact original text; `end` is exclusive.
"""
SEG_MAX_CHARS = 500            # LIM-SEG-CHARS (provisional)
WS = frozenset([" ", "\t", "\u00a0", "\u202f", "\u205f", "\u3000"] + [chr(c) for c in range(0x2000, 0x200B)])
ASCII_TERMS = frozenset([".", "!", "?", "\u2026"])      # need following whitespace / end of line
CJK_TERMS = frozenset(["\u3002", "\uff01", "\uff1f"])   # split immediately

def segment(text, seg_max=SEG_MAX_CHARS):
    spans = []
    n = len(text)

    def emit(s, e):
        while s < e and text[s] in WS: s += 1
        while e > s and text[e - 1] in WS: e -= 1
        while e - s > seg_max:                         # hard cut, no whitespace search (O(n))
            cut = s + seg_max
            piece_end = cut
            while piece_end > s and text[piece_end - 1] in WS: piece_end -= 1   # keep every segment trimmed
            spans.append((s, piece_end))                # s is non-WS (trimmed above), so piece_end > s
            s = cut
            while s < e and text[s] in WS: s += 1
        if e > s:
            spans.append((s, e))

    def split_line(a, b):
        s = a
        for k in range(a, b):
            c = text[k]
            if c in CJK_TERMS or (c in ASCII_TERMS and (k + 1 == b or text[k + 1] in WS)):
                emit(s, k + 1); s = k + 1
        emit(s, b)

    i = 0
    while i < n:
        j = i
        while j < n and text[j] != "\n" and text[j] != "\r": j += 1
        split_line(i, j)
        if j < n:
            j += 2 if (text[j] == "\r" and j + 1 < n and text[j + 1] == "\n") else 1
        i = j
    return spans

def citable(seg_text, min_alnum=8):
    return sum(1 for c in seg_text if c.isalnum()) >= min_alnum
