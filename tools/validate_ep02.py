#!/usr/bin/env python3
"""Validate EP02's production data; never substitutes for viewing real takes.

Run: python3 tools/validate_ep02.py
Optional --report writes a JSON report, --root checks another checkout.
The EP01 validator and production files are intentionally untouched.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
VOICE_FILES = {
    'C01': '01_sun_yalong.mp3', 'C02': '04_xika.mp3',
    'C03': '03_xiaotui.mp3', 'C04': '05_weixiao.mp3',
    'C05': '02_pan_hui.mp3',
}
DISPLAY_NAMES = {'C01':'笑皇','C02':'西卡','C03':'小腿','C05':'潘慧','E09':'买米老人','E10':'茶客','E11':'客席一人'}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def srt_time(value: str) -> float:
    h,m,s,ms = (int(x) for x in re.split('[:,]',value))
    return h*3600+m*60+s+ms/1000

def validate(root: Path) -> dict:
    errors, warnings = [], []
    def check(condition, message):
        if not condition:
            errors.append(message)
    def close(a,b):
        return abs(float(a)-float(b)) < 1e-7
    def read(rel):
        return json.loads((root/rel).read_text(encoding='utf-8'))
    base='episodes/ep02/production/'
    timeline=read(base+'timeline.json')
    refs=read(base+'refs_upload.json')
    contract=read(base+'audio/dialogue_contract.json')
    script=(root/'episodes/ep02/script/EP02_DIRECTOR_v1.md').read_text(encoding='utf-8')
    pack=(root/base/'VIDEO_PRODUCTION_PACK.md').read_text(encoding='utf-8')
    expected_blocks=['N01','N02','N03','N04','N05']
    blocks=timeline['blocks']; shots=timeline['shots']; dialogue=timeline['dialogues']
    jobs=refs['jobs']; prompts={}; char_counts={}; bytes_counts={}; rates={}; checked_assets={}
    check([b['id'] for b in blocks]==expected_blocks,'Expected five ordered 30-second blocks N01–N05')
    check([j['id'] for j in jobs]==expected_blocks,'Reference jobs must follow N01–N05')
    check(timeline['duration_seconds']==150 and timeline['fps']==24 and timeline['total_frames']==3600,'150 sec / 24 fps / 3600 frame contract mismatch')
    check(len(shots)==29==timeline['shot_count'],'Expected 29 shots')
    check(len(dialogue)==21==timeline['dialogue_count'],'Expected 21 dialogue cues')
    check([s['id'] for s in shots]==[f'{n:02d}' for n in range(1,30)],'Shot IDs are not unique and consecutive')
    check([d['id'] for d in dialogue]==[f'E2_D{n:02d}' for n in range(1,22)],'Dialogue IDs are not unique and consecutive')
    check(contract['dialogues']==dialogue,'Audio contract differs from timeline dialogue text, timing, or speaker')
    check(timeline['actual_video_generated'] is False and timeline['actual_av_review_performed'] is False,'Do not claim generated or reviewed video in draft pack')
    check(contract['new_final_dialogue_audio_generated'] is False and contract['actual_av_review_performed'] is False,'Reference samples are not generated dramatic dialogue or completed AV review')

    for i,(block,job) in enumerate(zip(blocks,jobs)):
        bid=block['id']; off=i*30
        check((block['start'],block['end'],block['duration'])==(off,off+30,30),f'{bid}: global block range')
        check((block['source_start'],block['source_end'],block['source_to_global_offset_s'])==(0,30,off),f'{bid}: source mapping')
        check(job['source_keep_s']==[0,30] and job['source_duration_s']==30 and job['target_timeline_s']==[off,off+30],f'{bid}: upload source mapping')
        check(contract['source_mapping'][bid]=={'source_seconds':[0,30],'timeline_seconds':[off,off+30],'offset':off},f'{bid}: audio source mapping')
        check(job['previous_reference']==block['previous_reference'],f'{bid}: previous-reference descriptions disagree')
        prev=block['previous_reference']
        check(prev['video_file'] is None and prev['tail_frame_file'] is None,f'{bid}: unexplained actual previous video/tail-frame file')
        if prev['source_segment_s']:
            a,b=prev['source_segment_s']; check(0<=a<b<=30,f'{bid}: previous segment outside source')
        for key in ('start_keyframe','end_keyframe'):
            check(block[key]['file'] is None and block[key]['status']=='planned_description_not_rendered',f'{bid}: storyboard completion status inconsistent')
        ss=[s for s in shots if s['block']==bid]
        cursor=0
        for s in ss:
            check(close(s['source_start'],cursor),f'{bid}/{s["id"]}: source gap/overlap')
            check(s['source_end']>s['source_start'],f'{bid}/{s["id"]}: non-positive duration')
            check(close(s['duration'],s['source_end']-s['source_start']),f'{bid}/{s["id"]}: shot duration')
            check(close(s['start'],s['source_start']+off) and close(s['end'],s['source_end']+off),f'{bid}/{s["id"]}: global/source offset')
            check(s['start_frame']==round(s['start']*24) and s['end_frame_exclusive']==round(s['end']*24),f'{bid}/{s["id"]}: frame range')
            check(s['action'] in script and s['camera'] in script,f'{bid}/{s["id"]}: director script action/camera differs')
            cursor=s['source_end']
        check(close(cursor,30),f'{bid}: shot coverage is not exactly 30 sec')
        prompt_path=root/job['prompt_file']; prompt=prompt_path.read_text(encoding='utf-8')
        prompts[bid]=prompt; char_counts[bid]=len(prompt); bytes_counts[bid]=len(prompt_path.read_bytes())
        check(0<len(prompt)<=2000,f'{bid}: complete Prompt exceeds 2000 Python-len characters')
        check(job['prompt_unicode_characters']==len(prompt),f'{bid}: recorded Prompt character count stale')
        check(prompt in pack,f'{bid}: pack embedded Prompt differs from standalone file')
        pshots=re.findall(r'^(\d+(?:\.\d+)?)–(\d+(?:\.\d+)?)秒[：:]',prompt,re.M)
        check([(float(a),float(b)) for a,b in pshots]==[(float(s['source_start']),float(s['source_end'])) for s in ss],f'{bid}: Prompt shot intervals differ')
        image_slots=job['slots']; audio_slots=job['audio_slots']; allslots=image_slots+audio_slots
        check(len(image_slots)==job['image_count']==refs['practical_image_counts'][bid],f'{bid}: image count disagreement')
        check(len(audio_slots)==job['audio_count']==refs['practical_audio_counts'][bid],f'{bid}: audio count disagreement')
        check(len(image_slots)<=30 and len(audio_slots)<=10 and len(allslots)<=50,f'{bid}: reference capacity exceeded')
        expected_labels={s['slot'] for s in allslots}
        used_labels=set(re.findall(r'@(?:图片|音频|视频)\d+',prompt))
        check(used_labels==expected_labels,f'{bid}: unbound or unused Prompt labels: {used_labels ^ expected_labels}')
        check([s['slot'] for s in image_slots]==[f'@图片{n}' for n in range(1,len(image_slots)+1)],f'{bid}: nonsequential image slots')
        check([s['slot'] for s in audio_slots]==[f'@音频{n}' for n in range(1,len(audio_slots)+1)],f'{bid}: nonsequential audio slots')
        for item in allslots:
            rel=item['file']; p=root/rel
            check(p.is_file(),f'{bid}: missing reference {rel}')
            if p.is_file():
                actual=sha(p); checked_assets[rel]=actual
                check(item.get('sha256')==actual,f'{bid}: stale reference SHA256 {rel}')
            if item in audio_slots:
                check(Path(rel).name==VOICE_FILES.get(item['character_id']),f'{bid}: wrong cast voice {item["character_id"]}')
            if bid in ['N03','N04','N05'] and '/characters/C01/' in rel:
                check('DISGUISE' in rel,f'{bid}: emperor court image leaks into disguise job')
            if bid in ['N03','N04','N05'] and '/characters/C03/' in rel:
                check('DISGUISE' in rel,f'{bid}: Xiaotui court image leaks into disguise job')
            check('ANGLES_EXPRESSIONS' not in rel and 'DANCE_STUDY' not in rel,f'{bid}: human-review board/study uploaded as actor reference')
        dd=[d for d in dialogue if d['block']==bid]
        check(re.findall('“([^”]+)”',prompt)==[d['text'] for d in dd],f'{bid}: Prompt dialogue text/order differs from 21-line contract')
        cast={d['speaker_id'] for d in dd if d['speaker_id'] in VOICE_FILES}
        check({s['character_id'] for s in audio_slots}==cast,f'{bid}: silent actor voice uploaded or speaking actor voice missing')
        cursor=0
        for d in dd:
            did=d['id']; a=d['source_start']; b=d['source_end']
            check(0<=a<b<=30 and a>=cursor,f'{did}: out-of-range or overlapping dialogue')
            check(close(d['start'],a+off) and close(d['end'],b+off),f'{did}: wrong global dialogue offset')
            check(d['text'] in script and d['text'] in pack,f'{did}: dialogue absent from script or pack')
            owners=[s for s in ss if did in s['dialogue_ids']]
            check(len(owners)==1,f'{did}: no shot or multiply assigned')
            if len(owners)==1:
                owner=owners[0]
                check(owner['source_start']<=a<b<=owner['source_end'],f'{did}: dialogue extends beyond designated shot')
            check(d['visible_speaker']==(did!='E2_D08'),f'{did}: visible/offscreen mouth assignment changed')
            if d['speaker_id'] in VOICE_FILES:
                check(Path(d['voice_reference_file']).name==VOICE_FILES[d['speaker_id']],f'{did}: wrong voice file')
            else:
                check(d['voice_reference_file'] is None,f'{did}: original extra incorrectly uses principal voice')
            check(d['voice_reference_is_final_dialogue'] is False,f'{did}: voice sample mislabeled final dialogue')
            rate=len(re.findall('[\u3400-\u9fff]',d['text']))/(b-a); rates[did]=round(rate,4)
            if rate>4:
                warnings.append(f'{did}: {rate:.2f} Hanzi/sec needs rehearsal review, not proof of failure')
            window=f'{a:g}–{b:g}秒'
            check(window in prompt,f'{did}: precise voice window absent from Prompt')
            cursor=b
        if bid in ['N04','N05']:
            check(any(s['file']=='assets/characters/C05/C05_FRONT_HALF_v04.png' for s in image_slots),f'{bid}: missing Pan identity/mole authority')
            check(all(x in prompt for x in ['嘴角下方','皮肤','唇线','玉簪','镜像']),f'{bid}: Pan mole-side instructions missing')

    check(not [d for d in dialogue if d['block']=='N04'],'N04 dance cannot have dialogue')
    silent=contract['silent_block']
    check(silent['id']=='N04' and silent['source_seconds']==[0,30] and all(silent[x] for x in ['no_dialogue','no_music','no_vocalization','user_music_post_only']), 'N04 silent dance policy mismatch')
    check('不做唱歌口型' in prompts['N04'] and '后期配音乐' in prompts['N04'],'N04 cannot add singing mouth motions before user music')
    check('西卡画外声' in prompts['N02'] and '始终闭嘴' in prompts['N02'],'N02 listener-mouth exception missing')

    with (root/base/'audio/dialogue_cues.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    check(len(rows)==len(dialogue),'CSV dialogue count mismatch')
    for row,d in zip(rows,dialogue):
        check(row['id']==d['id'] and row['block']==d['block'] and row['text']==d['text'] and row['speaker']==DISPLAY_NAMES[d['speaker_id']],f'{d["id"]}: CSV text/role mismatch')
        check(row['visible']==str(d['visible_speaker']),f'{d["id"]}: CSV visibility mismatch')
        for ck,jk in [('source_start','source_start'),('source_end','source_end'),('global_start','start'),('global_end','end')]:
            check(close(row[ck],d[jk]),f'{d["id"]}: CSV {ck} mismatch')
    raw=(root/base/'audio/dialogue_timing.srt').read_text(encoding='utf-8').strip()
    cues=re.split(r'\n\s*\n',raw)
    check(len(cues)==len(dialogue),'SRT dialogue count mismatch')
    for cue,d in zip(cues,dialogue):
        lines=cue.splitlines(); a,b=lines[1].split(' --> ')
        check(close(srt_time(a),d['start']) and close(srt_time(b),d['end']) and '\n'.join(lines[2:])==d['text'],f'{d["id"]}: SRT time/text mismatch')

    baseline=read('history/validation/EP01_pre_EP02_sha256.json')
    actual_ep01={str(p.relative_to(root)):sha(p) for p in (root/'episodes/ep01').rglob('*') if p.is_file()}
    ep01_unchanged=all(actual_ep01.get(path)==digest for path,digest in baseline.items())
    added_ep01=sorted(set(actual_ep01)-set(baseline))
    check(ep01_unchanged,'Existing EP01 files changed or were deleted during EP02 work')
    check(set(added_ep01)<= {'episodes/ep01/STATUS_v4.json'},'Unexpected new content inside frozen EP01 directory')
    return {
        'date':'2026-09-23','episode':'EP02','status':'independent_static_audit',
        'integrity_pass':not errors,'errors':errors,'warnings':warnings,
        'duration_seconds':timeline['duration_seconds'],'source_seconds_per_block':30,
        'base_jobs':len(blocks),'narrative_shots':len(shots),'dialogue_count':len(dialogue),
        'prompt_character_count_definition':'Python len of complete UTF-8 decoded file, including whitespace, punctuation and reference labels',
        'prompt_character_limit':2000,'prompt_characters':char_counts,'prompt_utf8_bytes':bytes_counts,
        'dialogue_hanzi_per_second':rates,'max_dialogue_hanzi_per_second':max(rates.values()),
        'image_counts':{j['id']:j['image_count'] for j in jobs},'voice_reference_counts':{j['id']:j['audio_count'] for j in jobs},
        'reference_unique_file_count':len(checked_assets),'reference_sha256':checked_assets,
        'ep01_baseline_file_count':len(baseline),'ep01_byte_unchanged':ep01_unchanged,'ep01_added_metadata_files':added_ep01,
        'actual_media_audited':False,'mouth_sync_verified_from_video':False,'new_drama_voice_generated':False,
        'limits':['This checks production data, not Seedance output quality.','Images and candidate choreography require human approval.','Source voice sample playback and likeness are not independently verified here.','Performance speed statistics are estimates; real delivery must be watched and listened to.'],
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    try:
        report=validate(args.root.resolve())
    except (KeyError, ValueError, IndexError, OSError, TypeError) as exc:
        report={'integrity_pass':False,'errors':[f'{type(exc).__name__}: {exc}'],'actual_media_audited':False}
    output=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(output,encoding='utf-8')
    print(output,end='')
    return 0 if report['integrity_pass'] else 1

if __name__=='__main__':
    sys.exit(main())
