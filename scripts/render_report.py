#!/usr/bin/env python3
"""Render a validated spec into a self-contained HTML; unverified drafts remain visibly marked."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import sys
from common import ROOT, load_json, save_text, validate_spec

def spec_digest(spec):
    # Intentionally separate from the evidence verifier's implementation.
    def stripped(value):
        if isinstance(value,list): return [stripped(item) for item in value]
        if isinstance(value,dict): return {key:stripped(item) for key,item in value.items() if key not in {'verification','verified','verification_status'}}
        return value
    canonical=json.dumps(stripped(spec),sort_keys=True,ensure_ascii=False,separators=(',',':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

def inline(text):
    parts=[]; cursor=0
    for match in re.finditer(r'\*\*([^\n]+?)\*\*|`([^`\n]+)`|\{(S[1-9][0-9]*)\}',text):
        parts.append(html.escape(text[cursor:match.start()]))
        if match[1] is not None: parts.append('<strong>'+html.escape(match[1])+'</strong>')
        elif match[2] is not None: parts.append('<code>'+html.escape(match[2])+'</code>')
        else: parts.append(f'<a class="anchor" href="#{match[3]}" aria-label="查看来源 {match[3]}">{match[3]}</a>')
        cursor=match.end()
    parts.append(html.escape(text[cursor:])); return ''.join(parts).replace('\n','<br>')

def build(spec,static=False):
    digest=spec_digest(spec); v=spec.get('verification',{})
    current=v.get('passed') is True and v.get('spec_sha256')==digest
    if current:
        try:
            current=hashlib.sha256(Path(v['source_path']).read_bytes()).hexdigest()==v.get('source_sha256')
        except (KeyError,OSError,TypeError):
            current=False
    # Per-item flags only count when the complete content stamp is current.
    count=sum(len(f['claims']) for f in spec['frames'])+len(spec['sources'])
    current=current and v.get('total')==count and v.get('failed')==0 and v.get('coverage',0)>=.9
    status=('已通过锚点核验 · 覆盖率 '+f"{v.get('coverage',0):.1%}") if current else '未核验或内容已变更 · 草稿请勿交付'
    frames=[]; nav=[]; marks=[]
    for i,f in enumerate(spec['frames'],1):
        fid=f['id']; nav.append(f'<a href="#{fid}"><span>{fid}</span> {html.escape(f["title"])}</a>')
        claims=[]
        for c in f['claims']:
            ai=c.get('ai_only') is True; verified=current and c.get('verified') is True
            cls='ai-only' if ai else 'verified' if verified else 'unverified'
            badge='AI 补充，无来源' if ai else '来源已定位' if verified else '未核验断言'
            evidence='' if ai else '<div class="quote">来源片段：'+inline(c['anchor'])+f' <a class="anchor" href="#{c["source_id"]}">{c["source_id"]}</a></div>'
            claims.append(f'<li class="claim {cls}"><span class="badge">{badge}</span><p>{inline(c["text"])}</p>{evidence}</li>')
        frames.append(f'''<article class="frame" id="{fid}"><details open><summary><span class="frame-no">{i:02}</span><span><small>{fid} · 最小知识单元</small><strong>{inline(f['title'])}</strong><em>{inline(f['subtitle'])}</em></span><span class="chevron" aria-hidden="true">⌄</span></summary>
<div class="frame-content"><p class="body-copy">{inline(f['body'])}</p><aside class="why"><b>为什么不能删掉这一帧</b><p>{inline(f['why'])}</p></aside><ul class="claims">{''.join(claims)}</ul><label class="completion"><input type="checkbox" data-done="{fid}"> 我能不看原文解释这一帧（自评）</label></div></details></article>''')
        marks.append(f'<label><input type="checkbox" data-gap="{fid}"> 漏帧 {fid} · {html.escape(f["title"])}</label>')
    probes=[]
    for i,p in enumerate(spec['probes'],1):
        opened=' open' if static else ''
        probes.append(f'''<article class="probe" id="{p['id']}"><span class="eyebrow">PROBE {i:02} · {html.escape(p['kind'])}</span><h3>找出这个版本丢掉了什么</h3><p class="lossy">{inline(p['prompt'])}</p><label class="field-label" for="probe-{p['id']}">先写下你的判断</label><textarea id="probe-{p['id']}" data-save="probe-{p['id']}" rows="3" placeholder="缺了什么？会造成什么误解？"></textarea><details class="reveal"{opened}><summary>完成判断后，点击核对答案</summary><div><p>{inline(p['answer'])}</p><p class="muted">{inline(p['explanation'])}</p><a href="#{p['target']}">返回 {p['target']} 走查</a></div></details></article>''')
    sources=[]
    for s in spec['sources']:
        loc=' · '.join([s.get('paragraph_id','')]+([f"行 {s['line_start']}–{s['line_end']}"] if 'line_start' in s else []))
        cls='verified' if current and s.get('verified') is True else 'unverified'
        sources.append(f'<article class="source {cls}" id="{s["id"]}"><span class="source-label">{s["id"]}</span><div><small>{html.escape(loc)}</small><blockquote>{html.escape(s["text"])}</blockquote></div></article>')
    r=spec['rationale']
    rationale=f'<p>{inline(r["flow"])}</p><h3>帧如何切分</h3><p>{inline(r["frame_method"])}</p><div class="theories">'+''.join(f'<article><b>{inline(t["name"])}</b><p>{inline(t["application"])}</p></article>' for t in r['theory_map'])+f'</div><h3>与已有方法的关系</h3><p>{inline(r["prior_art"])}</p>'
    return {'TITLE':html.escape(spec['topic']),'SUBTITLE':inline(spec.get('subtitle','')),
            'STATUS':f'<div class="status {"pass" if current else "draft"}" role="status">{status}</div>',
            'NAV':''.join(nav),'FRAMES':''.join(frames),'PROBES':''.join(probes),'OWN_PROMPT':inline(spec['own_words']['prompt']),
            'OWN_MARKS':''.join(marks),'SOURCES':''.join(sources),'RATIONALE':rationale,'REPORT_KEY':digest,
            'SCRIPT':'' if static else '<script>'+ (ROOT/'assets/report.js').read_text(encoding='utf-8')+'</script>'}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('spec'); p.add_argument('--out',default='report.html')
    p.add_argument('--dry-run',action='store_true'); p.add_argument('--static',action='store_true')
    p.add_argument('--template',default=str(ROOT/'assets/html_template.html')); args=p.parse_args()
    try:
        spec=load_json(args.spec); validate_spec(spec)
        if args.dry_run: print('spec 校验通过；未写入 HTML。'); return 0
        template=Path(args.template).read_text(encoding='utf-8')
        values=build(spec,args.static)
        required=set(values); present=set(re.findall(r'@@([A-Z_]+)@@',template))
        if required!=present:
            print(f'模板占位符错误，缺少 {sorted(required-present)}；未知 {sorted(present-required)}',file=sys.stderr); return 3
        # One substitution pass: user data resembling a placeholder is never evaluated again.
        rendered=re.sub(r'@@([A-Z_]+)@@',lambda m:values[m[1]],template)
        if args.static: rendered=rendered.replace('<details class="reveal">','<details class="reveal" open>')
        save_text(args.out,rendered); print(json.dumps({'html':str(Path(args.out).resolve()),'static':args.static},ensure_ascii=False)); return 0
    except Exception as exc: print(f'渲染失败: {exc}',file=sys.stderr); return 2

if __name__=='__main__': sys.exit(main())

