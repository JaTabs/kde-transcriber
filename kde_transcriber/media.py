import json
import subprocess


class MediaError(Exception):
    pass


def has_audio_stream(path):
    out = _run([
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=index", "-of", "json", str(path),
    ])
    return bool(json.loads(out).get("streams"))


def extract_audio(src, dst):
    # 16 kHz mono PCM is what Whisper expects; -vn drops the video track.
    _run([
        "ffmpeg", "-y", "-i", str(src), "-vn",
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst),
    ])


def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise MediaError(proc.stderr.strip() or f"{cmd[0]} failed")
    return proc.stdout
