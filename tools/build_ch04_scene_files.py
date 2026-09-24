#!/usr/bin/env python3
"""Export one independently usable ZIP per chapter-four scene."""
from pathlib import Path
import argparse, copy, json, shutil, tempfile, zipfile
from build_ch04_ordered import (ROOT, RELEASE, collect, digest, write_text,
    write_json, scene_markdown, render_html, previous_text, validate_archive_tree)


def build(out):
    manifest = collect()
    timeline = json.loads((RELEASE / 'timeline.json').read_text())
    contract = json.loads((RELEASE / 'audio/contract.json').read_text())
    results = []
    out.mkdir(parents=True, exist_ok=True)
    for original in manifest['blocks']:
        block = copy.deepcopy(original)
        prefix = f"{block['ordinal']:02}_{block['id']}/"
        for key in ['prompt_bundle_path', 'previous_video_bundle_readme']:
            assert block[key].startswith(prefix)
            block[key] = block[key][len(prefix):]
        for kind in ['images', 'audio']:
            for row in block[kind]:
                assert row['bundle_path'].startswith(prefix)
                row['bundle_path'] = row['bundle_path'][len(prefix):]
        one = {**manifest, 'blocks': [block], 'duration_seconds': 30}
        with tempfile.TemporaryDirectory(prefix='ch04_scene_') as temp:
            stage = Path(temp)
            prompt = (ROOT / block['prompt_source']).read_text()
            write_text(stage / block['prompt_bundle_path'], prompt)
            for kind in ['images', 'audio']:
                for row in block[kind]:
                    target = stage / row['bundle_path']
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if row['available']:
                        shutil.copyfile(ROOT / row['source_path'], target)
                        assert digest(target.read_bytes()) == row['sha256']
                    else:
                        write_text(target, f"# 待补：{row['label']}\n\n固定编号{row['slot']}，不要前移后面的编号。此MD只是说明，不能上传Seedance。\n")
            write_text(stage / '00_UPLOAD_ORDER.md', scene_markdown(block, prompt,
                stage / '00_UPLOAD_ORDER.md', lambda r: stage / r['bundle_path']))
            write_json(stage / 'INPUT_MANIFEST.json', block)
            actual_block = next(b for b in timeline['blocks'] if b['id'] == block['id'])
            write_json(stage / '02_TIMELINE.json', {'chapter': 4, 'block': actual_block,
                'music_cues': [c for c in contract['cues'] if c['block'] == block['id']]})
            write_text(stage / block['previous_video_bundle_readme'], previous_text(block) + '\n')
            page = render_html(one)
            page = page.replace('六段×30秒。', f"本文件只包含{block['id']}，30秒。")
            page = page.replace('href="START_HERE.md"', 'href="00_UPLOAD_ORDER.md"')
            page = page.replace('href="UPLOAD_ORDER.json"', 'href="INPUT_MANIFEST.json"')
            page = page.replace('href="documentation/DIRECTOR_AND_PRODUCTION_PACK.md"', 'href="02_TIMELINE.json"')
            page = page.replace('导演生产稿</a>', '本场分镜</a>')
            write_text(stage / 'index.html', page)
            if block['id'] in ['H04', 'H05', 'H06']:
                write_text(stage / '03_MUSIC_README.md',
                    f"# {block['id']} 音频使用\n\n音频1：本场真实《卜卦》曲参，最长22秒，尚待补。音频2：孙亚龙4秒音色；音频3：潘慧4秒音色。后两份已有并随包提供。三份总长不得超过30秒。不要把说话样本当作歌声或伴奏。\n\n本场分唱与预排时码见02_TIMELINE.json的music_cues和01_PROMPT.txt。真实音源尚未锁定，需依实际歌句校准，不能声称已逐字对齐。\n\n如果改为一条完整30秒混合导唱，仅上传该导唱，并同步替换Prompt的音频约定；不再附加音色2/3。\n\n" + previous_text(block) + '\n')
            validate_archive_tree(stage, one)
            path = out / f"CH04_{block['id']}.zip"
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                for file in sorted(p for p in stage.rglob('*') if p.is_file()):
                    info = zipfile.ZipInfo(file.relative_to(stage).as_posix(), (2026,9,24,0,0,0))
                    info.external_attr = 0o644 << 16
                    z.writestr(info, file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
            with zipfile.ZipFile(path) as z:
                assert z.testzip() is None
                assert digest(z.read(block['prompt_bundle_path'])) == block['prompt_sha256']
            results.append({'id': block['id'], 'name': block['name'], 'file_name': path.name,
                'local_path': str(path), 'bytes': path.stat().st_size,
                'sha256': digest(path.read_bytes()), 'standalone_links_valid': True,
                'missing_reference_ids': block['missing_slot_ids']})
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    dest = args.out.resolve()
    assert not dest.is_relative_to(ROOT), 'Deliver ZIPs outside the Git repository'
    results = build(dest)
    write_json(dest / 'BUILD_RECEIPT.json', results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
