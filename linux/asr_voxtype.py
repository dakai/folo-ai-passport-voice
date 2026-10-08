#!/usr/bin/env python3
"""Local offline ASR via the voxtype CLI (SenseVoice engine default).

One utterance = one WAV file + one `voxtype transcribe` call. The local
engines are batch: one final result per utterance, no partials.
"""

import os
import struct
import subprocess
import tempfile
import wave

SAMPLE_RATE = 16000
TRANSCRIBE_TIMEOUT = 60.0
VAD_SKIP_MARK = "No speech detected, skipping transcription."


class AsrError(Exception):
    """voxtype invocation failed (missing binary, timeout, nonzero exit)."""


def parse_transcribe_output(stdout):
    """Extract the transcript from `voxtype transcribe` stdout.

    Tracing logs also go to stdout, so split on the FIRST blank line and
    keep the remainder (a transcript can hold blank lines). VAD skips and
    unparsable output yield "".
    """
    if not stdout:
        return ""
    if VAD_SKIP_MARK in stdout:
        return ""
    _, sep, tail = stdout.partition("\n\n")
    if not sep:
        return ""
    return tail.strip()


def write_wav(path, samples, sample_rate=SAMPLE_RATE):
    """Write mono int16 samples to a WAV file voxtype accepts."""
    clamped = [max(-32768, min(32767, int(v))) for v in samples]
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack("<%dh" % len(clamped), *clamped))


def transcribe_wav(path, voxtype_bin="voxtype", engine="sensevoice",
                   timeout=TRANSCRIBE_TIMEOUT):
    """Transcribe one WAV file. Raises AsrError on tool failure."""
    try:
        proc = subprocess.run(
            [voxtype_bin, "transcribe", "--engine", engine, path],
            capture_output=True, text=True, timeout=timeout)
    except OSError as e:
        raise AsrError(f"voxtype 启动失败: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise AsrError(f"voxtype 超时({timeout:.0f}s)") from e
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise AsrError(f"voxtype 退出码 {proc.returncode}: "
                       f"{err[-1] if err else '无输出'}")
    return parse_transcribe_output(proc.stdout or "")


def transcribe_pcm(samples, voxtype_bin="voxtype", engine="sensevoice",
                   timeout=TRANSCRIBE_TIMEOUT):
    """Transcribe mono int16 samples at 16 kHz. Empty input yields ""."""
    if not samples:
        return ""
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="voice-utt-")
    os.close(fd)
    try:
        write_wav(path, samples)
        return transcribe_wav(path, voxtype_bin=voxtype_bin,
                              engine=engine, timeout=timeout)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
