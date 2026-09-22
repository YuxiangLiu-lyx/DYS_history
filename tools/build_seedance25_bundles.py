#!/usr/bin/env python3
"""Build reproducible, per-act upload ZIPs from current v4 references; no generation."""
from pathlib import Path
import argparse,hashlib,json,zipfile,re,posixpath
ROOT=Path(__file__).resolve().parents[1]
PROD=ROOT/'episodes/ep01/production'
def sha(data): return hashlib.sha256(data).hexdigest()
def build(out):
    out.mkdir(parents=True,exist_ok=True)
    refs=json.loads((PROD/'refs_upload.json').read_text())
    result=[]
    for job in refs['jobs']:
        jid=job.get('id',job.get('job'))
        if jid not in ('M01','M02','M03'): raise ValueError('Current v4 references required')
        rows=[]; contents={}
        for modality,key,folder in [('image','slots','images'),('audio','audio_slots','audio')]:
            for i,item in enumerate(job[key],1):
                path=ROOT/item['file']
                if not path.is_file(): raise FileNotFoundError(path)
                data=path.read_bytes(); entry=f'{folder}/{i:02d}__{path.name}'
                contents[entry]=data
                rows.append({'modality':modality,'slot':item['slot'],'bundle_file':entry,'repository_file':item['file'],'sha256':sha(data),'role':item.get('role')})
        prompt=(ROOT/job['prompt_file']).read_bytes()
        contents['PROMPT.txt']=prompt
        order=['# '+jid+' · 30秒上传包 v4','','按本表顺序分别上传图片和音频，再绑定界面实际标签并复制PROMPT.txt。只用本幕文件；原声只参考音色，不复述样本原话。','','| 标签 | 包内文件 | 用途 |','|---|---|---|']
        order += [f"| {x['slot']} | {x['bundle_file']} | {x['role']} |" for x in rows]
        order += ['','本包不含已生成视频、前幕实拍尾帧或已制作剧中对白。可选视频追加参考请在取得已采用原片后按生产包执行。原文件字节保持，文件名前序号仅为明确上传次序。','人物名、地名、字幕和片尾后期叠加；先验同期口型和声音，再统一配乐。','当前GitHub入口：https://github.com/YuxiangLiu-lyx/DYS_history','']
        contents['UPLOAD_ORDER.md']='\n'.join(order).encode()
        contents['INPUT_MANIFEST.json']=(json.dumps({'job':jid,'revision':'v4','source_duration_seconds':30,'references':rows,'prompt_sha256':sha(prompt),'generated_video_included':False},ensure_ascii=False,indent=2)+'\n').encode()
        for name in ['SEEDANCE_QUICKSTART.md','TIMING_CHANGES_v4.md','POSTPRODUCTION.md']:
            doc=(PROD/name).read_text()
            def remote_link(match):
                label,target=match.groups()
                if target.startswith(('https://','http://','#','mailto:')): return match.group(0)
                rel=posixpath.normpath('episodes/ep01/production/'+target)
                return '['+label+'](https://github.com/YuxiangLiu-lyx/DYS_history/blob/main/'+rel+')'
            contents[name]=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',remote_link,doc).encode()
        dest=out/f'EP01_{jid}_Seedance25_v4.zip'
        with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for name,data in contents.items():
                info=zipfile.ZipInfo(name,date_time=(2026,9,22,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
        with zipfile.ZipFile(dest) as z:
            assert z.testzip() is None
            assert len(z.namelist())==len(contents)
            for row in rows: assert sha(z.read(row['bundle_file']))==row['sha256']
        result.append({'job':jid,'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest.read_bytes()),'images':len(job['slots']),'audio':len(job['audio_slots']),'verified':True})
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();build(args.out.resolve())
