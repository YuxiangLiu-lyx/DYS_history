#!/usr/bin/env python3
"""Build EP02 per-block upload ZIPs from refs_upload.json, without media generation."""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROD = "episodes/ep02/production"
REFS_FILE = f"{PROD}/refs_upload.json"
GITHUB = "https://github.com/YuxiangLiu-lyx/DYS_history"
JOB_IDS = ["N01", "N02", "N03", "N04", "N05"]
ZIP_DATE = (2026, 9, 23, 0, 0, 0)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def read_source(relative: str) -> bytes:
    path = (ROOT / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(ROOT):
        raise ValueError(f"Repository-relative source required: {relative}")
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_bytes()


def remote_links(doc: str, directory: str) -> str:
    """Make repository document links usable after extracting a standalone ZIP."""
    def replace(match: re.Match) -> str:
        label, target = match.groups()
        if target.startswith(("https://", "http://", "#", "mailto:")):
            return match.group(0)
        relative = posixpath.normpath(posixpath.join(directory, target))
        return f"[{label}]({GITHUB}/blob/main/{relative})"
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace, doc)


def prepare(selected_jobs: list[str] | None = None, revision: str = "v1_1") -> tuple[dict, list[dict], dict[str, bytes]]:
    sources = {REFS_FILE: read_source(REFS_FILE)}
    refs = json.loads(sources[REFS_FILE])
    if refs["episode"] != "EP02" or [j["id"] for j in refs["jobs"]] != JOB_IDS:
        raise ValueError("EP02 N01–N05 references required, in that order")
    if refs["source_duration_s"] != 30:
        raise ValueError("This builder expects five 30-second source jobs")
    max_chars = min(2000, refs["prompt_max_unicode_characters"])
    quickstart_file = f"{PROD}/QUICKSTART.md"
    sources[quickstart_file] = read_source(quickstart_file)
    quickstart = remote_links(sources[quickstart_file].decode("utf-8"), PROD).encode("utf-8")
    bundles = []
    for job in refs["jobs"]:
        jid = job["id"]
        if selected_jobs and jid not in selected_jobs:
            continue
        if job["source_duration_s"] != 30 or job["source_keep_s"] != [0, 30]:
            raise ValueError(f"{jid}: unexpected source duration or keep interval")
        rows, contents = [], {}
        for modality, field, folder, prefix, label in [
            ("image", "slots", "images", "img", "图片"),
            ("audio", "audio_slots", "audio", "audio", "音频"),
        ]:
            slots = job[field]
            if len(slots) != job[f"{modality}_count"]:
                raise ValueError(f"{jid}: {modality} count disagrees with upload slots")
            for number, item in enumerate(slots, 1):
                if item["slot"] != f"@{label}{number}":
                    raise ValueError(f"{jid}: nonconsecutive {modality} slots")
                source = item["file"]
                if source is None:
                    # An explicit missing final song is a production blocker,
                    # not an audio file to fabricate or silently omit.
                    allowed_pending = (
                        jid == "N04" and modality == "audio" and number == 1
                        and item.get("character_id") == "C05"
                        and item.get("purpose") == "final_song_segment_timing_and_phonemes"
                        and item.get("status") == "awaiting_user_song_excerpt"
                        and item.get("required") is True
                        and item.get("sha256") is None
                    )
                    if not allowed_pending:
                        raise ValueError(f"{jid}: undeclared missing reference: {item['slot']}")
                    rows.append({
                        "modality": modality, "slot": item["slot"],
                        "bundle_file": None, "repository_file": None, "sha256": None,
                        "role": "最终18秒演唱选段；待用户提供，生成前必须绑定",
                        "character_id": "C05", "purpose": item["purpose"],
                        "status": item["status"], "required": True,
                        "expected_reference_seconds": [0, 18],
                        "maps_to_video_seconds": [4, 22],
                    })
                    continue
                basename = Path(source).name
                if modality == "image" and re.search(
                    r"ANGLES|EXPRESSIONS|CONTACT|BOARD|COLLAGE|REVIEW", basename, re.I
                ):
                    raise ValueError(f"Human-review board must not be uploaded: {source}")
                data = read_source(source)
                if sha(data) != item["sha256"]:
                    raise ValueError(f"{jid}: reference SHA mismatch: {source}")
                sources[source] = data
                entry = f"{folder}/{prefix}{number:02d}_{basename}"
                contents[entry] = data
                rows.append({
                    "modality": modality,
                    "slot": item["slot"],
                    "bundle_file": entry,
                    "repository_file": source,
                    "sha256": sha(data),
                    "role": item.get("role"),
                    "character_id": item.get("character_id"),
                    "purpose": item.get("purpose"),
                    "status": item.get("status", "user_voice_timbre_reference"),
                })
        prompt_file = job["prompt_file"]
        prompt = read_source(prompt_file)
        sources[prompt_file] = prompt
        prompt_text = prompt.decode("utf-8")
        if len(prompt_text) > max_chars:
            raise ValueError(f"{jid}: prompt is {len(prompt_text)} characters, over {max_chars}")
        if len(prompt_text) != job["prompt_unicode_characters"]:
            raise ValueError(f"{jid}: stored prompt character count is stale")
        bound = {row["slot"] for row in rows}
        mentioned = set(re.findall(r"@(?:图片|音频|视频)\d+", prompt_text))
        if mentioned - bound:
            raise ValueError(f"{jid}: unbound prompt references: {sorted(mentioned - bound)}")
        contents["PROMPT.txt"] = prompt
        order = [
            f"# {jid} · 30秒上传清单", "",
            "先解压。分别按本表上传本幕图片、音频，并核对界面的实际标签；只粘贴 PROMPT.txt 正文。",
            "图片和音频各自从1编号；同名角色在不同幕的槽位可能不同，不沿用上幕标签。", "",
            "| 标签 | 包内文件 | 用途 |", "|---|---|---|",
        ]
        for row in rows:
            purpose = row["role"] or f"{row['character_id']} 原声音色；仅生成本幕新台词"
            entry = row["bundle_file"] or "**待提供，包内无此音频**"
            order.append(f"| {row['slot']} | {entry} | {purpose} |")
        pending = [row for row in rows if row["bundle_file"] is None]
        if pending:
            order.extend(["", "**N04尚不能生成：必须补齐最终18秒演唱选段。音频0–18秒映射视频4–22秒，9–16秒面部近景核对口型。潘慧说话样本不能替代这段歌曲。包内未制作静音占位或假音轨。**"])
        order.extend([
            "", "前段参考：" + job["previous_reference"]["purpose"],
            "", "本包未包含真实前段视频或尾帧，当前Prompt没有虚构的视频标签。取得合格素材后按生产包提取、记录并绑定。",
            "新定妆和场景为待用户审阅的候选图；本包没有完整Storyboard实物、起末关键帧、视频或正式对白音轨。",
            "源图片与MP3字节不变；编号只明确上传次序。原声只借音色，不复读聊天、不复制背景声。", "",
        ])
        contents["UPLOAD_ORDER.md"] = "\n".join(order).encode("utf-8")
        contents["QUICKSTART.md"] = quickstart
        included_sources = {
            source: sha(sources[source])
            for source in [REFS_FILE, quickstart_file, prompt_file]
        }
        included_sources.update({row["repository_file"]: row["sha256"] for row in rows if row["repository_file"] is not None})
        input_manifest = {
            "episode": "EP02", "revision": revision, "job": jid,
            "source_duration_seconds": 30,
            "target_timeline_s": job["target_timeline_s"],
            "references": rows,
            "prompt_file": prompt_file,
            "prompt_sha256": sha(prompt),
            "prompt_unicode_characters_including_newlines": len(prompt_text),
            "source_file_sha256": included_sources,
            "new_visual_assets_status": "pending_user_review",
            "generated_video_included": False,
            "actual_start_end_keyframes_included": False,
            "actual_previous_video_or_tail_frame_included": False,
            "final_dialogue_audio_included": False,
            "music_included": False,
            "audio_reference_slots": job["audio_count"],
            "available_audio_reference_files": sum(row["modality"] == "audio" and row["bundle_file"] is not None for row in rows),
            "pending_required_references": pending,
            "required_references_complete": not pending,
            "ready_for_generation": False,
        }
        contents["INPUT_MANIFEST.json"] = json_bytes(input_manifest)
        contents["README_DELIVERY.md"] = (f"""# EP02 {jid} 材料包

1. 新便装、场景先按候选图审阅；起末帧目前只有构图说明，未生成实物。确认资产与分镜后再试片。
2. 解压，按 UPLOAD_ORDER.md 顺序单独上传图像和音频；ZIP本身不是Seedance输入。
3. 选择实际可用的Seedance 2.5、30秒、16:9；复制PROMPT.txt，核对引用标签。此文和上传表无需粘贴进Prompt。
4. 原声音频仅参考音色，生成指定角色的新台词；只让可见说话人动嘴，画外声不驱动听者。先检查同期口型、声音来源，再后期混音。
5. N04边唱边舞；先补齐最终18秒歌曲选段作为音节与节奏参考，4–22秒演唱、9–16秒近景看清口型和句间微笑。当前选段未收到，N04不能生成。后期铺同版同速选段，不用说话样本或凭歌名编曲替代。
6. 保存实际输出与验收记录；逐段检查人物、手脚、杯子、服装、轴线、尾字与口型。没有任何一次生成零错误的保证。修正错误后再接下一段。

本包不含已生成视频、正式对白音轨、真实首末帧或前段参考片。新图是候选，不等同于用户已验收。字幕、标题和时间地点提示后期叠加。

[完整生产包]({GITHUB}/blob/main/{PROD}/VIDEO_PRODUCTION_PACK.md) · [导演稿]({GITHUB}/blob/main/episodes/ep02/script/EP02_DIRECTOR_v1.md) · [权威上传清单]({GITHUB}/blob/main/{REFS_FILE})

AI生成／AI辅助制作／架空历史二创。人物官职、事件与对白为艺术虚构。
""").encode("utf-8")
        bundles.append({"job": job, "contents": contents, "manifest": input_manifest})
    return refs, bundles, sources


def verify_sources(sources: dict[str, bytes]) -> None:
    for source, data in sources.items():
        if read_source(source) != data:
            raise RuntimeError(f"Source changed during packaging; rerun: {source}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate sources without creating ZIPs")
    parser.add_argument("--out", type=Path, help="Output directory outside the Git repository")
    parser.add_argument("--record", type=Path, help="Write derived ZIP/SHA validation record after build")
    parser.add_argument("--job", action="append", choices=JOB_IDS, help="Build selected job only; may repeat")
    parser.add_argument("--revision", default="v1_1", help="Revision suffix, e.g. v1_1")
    args = parser.parse_args()
    if not args.check and not args.out:
        parser.error("Supply --check or --out")
    if args.check and args.record:
        parser.error("--record requires a completed ZIP build")
    if not re.fullmatch(r"[A-Za-z0-9_]+", args.revision):
        parser.error("--revision must contain only letters, digits and underscores")
    refs, bundles, sources = prepare(args.job, args.revision)
    verify_sources(sources)
    if args.check:
        print(json.dumps({
            "source_validation_pass": True,
            "source_file_count": len(sources),
            "jobs": [{"id": b["job"]["id"], "images": b["job"]["image_count"],
                      "audio": b["job"]["audio_count"],
                      "available_audio": b["manifest"]["available_audio_reference_files"],
                      "pending_required_references": b["manifest"]["pending_required_references"],
                      "prompt_characters": b["manifest"]["prompt_unicode_characters_including_newlines"]}
                     for b in bundles],
            "generated_media_checked": False,
        }, ensure_ascii=False, indent=2))
        return
    out = args.out.resolve()
    if out.is_relative_to(ROOT):
        raise ValueError("Derived ZIPs must be outside the Git repository")
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for bundle in bundles:
        jid, contents = bundle["job"]["id"], bundle["contents"]
        dest = out / f"EP02_{jid}_Seedance25_{args.revision}.zip"
        # Readers must never see a partially written final ZIP.
        with tempfile.TemporaryDirectory(prefix=f".ep02_{jid}_", dir=out) as temporary:
            staged = Path(temporary) / dest.name
            with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for name, data in contents.items():
                    info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data, compresslevel=6)
            with zipfile.ZipFile(staged) as archive:
                bad = archive.testzip()
                if bad:
                    raise ValueError(f"ZIP CRC failure: {dest.name}/{bad}")
                if archive.namelist() != list(contents):
                    raise ValueError(f"ZIP entries differ: {dest.name}")
                for name, data in contents.items():
                    if archive.read(name) != data:
                        raise ValueError(f"ZIP contents differ: {dest.name}/{name}")
            staged.replace(dest)
        results.append({
            "job": jid, "filename": dest.name,
            "bytes": dest.stat().st_size, "sha256": sha(dest.read_bytes()),
            "images": bundle["job"]["image_count"], "audio": bundle["job"]["audio_count"],
            "available_audio": bundle["manifest"]["available_audio_reference_files"],
            "pending_required_references": bundle["manifest"]["pending_required_references"],
            "ready_for_generation": bundle["manifest"]["ready_for_generation"],
            "prompt_unicode_characters": bundle["manifest"]["prompt_unicode_characters_including_newlines"],
            "zip_crc_verified": True, "all_entries_byte_verified": True,
            "source_file_sha256": bundle["manifest"]["source_file_sha256"],
        })
    verify_sources(sources)
    for result in results:
        if sha((out / result["filename"]).read_bytes()) != result["sha256"]:
            raise RuntimeError(f"Output changed during packaging: {result['filename']}")
    record = {
        "episode": "EP02", "revision": args.revision, "date": refs["date"],
        "rebuild_command": "python3 tools/build_ep02_bundles.py " + " ".join(f"--job {b['job']['id']}" for b in bundles) + f" --revision {args.revision} --out /tmp/DYS_EP02_{args.revision}",
        "archives_are_derived_from_repository_files": True,
        "reference_source": REFS_FILE,
        "reference_source_sha256": sha(sources[REFS_FILE]),
        "zip_not_direct_seedance_input": True,
        "new_visual_assets_status": "pending_user_review",
        "video_generated": False, "final_dialogue_audio_generated": False,
        "actual_av_review_performed": False,
        "actual_start_end_keyframes_included": False,
        "actual_previous_video_or_tail_frame_included": False,
        "bundles": results,
    }
    if args.record:
        record_path = args.record.resolve()
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_bytes(json_bytes(record))
    print(json.dumps({"output_directory": str(out), **record}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
