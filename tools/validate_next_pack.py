#!/usr/bin/env python3
"""Audit EP03–EP05 source documents. Does not claim video or lip-sync validation."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPISODES = {"ep03": ["P01", "P02"], "ep04": ["Q01", "Q02", "Q03"], "ep05": ["R01", "R02", "R03"]}
SINGING = {"R02", "R03"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: str | Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def safe_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(ROOT):
        raise ValueError(f"Repository-relative path required: {relative}")
    return path


def audit() -> dict:
    errors, warnings, pending, rows = [], [], [], []
    all_blocks, previous_rows = {}, []
    source_hashes = {}

    def issue(message: str, target: list = errors) -> None:
        target.append(message)

    for episode, expected in EPISODES.items():
        base = Path("episodes") / episode / "production"
        try:
            timeline = read_json(base / "timeline.json")
            refs = read_json(base / "refs_upload.json")
        except (FileNotFoundError, ValueError) as exc:
            issue(f"{episode}: production inputs unavailable: {exc}")
            continue
        for source in [base / "timeline.json", base / "refs_upload.json"]:
            source_hashes[str(source)] = sha((ROOT / source).read_bytes())
        contract_file = base / "audio" / "dialogue_contract.json"
        try:
            contract = read_json(contract_file)
            source_hashes[str(contract_file)] = sha((ROOT / contract_file).read_bytes())
            if contract.get("dialogues") != timeline.get("dialogues"):
                issue(f"{episode}: dialogue contract diverges from the timeline")
        except (FileNotFoundError, ValueError) as exc:
            issue(f"{episode}: missing dialogue contract: {exc}")
        blocks = timeline.get("blocks", [])
        if [b["id"] for b in blocks] != expected:
            issue(f"{episode}: block order must be {expected}")
        jobs = refs.get("jobs", [])
        if [j["id"] for j in jobs] != expected:
            issue(f"{episode}: upload job order must be {expected}")
        if timeline.get("duration_seconds") != 30 * len(expected):
            issue(f"{episode}: duration_seconds must be {30 * len(expected)}")
        if timeline.get("actual_video_generated") is not False or timeline.get("actual_av_review_performed") is not False:
            issue(f"{episode}: must explicitly state no generated video or actual AV review")
        for i, block in enumerate(blocks):
            jid = block["id"]
            all_blocks[jid] = block
            if [block.get("start"), block.get("end"), block.get("duration")] != [i * 30, (i + 1) * 30, 30]:
                issue(f"{jid}: chapter timing is not contiguous 30-second blocks")
            if [block.get("source_start"), block.get("source_end")] != [0, 30]:
                issue(f"{jid}: source interval must be [0,30]")
            shots = [s for s in timeline.get("shots", []) if s.get("block") == jid]
            cursor = 0
            for shot in shots:
                start, end = shot.get("source_start"), shot.get("source_end")
                if start != cursor or not isinstance(end, (int, float)) or end <= start:
                    issue(f"{jid}/{shot.get('id')}: shot gap, overlap, or nonpositive duration")
                if [shot.get("start"), shot.get("end")] != [i * 30 + start, i * 30 + end]:
                    issue(f"{jid}/{shot.get('id')}: local/global timestamp mismatch")
                cursor = end
            if cursor != 30:
                issue(f"{jid}: shots end at {cursor}, expected 30")
            previous_rows.append((jid, block.get("previous_reference", {})))
            for side in ["start_keyframe", "end_keyframe"]:
                keyframe = block.get(side, {})
                if not keyframe.get("file"):
                    issue(f"{jid}: {side} is a description, not a rendered keyframe", pending)
        for job in jobs:
            jid = job["id"]
            job_pending = []
            images, audio = job.get("slots", []), job.get("audio_slots", [])
            if not 4 <= len(images) <= 7:
                issue(f"{jid}: expected a restrained 4–7 image upload set, got {len(images)}")
            if job.get("source_duration_s") != 30 or job.get("source_keep_s") != [0, 30]:
                issue(f"{jid}: job must retain source [0,30]")
            if job.get("image_count") != len(images) or job.get("audio_count") != len(audio):
                issue(f"{jid}: declared reference count mismatch")
            bound = set()
            for field, label in [(images, "图片"), (audio, "音频")]:
                for n, ref in enumerate(field, 1):
                    slot = ref.get("slot")
                    if slot != f"@{label}{n}":
                        issue(f"{jid}: {label} slots are not consecutive")
                    bound.add(slot)
                    relative = ref.get("file")
                    if not relative:
                        message = f"{jid}/{slot}: required final song guide missing" if jid in SINGING and label == "音频" else f"{jid}/{slot}: reference file missing"
                        if not (jid in SINGING and label == "音频" and ref.get("required") is True):
                            issue(message)
                        job_pending.append(message)
                        continue
                    path = safe_path(relative)
                    if not path.is_file():
                        issue(f"{jid}/{slot}: missing referenced file {relative}")
                        job_pending.append(relative)
                        continue
                    actual = sha(path.read_bytes())
                    source_hashes[relative] = actual
                    if ref.get("sha256") != actual:
                        issue(f"{jid}/{slot}: missing or stale SHA-256 for {relative}")
                    if label == "图片" and re.search(r"ANGLES|EXPRESSIONS|CONTACT|COLLAGE|REVIEW", path.name, re.I):
                        issue(f"{jid}: review/contact board included as model image input: {relative}")
            prompt_file = job.get("prompt_file")
            try:
                prompt_bytes = safe_path(prompt_file).read_bytes()
                prompt = prompt_bytes.decode("utf-8")
            except (TypeError, OSError, ValueError) as exc:
                issue(f"{jid}: prompt unavailable: {exc}")
                continue
            count = len(prompt)
            source_hashes[prompt_file] = sha(prompt_bytes)
            if count > 2000:
                issue(f"{jid}: prompt {count} Unicode code points exceeds 2000")
            if job.get("prompt_unicode_characters") != count:
                issue(f"{jid}: prompt character count is stale")
            mentioned = set(re.findall(r"@(?:图片|音频|视频)\d+", prompt))
            if mentioned - bound:
                issue(f"{jid}: unbound reference tags {sorted(mentioned - bound)}")
            if jid in SINGING:
                if len(audio) != 1 or audio[0].get("required") is not True:
                    issue(f"{jid}: one mandatory final-performance guide slot required")
                if not audio[0].get("file") and job.get("ready_for_generation") is not False:
                    issue(f"{jid}: cannot mark generation ready without the final song guide")
                if "口型" not in prompt or "@音频1" not in prompt:
                    issue(f"{jid}: final guide and lip instructions must both be present")
            dialogues = [d for d in timeline.get("dialogues", []) if d.get("block") == jid]
            rates = []
            for d in dialogues:
                start, end = d.get("source_start"), d.get("source_end")
                if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not 0 <= start < end <= 30:
                    issue(f"{jid}/{d.get('id')}: invalid dialogue window")
                    continue
                chars = len(re.findall(r"[\u3400-\u9fffA-Za-z0-9]", d.get("text", "")))
                rate = round(chars / (end - start), 3)
                rates.append({"id": d.get("id"), "speaker_id": d.get("speaker_id"), "spoken_characters": chars, "duration_s": round(end-start, 3), "characters_per_second": rate})
                if rate > 5.5:
                    issue(f"{jid}/{d.get('id')}: dialogue rate {rate} characters/s is too dense")
                elif rate > 4.8:
                    issue(f"{jid}/{d.get('id')}: brisk dialogue {rate} characters/s requires take review", warnings)
                if d.get("speaker_id") in {"C01", "C02", "C03", "C04", "C05"}:
                    matched = [a for a in audio if a.get("character_id") == d["speaker_id"]]
                    if len(matched) != 1 or not matched[0].get("file"):
                        issue(f"{jid}/{d.get('id')}: speaking principal needs exactly one real voice-timbre reference")
                    elif d.get("voice_reference_file") != matched[0]["file"]:
                        issue(f"{jid}/{d.get('id')}: voice reference belongs to the wrong slot/file")
                if not any(s.get("source_start", 31) <= start and s.get("source_end", -1) >= end for s in timeline.get("shots", []) if s.get("block") == jid and d.get("id") in s.get("dialogue_ids", [])):
                    issue(f"{jid}/{d.get('id')}: dialogue window is not contained in its assigned shot")
            pending.extend(job_pending)
            rows.append({"episode": episode.upper(), "id": jid, "duration_s": 30, "shots": sum(s.get("block") == jid for s in timeline.get("shots", [])), "spoken_lines": len(dialogues), "images": len(images), "audio_slots": len(audio), "available_audio_files": sum(bool(a.get("file")) for a in audio), "prompt_unicode_characters": count, "all_declared_reference_files_ready": not job_pending, "production_ready": False, "dialogue_rates": rates})
    for jid, previous in previous_rows:
        source = previous.get("from_block")
        segment = previous.get("source_segment_s")
        if source and source not in all_blocks and source != "N05":
            issue(f"{jid}: unknown previous block {source}")
        if segment is not None and (len(segment) != 2 or not 0 <= segment[0] < segment[1] <= 30):
            issue(f"{jid}: previous source interval outside [0,30]")
        if not previous.get("purpose"):
            issue(f"{jid}: missing explicit continuity purpose")
        previous_scene = all_blocks.get(source, {}).get("end_scene_id")
        current_scene = all_blocks[jid].get("start_scene_id")
        if not previous_scene or not current_scene:
            if source in all_blocks:
                issue(f"{jid}: explicit start_scene_id/end_scene_id required to audit spatial continuity")
        if source in all_blocks and previous_scene and current_scene and previous_scene != current_scene:
            purpose = previous.get("purpose", "")
            if segment is not None or previous.get("video_file") or previous.get("tail_frame_file"):
                issue(f"{jid}: location changes; prior spatial reference must not be attached")
            if not any(word in purpose for word in ["不同", "新", "不继承", "换场", "切", "另", "不引用"]):
                issue(f"{jid}: location change needs an explicit continuity reset", warnings)
    for relative in ["episodes/ep03/production/audio/COMEDY_BEAT_CONTRACT.json", "episodes/ep05/production/audio/song_cues.json", "episodes/ep05/production/audio/song_cues.csv", "episodes/ep05/production/audio/SONG_SYNC_WORKFLOW.md"]:
        path = ROOT / relative
        if not path.is_file():
            issue(f"Required performance timing document missing: {relative}")
        else:
            source_hashes[relative] = sha(path.read_bytes())
    return {"schema_version": "1.0", "date": "2026-09-23", "scope": "EP03–EP05 static source audit", "static_validation_pass": not errors, "errors": errors, "warnings": warnings, "pending_production_items": list(dict.fromkeys(pending)), "blocks": rows, "block_count": len(rows), "duration_seconds": sum(r["duration_s"] for r in rows), "generated_video_checked": False, "real_lip_sync_verified": False, "source_performance_waveform_received": False, "first_last_keyframe_images_generated": False, "production_ready": False, "source_file_sha256": source_hashes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = audit()
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        path = args.report if args.report.is_absolute() else ROOT / args.report
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "source_file_sha256"}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["static_validation_pass"] else 1)


if __name__ == "__main__":
    main()
