"""Near-duplicate guidance: overlap % and only readable change hunks (no giant unified diff)."""

from __future__ import annotations

import difflib
import re


def _clip(s: str, max_len: int = 280) -> str:
    s = s.strip().replace("\n", " ")
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _words(s: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", s, flags=re.UNICODE) or [s]


def _word_change_bullets(
    ref_text: str,
    new_text: str,
    max_hunks: int = 20,
    frag_len: int = 140,
) -> list[str]:
    aw = _words(ref_text)
    bw = _words(new_text)
    if not aw and not bw:
        return []
    sm = difflib.SequenceMatcher(None, aw, bw, autojunk=False)
    lines: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if len(lines) >= max_hunks:
            lines.append("… (more word-level differences omitted)")
            break
        ref_chunk = _clip(" ".join(aw[i1:i2]), frag_len)
        new_chunk = _clip(" ".join(bw[j1:j2]), frag_len)
        if tag == "replace":
            lines.append(f"• Change «{new_chunk}» → «{ref_chunk}» (reference).")
        elif tag == "delete":
            lines.append(f"• Add (in reference, missing in yours): «{ref_chunk}»")
        elif tag == "insert":
            lines.append(f"• Remove (not in reference): «{new_chunk}»")
    return lines


def _line_change_bullets(
    ref_text: str,
    new_text: str,
    max_hunks: int = 25,
    line_clip: int = 320,
) -> list[str]:
    ref_lines = ref_text.splitlines() or [ref_text]
    new_lines = new_text.splitlines() or [new_text]
    sm = difflib.SequenceMatcher(None, ref_lines, new_lines, autojunk=False)
    out: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if len(out) >= max_hunks:
            out.append("… (more line blocks omitted)")
            break
        ref_block = "\n".join(ref_lines[i1:i2])
        new_block = "\n".join(new_lines[j1:j2])
        ref_block = _clip(ref_block, line_clip)
        new_block = _clip(new_block, line_clip)
        if tag == "replace":
            out.append(
                f"• Lines ref {i1 + 1}–{i2} vs yours {j1 + 1}–{j2}:\n"
                f"  REF:   {ref_block}\n"
                f"  YOURS: {new_block}"
            )
        elif tag == "delete":
            out.append(f"• Reference has extra lines {i1 + 1}–{i2} (add to match):\n  {ref_block}")
        elif tag == "insert":
            out.append(f"• Your upload has extra lines {j1 + 1}–{j2} (remove to match):\n  {new_block}")
    return out


def build_content_guidance(
    new_text: str,
    ref_text: str,
    ref_filename: str,
    jaccard_similarity: float,
    max_chars: int = 6000,
) -> str:
    match_pct = round(jaccard_similarity * 100, 2)
    diff_pct = round(max(0.0, (1.0 - jaccard_similarity) * 100), 2)
    header = [
        f"Overlap with \"{ref_filename}\": ~{match_pct}% (word Jaccard). ~{diff_pct}% of words differ.",
        "",
        "Changes to apply (only differing parts; truncated for readability):",
        "",
    ]

    # Prefer line-level when documents have multiple lines (readable blocks).
    ref_line_count = ref_text.count("\n") + (1 if ref_text.strip() else 0)
    new_line_count = new_text.count("\n") + (1 if new_text.strip() else 0)
    use_line_first = max(ref_line_count, new_line_count) >= 2

    if use_line_first:
        bullets = _line_change_bullets(ref_text, new_text)
        if not bullets or (len(bullets) == 1 and len(ref_text) > 2000):
            # Long single-line PDF dumps: fall back to word bullets
            bullets = _word_change_bullets(ref_text, new_text)
    else:
        bullets = _word_change_bullets(ref_text, new_text)

    if not bullets:
        bullets = ["(No discrete diff hunks — texts may differ only in spacing.)"]

    out = "\n".join(header) + "\n".join(bullets)
    if len(out) > max_chars:
        return out[: max_chars - 20] + "\n… (truncated)"
    return out


def build_image_guidance(similarity: float, ref_filename: str) -> str:
    pct = round(similarity * 100, 2)
    return f"Visual similarity vs \"{ref_filename}\": ~{pct}% (perceptual hash)."
