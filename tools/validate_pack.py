#!/usr/bin/env python3
"""Read-only checks of the production specification, never a video/audio review.

Run from any directory. Exit 1 means a broken production dependency or contract;
manual release gates are reported separately, including unrendered media.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = Path('episodes/ep01/production')
BASE_JOBS = {'A', 'B', 'C', 'D', 'E', 'F', 'G20', 'G21', 'G22', 'G23', 'G24'}
SPEAKERS = {
    'DLG01': 'E02', 'DLG02': 'E01', 'DLG03': 'E08',
    'DLG04': 'E04', 'DLG05': 'C04', 'DLG06': 'C03', 'DLG07': 'C03',
    'DLG08': 'C01', 'DLG09': 'E05', 'DLG10': 'C05',
    'DLG11': 'E06', 'DLG12': 'C05', 'DLG13': 'C05', 'DLG14': 'NARRATOR',
}
EXPECTED_VISIBILITY = {
    'DLG01': [('02', 3.2, 5.3, 'diegetic_offscreen')],
    'DLG02': [('02', 5.7, 7.0, 'onscreen_speaking')],
    'DLG03': [('03', 8.6, 12.7, 'diegetic_offscreen')],
    'DLG04': [('04', 14.0, 16.5, 'onscreen_speaking')],
    'DLG05': [('05', 18.0, 20.5, 'onscreen_speaking')],
    'DLG06': [('09', 33.6, 34.0, 'diegetic_offscreen'), ('10', 34.0, 38.1, 'onscreen_speaking')],
    'DLG07': [('11', 39.2, 42.3, 'diegetic_offscreen')],
    'DLG08': [('12', 43.2, 46.6, 'onscreen_speaking')],
    'DLG09': [('14', 50.7, 54.6, 'onscreen_speaking')],
    'DLG10': [('15', 55.1, 58.8, 'onscreen_speaking')],
    'DLG11': [('17', 64.0, 65.0, 'onscreen_speaking'), ('18', 65.0, 67.4, 'diegetic_offscreen')],
    'DLG12': [('18', 68.0, 69.0, 'onscreen_speaking'), ('19', 69.0, 69.4, 'onscreen_speaking')],
    'DLG13': [('19', 70.2, 73.6, 'onscreen_speaking')],
    'DLG14': [('21', 78.7, 80.0, 'voiceover'), ('22', 80.0, 81.5, 'voiceover'),
              ('23', 81.5, 84.5, 'voiceover'), ('24', 84.5, 87.3, 'voiceover')],
}


def close(a, b):
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, abs_tol=1e-7)


def shot_id(value):
    return str(value).removeprefix('SHOT').removeprefix('S').zfill(2)


def ref_path(ref):
    return ref.get('path', ref.get('file', ref.get('file_path')))


def check_image_references(root, label, refs, prompt, errors, pending):
    """Count optional images too; uncreated extraction is not a present asset."""
    if len(refs) > 5:
        errors.append(f'{label}: image budget {len(refs)} exceeds 5 including optional images')
    slots = [ref.get('slot') for ref in refs]
    expected = [f'@图片{i}' for i in range(1, len(refs) + 1)]
    if slots != expected:
        errors.append(f'{label}: image slots must be unique and consecutive {expected}, got {slots}')
    used = set(re.findall(r'@图片\d+', prompt))
    if used - set(slots):
        errors.append(f'{label}: unbound image labels {sorted(used - set(slots))}')
    for ref in refs:
        path = ref_path(ref)
        token = ref.get('slot', '')
        if path and any(x in path.upper() for x in ('ANGLES_EXPRESSIONS', 'WARDROBE_ONLY', 'CONTACT_SHEET')):
            errors.append(f'{label}: contact sheet or faceless wardrobe cannot be a video identity input: {path}')
        if path:
            resolved = (root / path).resolve()
            if not resolved.is_relative_to(root.resolve()):
                errors.append(f'{label}: reference outside repository: {path}')
            elif not resolved.is_file():
                if ref.get('optional') and ref.get('status') in {'not_generated', 'pending_extraction', 'requires_extraction'} and ref.get('derive_from'):
                    pending.append({'job': label, 'slot': token, 'path': path, 'status': ref['status'], 'derive_from': ref['derive_from']})
                else:
                    errors.append(f'{label}: required reference missing: {path}')
        elif ref.get('optional') and ref.get('status') in {'not_generated', 'pending_extraction', 'requires_extraction'} and ref.get('derive_from'):
            pending.append({'job': label, 'slot': token, 'path': None, 'status': ref['status'], 'derive_from': ref['derive_from']})
        else:
            errors.append(f'{label}: empty image path without an explicit pending derivation: {token}')
        if ref.get('optional') and token in used:
            # Optional tags must be guarded, not silently treated as uploaded files.
            mention_positions = [m.start() for m in re.finditer(re.escape(token), prompt)]
            if not any(re.search(r'若|如果|如已|仅在|只有|可选|有上传|已上传', prompt[max(0, p - 100):p + 100]) for p in mention_positions):
                errors.append(f'{label}: optional image label is not explicitly conditional: {token}')


def check_source_mapping(job, errors):
    label = job.get('id', job.get('job'))
    duration = job.get('source_duration_s')
    keep = job.get('source_keep_s', [])
    target = job.get('target_timeline_s', [])
    offset = job.get('source_to_global_offset_s')
    if not isinstance(duration, (int, float)) or len(keep) != 2 or len(target) != 2 or not isinstance(offset, (int, float)):
        errors.append(f'{label}: numeric source duration/keep/global mapping missing')
        return
    if not 0 < duration <= 15:
        errors.append(f'{label}: source duration must be positive and no more than 15 seconds in this production plan')
    if not 0 <= keep[0] < keep[1] <= duration:
        errors.append(f'{label}: picture keep is outside its source duration')
    if not close(keep[0] + offset, target[0]) or not close(keep[1] + offset, target[1]):
        errors.append(f'{label}: source picture/global mapping does not preserve the edit duration')
    if label == 'D' and not (close(duration, 14) and close(keep[0], .5) and close(keep[1], 13.5) and close(offset, 33.5)):
        errors.append('D: required 14-second source, picture [.5,13.5), offset 33.5 was changed')


def check_uploads(root, uploads, pack, errors, pending):
    if uploads.get('image_reference_limit_planned') != 5:
        errors.append("Upload manifest must declare the user's five-image limit")
    jobs = uploads.get('jobs', [])
    ids = [j.get('id', j.get('job')) for j in jobs]
    if len(ids) != 11 or set(ids) != BASE_JOBS:
        errors.append(f'Expected exactly 11 executable base jobs A–F/G20–G24; got {ids}')
    for job in jobs:
        label = job.get('id', job.get('job'))
        prompt_path = job.get('prompt_file')
        prompt_file = root / prompt_path if prompt_path else None
        if not prompt_file or not prompt_file.is_file():
            errors.append(f'{label}: prompt file missing: {prompt_path}')
            prompt = ''
        else:
            prompt = prompt_file.read_text().strip()
            if prompt not in pack:
                errors.append(f'{label}: prompt is not identical to production-pack text')
        refs = job.get('slots', []) + job.get('optional_image_slots', [])
        check_image_references(root, label, refs, prompt, errors, pending)
        if job.get('max_image_count_with_optional') != len(refs):
            errors.append(f'{label}: declared maximum image count does not match all slots')
        videos = job.get('optional_video_references', [])
        video_slots = [x.get('slot') for x in videos]
        if len(set(video_slots)) != len(video_slots):
            errors.append(f'{label}: duplicate video reference labels')
        unbound_videos = set(re.findall(r'@视频\d+', prompt)) - set(video_slots)
        if unbound_videos:
            errors.append(f'{label}: unbound video labels {sorted(unbound_videos)}')
        for ref in videos:
            if ref.get('source_job') not in BASE_JOBS:
                errors.append(f'{label}: unknown predecessor video job {ref.get("source_job")}')
            a, b = ref.get('source_local_in_s'), ref.get('source_local_out_s')
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or not 0 <= a < b:
                errors.append(f'{label}: invalid predecessor video range')
        check_source_mapping(job, errors)
    return {j.get('id', j.get('job')): j for j in jobs}


def check_dialogue_contract(contract, timeline, job_map, errors):
    if contract.get('source_script_sha256') != timeline.get('source_script_sha256'):
        errors.append('Dialogue contract names a different locked script')
    dialogues = contract.get('dialogues', [])
    locked = {x['id']: x for x in timeline['dialogue']}
    ids = [x.get('id') for x in dialogues]
    if len(ids) != 14 or set(ids) != set(locked):
        errors.append('Dialogue contract must contain the 14 unique locked dialogue IDs')
    shots = {shot_id(x['id']): x for x in timeline['shots']}
    blocks = {x['id']: x for x in timeline['blocks']}
    declared_jobs = {j.get('job'): j for j in contract.get('block_picture_jobs', [])}
    if set(declared_jobs) != set('ABCDEF'):
        errors.append('Dialogue contract must list all six A–F picture source mappings')
    for name, mapping in declared_jobs.items():
        base = job_map.get(name, {})
        keep = base.get('source_keep_s', [])
        target = base.get('target_timeline_s', [])
        if len(keep) != 2 or len(target) != 2:
            continue  # reported by upload validation already
        wanted = (base.get('source_duration_s'), keep[0], keep[1], target[0], target[1])
        actual = tuple(mapping.get(k) for k in ('source_duration_seconds', 'source_in', 'source_out', 'global_in', 'global_out'))
        if not all(close(a, b) for a, b in zip(actual, wanted)):
            errors.append(f'{name}: dialogue-contract picture mapping differs from upload recipe')
    dm = contract.get('d_source_mapping', {})
    required_d = {'source_duration_seconds': 14, 'picture_source_in': .5, 'picture_source_out': 13.5,
                  'picture_global_in': 34, 'picture_global_out': 47, 'native_audio_source_in': .1,
                  'native_audio_source_out': 13.5, 'native_audio_global_in': 33.6, 'native_audio_global_out': 47,
                  'global_equals_source_plus': 33.5}
    if any(not close(dm.get(k), v) for k, v in required_d.items()):
        errors.append('D source mapping metadata breaks its picture/audio J-cut contract')
    if dm.get('source_shot_cuts') != [5.5, 9.5] or dm.get('source_first_sentence') != [.1, 4.6]:
        errors.append('D source shot cuts or first sentence range are incorrect')
    for d in dialogues:
        label = d.get('id')
        original = locked.get(label)
        if not original:
            continue
        if d.get('text') != original['text']:
            errors.append(f'{label}: text differs from locked dialogue')
        if d.get('speaker_id') != SPEAKERS[label]:
            errors.append(f'{label}: wrong speaker identity {d.get("speaker_id")}')
        start, end = d.get('global_start'), d.get('global_end')
        if not close(start, original['start']) or not close(end, original['end']):
            errors.append(f'{label}: dialogue timing differs from locked timeline')
        src = d.get('source_audio', {})
        offset = src.get('global_offset_seconds')
        s0, s1 = src.get('source_start'), src.get('source_end')
        if not all(isinstance(x, (int, float)) for x in (start, end, offset, s0, s1)):
            errors.append(f'{label}: numeric audio source/global mapping missing')
            continue
        if not close(s0 + offset, start) or not close(s1 + offset, end):
            errors.append(f'{label}: audio source offset maps to the wrong global time')
        job = src.get('job')
        if job in job_map:
            expected_offset = job_map[job].get('source_to_global_offset_s')
            if not close(offset, expected_offset):
                errors.append(f'{label}: audio source offset differs from owning source job')
            if not 0 <= s0 < s1 <= job_map[job].get('source_duration_s', -1):
                errors.append(f'{label}: audio source interval is outside source duration')
        elif not (job == f'AUDIO_{label}' and src.get('mode') == 'independent_offscreen_audio' and d.get('lip_sync_required') is False):
            errors.append(f'{label}: dialogue audio must name its source job, or explicit offscreen-only audio recording')
        if label == 'DLG06' and not (job == 'D' and close(s0, .1) and close(s1, 4.6) and close(offset, 33.5)):
            errors.append('DLG06: J-cut must come from one D recording [.1,4.6) mapped to [33.6,38.1)')
        segments = d.get('visibility_segments', [])
        expected_segments = EXPECTED_VISIBILITY[label]
        if len(segments) != len(expected_segments):
            errors.append(f'{label}: visibility segmentation does not match locked shot cuts')
        cursor = start
        any_lips = False
        for i, seg in enumerate(segments):
            a, b = seg.get('global_start'), seg.get('global_end')
            if not all(isinstance(x, (int, float)) for x in (a, b)) or not close(a, cursor) or b <= a:
                errors.append(f'{label}: visibility segments have a gap, overlap, or invalid interval')
                continue
            cursor = b
            sid = shot_id(seg.get('shot_id'))
            shot = shots.get(sid)
            mode = seg.get('visibility')
            if i < len(expected_segments):
                esid, ea, eb, emode = expected_segments[i]
                if sid != esid or not close(a, ea) or not close(b, eb) or mode != emode:
                    errors.append(f'{label}: shot {sid} uses incorrect visibility or cut boundaries')
            on_camera = mode == 'onscreen_speaking'
            any_lips |= on_camera
            if seg.get('lip_sync_required') is not on_camera:
                errors.append(f'{label}: visible speech requires lip sync; offscreen/VO requires none')
            if seg.get('speaker_id', d.get('speaker_id')) != SPEAKERS[label]:
                errors.append(f'{label}: visibility segment assigned to the wrong speaking face')
            if not shot or seg.get('block') != shot['block'] or a < shot['start'] - 1e-7 or b > shot['end'] + 1e-7:
                errors.append(f'{label}: segment not contained in its declared shot/block')
            else:
                block_start = blocks[shot['block']]['start']
                if not close(seg.get('block_local_start'), a - block_start) or not close(seg.get('block_local_end'), b - block_start):
                    errors.append(f'{label}: visibility block-local times are incorrect')
            if not close(seg.get('source_start'), a - offset) or not close(seg.get('source_end'), b - offset):
                errors.append(f'{label}: visibility source times are incorrect')
        if not close(cursor, end):
            errors.append(f'{label}: visibility segments do not cover the entire dialogue')
        if d.get('lip_sync_required') is not any_lips:
            errors.append(f'{label}: dialogue lip-sync flag conflicts with its segments')
        if d.get('speaker_id') in d.get('listeners', []):
            errors.append(f'{label}: speaking character is also incorrectly assigned as a closed-mouth listener')
        if d.get('verified') and not src.get('file'):
            errors.append(f'{label}: verified speech claims require an actual source file and review evidence')
        if not d.get('listener_instruction'):
            errors.append(f'{label}: listener mouth/reaction instructions missing')
    return {d.get('id'): d for d in dialogues}



def check_repair_plan(root, plan, timeline, contract, errors, pending):
    """A repair may replace existing shots; it may not insert new story shots."""
    if plan.get('max_images_per_job') != 5:
        errors.append('Repair plan does not use the five-image budget')
    shots = {shot_id(x['id']): x for x in timeline['shots']}
    lines = {d['id']: d for d in contract['dialogues']}
    jobs = plan.get('jobs', [])
    ids = [j.get('id') for j in jobs]
    if len(ids) != len(set(ids)):
        errors.append('Duplicate repair job IDs')
    assigned = {}
    for job in jobs:
        label = job.get('id')
        refs = [dict(ref, slot=f"@图片{ref['slot']}") if isinstance(ref.get('slot'), int) else ref for ref in job.get('image_references', [])]
        prompt = job.get('prompt', '')
        prompt_path = job.get('prompt_file')
        prompt_file = root / prompt_path if prompt_path else None
        if not prompt_file or not prompt_file.is_file():
            errors.append(f'{label}: standalone repair prompt file missing: {prompt_path}')
        elif not prompt_file.resolve().is_relative_to(root.resolve()):
            errors.append(f'{label}: repair prompt path is outside repository: {prompt_path}')
        elif prompt_file.read_text().strip() != prompt.strip():
            errors.append(f'{label}: repair prompt TXT differs from JSON prompt')
        check_image_references(root, label, refs, prompt, errors, pending)
        optional = job.get('optional_actual_shot_frame')
        if optional:
            # Reserve a potential actual frame too; the current recipe has <=4 static inputs.
            if len(refs) + 1 > 5:
                errors.append(f'{label}: actual-shot frame would become image six')
            actual_file = optional.get('file')
            if actual_file:
                if not (root / actual_file).is_file():
                    errors.append(f'{label}: extracted frame file is missing: {actual_file}')
            elif optional.get('status') == 'not_received_or_extracted':
                pending.append({'job': label, 'path': None, 'status': optional['status'], 'derive_from': 'accepted actual source shot, not supplied yet'})
            else:
                errors.append(f'{label}: unextracted actual frame must remain explicitly pending')
        if job.get('max_image_count', 5) > 5:
            errors.append(f'{label}: repair declares more than five images')
        duration = job.get('source_duration_seconds')
        if not isinstance(duration, (int, float)) or not 0 < duration <= 15:
            errors.append(f'{label}: invalid repair source duration')
            continue
        speaker_ids = job.get('speaker_ids', [])
        if len(speaker_ids) != 1:
            errors.append(f'{label}: targeted repair must have exactly one speaking character')
        offsets = []
        for use in job.get('picture_uses', []):
            a, b, ga, gb = [use.get(k) for k in ('source_in', 'source_out', 'global_in', 'global_out')]
            if not all(isinstance(x, (int, float)) for x in (a, b, ga, gb)) or not 0 <= a < b <= duration:
                errors.append(f'{label}: invalid repair picture source range')
                continue
            offsets.append(ga - a)
            if not close(b - a, gb - ga):
                errors.append(f'{label}: repair picture mapping changes duration')
            declared_shots = [shots.get(shot_id(x)) for x in use.get('shot_ids', [])]
            if not declared_shots or any(x is None for x in declared_shots):
                errors.append(f'{label}: repair has an unknown/empty shot ID')
            elif not close(ga, declared_shots[0]['start']) or not close(gb, declared_shots[-1]['end']):
                errors.append(f'{label}: repair picture must replace exactly its existing shot interval')
        for use in job.get('dialogue_uses', []):
            did = use.get('dialogue_id')
            d = lines.get(did)
            if not d:
                errors.append(f'{label}: unknown dialogue {did}')
                continue
            assigned.setdefault(did, []).append(label)
            if use.get('speaker_id') != SPEAKERS[did] or use.get('speaker_id') not in speaker_ids:
                errors.append(f'{label}: repair assigned to wrong speaker for {did}')
            if use.get('text') != d['text'] or d['text'] not in prompt:
                errors.append(f'{label}: repair dialogue text differs from locked {did}')
            a, b, ga, gb = [use.get(k) for k in ('source_start', 'source_end', 'global_start', 'global_end')]
            if not all(isinstance(x, (int, float)) for x in (a, b, ga, gb)) or not 0 <= a < b <= duration:
                errors.append(f'{label}: invalid repair dialogue source range')
                continue
            if not close(ga, d['global_start']) or not close(gb, d['global_end']) or not close(b - a, gb - ga):
                errors.append(f'{label}: repair changes locked dialogue time or duration for {did}')
            offsets.append(ga - a)
            if job.get('type') == 'audio_only_offscreen' and d['lip_sync_required']:
                errors.append(f'{label}: audio-only repair cannot repair visible speech {did}')
        if offsets and any(not close(x, offsets[0]) for x in offsets):
            errors.append(f'{label}: repair picture/audio do not share one source-to-global offset')
        if job.get('type') == 'audio_only_offscreen' and (refs or job.get('picture_uses')):
            errors.append(f'{label}: audio-only repair unexpectedly replaces imagery')
    if set(assigned) != set(lines) or any(len(x) != 1 for x in assigned.values()):
        errors.append('Repair plan must provide one unambiguous targeted option for each of the 14 lines')
    mapping = plan.get('dialogue_to_repair_job', {})
    if mapping != {k: v[0] for k, v in assigned.items()}:
        errors.append('Repair dialogue-to-job index differs from repair job contents')
    if set(plan.get('no_visual_repair_needed_ids', [])) != {k for k, d in lines.items() if not d['lip_sync_required']}:
        errors.append('Repair offscreen-only index conflicts with actual visibility')
    if plan.get('global_duration_seconds_after_repair') != 90 or plan.get('shot_count_after_repair') != 25:
        errors.append('Repair plan changes the locked duration or shot count')
    return len(jobs)

def validate(root=ROOT):
    errors, pending = [], []
    def read(path):
        return json.loads((root / path).read_text())
    lock = read('episodes/ep01/script/LOCK.json')
    if hashlib.sha256((root / lock['path']).read_bytes()).hexdigest() != lock['sha256']:
        errors.append('Locked script changed')
    timeline = read(PRODUCTION / 'timeline.json')
    if timeline.get('source_script_sha256') != lock['sha256']:
        errors.append('Timeline names a different script source')
    script_text = (root / lock['path']).read_text()
    if len(timeline.get('dialogue', [])) != 14:
        errors.append('Timeline must preserve all 14 locked dialogue lines')
    for line in timeline.get('dialogue', []):
        if line.get('text', '') not in script_text:
            errors.append('Timeline contains dialogue absent from locked script: ' + str(line.get('id')))
    if len(timeline['blocks']) != 7 or not close(sum(x['duration'] for x in timeline['blocks']), 90):
        errors.append('Block duration/count changed')
    if any(not 8 <= x['duration'] <= 15 for x in timeline['blocks']):
        errors.append('Block outside 8–15 seconds')
    shots = timeline['shots']
    if len(shots) != 25 or sum(x['end_frame_exclusive'] - x['start_frame'] for x in shots) != 2160:
        errors.append('Shot/frame total mismatch')
    for a, b in zip(shots, shots[1:]):
        if not close(a['end'], b['start']) or a['end_frame_exclusive'] != b['start_frame']:
            errors.append('Shot gap/overlap')
    if not close(shots[0]['start'], 0) or not close(shots[-1]['end'], 90):
        errors.append('Timeline does not cover 0–90 seconds')
    pack = (root / PRODUCTION / 'VIDEO_PRODUCTION_PACK.md').read_text()
    for d in timeline['dialogue']:
        if d['text'] not in pack:
            errors.append('Missing locked line in production pack: ' + d['id'])
    for asset in read('assets/manifest.json')['assets']:
        path = root / asset['path']
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
            errors.append('Asset missing/changed: ' + asset['path'])
    for path in read('assets/current_selection.json')['current_paths']:
        if not (root / path).is_file():
            errors.append('Selected current asset missing: ' + path)
    jobs = check_uploads(root, read(PRODUCTION / 'refs_upload.json'), pack, errors, pending)
    contract_path = root / PRODUCTION / 'audio/dialogue_contract.json'
    if not contract_path.is_file():
        errors.append('Dialogue contract missing')
    else:
        contract = json.loads(contract_path.read_text())
        check_dialogue_contract(contract, timeline, jobs, errors)
        repair_path = root / PRODUCTION / 'audio/dialogue_repair_plan.json'
        if not repair_path.is_file():
            errors.append('Targeted dialogue repair plan missing')
        else:
            check_repair_plan(root, json.loads(repair_path.read_text()), timeline, contract, errors, pending)
    status = read('context/STATUS.json')
    return {
        'integrity_pass': not errors,
        'validation_scope': 'Static files, image budgets, prompt binding, locked timing and dialogue contracts only; no generated video or audio was watched/listened to by this validator.',
        'actual_media_audited': False,
        'errors': errors,
        'image_budget_per_job': 5,
        'executable_base_jobs': len(jobs),
        'pending_derived_references': pending,
        'production_release_gates': [x['id'] for x in status.get('blockers', [])],
        'video_generated': status.get('video_generated', False),
        'video_generated_field_scope': status.get('video_generated_field_scope'),
        'user_reported_external_video_generation': status.get('user_reported_external_video_generation', False),
        'received_user_video_files': status.get('received_user_video_files', False),
        'github_synced': status.get('github', {}).get('synced', False),
    }


if __name__ == '__main__':
    try:
        result = validate()
    except (KeyError, TypeError, ValueError, OSError) as exc:
        result = {'integrity_pass': False, 'errors': [f'Invalid or incomplete production schema: {exc}']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(not result['integrity_pass'])
