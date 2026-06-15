import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transcriber import output

SEGMENTS = [(0.0, 2.0, "Hello"), (2.5, 5.0, "there")]
META = {"source": "clip.mp4", "date": "2026-06-15", "duration": "0:00:05",
        "model": "large-v3", "language": "en"}


def test_hms():
    assert output.hms(0) == "0:00:00"
    assert output.hms(3661) == "1:01:01"


def test_srt_time():
    assert output.srt_time(3661.5) == "01:01:01,500"


def test_raw_text():
    assert output.raw_text(SEGMENTS, False) == "Hello\nthere\n"
    assert output.raw_text(SEGMENTS, True) == "[0:00:00] Hello\n[0:00:02] there\n"


def test_srt():
    expected = ("1\n00:00:00,000 --> 00:00:02,000\nHello\n"
                "\n2\n00:00:02,500 --> 00:00:05,000\nthere\n")
    assert output.srt(SEGMENTS) == expected


def test_strip_fillers():
    assert output.strip_fillers("um hello uh there") == "hello there"
    assert output.strip_fillers("Well, eh, this is a test.") == "Well, this is a test."


def test_compressed_md_frontmatter():
    md = output.compressed_md([(0, 1, "Hello"), (1, 2, "um"), (2, 3, "world")], META)
    assert "source: clip.mp4" in md and "language: en" in md
    assert md.strip().endswith("Hello world")     # filler "um" removed, no timestamps


def test_write_results_with_and_without_markdown():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "out"
        md = Path(d) / "md"
        # con markdown
        paths = output.write_results(SEGMENTS, "/x/clip.mp4", META, False, str(out), str(md))
        names = sorted(p.name for p in paths)
        assert names == ["clip.md", "clip.srt", "clip.txt"], names
        assert (out / "clip.txt").exists() and (md / "clip.md").exists()
        # sin markdown (markdown_dir vacío) -> solo txt+srt
        paths2 = output.write_results(SEGMENTS, "/x/other.mp4", META, False, str(out), "")
        assert sorted(p.name for p in paths2) == ["other.srt", "other.txt"]


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} tests OK")


if __name__ == "__main__":
    _run()
