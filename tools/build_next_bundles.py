#!/usr/bin/env python3
"""Build one reproducible ZIP per EP03–EP05, with a separate upload folder per block."""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

from validate_next_pack import EPISODES, NATIVE_SINGING, ROOT, SINGING, audit, safe_path, sha

GITHUB = "https://github.com/YuxiangLiu-lyx/DYS_history"
ZIP_DATE = (2026, 9, 23, 0, 0, 0)


def jbytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def prepare(episodes=EPISODES) -> tuple[list[dict], dict[str, bytes], dict]:
    validation = audit()
    if not validation["static_validation_pass"]:
        raise ValueError("Static source audit failed:\n" + "\n".join(validation["errors"]))
    sources, bundles = {}, []

    def read(relative: str | Path) -> bytes:
        key = str(relative)
        data = safe_path(key).read_bytes()
        if key in sources and sources[key] != data:
            raise RuntimeError(f"Source changed during packaging: {key}")
        sources[key] = data
        return data

    for episode in episodes:
        prod = Path("episodes") / episode / "production"
        refs = json.loads(read(prod / "refs_upload.json"))
        timeline = json.loads(read(prod / "timeline.json"))
        revision = timeline.get("revision", "v1")
        contents, job_records = {}, []
        for job in refs["jobs"]:
            jid = job["id"]
            block = next(b for b in timeline["blocks"] if b["id"] == jid)
            native = job.get("audio_mode", block.get("audio_mode")) == NATIVE_SINGING
            previous = job["previous_reference"]
            previous_included = bool(previous.get("video_file"))
            previous_missing = bool(previous.get("required") and not previous_included)
            folder = f"{jid}/"
            rows, missing = [], []
            for label, field, subdir, prefix in [("图片", "slots", "images", "img"), ("音频", "audio_slots", "audio", "audio")]:
                for n, ref in enumerate(job[field], 1):
                    relative = ref.get("file")
                    row = dict(ref)
                    row["repository_file"] = relative
                    row.pop("file", None)
                    row["modality"] = "image" if label == "图片" else "audio"
                    if relative is None:
                        if jid not in SINGING or label != "音频" or ref.get("required") is not True:
                            raise ValueError(f"Unexpected missing source: {jid}/{ref['slot']}")
                        row["bundle_file"] = None
                        missing.append(ref["slot"])
                    else:
                        data = read(relative)
                        if sha(data) != ref["sha256"]:
                            raise ValueError(f"Reference SHA mismatch: {jid}/{relative}")
                        name = f"{subdir}/{prefix}{n:02d}_{Path(relative).name}"
                        contents[folder + name] = data
                        row["bundle_file"] = name
                    rows.append(row)
            prompt = read(job["prompt_file"])
            contents[folder + "PROMPT.txt"] = prompt
            if previous_included:
                previous_file = previous["video_file"]
                previous_data = read(previous_file)
                previous_name = f"video/{Path(previous_file).name}"
                contents[folder + previous_name] = previous_data
                rows.append({"slot": previous.get("slot", "@视频1"), "repository_file": previous_file, "bundle_file": previous_name, "modality": "video", "purpose": previous["purpose"], "sha256": sha(previous_data), "preserve_audio": previous.get("preserve_audio", False)})
            local_timeline = {"episode": episode.upper(), "block": block, "shots": [s for s in timeline["shots"] if s["block"] == jid], "dialogues": [d for d in timeline["dialogues"] if d["block"] == jid]}
            contents[folder + "TIMELINE.json"] = jbytes(local_timeline)
            contents[folder + "REFS.json"] = jbytes(job)
            order = [f"# {episode.upper()} {jid} · 30秒上传次序", "", "先解压；只上传本文件夹内的图片、音频，按表核对标签。ZIP不是模型输入。", "", "| 标签 | 包内文件 | 用途 |", "|---|---|---|"]
            for row in rows:
                purpose = row.get("role") or row.get("purpose") or row.get("character_id") or ""
                missing_label = "待补本段真实歌曲参考（最长22秒）；当前无文件" if native else "待补最终演唱导轨；当前无文件"
                order.append(f"| {row['slot']} | {row['bundle_file'] or missing_label} | {purpose} |")
            if previous_missing:
                order.append(f"| {previous.get('slot', '@视频1')} | 待上一段生成合格后补入 | {previous['purpose']} |")
                contents[folder + "MISSING_PREVIOUS_VIDEO.txt"] = (
                    f"先完成{previous['from_block']}，再将其0–30秒完整有声视频作为@视频1。\n"
                    "保留原声轨、末句收音与伴奏。不可把静音尾帧当成声音接续参考。\n"
                    "登记video_file与检查结果后再生成此段；延续从前段结束的下一拍开始，不重复已有歌词。\n"
                ).encode("utf-8")
            previous_note = "包内已包含登记的前段视频；按REFS.json指定用途引用，保持其原声轨。" if previous_included else "本包未包含真实前段视频或尾帧。取得合格素材后按REFS.json的区间提取；跨地点只继承人物、衣物和剧情，不把前场空间套到新场。"
            order += ["", "只复制 PROMPT.txt 正文，完整Prompt字符数（含换行）：" + str(len(prompt.decode("utf-8"))) + "。", "", "前段引用：" + previous["purpose"], "", previous_note, "新生成参考图待人审；起末关键帧目前为构图说明。视频生成前补齐必要Storyboard。"]
            if jid in SINGING:
                if native:
                    message = "本幕改为Seedance原生演唱与伴奏，生成时开启声音，保留经试听验收的生成歌声和背景音乐。\n尚缺@音频1本段实际《卜卦》歌曲参考，最长22秒；@音频2男声音色4秒，@音频3女声音色4秒，总音频不得超过30秒。\n歌曲参考约束旋律、词序、速度及伴奏；两段说话样本只借音色，不复述聊天，也不代表已经完成保真演唱。\n补入合法取得的实际音频，登记路径、SHA-256、原片选段及真实时长，按乐句校正预排秒表。只写歌名无法证明原曲准确。\nR03须引用R02完整有声视频，从末尾下一拍延续；保持调性、速度、人物位置和音色，不重奏前奏或复唱已唱内容。\n结构校验与音频时长检查不等于已经试听原曲、校准口型或验收视频。\n"
                else:
                    message = "本幕尚缺用户最终采用的演唱导轨，不能开始随意哑唱生成。\n先将原声剪成与最终成片一致的30秒，保留真实换气、字头字尾、换唱和笑场，锁定速度；R02/R03必须共同检查衔接。\n将导轨登记至REFS.json的@音频1（文件路径、SHA-256、原片取段与最终时间轴），再依真实波形重定口型窗口。\n本包暂定镜头时间不是孙亚龙、潘慧原片的实测音乐时间。现有两人说话样本不能替代演唱时序。\n若平台不能仅以音频驱动嘴型并关闭人声输出，先以导轨生成同步画面，导出后移除生成声轨，再由用户铺同一最终原声；不可换另一版歌而声称逐字同步。\n"
                if missing:
                    missing_name = "MISSING_SONG_REFERENCE.txt" if native else "MISSING_GUIDE.txt"
                    contents[folder + missing_name] = message.encode("utf-8")
                    order += ["", f"**暂不能生成：缺少@音频1实际歌曲参考。请先读{missing_name}。**"]
                elif native:
                    order += ["", "开启声音，生成并保留人物演唱与伴奏。试听原曲、两人音色与转唱，并逐镜验收口型；不自动移除歌声。"]
                else:
                    order += ["", "演唱导轨只约束口型与表演节奏；最终画面不保留模型歌声，用户后配同一版本原声。实际嘴型仍需逐镜听看验收。"]
            else:
                order += ["", "角色原声只借音色，不复读样本聊天。生成指定的新台词；只让当前可见说话人逐字动嘴，其余角色聆听。"]
            contents[folder + "UPLOAD_ORDER.md"] = ("\n".join(order) + "\n").encode("utf-8")
            manifest = {"episode": episode.upper(), "job": jid, "source_duration_seconds": 30, "prompt_unicode_characters": len(prompt.decode("utf-8")), "prompt_sha256": sha(prompt), "references": rows, "previous_reference": previous, "missing_required_audio_slots": missing, "missing_required_previous_video": previous_missing, "all_reference_files_ready": not missing and not previous_missing, "production_ready": False, "generated_video_included": False, "rendered_start_end_keyframes_included": False, "actual_previous_video_included": previous_included, "actual_source_song_received": bool(jid in SINGING and not missing), "actual_lip_sync_verified": False}
            if native:
                manifest.update({"audio_mode": NATIVE_SINGING, "generate_audio": True, "preserve_generated_singing_and_music": True, "reference_audio_total_limit_seconds": 30})
            contents[folder + "INPUT_MANIFEST.json"] = jbytes(manifest)
            job_records.append(manifest)
        for name in ["VIDEO_PRODUCTION_PACK.md", "QUICKSTART.md"]:
            file = prod / name
            if (ROOT / file).is_file():
                contents[f"documentation/{name}"] = read(file)
        for file in sorted((ROOT / prod / "audio").glob("*")):
            if file.is_file() and file.suffix.lower() in {".json", ".md", ".csv", ".srt"}:
                contents[f"documentation/audio/{file.name}"] = read(file.relative_to(ROOT))
        for file in sorted((ROOT / "episodes" / episode / "script").glob("*.md")):
            relative = file.relative_to(ROOT)
            contents[f"documentation/{file.name}"] = read(relative)
        contents["FICTION_NOTICE.txt"] = ("AI生成／AI辅助制作／架空历史二创。\n人物官职、事件与对白为艺术虚构；不得将生成画面作为真实私人事件的证据或司法结论。\n梦画中的夺冠合影如为AI重建或C位重排，属于梦境道具，不是2018年原始纪实照片。\n").encode("utf-8")
        contents["README.md"] = (f"# {episode.upper()} Seedance 2.5 制作材料包 {revision}\n\n本章{len(job_records)}段，每段30秒。每个子目录各自是一项生成任务，不把整包所有图片同时塞入同一任务。\n\n1. 先审人物、场景与梦画；依剧本补齐必要首末Storyboard。\n2. 解压，进入对应P/Q/R目录，按UPLOAD_ORDER.md上传该段4–7张图片和对应音频。\n3. 选择入口实际支持的30秒、16:9，核对标签，只复制PROMPT.txt。\n4. R02、R03若有MISSING_GUIDE.txt，须先补用户最终演唱导轨并锁音节时间，不能先生成随意口型。\n5. 逐段审查同一张脸、嘴角下痣、发型服装、声音归属、口型、手部、轴线及尾字；合格后提取承接视频片段或尾帧。\n6. 成片中移除演唱段模型歌声，由用户后配同一最终原声；正常对白段保留经核验的同期声。\n\n本包不含真实视频、完整图像Storyboard、实际前段尾帧或最终演唱音轨。结构校验不能保证一次生成无错误。\n\n[权威仓库]({GITHUB}) · [本章生产包]({GITHUB}/blob/main/{prod}/VIDEO_PRODUCTION_PACK.md)\n").encode("utf-8")
        if any(j.get("audio_mode") == NATIVE_SINGING for j in job_records):
            for name in ["timeline.json", "refs_upload.json"]:
                contents[f"documentation/{name}"] = read(prod / name)
            for name in ["manifest.json", "README.md"]:
                contents[f"documentation/voice_refs/{name}"] = read(Path("assets/audio/ep05") / name)
            research = Path("history/research/EP05_NATIVE_SINGING_20260924.md")
            contents[f"documentation/research/{research.name}"] = read(research)
            contents["README.md"] = (
                f"# {episode.upper()} Seedance 2.5 制作材料包 {revision}\n\n"
                f"本章{len(job_records)}段，每段30秒。R01剧情对白；R02男声引曲与缓慢走近；R03有声延续、接唱合唱、对视靠近及深情相吻。\n\n"
                "1. 先审人物、场景和首末Storyboard；每段只上传自己的五张图。\n"
                "2. R02/R03按UPLOAD_ORDER.md绑定@音频1本段真实歌曲参考（最长22秒）、@音频2男声音色4秒、@音频3女声音色4秒。音频总计不得超过30秒。\n"
                "3. 若有MISSING_SONG_REFERENCE.txt，须先补实际曲源，核定所用版本、歌词乐句与节拍；预排秒表并非已测原曲时间。\n"
                "4. 选择30秒、开启声音，只复制对应PROMPT.txt。保留生成并通过试听验收的歌声、伴奏与自然环境声。\n"
                "5. 先验收R02，再把其0–30秒完整有声视频作为R03的@视频1。R03选择延续／向后延长，从前段末尾下一拍继续，不复唱、不重新奏前奏。\n"
                "6. 检查曲调、词序、男女音色、口型、伴奏接缝、空间距离、脸与嘴角下痣；歌声收束后再相互靠近，吻中不继续唱。\n\n"
                "本包歌曲参考与合格前段视频尚待登记，首末关键帧仍为构图说明。时长和结构校验不代表已完成歌曲试听、音色还原、口型或成片验收；不承诺一次生成无错误。\n\n"
                f"[权威仓库]({GITHUB}) · [本章生产包]({GITHUB}/blob/main/{prod}/VIDEO_PRODUCTION_PACK.md)\n"
            ).encode("utf-8")
        contents["BUNDLE_MANIFEST.json"] = jbytes({"episode": episode.upper(), "revision": revision, "jobs": job_records, "static_validation_pass": True, "real_video_generated": False, "source_repository": GITHUB})
        bundles.append({"episode": episode.upper(), "revision": revision, "date": timeline["date"], "contents": contents, "jobs": job_records})
    for relative, data in sources.items():
        if safe_path(relative).read_bytes() != data:
            raise RuntimeError(f"Source changed during packaging; rerun: {relative}")
    return bundles, sources, validation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--episode", choices=EPISODES, help="Rebuild only this episode")
    args = parser.parse_args()
    if not args.check and not args.out:
        parser.error("Supply --check or --out")
    bundles, sources, validation = prepare([args.episode] if args.episode else EPISODES)
    if args.check:
        print(json.dumps({"static_validation_pass": True, "source_files": len(sources), "episodes": [{"id": b["episode"], "jobs": [j["job"] for j in b["jobs"]]} for b in bundles], "production_ready": False}, ensure_ascii=False, indent=2))
        return
    out = args.out.resolve()
    if out.is_relative_to(ROOT):
        raise ValueError("Derived ZIPs must remain outside the Git repository")
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for bundle in bundles:
        revision_tag = bundle["revision"].replace(".", "_")
        dest = out / f"{bundle['episode']}_Seedance25_{revision_tag}.zip"
        contents = bundle["contents"]
        with tempfile.NamedTemporaryFile(dir=out, prefix=dest.name + ".", suffix=".tmp", delete=False) as temp:
            temporary = Path(temp.name)
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for name, data in sorted(contents.items()):
                    info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data)
            with zipfile.ZipFile(temporary) as archive:
                if archive.testzip() is not None or set(archive.namelist()) != set(contents):
                    raise RuntimeError(f"Archive integrity failed: {dest.name}")
                if any(archive.read(name) != data for name, data in contents.items()):
                    raise RuntimeError(f"Archive byte comparison failed: {dest.name}")
            temporary.replace(dest)
        finally:
            temporary.unlink(missing_ok=True)
        records.append({"episode": bundle["episode"], "local_file": str(dest), "filename": dest.name, "bytes": dest.stat().st_size, "sha256": sha(dest.read_bytes()), "entry_count": len(contents), "jobs": [j["job"] for j in bundle["jobs"]], "missing_required_guide_jobs": [j["job"] for j in bundle["jobs"] if j["missing_required_audio_slots"]], "zip_crc_and_exact_entry_bytes_verified": True})
    result = {"date": max(b["date"] for b in bundles), "builder": "tools/build_next_bundles.py", "derived_archives_stored_in_git": False, "generated_video_included": False, "actual_lip_sync_verified": False, "production_ready": False, "source_sha256": {p: sha(d) for p, d in sorted(sources.items())}, "bundles": records, "storage_upload_status": "not_performed_by_builder"}
    if args.record:
        path = args.record if args.record.is_absolute() else ROOT / args.record
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(jbytes(result))
    print(json.dumps({"bundles": records, "production_ready": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
