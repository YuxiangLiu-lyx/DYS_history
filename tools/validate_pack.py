#!/usr/bin/env python3
"""Read-only integrity check. Expected production blockers are reported separately."""
from pathlib import Path
import json,hashlib,re,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def read(path):return json.loads((ROOT/path).read_text())
lock=read('episodes/ep01/script/LOCK.json')
if hashlib.sha256((ROOT/lock['path']).read_bytes()).hexdigest()!=lock['sha256']:errors.append('Locked script changed')
t=read('episodes/ep01/production/timeline.json')
if len(t['blocks'])!=7 or sum(x['duration'] for x in t['blocks'])!=90:errors.append('Block duration/count changed')
if any(not 8<=x['duration']<=15 for x in t['blocks']):errors.append('Block outside 8–15 seconds')
if len(t['shots'])!=25 or sum(x['end_frame_exclusive']-x['start_frame'] for x in t['shots'])!=2160:errors.append('Shot/frame total mismatch')
for a,b in zip(t['shots'],t['shots'][1:]):
    if a['end']!=b['start']:errors.append('Shot gap/overlap')
pack=(ROOT/'episodes/ep01/production/VIDEO_PRODUCTION_PACK.md').read_text()
for d in t['dialogue']:
    if d['text'] not in pack:errors.append('Missing locked line: '+d['id'])
for a in read('assets/manifest.json')['assets']:
    path=ROOT/a['path']
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=a['sha256']:errors.append('Asset missing/changed: '+a['path'])
for path in read('assets/current_selection.json')['current_paths']:
    if not (ROOT/path).exists():errors.append('Selected current asset missing: '+path)
uploads=read('episodes/ep01/production/refs_upload.json')
jobs=uploads.get('jobs',uploads.get('tasks',[]))
if isinstance(jobs,dict):jobs=[dict(id=k,**v) for k,v in jobs.items()]
missing=[]
for job in jobs:
    prompt_path=job.get('prompt_file')
    if not prompt_path or not (ROOT/prompt_path).is_file():
        errors.append('Prompt missing: '+str(job.get('id')))
    elif (ROOT/prompt_path).read_text().strip() not in pack:
        errors.append('Prompt differs from production pack: '+str(job.get('id')))
    refs=job.get('images',job.get('slots',job.get('references',[])))
    if len(refs)>9:errors.append('Too many image slots: '+str(job.get('id')))
    for ref in refs:
        path=ref.get('path',ref.get('file',ref.get('file_path','')))
        if path and not ref.get('optional',False) and not (ROOT/path).exists():missing.append({'job':job.get('id'),'path':path})
        if 'ANGLES_EXPRESSIONS' in path or 'WARDROBE_ONLY' in path:errors.append('Invalid face reference: '+path)
for m in missing:
    errors.append('Required reference missing: '+m['path'])
status=read('context/STATUS.json')
result={'integrity_pass':not errors,'errors':errors,'missing_required_references':missing,
        'production_release_gates':[x['id'] for x in status.get('blockers',[])],
        'video_generated':status.get('video_generated',False),'github_synced':status.get('github',{}).get('synced',False)}
print(json.dumps(result,ensure_ascii=False,indent=2))
sys.exit(bool(errors))
