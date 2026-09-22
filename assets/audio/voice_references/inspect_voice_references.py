#!/usr/bin/env python3
"""Inspect preserved user audio. Analysis only: never modifies audio bytes."""
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
CHARACTERS = [
    ("C01", "孙亚龙", "笑皇", "01_sun_yalong.mp3", "libfile_9931df6364ac81918c54ef7f4b3cd4b7", True),
    ("C05", "潘慧", "徽州才女潘慧", "02_pan_hui.mp3", "libfile_01b7b08a8a68819194d4d89b4b98d275", True),
    ("C03", "小腿", "腿校尉", "03_xiaotui.mp3", "libfile_8a3d543b050c81918df06338855378b7", True),
    ("C02", "西卡", "内阁首辅", "04_xika.mp3", "libfile_136c35c06b8081918cbdb1240c2621a3", False),
    ("C04", "微笑", "江南转运使魏笑", "05_weixiao.mp3", "libfile_a6bb7a0c5be48191bfe37f53ea278ef6", True),
]


def db(value):
    return round(20 * math.log10(value), 6) if value > 0 else None


def inspect(row):
    cid, person, character, name, library_id, speaks = row
    path = ROOT / name
    raw = path.read_bytes()
    probe_run = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,size,bit_rate:stream=codec_name,sample_rate,channels,channel_layout,duration,bit_rate",
         "-of", "json", str(path)], capture_output=True, text=True, check=True)
    probe = json.loads(probe_run.stdout)
    stream = probe["streams"][0]
    decoded = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "error", "-i", str(path), "-map", "0:a:0",
         "-f", "f32le", "-acodec", "pcm_f32le", "pipe:1"], capture_output=True, check=True)
    values = np.frombuffer(decoded.stdout, dtype="<f4").astype(np.float64)
    rate, channels = int(stream["sample_rate"]), int(stream["channels"])
    duration = values.size / channels / rate
    amplitude = np.abs(values)
    peak = float(amplitude.max())
    rms = float(np.sqrt(np.mean(values ** 2)))
    silent = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
         "silencedetect=noise=-40dB:d=0.25", "-f", "null", "-"],
        capture_output=True, text=True, check=True)
    intervals, last_start = [], None
    for line in silent.stderr.splitlines():
        start = re.search(r"silence_start: ([\d.]+)", line)
        if start:
            last_start = float(start.group(1))
        end = re.search(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", line)
        if end:
            stop, length = float(end.group(1)), float(end.group(2))
            intervals.append({"start_seconds": last_start, "end_seconds": stop,
                              "duration_seconds": length})
            last_start = None
    if last_start is not None:
        intervals.append({"start_seconds": last_start, "end_seconds": duration,
                          "duration_seconds": duration - last_start})
    return {
        "id": f"VOICE_{cid}_USER_v01", "character_id": cid,
        "user_identified_person": person, "character_name": character,
        "file": "assets/audio/voice_references/" + name,
        "original_uploaded_filename": name, "current": True,
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        "provenance": {"kind": "user_uploaded_audio", "received_date": "2026-09-22",
                       "library_file_id": library_id,
                       "identity_binding_basis": "explicit_user_filename_to_character_mapping",
                       "independently_verified_speaker_identity": False,
                       "upstream_public_url": None},
        "preservation": {"original_bytes_preserved": True, "reencoded": False,
                         "denoised": False, "trimmed": False, "derived_audio_file": None},
        "technical": {"codec": stream["codec_name"], "sample_rate_hz": rate,
                      "channels": channels, "channel_layout": stream.get("channel_layout"),
                      "codec_bit_rate_bps": int(stream["bit_rate"]),
                      "container_duration_seconds": float(probe["format"]["duration"]),
                      "decoded_duration_seconds": round(duration, 9),
                      "decoded_sample_frames": int(values.size / channels),
                      "full_decode_pass": decoded.returncode == 0 and not decoded.stderr,
                      "decoder_errors": decoded.stderr.decode("utf-8", errors="replace") or None,
                      "sample_peak_linear": round(peak, 9), "sample_peak_dbfs": db(peak),
                      "rms_dbfs": db(rms),
                      "decoded_samples_abs_gte_1": int((amplitude >= 1.0).sum()),
                      "decoded_samples_abs_gte_0_999": int((amplitude >= 0.999).sum()),
                      "all_samples_finite": bool(np.isfinite(values).all()),
                      "silence_detection": {"threshold_dbfs": -40, "minimum_duration_seconds": 0.25,
                                            "intervals": intervals,
                                            "total_seconds": round(sum(v["duration_seconds"] for v in intervals), 6),
                                            "is_speech_activity_detection": False},
                      "true_peak_dbtp": None, "integrated_loudness_lufs": None},
        "review": {"technical_integrity_pass": bool(decoded.returncode == 0 and not decoded.stderr
                                                    and values.size > 0 and np.isfinite(values).all()
                                                    and peak > 0), "listened_by_assistant": False,
                   "human_listening_review": None, "speech_transcript": None,
                   "speaker_count": None, "target_speaker_solo": None,
                   "background_music_present": None, "overlapping_speech_present": None,
                   "intelligibility": None, "noise_assessment": None,
                   "audible_clipping": None, "selected_clean_speech_interval": None},
        "technical_flags": (["decoded_mp3_float_samples_exceed_full_scale; not proof of audible clipping"]
                            if peak >= 1 else []),
        "intended_use": {"role": "voice_timbre_reference_only",
                         "has_locked_ep01_dialogue": speaks,
                         "upload_only_to_jobs_with_this_character_speaking": True,
                         "copy_sample_words_to_film": False,
                         "copy_sample_music_or_noise_to_film": False,
                         "lip_timing_from_reference_sample": False,
                         "seedance_upload_verified": False,
                         "model_voice_similarity_verified": False,
                         "platform_accepted_duration_seconds": None,
                         "platform_accepted_audio_count": None},
    }


if __name__ == "__main__":
    records = [inspect(row) for row in CHARACTERS]
    result = {
        "schema_version": "1.0", "updated_date": "2026-09-22",
        "purpose": "Preserved original user audio and measured technical quality; no generated dialogue",
        "asset_count": len(records), "total_original_bytes": sum(r["bytes"] for r in records),
        "total_decoded_duration_seconds": round(sum(r["technical"]["decoded_duration_seconds"] for r in records), 9),
        "measurement_scope": "ffprobe metadata, full ffmpeg float decode, sample peak/RMS, amplitude silence; no listening or transcription",
        "tools": {"ffmpeg": subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True).stdout.splitlines()[0],
                  "ffprobe": subprocess.run(["ffprobe", "-version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]},
        "limitations": ["Mono describes channels, not number of speakers.",
                        "Sample peak is not oversampled true peak; positive MP3 float peaks need listening, not a claim of audible clipping.",
                        "No amplitude silence does not prove continuous clean speech.",
                        "Voice reference does not drive the timing or phonemes of new script dialogue.",
                        "User reports the platform version; this archive has not uploaded or tested these files in Seedance."],
        "assets": records,
    }
    (ROOT / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"assets": len(records), "technical_pass": all(r["review"]["technical_integrity_pass"] for r in records),
                      "original_bytes": result["total_original_bytes"], "decoded_seconds": result["total_decoded_duration_seconds"],
                      "technical_flags": {r["character_id"]: r["technical_flags"] for r in records if r["technical_flags"]}}, ensure_ascii=False))
