#!/usr/bin/env python3
"""Validate and export the current CH04 revision as standalone scene ZIPs.

No media generation. A missing song remains a missing song; measured time cannot
be substituted with the previous release's director budget.
"""
from pathlib import Path
import argparse, copy, hashlib, html, json, os, re, shutil, tempfile, wave, zipfile

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'releases/huibenji/chapter04_v1'
BASE=ROOT/'archive/chapter04_before_identity_detail_v14'
IDS=[f'H{i:02}' for i in range(1,8)]
ACTIVE_IDS=IDS[2:]

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(data):return hashlib.sha256(data).hexdigest()
def write(path,text):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text.rstrip()+'\n',encoding='utf-8')
def js(path,data):write(path,json.dumps(data,ensure_ascii=False,indent=2))
def relative(origin,target):return Path(os.path.relpath(target,origin.parent)).as_posix()

def validate():
 t=read(RELEASE/'timeline.json');a=read(RELEASE/'assets.json');am=read(RELEASE/'audio/UPLOAD_MAP.json');c=read(RELEASE/'audio/contract.json');old=read(BASE/'timeline.json');blocks=t['blocks'];spec=read(RELEASE/'SEEDANCE_SPECS.json')
 assert [b['id'] for b in blocks]==IDS
 assert t['duration_seconds'] is None and t['duration_range_seconds']==[150,160]
 assert [b['duration'] for b in blocks]==[30,30,30,None,10,12,18]
 assert [b['global_start'] for b in blocks]==[0,30,60,90,None,None,None]
 assert [b['global_start_expression'] for b in blocks]==['0','30','60','90','90 + D_H04','100 + D_H04','112 + D_H04']
 for i in range(3):assert blocks[i]['dialogues']==old['blocks'][i]['dialogues'],f'Locked dialogue or timing changed: {IDS[i]}'
 freeze=read(RELEASE/'COMPLETED_BLOCKS_LOCK.json')
 for i in range(2):
  assert blocks[i]==old['blocks'][i],f'Completed block changed: {IDS[i]}'
  assert digest(json.dumps(blocks[i],ensure_ascii=False,sort_keys=True).encode())==freeze['blocks'][IDS[i]]
 for source,expected in freeze['files'].items():assert digest((ROOT/source).read_bytes())==expected,source
 assert blocks[2]['shots'][:2]==freeze['H03_locked_shots_before_20s']
 assert blocks[2]['shots'][2]['start']==20 and blocks[2]['shots'][2]['end']==24
 assert blocks[2]['shots'][3]['start']==24
 assert blocks[2]['image_reference_ids'][:6]==['C01','C03','S14','S15_NEW','P_RUAN','C05']
 assert [q['approx_degrees'] for q in blocks[5]['pan_face_angle_schedule']]==[0,15,30,45,45]
 assert '约45°' in blocks[6]['first_frame_description']
 assert all('KF_PREKISS' not in b['image_reference_ids'] and 'KF_C05_TURN' not in b['image_reference_ids'] for b in blocks[2:])
 for b in blocks[2:]:
  assert 'PAN HUI IDENTITY LOCK' in b['prompt'] and '不放大眼睛' in b['prompt']
  assert '鼻宽鼻长鼻尖' in b['prompt'] and '下颌和下巴长度与脸宽比例' in b['prompt']
 assert blocks[0]['image_reference_ids'][:6]==['C05','E06','S06','D01','D02','D03']
 assert blocks[0]['dream_image_slots']==old['blocks'][0]['dream_image_slots']
 assert a['dreams']['order']==['D01','D02','D03']
 for ref in ['D01','D02','D03']:
  assert a['refs'][ref]==read(BASE/'assets.json')['refs'][ref]
  # Baseline remains in Git and must have the identical source bytes.
  import subprocess
  before=subprocess.check_output(['git','show','be62579e016b31d7f0ba1e8d62f3ec9a3527a000:'+a['refs'][ref]],cwd=ROOT)
  assert digest(before)==digest((ROOT/a['refs'][ref]).read_bytes()),f'Dream image changed: {ref}'
 assert c['master_file'] is None and c['cues']==[]
 assert c['listened_audio'] is False and c['singer_alignment_verified'] is False
 assert am['H04']==['SONG_DUET_MASTER_PENDING']
 assert all(am[x]==[] for x in ['H05','H06','H07'])
 assert '禁止提交' in blocks[3]['prompt'] and blocks[3]['shots']==[]
 assert all(x['time'] is None and x['singer'] is None and x['lyrics'] is None for x in blocks[3]['events'])
 identities=read(RELEASE/'IDENTITY_LOCK.json')['identities']
 for q in identities:assert digest((ROOT/q['master_file']).read_bytes())==q['master_sha256']
 manifests=[]
 for i,b in enumerate(blocks):
  bid=b['id'];p=(RELEASE/'prompts'/f'{bid}.txt').read_text()
  assert p.rstrip('\n')==b['prompt']
  assert 0<len(p)<2000
  assert b['production_ready'] is False and b['actual_av_review'] is False
  assert b['first_frame_file'] is None and b['last_frame_file'] is None
  prev=b['previous_reference'];assert prev.get('source')==(IDS[i-1] if i else None)
  assert prev.get('file') is None
  if prev.get('range') is not None:
   x,y=prev['range'];assert 0<=x<y<=blocks[i-1]['duration'] and y-x==4
  if b['duration'] is not None:
   end=0
   for s in b['shots']:assert s['start']==end and end<s['end']<=b['duration'];end=s['end']
   assert end==b['duration']
  if i>=4:assert b['first_frame_description']==blocks[i-1]['last_frame_description'],f'{bid} boundary state mismatch'
  m={'id':bid,'name':b['name'],'duration_seconds':b['duration'],'target_duration_range':b['target_duration_range'],'film_start_seconds':b['global_start'],'global_start_expression':b['global_start_expression'],'time_domain':b['time_domain'],'prompt_status':b['prompt_status'],'production_ready':False,'prompt_characters':len(p),'prompt_sha256':digest(p.encode()),'prompt_bundle_path':'01_PROMPT.txt','images':[],'audio':[],'previous_video':prev,'first_frame_description':b['first_frame_description'],'last_frame_description':b['last_frame_description'],'planning_frames_are_actual_video_frames':False,'identity_lock':'05_IDENTITY_LOCK.json','continuity':'06_CONTINUITY.json','audio_status':'07_AUDIO_STATUS.json'}
  for kind,refids,folder in [('images',b['image_reference_ids'],'02_images'),('audio',am[bid],'03_audio')]:
   assert len(refids)==len(set(refids))
   for n,ref in enumerate(refids,1):
    src=a['refs'].get(ref);available=src is not None
    if available:assert (ROOT/src).is_file(),src
    suffix=Path(src).suffix if available else '_MISSING.md'
    row={'slot':n,'ref_id':ref,'available':available,'upload_this_file':available,'source_path':src,'bundle_path':f'{folder}/{n:02}_{ref}{suffix}','sha256':digest((ROOT/src).read_bytes()) if available else None,'bytes':(ROOT/src).stat().st_size if available else None}
    if kind=='images':
     row['role']='identity_master' if ref in ['C01','C05','C03'] else 'pose_and_composition_only' if ref.startswith('KF_') or ref=='C01_RUAN_HOLD' else 'source_image'
     row['actual_video_frame']=False
     row['review_status']=a.get('review_status',{}).get(ref,'existing_reference')
    if kind=='audio':
     seconds=None
     if available:
      with wave.open(str(ROOT/src),'rb') as f:seconds=f.getnframes()/f.getframerate()
      assert 2<=seconds<=30 and row['bytes']<=15*1024*1024
     row.update(duration_seconds=seconds,maximum_seconds=30 if not available else seconds)
    m[kind].append(row)
  assert len(m['images'])<=spec['max_images'] and len(m['audio'])<=spec['max_audios']
  assert len(m['images'])+len(m['audio'])+(1 if i else 0)<=spec['max_references_total']
  assert sum(r['maximum_seconds'] for r in m['audio'])<=30
  # Every numbered reference used by a prompt must exist in its local mapping.
  for n in map(int,re.findall(r'图(\d+)',p)):assert 1<=n<=len(m['images']),(bid,n)
  m['missing_reference_ids']=[r['ref_id'] for r in m['images']+m['audio'] if not r['available']]
  if bid in ['H01','H02']:
   m=read(RELEASE/'scenes'/bid/'INPUT_MANIFEST.json')
   manifests.append(m)
   continue
  m['gate']='actual song, singer and lyric timecodes required' if bid=='H04' else 'requires actual previous video and moving-shot QA' if i else 'static reference review complete; real video and AV QA not performed'
  manifests.append(m)
 return {'schema':'ch04_scene_inputs_v14','completed_blocks_user_reported':['H01','H02'],'active_blocks':ACTIVE_IDS,'title':t['title'],'revision':t['revision'],'production_ready':False,'duration_seconds':None,'duration_range_seconds':t['duration_range_seconds'],'blocks':manifests,'validation':{'locked_H01_H03_dialogues_unchanged':True,'H01_H02_complete_blocks_and_files_unchanged':True,'H03_dialogue_and_20_24_transition_preserved':True,'PanHui_detail_lock_and_angle_progression_present':True,'dream_order_windows_and_bytes_unchanged':True,'no_fabricated_song_or_timecodes':True,'references_exist_and_numbered':True,'all_prompts_under_2000_characters':True,'actual_video_QA_performed':False}}

def previous_text(m):
 p=m['previous_video']
 if not p.get('source'):return '本回开场，不上传上一回视频。'
 if p['source']=='H02':return '视频1：用户已完成H02的真实末4秒；本仓库尚未收到视频文件。'+p['instruction']+' 不重做H02，不用规划图假冒实际尾帧。'
 return f"视频1：{p['source']}的实际末4秒（当前尚未生成/归档）。{p['instruction']} 规划图不能当实际输出帧。"

def duration_text(m):
 return f"{m['duration_seconds']}秒" if m['duration_seconds'] is not None else '目标20–30秒，待真实音频定长'

def scene_md(m,prompt,path,target):
 lines=[f"# {m['id']} · {m['name']} · v1.4",'',f"本场{duration_text(m)}；全片起点：{m['global_start_expression']}。D_H04未定。",'',f"**状态：{('歌曲母带与逐句唱者/时码未通过，Prompt禁止直接提交。' if m['id']=='H04' else '导演准备稿；实际前片和动态音画验收未完成。')}**",'','先复制本场TXT，再按图片、音频、视频编号投料。缺项MD不是媒体，不上传，不用其他文件顶替。','','## Prompt','',f"{m['prompt_characters']}字符，含换行。",'','```text',prompt.rstrip(),'```','','## 图片顺序','']
 for r in m['images']:
  link=relative(path,target(r));lines.extend([f"### 图{r['slot']} · {r['ref_id']}",'',f"![{r['ref_id']}]({link})",'',f"[原文件]({link}) · {r['role']}",''])
 lines.extend(['## 音频顺序',''])
 for r in m['audio']:
  lines.append(f"- 音频{r['slot']}：[{r['ref_id']}]({relative(path,target(r))})，{r['duration_seconds']:g}秒，仅供原有对白声线。" if r['available'] else f"- 音频{r['slot']}：{r['ref_id']}，未取得合格歌曲。槽位保留，禁止提交H04。")
 if not m['audio']:lines.append('不上传独立歌曲或声线；仅自然环境、衣料与呼吸。')
 if m['id']=='H04':lines.append('本路线只用一条最终真实母带≤30秒，不叠加4秒说话声样；歌词、实际唱者、逐句秒点未填。')
 lines.extend(['','## 连续状态','',previous_text(m),'',f"- 开场：{m['first_frame_description']}",f"- 结束：{m['last_frame_description']}",'','多模态参考模式：图中初末态只是软构图约束，不与严格first_frame/last_frame API模式混投。'])
 return '\n'.join(lines)

def html_page(m,prompt):
 esc=html.escape
 figures=''.join(f'<figure><a href="{esc(r["bundle_path"],quote=True)}"><img src="{esc(r["bundle_path"],quote=True)}" alt="{esc(r["ref_id"])}"></a><figcaption>图{r["slot"]} · {esc(r["ref_id"])}</figcaption></figure>' for r in m['images'])
 sounds=''.join(f'<p>音频{r["slot"]} · {esc(r["ref_id"])}</p><audio controls src="{esc(r["bundle_path"],quote=True)}"></audio>' if r['available'] else '<p class="alert">音频1：最终真实对唱未通过。没有可上传WAV。</p>' for r in m['audio']) or '<p>无独立歌曲或声线输入。只保留自然风、衣料与呼吸。</p>'
 warning='歌曲母带、歌词、实际唱者和逐句秒点未锁，禁止直接提交此Prompt。' if m['id']=='H04' else '当前为制作准备包；规划图非真实视频帧，实片音画验收未完成。'
 return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{m['id']} · 第四回v1.4</title><style>body{{margin:0;background:#f2eee7;color:#292723;font:16px/1.65 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:28px}}section{{background:#fff;padding:24px;margin:18px 0;border-radius:10px}}h1{{font-size:28px}}h2{{font-size:21px}}a{{color:#72502d}}.alert{{border-left:4px solid #b47527;padding:12px;background:#fff0dc}}textarea{{box-sizing:border-box;width:100%;min-height:310px;font:15px/1.8 monospace;padding:14px;border:1px solid #cdc2b2}}.images{{display:flex;gap:12px;flex-wrap:wrap}}figure{{margin:0;width:185px;padding:8px;border:1px solid #ddd}}img{{width:100%;height:185px;object-fit:contain;background:#202020}}figcaption{{font-size:13px;overflow-wrap:anywhere}}audio{{max-width:100%;width:420px}}button{{padding:9px 18px;cursor:pointer}}nav{{display:flex;gap:16px;flex-wrap:wrap}}@media(max-width:600px){{main{{padding:14px}}section{{padding:14px}}figure{{width:calc(50% - 26px)}}}}</style></head><body><main><h1>第四回 · {m['id']} {esc(m['name'])}</h1><p>v1.4 · {duration_text(m)} · 全片起点 {esc(m['global_start_expression'])}</p><p class="alert">{warning}</p><nav><a href="00_UPLOAD_ORDER.md">投料说明</a><a href="INPUT_MANIFEST.json">素材清单</a><a href="02_TIMELINE.json">本场分镜</a><a href="05_REFERENCE_RULES.md">身份规则</a><a href="08_SEEDANCE_SPECS.md">规格</a><a href="09_SOURCE_REPORT.md">歌曲状态</a></nav><section><h2>1 · Prompt</h2><p>{m['prompt_characters']}字符（含换行） · <a href="01_PROMPT.txt">打开TXT</a></p><button id="copy">复制Prompt</button><span id="feedback" aria-live="polite"></span><textarea id="prompt" readonly>{esc(prompt)}</textarea></section><section><h2>2 · 图片顺序</h2><div class="images">{figures}</div></section><section><h2>3 · 音频顺序</h2>{sounds}</section><section><h2>4 · 前片与连续性</h2><p>{esc(previous_text(m))}</p><p>开场：{esc(m['first_frame_description'])}</p><p>结束：{esc(m['last_frame_description'])}</p></section></main><script>document.getElementById('copy').onclick=async()=>{{const p=document.getElementById('prompt'),f=document.getElementById('feedback');try{{if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(p.value);else{{p.focus();p.select();if(!document.execCommand('copy'))throw Error();}}f.textContent=' 已复制';}}catch(e){{p.focus();p.select();f.textContent=' 已选中，请手动复制';}}}};</script></body></html>'''

def validate_tree(stage,m):
 for r in m['images']+m['audio']:
  p=stage/r['bundle_path'];assert p.is_file()
  if r['available']:assert digest(p.read_bytes())==r['sha256']
  else:assert p.suffix=='.md' and not r['upload_this_file']
 for doc in stage.rglob('*.md'):
  for target in re.findall(r'!?\[[^\]\n]*\]\(([^\s)]+)\)',doc.read_text()):
   if re.match(r'^[a-zA-Z][a-zA-Z+.-]*:',target) or target.startswith('#'):continue
   assert (doc.parent/target.split('#')[0]).resolve().is_file(),(doc,target)
 for target in re.findall(r'(?:src|href)="([^"]+)"',(stage/'index.html').read_text()):
  if target.startswith('#') or re.match(r'^\w+:',target):continue
  assert (stage/html.unescape(target)).is_file(),target
 for q in read(stage/'05_IDENTITY_LOCK.json')['identities']:
  assert digest((stage/q['bundle_master_file']).read_bytes())==q['master_sha256']
 assert (stage/read(stage/'05_IDENTITY_LOCK.json')['pan_hui_highest_priority_rule']).is_file()
 assert (stage/read(stage/'02_TIMELINE.json')['block']['identity_rules']).is_file()

def build(out,selection=None,docs_only=False):
 manifest=validate();selected=set(selection or ACTIVE_IDS);assert selected<=set(ACTIVE_IDS),'H01/H02 are completed and frozen'
 js(RELEASE/'UPLOAD_ORDER.json',manifest)
 ordered=['# 第四回逐场投料册 · v1.4','','H01/H02已由用户完成，内容冻结，保留原文件，不重新生产。本轮从H03继续，只交H03–H07五个更新包。H03对白不改，20–24秒沿用户转场，24秒起新巨松草坡。H04实曲仍未定，H06先正脸→15°→30°→45°，H07继承45°停顿后再吻。','','每场独立ZIP自含全部已有素材。新图是候选，不是视频；音频缺项是说明，不能上传。','']
 for m in manifest['blocks']:
  if m['id'] in ['H01','H02']:
   ordered.extend([f"## {m['id']} 已完成，冻结",'',f"用户已完成，不改不重做。[原制作记录](scenes/{m['id']}/README.md)仅供追溯；其中未收视频/未验收字段指本仓库接收范围。",''])
   continue
  prompt=(RELEASE/'prompts'/f"{m['id']}.txt").read_text();sc=RELEASE/'scenes'/m['id']
  write(sc/'PROMPT.txt',prompt);js(sc/'INPUT_MANIFEST.json',m)
  write(sc/'README.md',scene_md(m,prompt,sc/'README.md',lambda r:ROOT/r['source_path']))
  ordered.extend([scene_md(m,prompt,RELEASE/'ORDERED_INPUTS.md',lambda r:ROOT/r['source_path']),'','---',''])
 write(RELEASE/'ORDERED_INPUTS.md','\n'.join(ordered))
 results=[]
 if not docs_only:
  out.mkdir(parents=True,exist_ok=True)
  timeline=read(RELEASE/'timeline.json');ident=read(RELEASE/'IDENTITY_LOCK.json');continuity=read(RELEASE/'CONTINUITY.json');contract=read(RELEASE/'audio/contract.json')
  for m in manifest['blocks']:
   if m['id'] not in selected:continue
   with tempfile.TemporaryDirectory(prefix='ch04_v14_') as tmp:
    stage=Path(tmp);prompt=(RELEASE/'prompts'/f"{m['id']}.txt").read_text()
    write(stage/'01_PROMPT.txt',prompt);js(stage/'INPUT_MANIFEST.json',m)
    for r in m['images']+m['audio']:
     dst=stage/r['bundle_path'];dst.parent.mkdir(parents=True,exist_ok=True)
     if r['available']:shutil.copyfile(ROOT/r['source_path'],dst)
     else:write(dst,'# 音频1尚未通过\n\n这不是媒体。未取得合格真实孙潘对唱母带、歌词、演唱者和逐句秒点；H04不可提交。不得拿说话样本顶替，不能从旧Live估算时码。')
    if not m['audio']:write(stage/'03_audio/README.md','本场不上传独立歌曲或声线。只有自然风声、衣料与呼吸。此文件不是音频。')
    write(stage/'00_UPLOAD_ORDER.md',scene_md(m,prompt,stage/'00_UPLOAD_ORDER.md',lambda r:stage/r['bundle_path']))
    block=next(b for b in timeline['blocks'] if b['id']==m['id'])
    js(stage/'02_TIMELINE.json',{'block':block,'actual_music_cues':[],'time_domain':block['time_domain']})
    write(stage/'04_previous_video/README.md',previous_text(m))
    localident=copy.deepcopy(ident);byid={r['ref_id']:r for r in m['images']}
    localident['identities']=[q for q in localident['identities'] if q['id'] in byid]
    for q in localident['identities']:q['bundle_master_file']=byid[q['id']]['bundle_path']
    js(stage/'05_IDENTITY_LOCK.json',localident)
    shutil.copyfile(RELEASE/'IDENTITY_LOCK.md',stage/'05_REFERENCE_RULES.md')
    shutil.copyfile(RELEASE/'PAN_HUI_IDENTITY_RULES.md',stage/'PAN_HUI_IDENTITY_RULES.md')
    js(stage/'06_CONTINUITY.json',{'world_axis':continuity['world_axis'],'prop_lock':continuity['prop_lock'],'block':next(x for x in continuity['blocks'] if x['id']==m['id'])})
    js(stage/'07_AUDIO_STATUS.json',contract)
    shutil.copyfile(RELEASE/'SEEDANCE_SPECS.md',stage/'08_SEEDANCE_SPECS.md')
    shutil.copyfile(RELEASE/'audio/BUGUA_SOURCE_REPORT.md',stage/'09_SOURCE_REPORT.md')
    shutil.copyfile(RELEASE/'audio/BUGUA_SOURCE_REPORT.json',stage/'BUGUA_SOURCE_REPORT.json')
    write(stage/'10_PATHS_AND_STATUS.md','# 路径与状态\n\nJSON的source_path、master_file、provenance_file是原仓库溯源路径。解压包内应使用bundle_path、bundle_master_file。规划图的原文件名保留历史编号，本版以场次清单为准。原始第三方研究视频未授权为制作母带，不在本包。\n\nH01/H02已由用户完成，保持原内容；本库尚未收到/观看这两段片。H03–H07尚无本轮动态视频验收，H04母带仍明确阻塞。本包为后续制作准备材料。')
    write(stage/'index.html',html_page(m,prompt));validate_tree(stage,m)
    dest=out/f"CH04_{m['id']}_v14.zip"
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
     for p in sorted(x for x in stage.rglob('*') if x.is_file()):
      info=zipfile.ZipInfo(p.relative_to(stage).as_posix(),(2026,9,25,0,0,0));info.external_attr=0o644<<16
      z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(dest) as z:assert z.testzip() is None;assert digest(z.read('01_PROMPT.txt'))==m['prompt_sha256']
    results.append({'id':m['id'],'name':m['name'],'file_name':dest.name,'local_path':str(dest),'bytes':dest.stat().st_size,'sha256':digest(dest.read_bytes()),'standalone_links_valid':True,'media_hashes_match':True,'prompt_characters':m['prompt_characters'],'missing_reference_ids':m['missing_reference_ids'],'production_ready':False})
  js(out/'BUILD_RECEIPT_v14.json',results)
 return {'validation':manifest['validation'],'bundles':results,'production_ready':False}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--blocks',nargs='+',choices=ACTIVE_IDS);p.add_argument('--docs-only',action='store_true');args=p.parse_args()
 out=args.out.resolve();assert not out.is_relative_to(ROOT),'Use a delivery folder outside Git repository'
 print(json.dumps(build(out,args.blocks,args.docs_only),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
