#!/usr/bin/env python3
"""Export the fixed 60-second audio continuation; never guess singer cues."""
from pathlib import Path
import argparse,base64,copy,hashlib,html,json,re,shutil,tempfile,wave,zipfile

ROOT=Path(__file__).resolve().parents[1]
REL=ROOT/'releases/huibenji/chapter04_v1'
BASE=ROOT/'archive/chapter04_before_final_audio_v15'
ACTIVE=[f'H{i:02}' for i in range(4,10)]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def digest(b):return hashlib.sha256(b).hexdigest()
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s.rstrip()+'\n',encoding='utf8')
def js(p,v):write(p,json.dumps(v,ensure_ascii=False,indent=2))

def validate():
 t=read(REL/'timeline.json');old=read(BASE/'timeline.json');a=read(REL/'assets.json');audio=read(REL/'audio/contract.json');freeze=read(REL/'COMPLETED_BLOCKS_LOCK.json')
 assert t['blocks'][:3]==old['blocks'][:3]
 for b in t['blocks'][:3]:assert digest(json.dumps(b,ensure_ascii=False,sort_keys=True).encode())==freeze['blocks'][b['id']]
 for p,h in freeze['files'].items():assert digest((ROOT/p).read_bytes())==h,p
 assert audio['master_duration_seconds']==60 and audio['master_sha256']==digest((ROOT/audio['master_file']).read_bytes())
 assert audio['singer_alignment_verified'] is False and audio['listened_audio'] is False and audio['cues']==[]
 candidates=read(REL/'audio/CUE_REVIEW.json')['cues']
 assert all(c['singer'] is None and c['start'] is None and c['end'] is None for c in candidates)
 assert [b['duration'] for b in t['blocks'][3:]]==[30,30,12,18,14,24]
 assert [b['global_start'] for b in t['blocks'][3:]]==[90,120,150,162,180,194]
 assert t['blocks'][-1]['global_start']+t['blocks'][-1]['duration']==218
 assert [x['approx_degrees'] for x in t['blocks'][6]['pan_face_angle_schedule']]==[0,15,30,45,45]
 assert read(ROOT/'history/validation/CH04_v15_AUDIO_INTEGRITY.json')['concatenated_pcm_matches_full_decode']
 ident=read(REL/'IDENTITY_LOCK.json')
 for q in ident['identities']:assert digest((ROOT/q['master_file']).read_bytes())==q['master_sha256']
 for i,b in enumerate(t['blocks'][3:],3):
  assert b['id']==ACTIVE[i-3] and b['production_ready'] is False and b['actual_av_review'] is False
  p=(REL/'prompts'/f"{b['id']}.txt").read_text();assert p.rstrip()==b['prompt'] and len(p)<2000
  assert b['first_frame_file'] is None and b['last_frame_file'] is None
  assert b['first_frame_description']==t['blocks'][i-1]['last_frame_description']
  assert b['previous_reference']['source']==t['blocks'][i-1]['id'] and b['previous_reference']['file'] is None
  assert not any(k.startswith('KF_') or k=='C01_RUAN_HOLD' for k in b['image_reference_ids'])
  for k in b['image_reference_ids']:assert (ROOT/a['refs'][k]).is_file(),k
  if b['id'] in ['H04','H05']:
   assert b['shots']==[] and '未签发' in p and b['prompt_status']=='withheld_pending_real_singer_and_lyric_clock'
  else:
   assert 'PAN HUI IDENTITY LOCK' in p and '鼻宽鼻长鼻尖' in p and '不放大眼睛' in p
   end=0
   for s in b['shots']:assert s['start']==end and end<s['end'];end=s['end']
   assert end==b['duration']
   for k in map(int,re.findall(r'图(\d+)',p)):assert 1<=k<=len(b['image_reference_ids'])
 am=read(REL/'audio/UPLOAD_MAP.json')
 chunks=[]
 for bid in ['H04','H05']:
  assert len(am[bid])==1
  with wave.open(str(ROOT/a['refs'][am[bid][0]]),'rb') as w:
   assert w.getnframes()/w.getframerate()==30 and w.getframerate()==44100
   chunks.append(w.readframes(w.getnframes()))
  assert (ROOT/a['refs'][am[bid][0]]).stat().st_size<15*1024*1024
 # Decode original with FFmpeg and independently compare the PCM, not just a flag.
 import subprocess
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(ROOT/audio['master_file']),'-map','0:a:0','-f','s16le','-'])
 assert b''.join(chunks)==raw
 return t,a,audio,am

def audio_review_page(audio):
 data=read(REL/'audio/CUE_REVIEW.json')
 encoded=base64.b64encode((ROOT/audio['master_file']).read_bytes()).decode()
 payload=json.dumps(data,ensure_ascii=False).replace('</',r'<\/')
 return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>卜卦 · 最终60秒核听表</title><style>body{background:#f5f1e8;color:#252923;font:16px/1.65 system-ui;margin:0}main{max-width:1120px;margin:auto;padding:28px}h1{font-size:28px}aside{padding:15px;border-left:4px solid #a76a24;background:#ffebcd}audio{width:100%;position:sticky;top:0;background:#f5f1e8;padding:12px 0}table{border-collapse:collapse;width:100%;background:#fff}th,td{text-align:left;padding:12px;border-bottom:1px solid #ded8ca}thead{background:#e8e1d4}button,select,input{font:inherit;padding:7px;border:1px solid #afa590;background:#fff;border-radius:4px}input{width:65px}button{cursor:pointer}tbody tr.active{background:#fff2b9}small{color:#645e52}.scroll{overflow:auto}.tools{margin:16px 0}#stamp{font-variant-numeric:tabular-nums;font-weight:700}footer{margin:24px 0}</style><main><h1>《卜卦》完整60秒 · 核听定位表</h1><p>正式音轨已锁定为你提供的完整文件。播放、定位和填写不会改动音频。</p><aside>以下是识别与同版字幕交叉整理的候选，尚未核定实际演唱者和嘴型起止。两种识别的句尾最多出现1秒分歧，不能把小数位当精度。H04/H05正式演唱Prompt暂未签发。</aside><audio id="player" controls preload="metadata" src="data:audio/mpeg;base64,''' + encoded + '''"></audio><div class="tools"><span id="stamp">0.000 / 60.000秒</span>　<button id="playAll">从头完整播放</button>　<button id="save">导出本页核听标注</button></div><div class="scroll"><table><thead><tr><th>歌词候选</th><th>识别定位区间（秒）</th><th>定位播放</th><th>实际演唱者</th><th>核听起止</th></tr></thead><tbody id="rows"></tbody></table></div><footer>独唱时只让真实歌者做口型；合唱时双方严格依声部开合。孙全60秒持续弹奏。文件末端仍有伴奏，不擅自淡出或添加尾奏；60秒后进入放琴、静默和靠近。页面导出的是核听记录，不会自动把未核定项目标成通过。</footer></main><script>const data='''+payload+''';const player=document.getElementById('player'),rows=document.getElementById('rows');let stopAt=null;const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));data.cues.forEach((c,i)=>{let tr=document.createElement('tr');tr.innerHTML=`<td>${esc(c.lyrics_candidate)}</td><td><small>A ${c.asr_small_range.join('–')}<br>B ${c.asr_medium_range.join('–')}</small></td><td><button data-i="${i}">播放本句附近</button></td><td><select data-role="${i}"><option value="">未核定</option value="C01">孙亚龙</option><option value="C05">潘慧</option><option value="BOTH">二人合唱</option><option value="NONE">无演唱</option></select></td><td><input aria-label="第${i+1}句起点" data-start="${i}" type="number" min="0" max="60" step="0.01" placeholder="起点">–<input aria-label="第${i+1}句终点" data-end="${i}" type="number" min="0" max="60" step="0.01" placeholder="终点"></td>`;rows.appendChild(tr)});rows.onclick=e=>{const n=e.target.dataset.i;if(n!==undefined){const c=data.cues[+n];player.currentTime=c.review_window[0];stopAt=c.review_window[1];player.play().catch(()=>{});[...rows.children].forEach((r,i)=>r.classList.toggle('active',i===+n))}};player.ontimeupdate=()=>{document.getElementById('stamp').textContent=player.currentTime.toFixed(3)+' / 60.000秒';if(stopAt!==null&&player.currentTime>=stopAt){player.pause();stopAt=null}};document.getElementById('playAll').onclick=()=>{stopAt=null;player.currentTime=0;player.play().catch(()=>{})};document.getElementById('save').onclick=()=>{const copy=structuredClone(data);copy.status='user_review_export_requires_validation';copy.cues.forEach((c,i)=>{c.singer=rows.querySelector(`[data-role="${i}"]`).value||null;for(const k of ['start','end']){const v=rows.querySelector(`[data-${k}="${i}"]`).value;c[k]=v===''?null:Number(v)}c.singer_verified=false;c.lyrics_verified_by_listening=false});const url=URL.createObjectURL(new Blob([JSON.stringify(copy,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='CH04_final60_review_annotations.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};</script></html>'''

def build(out,selection=None):
 t,a,audio,am=validate();out.mkdir(parents=True,exist_ok=True);selected=selection or ACTIVE;assert set(selected)<=set(ACTIVE)
 manifest=[];results=[];ordered=['# 第四回 v1.5 · 每段独立文件','','H01/H02/H03冻结。演唱两包保留真实音频及待核听材料；H04/H05正式口型Prompt尚未签发，不能直接提交。歌后四包含可审阅Prompt。','']
 for b in t['blocks'][3:]:
  bid=b['id'];song=bid in ['H04','H05'];m={'revision':t['revision'],'id':bid,'name':b['name'],'duration_seconds':b['duration'],'global_start':b['global_start'],'song_range':b.get('song_range'),'prompt_status':b['prompt_status'],'production_ready':False,'images':[],'audio':[],'previous_video':b['previous_reference'],'actual_video_review':False}
  for kind,ids,folder in [('images',b['image_reference_ids'],'02_images'),('audio',am[bid],'03_audio')]:
   for n,k in enumerate(ids,1):
    src=ROOT/a['refs'][k];m[kind].append({'slot':n,'ref_id':k,'source_path':a['refs'][k],'bundle_path':f'{folder}/{n:02}_{k}{src.suffix}','sha256':digest(src.read_bytes()),'role':'identity_master' if k in ['C01','C05'] else 'exact_audio_slice' if kind=='audio' else 'environment_or_prop' if k in ['S15_NEW','P_RUAN'] else 'new_performance_candidate_not_identity_master','upload':True})
  promptname='01_PROMPT_NOT_READY.md' if song else '01_PROMPT.txt';m['prompt_bundle_path']=promptname
  write(REL/'scenes'/bid/'PROMPT.txt',b['prompt']);js(REL/'scenes'/bid/'INPUT_MANIFEST.json',m)
  intro=f"# {bid} · {b['name']} · v1.5\n\n时长{b['duration']}秒；全片计划起点{b['global_start']}秒。\n\n"+('**真实唱者/嘴型时钟待核，正式演唱Prompt尚未签发。**\n' if song else '**导演稿可审阅；新参考图非用户已批准，实际动态片及前片接点尚未验收。**\n')
  intro+=f'\n[Prompt状态或正文]({promptname}) · [分镜](02_TIMELINE.json) · [人物规则](PAN_HUI_IDENTITY_RULES.md)\n\n图片必须按以下顺序上传：\n\n'
  intro+='\n'.join(f"- 图{x['slot']}：[原图 {x['ref_id']}]({x['bundle_path']}) · {x['role']}" for x in m['images'])
  intro+='\n\n音频：\n\n'+('\n'.join(f"- 音频{x['slot']}：[本段连续30秒]({x['bundle_path']})；只上传此切片，不添加说话声线。" for x in m['audio']) if song else '不上传歌曲或说话样本；只保留松风、衣料、呼吸。')
  intro+=f"\n\n视频1：{b['previous_reference']['source']}真实末4秒，仅作连续性参考。新增成片不重复这4秒。实际前片文件未归档；H03由用户完成，不重做。多模态参考模式中规划图仅作构图参考，勿冒充真实首尾帧。\n\n开始：{b['first_frame_description']}\n\n结束：{b['last_frame_description']}\n"
  if song:intro+='\n最终音轨仍为完整原MP3，原文件放在reference_only目录，仅供最终合成与核听，不把60秒文件作为单条30秒音频投料。模型生成音频不替换用户正式原轨。\n'
  write(REL/'scenes'/bid/'README.md',f'# {bid} · v1.5\n\n{b["name"]}；{b["duration"]}秒。\n\n{b["prompt_status"]}。完整投料路径见本目录INPUT_MANIFEST.json；下载包内文件使用bundle_path，仓库使用source_path。\n\n[原Prompt/状态](PROMPT.txt)')
  ordered.append(f"- {bid}：{b['name']}，{b['duration']}秒；{b['prompt_status']}。")
  manifest.append(m)
  if bid not in selected:continue
  with tempfile.TemporaryDirectory(prefix='ch04_v15_') as tmp:
   bundle_prompt=b['prompt'].replace('audio/CUE_REVIEW.json','CUE_REVIEW.json')
   st=Path(tmp);write(st/'00_UPLOAD_ORDER.md',intro);write(st/promptname,bundle_prompt);js(st/'INPUT_MANIFEST.json',m);js(st/'02_TIMELINE.json',{'block':b,'actual_verified_audio_cues':[]})
   for row in m['images']+m['audio']:
    d=st/row['bundle_path'];d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/row['source_path'],d)
   ident=copy.deepcopy(read(REL/'IDENTITY_LOCK.json'));ident['identities']=[x for x in ident['identities'] if x['id'] in ['C01','C05']]
   for x in ident['identities']:x['bundle_master_file']=next(q['bundle_path'] for q in m['images'] if q['ref_id']==x['id'])
   js(st/'05_IDENTITY_LOCK.json',ident)
   for src,dst in [('PAN_HUI_IDENTITY_RULES.md','PAN_HUI_IDENTITY_RULES.md'),('IDENTITY_LOCK.md','05_REFERENCE_RULES.md'),('SEEDANCE_SPECS.md','08_SEEDANCE_SPECS.md'),('audio/BUGUA_SOURCE_REPORT.md','09_AUDIO_EVIDENCE.md'),('audio/BUGUA_SOURCE_REPORT.json','BUGUA_SOURCE_REPORT.json'),('audio/CUE_REVIEW.json','CUE_REVIEW.json')]:shutil.copyfile(REL/src,st/dst)
   js(st/'06_CONTINUITY.json',next(x for x in read(REL/'CONTINUITY.json')['blocks'] if x['id']==bid));js(st/'07_AUDIO_STATUS.json',audio)
   write(st/'04_previous_video/README.md',f"需要{b['previous_reference']['source']}真实末4秒；文件未归档，不用候选图假冒实际尾帧。H01–H03用户已经制作完成。")
   if song:
    (st/'reference_only').mkdir();shutil.copyfile(ROOT/audio['master_file'],st/'reference_only/FINAL60_ORIGINAL_DO_NOT_UPLOAD_AS_30S.mp3')
   else:write(st/'03_audio/README.md','本段无歌曲/声线输入；不再续唱或弹奏。')
   write(st/'10_PATHS_AND_STATUS.md','source_path、master_file、provenance_file为仓库溯源路径；解压包内使用bundle_path、bundle_master_file。H04/H05尚未签发口型Prompt，其他段为导演稿，全部尚无实际视频验收。')
   figures=''.join(f'<figure><img src="{x["bundle_path"]}" alt="{x["ref_id"]}"><figcaption>图{x["slot"]} · {x["ref_id"]}</figcaption></figure>' for x in m['images'])
   sounds=''.join(f'<audio controls src="{x["bundle_path"]}"></audio>' for x in m['audio'])
   page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{bid} v1.5</title><style>body{{font:16px/1.7 system-ui;background:#f1eee7;color:#292820;max-width:1150px;margin:auto;padding:24px}}.images{{display:flex;flex-wrap:wrap;gap:12px}}figure{{margin:0;width:240px}}img{{width:100%;height:240px;object-fit:contain;background:#ddd}}textarea{{width:100%;min-height:280px;font:15px/1.8 system-ui}}.status{{background:#ffe7c2;padding:15px}}</style><h1>{bid} · {b["name"]}</h1><p class="status">{html.escape(b["prompt_status"])} · {b["duration"]}秒 · 实际视频未验收</p><p><a href="00_UPLOAD_ORDER.md">投料说明</a> · <a href="{promptname}">Prompt正文或未签发状态</a> · <a href="09_AUDIO_EVIDENCE.md">音轨核验范围</a></p><textarea readonly>{html.escape(bundle_prompt)}</textarea><h2>图片顺序</h2><div class="images">{figures}</div><h2>本段音频</h2>{sounds or "仅环境声"}<p>图1、图2是唯一人物身份母版。新关键图只供构图与表演。</p></html>'
   write(st/'index.html',page)
   for row in m['images']+m['audio']:assert digest((st/row['bundle_path']).read_bytes())==row['sha256']
   for q in ident['identities']:assert digest((st/q['bundle_master_file']).read_bytes())==q['master_sha256']
   for linked in [ident['pan_hui_highest_priority_rule'],b['identity_rules'],audio['source_report'],audio['candidate_cues_file']]:assert (st/linked).is_file(),linked
   for doc in st.rglob('*.md'):
    for link in re.findall(r'!?\[[^\]\n]*\]\(([^\s)]+)\)',doc.read_text()):
     if re.match(r'^\w+:',link) or link.startswith('#'):continue
     assert (doc.parent/link).is_file(),(doc,link)
   for link in re.findall(r'(?:src|href)="([^"]+)"',page):assert (st/html.unescape(link)).is_file(),link
   dest=out/f'CH04_{bid}_v15.zip'
   with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(st.rglob('*')):
     if p.is_file():z.write(p,p.relative_to(st).as_posix())
   with zipfile.ZipFile(dest) as z:assert z.testzip() is None
   results.append({'id':bid,'file':str(dest),'bytes':dest.stat().st_size,'sha256':digest(dest.read_bytes()),'prompt_status':b['prompt_status'],'media_hashes_match':True,'local_links_valid':True})
 js(REL/'UPLOAD_ORDER.json',{'revision':t['revision'],'active_blocks':ACTIVE,'blocks':manifest});write(REL/'ORDERED_INPUTS.md','\n'.join(ordered));write(REL/'SCENE_FILES.md','\n'.join(ordered))
 write(out/'CH04_v15_AUDIO_REVIEW.html',audio_review_page(audio));shutil.copyfile(REL/'DIRECTOR_AND_PRODUCTION_PACK.md',out/'CH04_v15_DIRECTOR.md')
 with zipfile.ZipFile(out/'CH04_v15_NEW_REFERENCES.zip','w',zipfile.ZIP_DEFLATED) as z:
  for k in ['C01','C05','S15_NEW','P_RUAN']+[k for k in a['refs'] if k.startswith('V15_')]:z.write(ROOT/a['refs'][k],k+Path(a['refs'][k]).suffix)
  z.write(REL/'PAN_HUI_IDENTITY_RULES.md','PAN_HUI_IDENTITY_RULES.md');z.write(ROOT/'history/generation/CH04_v15_IMAGE_GENERATIONS.json','IMAGE_GENERATIONS.json')
 js(out/'BUILD_RECEIPT_v15.json',results)
 return {'frozen_blocks_unchanged':True,'full_audio_pcm_integrity':True,'actual_singer_verified':False,'song_prompts_withheld':True,'bundles':results}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--blocks',nargs='+',choices=ACTIVE);a=p.parse_args();out=a.out.resolve();assert not out.is_relative_to(ROOT)
 print(json.dumps(build(out,a.blocks),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
