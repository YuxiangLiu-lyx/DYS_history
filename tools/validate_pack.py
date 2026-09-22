#!/usr/bin/env python3
"""Read-only checks of the production specification, never a video/audio review.

Run from any directory. Exit 1 means a broken production dependency or contract;
manual release gates are reported separately, including unrendered media.
"""
from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import math
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = Path('episodes/ep01/production')
BASE_JOBS = {'M01', 'M02', 'M03'}
IMAGE_LIMIT = 30
AUDIO_LIMIT = 10
VIDEO_LIMIT = 10
TOTAL_LIMIT = 50
SCRIPT_SHA256 = '5219a9614cb565720f1fb2cab9d2615c3b35dd6647b3b77fc9c64198b5c2bbfa'
ORIGINAL = Path('archive/production_pack_v3/production')
ORIGINAL_TIMELINE_SHA256 = '94ab89fe27f8b0e19a6662edea753f6725556feec31ed1f441b45af3895765cf'
EXPECTED_PICTURE_COUNTS = {'M01': 9, 'M02': 9, 'M03': 11}
EXPECTED_AUDIO_SPEAKERS = {'M01': ['C04'], 'M02': ['C01', 'C03', 'C05'], 'M03': ['C05']}
VOICE_FILES = {'C01': '01_sun_yalong.mp3', 'C05': '02_pan_hui.mp3', 'C03': '03_xiaotui.mp3', 'C02': '04_xika.mp3', 'C04': '05_weixiao.mp3'}
SHOT_RETIMES = {'13': (47, 49), '14': (49, 54), '15': (54, 58), '16': (58, 60), '17': (60, 64), '18': (64, 69)}
DIALOGUE_RETIMES = {'DLG09': (49.7, 53.6), 'DLG10': (54.1, 57.8), 'DLG11': (63, 66.4)}
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
    'DLG09': [('14', 49.7, 53.6, 'onscreen_speaking')],
    'DLG10': [('15', 54.1, 57.8, 'onscreen_speaking')],
    'DLG11': [('17', 63.0, 64.0, 'onscreen_speaking'), ('18', 64.0, 66.4, 'diegetic_offscreen')],
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
    if len(refs) > IMAGE_LIMIT:
        errors.append(f'{label}: image budget {len(refs)} exceeds {IMAGE_LIMIT} including optional images')
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
    offset = {'M01': 0, 'M02': 30, 'M03': 60}.get(label)
    if not close(job.get('source_duration_s'), 30):
        errors.append(f'{label}: each base source must be exactly 30 seconds')
    if job.get('source_keep_s') != [0, 30]:
        errors.append(f'{label}: base picture source range must be [0,30)')
    if offset is not None and (not close(job.get('source_to_global_offset_s'), offset)
                              or job.get('target_timeline_s') != [offset, offset + 30]):
        errors.append(f'{label}: expected source-to-global offset {offset}, no legacy D trim')


def load_voice_manifest(root, errors):
    data = json.loads((root / 'assets/audio/voice_references/manifest.json').read_text())
    voices = data.get('assets', [])
    if len(voices) != 5 or {x.get('character_id') for x in voices} != set(VOICE_FILES):
        errors.append('Voice archive must preserve the five user-identified speakers')
    indexed = {}
    for voice in voices:
        cid, path = voice.get('character_id'), voice.get('file')
        if not path or Path(path).name != VOICE_FILES.get(cid):
            errors.append(f'{cid}: original filename/character voice binding changed')
            continue
        full = root / path
        if not full.is_file() or hashlib.sha256(full.read_bytes()).hexdigest() != voice.get('sha256'):
            errors.append(f'{cid}: original voice file missing or SHA-256 mismatch')
        elif full.stat().st_size != voice.get('bytes'):
            errors.append(f'{cid}: original voice byte count differs')
        if not voice.get('preservation', {}).get('original_bytes_preserved'):
            errors.append(f'{cid}: original voice bytes must remain preserved')
        use = voice.get('intended_use', {})
        if use.get('copy_sample_words_to_film') is not False or use.get('lip_timing_from_reference_sample') is not False:
            errors.append(f'{cid}: voice sample must not replace script words or phoneme timing')
        if cid == 'C02' and use.get('has_locked_ep01_dialogue') is not False:
            errors.append('C02: Xika has no EP01 dialogue; sample is archive-only')
        indexed[cid] = voice
    return indexed


def check_audio_references(root, label, refs, prompt, voices, errors, expected_speakers=None):
    if len(refs) > AUDIO_LIMIT:
        errors.append(f'{label}: audio budget exceeds {AUDIO_LIMIT}')
    slots = [x.get('label', f'@音频{x.get("slot")}') if isinstance(x.get('slot'), int) else x.get('slot', x.get('label')) for x in refs]
    expected_slots = [f'@音频{i}' for i in range(1, len(refs) + 1)]
    if slots != expected_slots:
        errors.append(f'{label}: audio slots must be consecutive and unique')
    if set(re.findall(r'@音频\d+', prompt)) - set(slots):
        errors.append(f'{label}: unbound audio labels in prompt')
    speakers = []
    for ref in refs:
        cid = ref.get('speaker_id', ref.get('character_id'))
        speakers.append(cid)
        voice = voices.get(cid, {})
        if ref_path(ref) != voice.get('file') or not voice:
            errors.append(f'{label}: wrong voice-reference file for speaker {cid}')
        if ref.get('sha256') is not None and ref.get('sha256') != voice.get('sha256'):
            errors.append(f'{label}: audio-reference hash differs from original speaker asset {cid}')
        if cid == 'C02':
            errors.append(f'{label}: silent Xika must not receive a speech reference')
    if expected_speakers is not None and speakers != expected_speakers:
        errors.append(f'{label}: expected voice references {expected_speakers}, got {speakers}')


def check_uploads(root, uploads, pack, errors, pending):
    if uploads.get('image_reference_limit_planned') != IMAGE_LIMIT:
        errors.append('Upload manifest must declare the verified 30-image ceiling')
    for field, expected in [('video_reference_limit_planned', VIDEO_LIMIT), ('audio_reference_limit_planned', AUDIO_LIMIT), ('total_reference_limit_planned', TOTAL_LIMIT)]:
        if uploads.get(field) != expected:
            errors.append(f'Upload manifest {field} must equal {expected}')
    jobs = uploads.get('jobs', [])
    ids = [j.get('id', j.get('job')) for j in jobs]
    if len(ids) != 3 or set(ids) != BASE_JOBS:
        errors.append(f'Expected exactly 3 executable base jobs M01–M03; got {ids}')
    voices = load_voice_manifest(root, errors)
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
        primary = job.get('slots', [])
        refs = primary + job.get('optional_image_slots', [])
        check_image_references(root, label, refs, prompt, errors, pending)
        if len(primary) != EXPECTED_PICTURE_COUNTS.get(label):
            errors.append(f'{label}: expected the curated {EXPECTED_PICTURE_COUNTS.get(label)} default images')
        if job.get('max_image_count_with_optional') != len(refs):
            errors.append(f'{label}: declared maximum image count does not match all slots')
        audios = job.get('audio_slots', job.get('audio_references', []))
        check_audio_references(root, label, audios, prompt, voices, errors, EXPECTED_AUDIO_SPEAKERS.get(label))
        videos = job.get('optional_video_references', [])
        video_slots = [x.get('slot') for x in videos]
        if len(videos) > VIDEO_LIMIT:
            errors.append(f'{label}: video budget exceeds {VIDEO_LIMIT}')
        if job.get('max_total_materials_with_optional') != len(refs) + len(audios) + len(videos):
            errors.append(f'{label}: declared total materials differs from actual plus optional inputs')
        if len(refs) + len(audios) + len(videos) > TOTAL_LIMIT:
            errors.append(f'{label}: total media budget exceeds {TOTAL_LIMIT}')
        if len(set(video_slots)) != len(video_slots):
            errors.append(f'{label}: duplicate video reference labels')
        if set(re.findall(r'@视频\d+', prompt)) - set(video_slots):
            errors.append(f'{label}: unbound video labels')
        for ref in videos:
            if ref.get('source_job') not in BASE_JOBS:
                errors.append(f'{label}: unknown predecessor video job {ref.get("source_job")}')
            a, b = ref.get('source_local_in_s'), ref.get('source_local_out_s')
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or not 0 <= a < b <= 30:
                errors.append(f'{label}: invalid predecessor video range')
            if ref_path(ref) is not None:
                if not (root / ref_path(ref)).is_file():
                    errors.append(f'{label}: predecessor video path is not a real file')
            elif ref.get('status') not in {'source_not_registered', 'not_generated', 'pending_generation', 'not_generated_not_uploaded', 'source_not_generated_or_registered'}:
                errors.append(f'{label}: absent predecessor video must remain explicitly pending')
            if ref.get('copy_audio') is not False:
                errors.append(f'{label}: video reference may not duplicate dialogue/music')
        if job.get('already_uploaded_to_video_tool') and not job.get('actual_task_id'):
            errors.append(f'{label}: submission claim needs an actual task ID')
        if job.get('generated_video') is not None and not (root / job['generated_video']).is_file():
            errors.append(f'{label}: generated-video claim needs a real file')
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
    if set(declared_jobs) != BASE_JOBS:
        errors.append('Dialogue contract must list the three 30-second source mappings')
    for name, mapping in declared_jobs.items():
        base = job_map.get(name, {})
        keep = base.get('source_keep_s', [])
        target = base.get('target_timeline_s', [])
        if len(keep) != 2 or len(target) != 2:
            continue
        wanted = (base.get('source_duration_s'), keep[0], keep[1], target[0], target[1])
        actual = tuple(mapping.get(k) for k in ('source_duration_seconds', 'source_in', 'source_out', 'global_in', 'global_out'))
        if not all(close(a, b) for a, b in zip(actual, wanted)):
            errors.append(f'{name}: dialogue-contract picture mapping differs from upload recipe')
    if contract.get('d_source_mapping'):
        errors.append('Legacy D 14-second source mapping must not remain an active v4 contract')
    contract_refs = contract.get('audio_reference_uploads_by_job', {})
    if set(contract_refs) != BASE_JOBS:
        errors.append('Contract must list voice uploads for all three acts')
    for name, refs in contract_refs.items():
        pairs = [(r.get('speaker_id', r.get('character_id')), ref_path(r)) for r in refs]
        upload_pairs = [(r.get('speaker_id', r.get('character_id')), ref_path(r)) for r in job_map.get(name, {}).get('audio_slots', job_map.get(name, {}).get('audio_references', []))]
        if pairs != upload_pairs:
            errors.append(f'{name}: voice-reference contract differs from upload slot order')
    for mapping in contract.get('act_source_mappings', []):
        name = mapping.get('job')
        expected_offset = {'M01': 0, 'M02': 30, 'M03': 60}.get(name)
        if expected_offset is None or not close(mapping.get('global_equals_source_plus'), expected_offset) or mapping.get('source_range') != [0, 30] or mapping.get('global_range') != [expected_offset, expected_offset+30]:
            errors.append(f'{name}: act source mapping differs from the 30-second source plan')
    for name, job in job_map.items():
        for ref in job.get('audio_slots', job.get('audio_references', [])):
            cid = ref.get('speaker_id', ref.get('character_id'))
            desired = [[d['source_audio']['source_start'], d['source_audio']['source_end']] for d in dialogues if d.get('speaker_id') == cid and d.get('source_audio', {}).get('job') == name]
            if ref.get('time_scope') != desired:
                errors.append(f'{name}: voice reference {cid} has incorrect or extra speaking intervals')
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
        if label == 'DLG06' and not (job == 'M02' and close(s0, 3.6) and close(s1, 8.1) and close(offset, 30)):
            errors.append('DLG06: J-cut must use one M02 recording [3.6,8.1) mapped to [33.6,38.1)')
        if label in {'DLG03', 'DLG14'} and job != f'AUDIO_{label}':
            errors.append(f'{label}: woman offscreen/narrator must remain post-only audio')
        cid = d.get('speaker_id')
        own_refs = contract_refs.get(job, [])
        own_ref = next((r for r in own_refs if r.get('speaker_id') == cid), None)
        if cid in VOICE_FILES:
            if not own_ref or d.get('voice_reference_file') != ref_path(own_ref) or d.get('voice_reference_label') != own_ref.get('label', own_ref.get('slot')):
                errors.append(f'{label}: per-line voice reference belongs to the wrong speaker/slot')
        elif d.get('voice_reference_file') is not None or d.get('voice_reference_label') is not None:
            errors.append(f'{label}: extra role cannot borrow a main actor voice sample')
        if d.get('verified') and not src.get('file'):
            errors.append(f'{label}: verified dialogue requires an actual source file')
        if not close(d.get('start_sample_48k'), start*48000) or not close(d.get('end_sample_exclusive_48k'), end*48000):
            errors.append(f'{label}: 48k sample timing differs from global timing')
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
    if plan.get('max_images_per_job', IMAGE_LIMIT) > IMAGE_LIMIT:
        errors.append('Repair plan exceeds the 30-image ceiling')
    shots = {shot_id(x['id']): x for x in timeline['shots']}
    lines = {d['id']: d for d in contract['dialogues']}
    jobs = plan.get('jobs', [])
    ids = [j.get('id') for j in jobs]
    if len(ids) != len(set(ids)):
        errors.append('Duplicate repair job IDs')
    assigned = {}
    voices = load_voice_manifest(root, errors)
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
        audios = job.get('audio_slots', job.get('audio_references', []))
        wanted_voices = [cid for cid in job.get('speaker_ids', []) if cid in VOICE_FILES]
        check_audio_references(root, label, audios, prompt, voices, errors, wanted_voices)
        optional = job.get('optional_actual_shot_frame')
        if optional:
            # Count an optional actual frame, without pretending it has been extracted.
            if len(refs) + 1 > min(IMAGE_LIMIT, job.get('max_image_count', IMAGE_LIMIT)):
                errors.append(f'{label}: actual-shot frame would exceed image budget')
            actual_file = optional.get('file')
            if actual_file:
                if not (root / actual_file).is_file():
                    errors.append(f'{label}: extracted frame file is missing: {actual_file}')
            elif optional.get('status') == 'not_received_or_extracted':
                pending.append({'job': label, 'path': None, 'status': optional['status'], 'derive_from': 'accepted actual source shot, not supplied yet'})
            else:
                errors.append(f'{label}: unextracted actual frame must remain explicitly pending')
        if job.get('max_image_count', IMAGE_LIMIT) > IMAGE_LIMIT:
            errors.append(f'{label}: repair declares more than {IMAGE_LIMIT} images')
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

def check_timeline(timeline, original, errors):
    blocks = timeline.get('blocks', [])
    if [x.get('id') for x in blocks] != ['M01', 'M02', 'M03']:
        errors.append('Timeline must have M01/M02/M03 in order')
    for i, block in enumerate(blocks):
        expected = (i * 30, (i + 1) * 30, 30, i * 720, (i + 1) * 720)
        actual = tuple(block.get(k) for k in ('start', 'end', 'duration', 'start_frame', 'end_frame_exclusive'))
        if not all(close(a, b) for a, b in zip(actual, expected)):
            errors.append(f'{block.get("id")}: block must be exactly 30 seconds/720 frames')
    shots = timeline.get('shots', [])
    orig_shots = {x['id']: x for x in original['shots']}
    if len(shots) != 25 or [x.get('id') for x in shots] != list(orig_shots):
        errors.append('Original 24 narrative shots plus one title must remain in exact order')
    for shot in shots:
        sid = shot.get('id')
        previous = orig_shots.get(sid)
        if not previous:
            continue
        a, b = SHOT_RETIMES.get(sid, (previous['start'], previous['end']))
        expected_block = 'M01' if a < 30 else 'M02' if a < 60 else 'M03'
        if not close(shot.get('start'), a) or not close(shot.get('end'), b):
            errors.append(f'Shot {sid}: unexpected timing change')
        if not close(shot.get('duration'), b-a) or not close(shot.get('start_frame'), a*24) or not close(shot.get('end_frame_exclusive'), b*24):
            errors.append(f'Shot {sid}: duration/frame mapping is incorrect')
        if shot.get('block') != expected_block:
            errors.append(f'Shot {sid}: belongs to {expected_block}')
        for key in ('action', 'camera'):
            if previous.get(key, '') not in shot.get(key, ''):
                errors.append(f'Shot {sid}: original {key} was removed or rewritten')
        if shot.get('kind') != previous.get('kind'):
            errors.append(f'Shot {sid}: narrative/title kind changed')
    for a, b in zip(shots, shots[1:]):
        if not close(a['end'], b['start']) or a['end_frame_exclusive'] != b['start_frame']:
            errors.append('Shot gap/overlap')
    if not shots or not close(shots[0]['start'], 0) or not close(shots[-1]['end'], 90):
        errors.append('Timeline does not cover 0–90 seconds')
    dialogues = timeline.get('dialogue', [])
    old_lines = {x['id']: x for x in original['dialogue']}
    if len(dialogues) != 14 or [x.get('id') for x in dialogues] != list(old_lines):
        errors.append('Preserve the 14 original dialogue IDs and order')
    for d in dialogues:
        previous = old_lines.get(d.get('id'))
        if not previous:
            continue
        if d.get('text') != previous['text'] or d.get('speaker') != previous.get('speaker'):
            errors.append(f'{d.get("id")}: locked dialogue text/speaker differs from v3')
        a, b = DIALOGUE_RETIMES.get(d['id'], (previous['start'], previous['end']))
        if not close(d.get('start'), a) or not close(d.get('end'), b):
            errors.append(f'{d["id"]}: unexpected dialogue timing change')
    if timeline.get('fps') != 24 or timeline.get('duration_seconds') != 90 or timeline.get('total_frames') != 2160:
        errors.append('Timeline must remain 24fps/90 seconds/2160 frames')


def check_dialogue_exports(root, timeline, errors):
    rows = list(csv.DictReader((root / PRODUCTION / 'audio/dialogue_cues.csv').read_text().splitlines()))
    lines = timeline['dialogue']
    if len(rows) != len(lines):
        errors.append('Dialogue cue CSV row count differs from timeline')
    for row, d in zip(rows, lines):
        if row.get('id') != d['id'] or row.get('text') != d['text'] or row.get('speaker') != d.get('speaker'):
            errors.append(f'{d["id"]}: CSV ID/text/speaker differs')
        if not close(float(row['start']), d['start']) or not close(float(row['end']), d['end']):
            errors.append(f'{d["id"]}: CSV cue retains incorrect dialogue time')
        if not close(int(row['start_sample_48k']), d['start']*48000) or not close(int(row['end_sample_exclusive_48k']), d['end']*48000):
            errors.append(f'{d["id"]}: CSV sample timing differs')
    def stamp(seconds):
        ms = round(seconds*1000)
        return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
    srt = (root / PRODUCTION / 'audio/dialogue_timing.srt').read_text()
    expected = '\n\n'.join(f'{i}\n{stamp(d["start"])} --> {stamp(d["end"])}\n{d["text"]}' for i, d in enumerate(lines, 1))
    if srt.strip() != expected:
        errors.append('Dialogue timing SRT differs from the current exact words/times')


def validate(root=ROOT):
    errors, pending = [], []
    def read(path):
        return json.loads((root / path).read_text())
    lock = read('episodes/ep01/script/LOCK.json')
    if lock.get('sha256') != SCRIPT_SHA256 or hashlib.sha256((root / lock['path']).read_bytes()).hexdigest() != SCRIPT_SHA256:
        errors.append('Locked script changed')
    timeline = read(PRODUCTION / 'timeline.json')
    if timeline.get('source_script_sha256') != SCRIPT_SHA256:
        errors.append('Timeline names a different script source')
    if hashlib.sha256((root / ORIGINAL / 'timeline.json').read_bytes()).hexdigest() != ORIGINAL_TIMELINE_SHA256:
        errors.append('Archived v3 timeline source changed; original story comparison is not trustworthy')
    original = read(ORIGINAL / 'timeline.json')
    check_timeline(timeline, original, errors)
    check_dialogue_exports(root, timeline, errors)
    pack = (root / PRODUCTION / 'VIDEO_PRODUCTION_PACK.md').read_text()
    for d in timeline['dialogue']:
        if d['text'] not in pack:
            errors.append('Missing locked line in production pack: ' + d['id'])
    for asset in read('assets/manifest.json')['assets']:
        path = root / asset['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
            errors.append('Asset missing/changed: ' + asset['path'])
    for path in read('assets/current_selection.json')['current_paths']:
        if not (root / path).is_file():
            errors.append('Selected current asset missing: ' + path)
    jobs = check_uploads(root, read(PRODUCTION / 'refs_upload.json'), pack, errors, pending)
    contract = read(PRODUCTION / 'audio/dialogue_contract.json')
    check_dialogue_contract(contract, timeline, jobs, errors)
    for d in contract.get('dialogues', []):
        owner = d.get('source_audio', {}).get('job')
        if owner in jobs:
            prompt = (root / jobs[owner]['prompt_file']).read_text()
            if prompt.count(d['text']) != 1:
                errors.append(f'{d["id"]}: native line must occur exactly once in its act prompt')
    repair_count = check_repair_plan(root, read(PRODUCTION / 'audio/dialogue_repair_plan.json'), timeline, contract, errors, pending)
    active_prompts = {p.stem.removesuffix('_PROMPT') for p in (root / PRODUCTION / 'prompts').glob('*_PROMPT.txt')}
    if active_prompts != BASE_JOBS:
        errors.append(f'Only M01/M02/M03 base prompts may remain active, found {sorted(active_prompts)}')
    status = read('context/STATUS.json')
    if status.get('received_user_audio_files') is not True:
        errors.append('Status must record the five received user voice-reference files')
    actual_audio_paths = [d['source_audio']['file'] for d in contract['dialogues'] if d.get('source_audio', {}).get('file')]
    for path in actual_audio_paths:
        if not (root / path).is_file():
            errors.append(f'Generated dialogue source file missing: {path}')
    if status.get('audio_generated') and not actual_audio_paths:
        errors.append('Received voice samples do not establish generated episode dialogue audio')
    if status.get('video_generated') and not any(j.get('generated_video') for j in jobs.values()):
        errors.append('Generated episode video claim needs actual source media')
    for field in ('actual_av_review_performed', 'actual_av_repair_performed'):
        evidence = status.get(field + '_evidence_file')
        if status.get(field) and (not evidence or not (root / evidence).is_file()):
            errors.append(f'{field}: actual AV claim needs a saved evidence file')
    return {
        'integrity_pass': not errors,
        'revision': 'EP01_v4_3x30',
        'validation_scope': 'Static assets and SHA-256, three 30-second jobs, media budgets, label/speaker binding, original story preservation, retimed dialogue and source mappings. No generated video or dialogue audio was watched/listened to by this validator.',
        'actual_media_audited': False,
        'errors': errors,
        'media_limits': {'images': IMAGE_LIMIT, 'videos': VIDEO_LIMIT, 'audio': AUDIO_LIMIT, 'combined': TOTAL_LIMIT},
        'planned_default_image_counts': EXPECTED_PICTURE_COUNTS,
        'planned_default_audio_counts': {k: len(v) for k, v in EXPECTED_AUDIO_SPEAKERS.items()},
        'original_voice_files_verified': 5,
        'script_sha256': SCRIPT_SHA256,
        'narrative_shots': 24,
        'title_cards': 1,
        'duration_seconds': 90,
        'executable_base_jobs': len(jobs),
        'targeted_repair_jobs': repair_count,
        'pending_derived_references': pending,
        'production_release_gates': [x['id'] for x in status.get('blockers', [])],
        'video_generated': status.get('video_generated', False),
        'audio_generated': status.get('audio_generated', False),
        'video_generated_field_scope': status.get('video_generated_field_scope'),
        'user_reported_external_video_generation': status.get('user_reported_external_video_generation', False),
        'received_user_video_files': status.get('received_user_video_files', False),
        'received_user_audio_files': status.get('received_user_audio_files', False),
        'github_synced': status.get('github', {}).get('synced', False),
    }


if __name__ == '__main__':
    try:
        result = validate()
    except (KeyError, TypeError, ValueError, OSError) as exc:
        result = {'integrity_pass': False, 'errors': [f'Invalid or incomplete production schema: {exc}']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(not result['integrity_pass'])
