#!/usr/bin/env python3
"""Build the ordered chapter-four Seedance handoff from canonical inputs.

This is a packaging tool: it never edits plot, canonical prompts, assets or status.
Media bytes are copied unchanged. Missing slots are Markdown notices, never media.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import wave
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'releases/huibenji/chapter04_v1'
ZIP_NAME = 'CH04_Dream_Duet_Production_Pack_v1.zip'
LABELS = {
    'C01': '孙亚龙·便装', 'C05': '潘慧·身份母版', 'C03': '小腿·便装',
    'E06': '侍女', 'S06': '卧房·空间参考', 'S14': '客栈·空间参考（上午需改光）',
    'S15_NEW': '申时松下·石台折布新场景', 'P_RUAN': '小阮·道具',
    'KF_H04_START': 'H04起始关键帧', 'KF_H05_START': 'H05起始关键帧',
    'KF_H06_START': 'H06起始关键帧', 'D01': '梦一·密集弹幕图',
    'D02': '梦二·求婚图', 'D03': '梦三·打码聊天图',
    'VOICE_C01': '孙亚龙·10秒对白音色', 'VOICE_C05': '潘慧·10秒对白音色',
    'VOICE_C03': '小腿·10秒对白音色', 'TIMBRE_C01_4S': '孙亚龙·4秒演唱音色参考',
    'TIMBRE_C05_4S': '潘慧·4秒演唱音色参考',
    'SONG_A_PENDING_MAX22S': '曲参A·本段真实歌曲（待补，最多22秒）',
    'SONG_B_PENDING_MAX22S': '曲参B·本段真实歌曲（待补，最多22秒）',
    'SONG_C_PENDING_MAX22S': '曲参C·本段真实歌曲（待补，最多22秒）',
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_text(path: Path, value: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')


def write_json(path: Path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def rel(source: Path, destination: Path) -> str:
    return Path(os.path.relpath(destination, source.parent)).as_posix()


def collect():
    timeline = read_json(RELEASE / 'timeline.json')
    assets = read_json(RELEASE / 'assets.json')
    audio_map = read_json(RELEASE / 'audio/UPLOAD_MAP.json')
    refs = assets['refs']
    blocks = timeline['blocks']
    prior_path = ROOT / 'archive/chapter04_v1_before_order_fix/timeline.json'
    assert prior_path.is_file(), 'Historical chapter-four baseline missing'
    prior = read_json(prior_path)
    assert blocks[1:] == prior['blocks'][1:], 'H02-H06 plot or prompt changed outside ordered-input correction'
    allowed_h01 = {'prompt', 'image_reference_ids', 'dream_image_slots', 'dream_image_strategy'}
    clean_h01 = lambda b: {k: v for k, v in b.items() if k not in allowed_h01}
    assert clean_h01(blocks[0]) == clean_h01(prior['blocks'][0]), 'H01 story changed outside dream-reference correction'
    assert [b['id'] for b in blocks] == [f'H{i:02}' for i in range(1, 7)]
    assert blocks[0]['image_reference_ids'] == ['C05', 'E06', 'S06', 'D01', 'D02', 'D03'], 'H01 canonical dream slots must be fixed before building'
    assert assets['dreams']['order'] == ['D01', 'D02', 'D03']
    results = []
    for ordinal, block in enumerate(blocks, 1):
        prompt_file = RELEASE / 'prompts' / (block['id'] + '.txt')
        prompt_bytes = prompt_file.read_bytes()
        prompt_file_text = prompt_bytes.decode('utf-8')
        assert prompt_file_text.rstrip('\n') == block['prompt'].rstrip('\n'), f'{block["id"]} prompt/timeline disagree'
        assert len(prompt_file_text) <= 2000, f'{block["id"]} prompt too long'
        assert block['duration'] == 30 and block['global_start'] == (ordinal - 1) * 30
        cursor = 0
        for shot in block['shots']:
            assert shot['start'] == cursor
            cursor = shot['end']
        assert cursor == 30
        folder = f'{ordinal:02}_{block["id"]}'
        result = {
            'id': block['id'], 'name': block['name'], 'ordinal': ordinal,
            'duration_seconds': 30, 'film_start_seconds': block['global_start'],
            'production_ready': False,
            'prompt_source': prompt_file.relative_to(ROOT).as_posix(),
            'prompt_sha256': digest(prompt_bytes), 'prompt_characters_including_newline': len(prompt_file_text),
            'prompt_bundle_path': folder + '/01_PROMPT.txt',
            'images': [], 'audio': [], 'previous_video': block['previous_reference'],
            'previous_video_bundle_readme': folder + '/04_previous_video/README.md',
            'first_frame_description': block['first_frame_description'],
            'last_frame_description': block['last_frame_description'],
        }
        for kind, ids, subdir in [('images', block['image_reference_ids'], '02_images'), ('audio', audio_map[block['id']], '03_audio')]:
            for slot, refid in enumerate(ids, 1):
                source_path = refs.get(refid)
                available = source_path is not None and (ROOT / source_path).is_file()
                if source_path is not None:
                    assert available, f'Mapped source does not exist: {source_path}'
                suffix = Path(source_path).suffix if available else '.md'
                filename = f'{slot:02}_{refid}' + (suffix if available else '_MISSING.md')
                row = {
                    'slot': slot, 'ref_id': refid, 'label': LABELS.get(refid, refid),
                    'available': available, 'source_path': source_path,
                    'sha256': digest((ROOT / source_path).read_bytes()) if available else None,
                    'size_bytes': (ROOT / source_path).stat().st_size if available else None,
                    'bundle_path': f'{folder}/{subdir}/{filename}',
                    'upload_this_file': available,
                }
                if kind == 'audio':
                    duration = None
                    if available and suffix.lower() == '.wav':
                        with wave.open(str(ROOT / source_path), 'rb') as wav:
                            duration = wav.getnframes() / wav.getframerate()
                    row['duration_seconds'] = duration
                    row['maximum_planned_seconds'] = 22 if refid.startswith('SONG_') else duration
                result[kind].append(row)
        known_audio = sum(x['duration_seconds'] or 0 for x in result['audio'])
        planned_audio = sum(x['maximum_planned_seconds'] or 0 for x in result['audio'])
        assert known_audio <= 30.001 and planned_audio <= 30.001
        result['known_audio_seconds'] = known_audio
        result['planned_maximum_audio_seconds'] = planned_audio
        result['missing_slot_ids'] = [x['ref_id'] for k in ('images', 'audio') for x in result[k] if not x['available']]
        result['other_required_checks'] = {
            'H01': '寝衣、松散睡发和卧床/惊醒关键帧仍需核定；现有母版只锁脸。',
            'H02': 'H01实际末4秒未生成；客栈上午光新关键帧仍需核定。',
            'H03': 'H02实际末4秒未生成；松下石台和小阮新图未生成。',
            'H04': 'H03实际末4秒未生成；真实曲源、歌声时码及新关键帧未完成。',
            'H05': 'H04实际有声30秒未生成；真实曲源、歌声时码及新关键帧未完成。',
            'H06': 'H05实际有声30秒未生成；真实曲源、歌声时码及新关键帧未完成。',
        }[block['id']]
        results.append(result)
    sources = {p: digest((ROOT / p).read_bytes()) for p in [
        'releases/huibenji/chapter04_v1/timeline.json',
        'releases/huibenji/chapter04_v1/assets.json',
        'releases/huibenji/chapter04_v1/audio/UPLOAD_MAP.json',
        *[b['prompt_source'] for b in results],
    ]}
    return {
        'schema': 'ch04_ordered_inputs_v1', 'chapter': 4,
        'title': timeline['title'], 'duration_seconds': 180,
        'production_ready': False,
        'plot_validation': {'baseline': prior_path.relative_to(ROOT).as_posix(), 'baseline_sha256': digest(prior_path.read_bytes()), 'H02_H06_unchanged': True, 'H01_story_unchanged': True, 'allowed_H01_changes': sorted(allowed_h01)},
        'note': '现有素材已按槽位整理；缺项用Markdown说明保留编号，不能上传说明文件，也不能把后续素材向前补位。',
        'dream_order': ['D01', 'D02', 'D03'], 'dream_slots_in_H01': [4, 5, 6],
        'dream_windows_seconds': [[4, 7], [9, 12], [15, 18]],
        'source_checksums': sources, 'blocks': results,
    }


def previous_text(block):
    previous = block['previous_video']
    if not previous.get('source'):
        return '本回开场，不上传上一回视频。'
    interval = previous.get('range')
    interval_text = f'第{interval[0]}–{interval[1]}秒' if interval else '末帧'
    return f'视频1：{previous["source"]}的{interval_text}。{previous["instruction"]} 当前真实视频未生成；没有可上传的MP4，不能用占位文件代替。'


def scene_markdown(block, prompt, path, asset_target):
    lines = [f'# {block["id"]} · {block["name"]}', '',
             f'成片第{block["film_start_seconds"]}–{block["film_start_seconds"] + 30}秒；本次生成30秒。', '',
             '**操作顺序：先复制本场Prompt，再按下列图片号上传图片，再按音频号上传音频，最后按说明加入视频参考。**', '',
             '缺项必须保留槽位；不能上传 `.md` 缺项说明，也不能让后面的文件自动前移。当前不是素材齐备状态。', '',
             f'## 1. Prompt（含TXT末尾换行{block["prompt_characters_including_newline"]}字符）', '',
             '```text', prompt.rstrip('\n'), '```', '', '## 2. 图片上传顺序', '']
    for row in block['images']:
        lines += [f'### 图片{row["slot"]} · {row["label"]}', '']
        if row['available']:
            target = asset_target(row)
            lines += [f'![图片{row["slot"]} {row["label"]}]({rel(path, target)})', '',
                      f'[图片{row["slot"]}原文件]({rel(path, target)}) · `{row["ref_id"]}`', '']
        else:
            lines += [f'**待补：图片{row["slot"]}（{row["ref_id"]}）。编号保留，当前没有图片文件。**', '']
    lines += ['## 3. 音频上传顺序', '', '| 槽位 | 内容 | 文件/状态 |', '|---|---|---|']
    for row in block['audio']:
        link = f'[{row["duration_seconds"]:g}秒原文件]({rel(path, asset_target(row))})' if row['available'] else '**待补；后续音频不可前移**'
        lines.append(f'| 音频{row["slot"]} | {row["label"]} | {link} |')
    lines += ['', f'现有音频合计{block["known_audio_seconds"]:g}秒；本路线补齐后最多{block["planned_maximum_audio_seconds"]:g}秒。', '',
              '音色样本仅提供声线，不能当作最终歌曲。音乐段音频1仍待实际曲源；如果改用一条完整30秒导唱，必须同步替换Prompt音频约定，不能再叠加音频2、3。', '',
              '## 4. 上一场视频与首尾状态', '', previous_text(block), '',
              f'- 起始：{block["first_frame_description"]}',
              f'- 结束：{block["last_frame_description"]}', '',
              f'**仍需完成：**{block["other_required_checks"]}', '']
    return '\n'.join(lines)


def render_docs(manifest):
    path = RELEASE / 'ORDERED_INPUTS.md'
    parts = ['# 第四回逐场投料册', '', '六场按H01→H06生产。每场完整Prompt之后紧跟图片、音频、上一场视频，编号与Prompt一一对应。', '',
             '**梦图顺序：密集弹幕→求婚→打码聊天；H01中分别为图片4、5、6，在4–7、9–12、15–18秒出现。**', '',
             '图片和声音均为现有原文件；待补槽位显式标记。歌曲、新场景及关键帧未齐，当前不宣称可直接生成全部成片。', '']
    for block in manifest['blocks']:
        prompt = (ROOT / block['prompt_source']).read_text(encoding='utf-8')
        parts += [scene_markdown(block, prompt, path, lambda r: ROOT / r['source_path']), '\n---\n']
        scene = RELEASE / 'scenes' / block['id']
        write_text(scene / 'README.md', scene_markdown(block, prompt, scene / 'README.md', lambda r: ROOT / r['source_path']))
        write_text(scene / 'PROMPT.txt', prompt)
        write_json(scene / 'INPUT_MANIFEST.json', block)
    write_text(path, '\n'.join(parts))
    write_json(RELEASE / 'UPLOAD_ORDER.json', manifest)


def missing_notice(row):
    media = '音频' if '/03_audio/' in row['bundle_path'] else '图片'
    return (f'# 待补{media}{row["slot"]}：{row["label"]}\n\n'
            f'固定槽位：{row["slot"]}；资产ID：{row["ref_id"]}。\n\n'
            '此文件是缺项说明，不是媒体，不可上传Seedance。补齐该槽位后再按原编号上传，禁止把后续素材向前补位。\n')


def render_html(manifest):
    sections = []
    esc = html.escape
    for block in manifest['blocks']:
        prompt = (ROOT / block['prompt_source']).read_text(encoding='utf-8')
        pictures = []
        for row in block['images']:
            title = f'图片{row["slot"]} · {row["label"]}'
            if row['available']:
                body = f'<a href="{esc(row["bundle_path"], quote=True)}"><img src="{esc(row["bundle_path"], quote=True)}" alt="{esc(title)}" loading="lazy"></a>'
            else:
                body = '<div class="missing-image">待补 · 编号保留<br>不要上传说明文件</div>'
            pictures.append(f'<figure class="{"missing" if not row["available"] else ""}">{body}<figcaption>{esc(title)}<br><small>{esc(row["ref_id"])}</small></figcaption></figure>')
        sounds = []
        for row in block['audio']:
            title = f'音频{row["slot"]} · {row["label"]}'
            if row['available']:
                body = f'<audio controls preload="none" src="{esc(row["bundle_path"], quote=True)}"></audio><a href="{esc(row["bundle_path"], quote=True)}" download>下载原文件（{row["duration_seconds"]:g}秒）</a>'
            else:
                body = '<p class="warning">待补真实曲源；后面音频2、3不能前移为1、2。</p>'
            sounds.append(f'<div class="sound {"missing" if not row["available"] else ""}"><strong>{esc(title)}</strong>{body}</div>')
        sections.append(f'''<section id="{block['id']}"><h2>{block['id']} · {esc(block['name'])}</h2><p>成片 {block['film_start_seconds']}–{block['film_start_seconds'] + 30} 秒 · 本段30秒</p>
<h3>1. Prompt</h3><button type="button" data-copy="prompt-{block['id']}">复制Prompt</button><span class="copy-result" aria-live="polite"></span><p>{block['prompt_characters_including_newline']}字符（含TXT末尾换行） · <a href="{block['prompt_bundle_path']}">打开TXT</a></p><textarea id="prompt-{block['id']}" readonly spellcheck="false">{esc(prompt)}</textarea>
<h3>2. 图片：从左到右，换行后继续</h3><div class="images">{''.join(pictures)}</div>
<h3>3. 音频：按号码上传</h3><div class="audio-list">{''.join(sounds)}</div><p>现有音频合计{block['known_audio_seconds']:g}秒，补齐后本路线最多{block['planned_maximum_audio_seconds']:g}秒。音色样本不是唱词或原版伴奏。</p>
<h3>4. 视频参考和衔接</h3><p>{esc(previous_text(block))}</p><p>起始：{esc(block['first_frame_description'])}<br>结束：{esc(block['last_frame_description'])}</p><p class="warning">仍需完成：{esc(block['other_required_checks'])}</p></section>''')
    navigation = ' '.join(f'<a href="#{b["id"]}">{b["id"]}</a>' for b in manifest['blocks'])
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>第四回逐场制作包</title><style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#f3f1ed;color:#222;font:16px/1.65 system-ui,sans-serif}}main{{max-width:1280px;margin:auto;padding:24px}}h1{{font-size:28px;line-height:1.35}}h2{{font-size:24px}}h3{{font-size:18px;margin-top:24px}}nav{{display:flex;gap:10px;flex-wrap:wrap;position:sticky;top:0;background:#f3f1edf5;padding:12px 0;z-index:2}}nav a,button{{border:1px solid #8a7662;background:white;padding:7px 16px;border-radius:6px;color:#483928}}a{{color:#714612}}section{{padding:24px;background:white;border-radius:12px;margin:20px 0;scroll-margin-top:70px}}textarea{{width:100%;min-height:240px;padding:14px;font:15px/1.7 ui-monospace,monospace;border:1px solid #c9c3b9;border-radius:6px;background:#fcfbf8;resize:vertical}}.images{{display:flex;gap:12px;flex-wrap:wrap;align-items:stretch}}figure{{margin:0;flex:0 0 185px;max-width:100%;border:1px solid #d5d0c8;border-radius:8px;padding:8px;background:#faf9f6}}figure img{{display:block;width:100%;height:185px;object-fit:contain;background:#171717}}figcaption{{font-size:14px;padding-top:8px}}.missing{{background:#fff2dc;border-color:#d38917}}.missing-image{{height:185px;display:flex;align-items:center;justify-content:center;text-align:center;color:#875007}}.warning{{border-left:4px solid #d58b16;background:#fff2dc;padding:10px 14px;color:#714100}}.audio-list{{display:flex;gap:12px;flex-wrap:wrap}}.sound{{border:1px solid #cfc8bd;border-radius:8px;padding:12px;flex:1 1 280px}}audio{{width:100%;display:block;margin:10px 0}}small{{color:#675e53}}.copy-result{{margin-left:10px;color:#386541}}button{{cursor:pointer}}@media(max-width:600px){{main{{padding:12px}}section{{padding:15px}}figure{{flex-basis:calc(50% - 6px)}}figure img,.missing-image{{height:160px}}}}
</style></head><body><main><h1>德云史记 · 慧后本纪<br>第四回《{esc(manifest['title'])}》</h1><p>六段×30秒。按每场 Prompt → 图片 → 音频 → 前片参考的顺序使用。</p><p class="warning">梦境固定顺序：密集弹幕 → 求婚 → 打码聊天。H01图片4、5、6分别出现3秒。橙色项尚未制作，不是可上传媒体；不要让现有文件自动补到缺失号码。当前关键帧与实际曲源未齐，不是已拍视频。</p><nav>{navigation}</nav>{''.join(sections)}<p><a href="START_HERE.md">制作入口</a> · <a href="UPLOAD_ORDER.json">完整槽位与原文件SHA-256</a> · <a href="documentation/DIRECTOR_AND_PRODUCTION_PACK.md">导演生产稿</a></p></main><script>
document.querySelectorAll('[data-copy]').forEach(function(b){{b.addEventListener('click',async function(){{const t=document.getElementById(b.dataset.copy),s=b.nextElementSibling;try{{if(navigator.clipboard&&window.isSecureContext){{await navigator.clipboard.writeText(t.value)}}else{{t.focus();t.select();if(!document.execCommand('copy'))throw new Error('copy')}}s.textContent='已复制'}}catch(e){{t.focus();t.select();s.textContent='已选中，请按 Ctrl/Cmd+C'}}}})}});
</script></body></html>'''


MARKDOWN_LINK = re.compile(r'(!?\[[^\]\n]*\]\()([^\s)]+)(\))')


def rewrite_links(text, original, destination, lookup, stage):
    def replace(match):
        target = match.group(2)
        if re.match(r'^[a-zA-Z][a-zA-Z+.-]*:', target) or target.startswith('#'):
            return match.group(0)
        base, separator, fragment = target.partition('#')
        resolved = (original.parent / base).resolve()
        if resolved in lookup:
            new_target = rel(destination, stage / lookup[resolved])
            return match.group(1) + new_target + (separator + fragment if separator else '') + match.group(3)
        if resolved.exists():
            raise AssertionError(f'Unpackaged local Markdown target: {original}: {target}')
        return match.group(0)
    return MARKDOWN_LINK.sub(replace, text)


def build_zip(manifest, out):
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ch04_ordered_') as tmp:
        stage = Path(tmp)
        source_lookup = {}
        for block in manifest['blocks']:
            folder = stage / f'{block["ordinal"]:02}_{block["id"]}'
            prompt = (ROOT / block['prompt_source']).read_text(encoding='utf-8')
            write_text(stage / block['prompt_bundle_path'], prompt)
            for kind in ('images', 'audio'):
                for row in block[kind]:
                    destination = stage / row['bundle_path']
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if row['available']:
                        source = ROOT / row['source_path']
                        shutil.copyfile(source, destination)
                        assert digest(destination.read_bytes()) == row['sha256']
                        source_lookup.setdefault(source.resolve(), row['bundle_path'])
                    else:
                        write_text(destination, missing_notice(row))
            write_json(folder / 'INPUT_MANIFEST.json', block)
            write_text(stage / block['previous_video_bundle_readme'], '# 上一场视频\n\n' + previous_text(block) + '\n')
            write_text(folder / '00_UPLOAD_ORDER.md', scene_markdown(block, prompt, folder / '00_UPLOAD_ORDER.md', lambda r: stage / r['bundle_path']))
        document_files = sorted(p for p in RELEASE.rglob('*') if p.is_file())
        for source in document_files:
            source_lookup[source.resolve()] = 'documentation/' + source.relative_to(RELEASE).as_posix()
        for source in document_files:
            destination = stage / source_lookup[source.resolve()]
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix.lower() == '.md':
                write_text(destination, rewrite_links(source.read_text(encoding='utf-8'), source, destination, source_lookup, stage))
            else:
                shutil.copyfile(source, destination)
        write_json(stage / 'UPLOAD_ORDER.json', manifest)
        write_text(stage / 'index.html', render_html(manifest))
        scene_links = '\n'.join(f'{b["ordinal"]}. [{b["id"]} {b["name"]}]({b["ordinal"]:02}_{b["id"]}/00_UPLOAD_ORDER.md)' for b in manifest['blocks'])
        write_text(stage / 'START_HERE.md', '# 第四回按顺序制作包\n\n解压后打开[index.html](index.html)：每场Prompt、图片、音频、前片引用已顺序排好，可离线查看和试听。\n\n' + scene_links + '\n\n梦图：密集弹幕→求婚→打码聊天，分别是H01图片4、5、6。\n\n橙色缺项和_MISSING.md仅说明未制作，不能上传。原编号保留，现有素材不能向前补位。H04–H06音频1歌曲待补，音频2/3只借真人声线。\n\n[完整导演稿](documentation/DIRECTOR_AND_PRODUCTION_PACK.md) · [槽位和原文件SHA](UPLOAD_ORDER.json)。documentation是本次仓库制作文件快照；实际媒体已放在各场编号目录，不再复制第二份。JSON中的source_path仍记录原仓库位置，解压后应使用bundle_path。\n\n当前未完成真实音乐、必需新关键帧、前段实际视频和音画验收。未生成任何占位图或假音频。\n')
        validate_archive_tree(stage, manifest)
        output = out / ZIP_NAME
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(p for p in stage.rglob('*') if p.is_file()):
                info = zipfile.ZipInfo(path.relative_to(stage).as_posix(), date_time=(2026, 9, 24, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
        return {'path': str(output), 'bytes': output.stat().st_size, 'sha256': digest(output.read_bytes()), 'under_50_mib': output.stat().st_size <= 50 * 1024 * 1024}


def validate_archive_tree(stage, manifest):
    for block in manifest['blocks']:
        for kind in ('images', 'audio'):
            rows = block[kind]
            assert [r['slot'] for r in rows] == list(range(1, len(rows) + 1))
            for row in rows:
                path = stage / row['bundle_path']
                assert path.is_file()
                if row['available']:
                    assert digest(path.read_bytes()) == row['sha256']
                else:
                    assert path.suffix == '.md' and not row['upload_this_file']
    for document in stage.rglob('*.md'):
        for match in MARKDOWN_LINK.finditer(document.read_text(encoding='utf-8')):
            target = match.group(2)
            if re.match(r'^[a-zA-Z][a-zA-Z+.-]*:', target) or target.startswith('#'):
                continue
            assert (document.parent / target.partition('#')[0]).resolve().exists(), f'Broken Markdown link in {document}: {target}'
    html_doc = (stage / 'index.html').read_text(encoding='utf-8')
    for target in re.findall(r'(?:href|src)="([^"]+)"', html_doc):
        if target.startswith('#') or re.match(r'^[a-zA-Z][a-zA-Z+.-]*:', target):
            continue
        assert (stage / html.unescape(target)).exists(), f'Broken HTML link: {target}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='Directory for deliverable ZIP (outside repository).')
    parser.add_argument('--docs-only', action='store_true', help='Only refresh tracked ordered Markdown and manifests; no ZIP.')
    args = parser.parse_args()
    if not args.docs_only:
        try:
            args.out.resolve().relative_to(ROOT)
        except ValueError:
            pass
        else:
            parser.error('--out must be outside the Git repository')
    manifest = collect()
    frozen = dict(manifest['source_checksums'])
    render_docs(manifest)
    result = {'docs': str(RELEASE / 'ORDERED_INPUTS.md'), 'production_ready': False}
    if not args.docs_only:
        result['zip'] = build_zip(manifest, args.out.resolve())
    for source, checksum in frozen.items():
        assert digest((ROOT / source).read_bytes()) == checksum, 'Builder modified a canonical plot or input file'
    result['canonical_inputs_unchanged'] = True
    result['prompt_lengths'] = {b['id']: b['prompt_characters_including_newline'] for b in manifest['blocks']}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
