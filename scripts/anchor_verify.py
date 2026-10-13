#!/usr/bin/env python3
"""Independent evidence gate. Does not import renderer/planner/schema code.

Exact normalized quote matching is evidence location, NOT semantic entailment.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata

def canonical_digest(spec):
    def clean(node):
        if isinstance(node,dict): return {k:clean(v) for k,v in node.items() if k not in ('verification','verified','verification_status')}
        if isinstance(node,list): return [clean(v) for v in node]
        return node
    return hashlib.sha256(json.dumps(clean(spec),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def normalized(text):
    return ''.join(unicodedata.normalize('NFKC',text).split())

def locate(quote,text):
    q=normalized(quote); corpus=normalized(text)
    if len(q)<4: return False,'锚点少于 4 个非空白字符'
    positions=[]; pos=corpus.find(q)
    while pos>=0:
        positions.append(pos); pos=corpus.find(q,pos+1)
    if not positions: return False,'未在指定源片段中找到锚点'
    negatives=('没','未','无','不','并非','不是','不能','never','not','without','no')
    if all(any(corpus[max(0,pos-12):pos].lower().endswith(n) for n in negatives) for pos in positions):
        return False,'疑似削去左邻否定词；请扩大引句'
    return True,'已定位原文'

def extract(path):
    path=Path(path); raw=path.read_bytes()
    if path.suffix.lower()=='.pdf':
        try: from pypdf import PdfReader
        except ImportError as exc: raise ValueError('PDF 需要可选依赖 pypdf') from exc
        reader=PdfReader(path)
        if reader.is_encrypted: raise ValueError('PDF 已加密')
        text='\n\n'.join(page.extract_text() or '' for page in reader.pages)
    else:
        text=raw.decode('utf-8-sig')
        if '\x00' in text: raise ValueError('源文本含二进制空字符')
    if not text.strip(): raise ValueError('源材料为空、损坏或没有可提取文本')
    return text,hashlib.sha256(raw).hexdigest()

def scopes(text):
    chunks={}; current=[]; lines=text.splitlines(); start=0
    for i,line in enumerate(lines+['']):
        if line.strip():
            if not current: start=i
            current.append(line)
        elif current:
            chunks[f'P{len(chunks)+1:04}']=('\n'.join(current),start+1,i)
            current=[]
    return lines,chunks

def evaluate(spec,text,source_error=None):
    items=[]; lines,blocks=scopes(text); source_map={}; malformed=False
    sources=spec.get('sources',[]); frames=spec.get('frames',[])
    if not isinstance(sources,list) or not isinstance(frames,list): sources=[]; frames=[]; malformed=True
    for i,source in enumerate(sources):
        ok=False; reason='来源结构错误'
        if isinstance(source,dict):
            sid=source.get('id'); scope=text; reason='源材料不可读' if source_error else ''
            try:
                if not isinstance(sid,str) or not re.fullmatch(r'S\d+',sid) or sid in source_map: raise ValueError('来源 ID 非法或重复')
                if 'paragraph_id' in source:
                    if source['paragraph_id'] not in blocks: raise ValueError('段落 ID 不存在')
                    scope=blocks[source['paragraph_id']][0]
                if 'line_start' in source or 'line_end' in source:
                    a,b=source.get('line_start'),source.get('line_end')
                    if type(a) is not int or type(b) is not int or not 1<=a<=b<=len(lines): raise ValueError('来源行号非法')
                    line_scope='\n'.join(lines[a-1:b])
                    if 'paragraph_id' in source and (a,b)!=blocks[source['paragraph_id']][1:]: raise ValueError('行号与段落不一致')
                    scope=line_scope
                if not isinstance(source.get('text'),str): raise ValueError('来源引句不是文本')
                if not source_error: ok,reason=locate(source['text'],scope)
            except (ValueError,TypeError) as exc: reason=str(exc)
            source_map[sid]=(source,ok)
        items.append({'kind':'source','index':i,'status':'verified' if ok else 'failed','reason':reason})
    for fi,frame in enumerate(frames):
        claims=frame.get('claims',[]) if isinstance(frame,dict) else []
        if not isinstance(claims,list): claims=[]; malformed=True
        if not claims: malformed=True
        for ci,claim in enumerate(claims):
            ok=False; status='failed'; reason='断言结构错误'
            if isinstance(claim,dict):
                if claim.get('ai_only') is True and not claim.get('anchor') and not claim.get('source_id') and isinstance(claim.get('text'),str) and claim['text'].strip():
                    status='ai_only'; reason='AI 补充，无来源；仍计入覆盖率分母'
                else:
                    anchor=claim.get('anchor'); src=source_map.get(claim.get('source_id'))
                    if source_error: reason='源材料不可读'
                    elif not isinstance(claim.get('text'),str) or not claim['text'].strip(): reason='断言正文为空'
                    elif not isinstance(anchor,str) or not anchor.strip(): reason='断言缺少锚点'
                    elif not src or not src[1]: reason='断言引用的来源未通过核验'
                    else:
                        ok,reason=locate(anchor,src[0]['text'])
                        if ok: ok,reason=locate(anchor,text)
                    if ok: status='verified'
            items.append({'kind':'claim','frame':fi,'index':ci,'status':status,'reason':reason})
    total=len(items); verified=sum(i['status']=='verified' for i in items)
    failed=sum(i['status']=='failed' for i in items); ai=sum(i['status']=='ai_only' for i in items)
    coverage=verified/total if total else 0.0
    gates={'source_readable':not source_error and bool(text.strip()),'at_least_one':verified>0,
           'coverage_90':coverage>=0.9,'zero_failed':failed==0 and not malformed and bool(frames) and bool(sources)}
    return {'passed':all(gates.values()),'coverage':coverage,'total':total,'verified':verified,
            'ai_only':ai,'failed':failed,'gates':gates,'items':items,'source_error':source_error}

def write_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream: json.dump(value,stream,ensure_ascii=False,indent=2); stream.write('\n')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('spec'); p.add_argument('source')
    p.add_argument('--log',nargs='?',const=True); p.add_argument('--write-back',action='store_true'); args=p.parse_args()
    try:
        spec=json.loads(Path(args.spec).read_text(encoding='utf-8-sig'))
        if not isinstance(spec,dict): raise ValueError('spec 顶层必须为对象')
        error=None; digest=None; text=''
        try: text,digest=extract(args.source)
        except Exception as exc: error=str(exc)
        result=evaluate(spec,text,error)
        result.update({'topic':spec.get('topic',''),'timestamp':datetime.now(timezone.utc).isoformat(),
                       'source_sha256':digest,'source_path':str(Path(args.source).resolve()),'spec_sha256':canonical_digest(spec)})
        if args.write_back:
            for item in result['items']:
                node=spec['sources'][item['index']] if item['kind']=='source' else spec['frames'][item['frame']]['claims'][item['index']]
                if isinstance(node,dict): node['verified']=item['status']=='verified'; node['verification_status']=item['status']
            spec['verification']=result; write_json(args.spec,spec)
        if args.log:
            log=Path(args.spec).with_suffix('.verification.jsonl') if args.log is True else Path(args.log)
            log.parent.mkdir(parents=True,exist_ok=True)
            with log.open('a',encoding='utf-8') as stream: stream.write(json.dumps(result,ensure_ascii=False)+'\n')
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['passed'] else 10
    except Exception as exc:
        print(json.dumps({'passed':False,'coverage':0.0,'error':str(exc)},ensure_ascii=False)); return 10

if __name__=='__main__': sys.exit(main())

