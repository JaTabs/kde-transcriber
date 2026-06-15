import re
from pathlib import Path

# Non-lexical fillers removed only in the compact Markdown copy. Deliberately
# conservative (English + Spanish): nothing ambiguous that could be a real word.
FILLERS = {
    "eh", "ehm", "em", "emm", "mmm", "mm", "ah", "ahm", "aah",
    "uh", "uhm", "um", "umm", "er", "err", "hmm", "hm",
}

_FILLER_RE = re.compile(
    r"\b(" + "|".join(sorted(FILLERS, key=len, reverse=True)) + r")\b,?",
    re.IGNORECASE,
)


def hms(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def srt_time(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def raw_text(segments, timestamps):
    lines = []
    for start, _end, text in segments:
        text = text.strip()
        lines.append(f"[{hms(start)}] {text}" if timestamps else text)
    return "\n".join(lines) + "\n"


def srt(segments):
    blocks = []
    for i, (start, end, text) in enumerate(segments, 1):
        blocks.append(f"{i}\n{srt_time(start)} --> {srt_time(end)}\n{text.strip()}\n")
    return "\n".join(blocks)


def strip_fillers(text):
    text = _FILLER_RE.sub("", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:])\1+", r"\1", text)
    text = re.sub(r",\s*\.", ".", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" ,;:")


def compressed_text(segments):
    joined = " ".join(text.strip() for _start, _end, text in segments)
    return strip_fillers(joined)


def compressed_md(segments, meta):
    front = (
        "---\n"
        f"source: {meta['source']}\n"
        f"date: {meta['date']}\n"
        f"duration: {meta['duration']}\n"
        f"model: {meta['model']}\n"
        f"language: {meta['language']}\n"
        "---\n\n"
    )
    return front + compressed_text(segments) + "\n"


def unique_path(path):
    path = Path(path)
    if not path.exists():
        return path
    n = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def write_results(segments, src, meta, timestamps, output_dir, markdown_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = Path(src).stem
    written = []

    txt = unique_path(out / f"{base}.txt")
    txt.write_text(raw_text(segments, timestamps), encoding="utf-8")
    written.append(txt)

    sub = unique_path(out / f"{base}.srt")
    sub.write_text(srt(segments), encoding="utf-8")
    written.append(sub)

    if markdown_dir:
        md_dir = Path(markdown_dir)
        md_dir.mkdir(parents=True, exist_ok=True)
        md = unique_path(md_dir / f"{base}.md")
        md.write_text(compressed_md(segments, meta), encoding="utf-8")
        written.append(md)

    return written
