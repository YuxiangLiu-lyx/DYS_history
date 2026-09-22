#!/usr/bin/env python3
"""Index preserved originals; never edits images or replaces current selections."""
from pathlib import Path
import json, hashlib, struct, html

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / 'assets/current_selection.json'
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    choices = json.loads(SELECTION.read_text())
    current = set(choices['current_paths'])
    records = []
    for path in sorted((ROOT/'assets').rglob('*')):
        if not path.is_file() or path.suffix.lower() not in ('.png','.jpg','.jpeg'):
            continue
        rel = path.relative_to(ROOT).as_posix()
        kind = rel.split('/')[1]
        dimensions = None
        if path.suffix == '.png':
            dimensions = list(struct.unpack('>II', path.read_bytes()[16:24]))
        status = 'candidate_pending_user_review'
        if kind == 'source_photos': status = 'identity_provenance_only_not_video_reference'
        elif rel.endswith('C03_WARDROBE_ONLY_v01.png'): status = 'wardrobe_only_design_reference'
        elif kind == 'characters' and '/C05/' not in rel and '/C03/' not in rel: status = 'accepted_base_design'
        if kind in ('characters','scenes','keyframes') and rel not in current:
            status = 'superseded_not_for_production'
        records.append(dict(id=path.stem,path=rel,kind=kind,current=rel in current,
            status=status,bytes=path.stat().st_size,sha256=digest(path),dimensions=dimensions,
            usable_as_single_character_reference=kind=='characters' and 'ANGLES' not in path.stem and 'WARDROBE_ONLY' not in path.stem and rel in current))
    result = dict(schema_version=1,project='德云史记·慧后本纪',episode='EP01',
        selection_authority='assets/current_selection.json',
        generated_images_are_original_bytes=True,
        new_scene_and_keyframe_approval='pending_user_review',
        blocked_character=None,
        c03_identity_source='assets/source_photos/C03_user_identity_anchor.png',
        pan_identity_authority='assets/characters/C05/C05_FRONT_HALF_v04.png',assets=records)
    (ROOT/'assets/manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    # Portable local review gallery, no external CDN or JavaScript dependency.
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>德云史记 · 资产审阅</title><style>body{margin:0;background:#121513;color:#eee7d4;font:16px/1.6 system-ui}main{max-width:1500px;margin:auto;padding:32px}h1{font-family:serif}a{color:#d8bc7d}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:22px}.card{background:#202720;padding:14px;border-radius:8px}.card img{width:100%;height:310px;object-fit:contain;background:#101210}small{word-break:break-all;color:#c6c1b1}h2{margin-top:42px}</style><main><h1>德云史记 · 第一回资产与关键帧</h1><p>剧本锁定90秒。本轮小腿按用户身份图建立母版；潘慧痣位在嘴角下方皮肤，与唇线留间隔。本轮人物修订、场景及关键帧为候选待审，图片本体均在本包内。<a href="episodes/ep01/production/VIDEO_PRODUCTION_PACK.md">生产包</a> · <a href="episodes/ep01/production/SEEDANCE_QUICKSTART.md">Seedance流程</a> · <a href="AGENTS.md">新AI续作规则</a></p>']
    for kind,title in [('characters','人物当前版本'),('scenes','场景空镜候选'),('keyframes','关键帧候选')]:
        parts.append('<h2>'+title+'</h2><section>')
        for a in records:
            if a['kind'] != kind or not a['current']: continue
            path=html.escape(a['path'],quote=True)
            note='六宫格仅供人审，不上传视频' if 'ANGLES' in a['id'] else a['status']
            parts.append(f'<article class="card"><a href="{path}"><img loading="lazy" src="{path}" alt="{html.escape(a["id"])}"></a><h3>{html.escape(a["id"])}</h3><small>{html.escape(note)}<br>{path}</small></article>')
        parts.append('</section>')
    parts.append('<p>G24以F_OUT_v02为状态参考；真实视频尾帧尚未生成。D_IN、G20_IN/OUT已按小腿同一历史化母版补齐，待静态复核。六宫格与无脸样衣不作视频身份参考。AI生成／架空历史二创。</p></main></html>')
    (ROOT/'REVIEW_GALLERY.html').write_text('\n'.join(parts))
    print(json.dumps({'indexed_images':len(records),'current_images':sum(a['current'] for a in records)},ensure_ascii=False))
if __name__=='__main__':main()
