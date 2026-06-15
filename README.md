# Transcriber

Turn audio and video into text on your own machine, on the GPU, without sending
anything to the cloud. Built with [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
and ffmpeg. For Linux desktops (tested on KDE Plasma).

## Features

- Queue one or many audio/video files (drag and drop, or "Add…").
- For video, only the audio is extracted (with ffmpeg) and transcribed.
- "Transcribe" only processes what's left: already-finished files are kept and
  skipped, so adding more files transcribes just the new ones.
- Live output with a typewriter effect as it transcribes.
- Choose where transcriptions are saved (`.txt` + `.srt` subtitles).
- Optional: also save a compact Markdown copy (no timestamps, filler trimmed) to
  any folder — handy for note apps like Obsidian or for feeding an LLM.
- Pick the model and language, with a progress bar and a collapsible log.

## Requirements

- Linux with `ffmpeg` installed.
- An NVIDIA GPU with the proprietary driver (CUDA 12) is recommended. Without a
  GPU it falls back to the CPU, which is much slower.
- [`uv`](https://github.com/astral-sh/uv) or a Python 3.10–3.12 interpreter to
  create the environment.

## Install

```bash
./install.sh      # creates an isolated environment and adds it to your app menu
./uninstall.sh    # removes it (keeps your transcriptions and the model cache)
```

The installer puts everything under `~/.local/share/transcriber/` and adds a
desktop entry. The first transcription downloads the selected Whisper model.

## Models and memory

The default is `large-v3` with `int8_float16` quantization on the GPU: it uses
about 2 GB of VRAM, so it fits on an 8 GB card even while the desktop and other
apps use some. Other options: `large-v3-turbo` (faster), `medium`, `small`.
Only one model is kept in VRAM at a time. If the GPU runs out of memory it falls
back to the CPU and tells you why.

## Development

```bash
python tests/test_output.py     # pure-logic tests (formatting, srt, filler trimming…)
```

## License

MIT — see [LICENSE](LICENSE).
