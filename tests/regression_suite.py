#!/usr/bin/env python3
"""31 CLI regression cases. Only stdlib; scratch data stays under the workspace derived
from this file's location (override with the LEARNING_CANVAS_TEST_ROOT environment variable)."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'HTTPS 使用 TLS 保护传输中的 HTTP 数据。\n\n证书验证帮助客户端核验服务器身份。\n\nHTTPS 不保证网站内容可信。\n'

def fixture():
    quotes = ['HTTPS 使用 TLS 保护传输中的 HTTP 数据。', '证书验证帮助客户端核验服务器身份。', 'HTTPS 不保证网站内容可信。']
    return {
        'version': '1.0', 'topic': 'HTTPS 入门', 'subtitle': '学会区分保护范围与边界',
        'frames': [dict(id=f'F{i}', title=t, subtitle='先预测，再核验', body=q + f' {{S{i}}}', why=w,
                        claims=[dict(text=q, anchor=q, source_id=f'S{i}', ai_only=False)])
                   for i, (q, t, w) in enumerate(zip(quotes, ['传输保护', '身份核验', '能力边界'],
                       ['删去后无法解释保护对象。', '删去后无法解释通信对象。', '删去后容易推导出过度保证。']), 1)],
        'probes': [dict(id='L1', target='F3', kind='drop', prompt='HTTPS 保护传输，因此内容一定可信。丢了什么？',
                        answer='遗漏了内容可信度不在保证范围内。', explanation='回看 F3，并定位原文中的否定。 {S3}')],
        'own_words': {'prompt': '关闭帧后，用自己的话重述；只标漏帧与新增。'},
        'sources': [dict(id=f'S{i}', text=q, line_start=2*i-1, line_end=2*i-1, paragraph_id=f'P{i:04}') for i, q in enumerate(quotes, 1)],
        'rationale': {'flow': '先切帧，再探测、重述与走查。', 'frame_method': '三帧分别回答对象、身份、边界。',
                      'theory_map': [{'name': '提取练习', 'application': '揭示答案前先作答。'}],
                      'prior_art': '用来源锚点连接解释与证据。'}
    }

class DOM(HTMLParser):
    def __init__(self, s):
        super().__init__(); self.tags=[]; self.text=[]; self.feed(s)
    def handle_starttag(self, tag, attrs): self.tags.append((tag, dict(attrs)))
    def handle_data(self, data): self.text.append(data)

class Cases(unittest.TestCase):
    def setUp(self):
        base=Path(os.environ.get('LEARNING_CANVAS_TEST_ROOT', ROOT.parent / 'test-runs'))
        base.mkdir(parents=True, exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=base); self.addCleanup(self.tmp.cleanup)
        self.d=Path(self.tmp.name); self.s=self.d/'spec.json'; self.src=self.d/'source.md'; self.out=self.d/'report.html'
        self.src.write_text(SOURCE, encoding='utf-8'); self.write(fixture())
    def write(self, data): self.s.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    def runcli(self, name, *args):
        result = subprocess.run([sys.executable, str(ROOT/'scripts'/name), *map(str,args)], cwd=self.d,
                              capture_output=True, text=True, encoding='utf-8', env={**os.environ,'PYTHONUTF8':'1'})
        self.assertNotIn("can't open file", result.stderr, 'CLI feature has not been implemented')
        return result
    def verify(self, code=0, *extra):
        p=self.runcli('anchor_verify.py',self.s,self.src,*extra)
        self.assertEqual(p.returncode,code,p.stdout+p.stderr); return json.loads(p.stdout)
    def render(self, code=0, *extra):
        p=self.runcli('render_report.py',self.s,'--out',self.out,*extra)
        self.assertEqual(p.returncode,code,p.stdout+p.stderr)
        return self.out.read_text(encoding='utf-8') if self.out.exists() else ''
    # Removing each guard below should permit an invalid evidence chain.
    def test_g01_valid_evidence(self): self.assertEqual(self.verify()['coverage'],1.0)
    def test_g02_missing_source(self): self.src.unlink(); self.verify(10)
    def test_g03_empty_source(self): self.src.write_text(' \n',encoding='utf-8'); self.verify(10)
    def test_g04_no_matches(self): self.src.write_text('完全无关的基准材料。',encoding='utf-8'); self.verify(10)
    def test_g05_missing_anchor(self):
        s=fixture(); s['frames'][0]['claims'][0]['anchor']=''; self.write(s); self.verify(10)
    def test_g06_ai_is_in_denominator(self):
        s=fixture(); s['frames'][0]['claims']=[dict(text='无依据的补充',ai_only=True) for _ in range(10)]; self.write(s)
        v=self.verify(10); self.assertEqual(v['total'],15); self.assertEqual(v['verified'],5)
    def test_g07_fake_display_quote(self):
        s=fixture(); s['sources'][0]['text']='证书永远不会过期。'; self.write(s); self.verify(10)
    def test_g08_removed_negation(self):
        s=fixture(); s['frames'][2]['claims'][0]['anchor']='保证网站内容可信。'; self.write(s); self.verify(10)
    def test_g09_broken_pdf(self):
        self.src=self.d/'bad.pdf'; self.src.write_bytes(b'%PDF-broken'); self.verify(10)
    # Structure cases assert observable acceptance/rejection rather than implementation text.
    def test_s01_frame_range(self):
        for n in (2,6):
            s=fixture(); s['frames']=(s['frames']*2)[:n]; self.write(s); self.render(2)
    def test_s02_probe_required(self):
        s=fixture(); s['probes']=[]; self.write(s); self.render(2)
    def test_s03_irreducible_reason(self):
        s=fixture(); s['frames'][0]['why']=''; self.write(s); self.render(2)
    def test_s04_duplicate_ids(self):
        s=fixture(); s['sources'][1]['id']='S1'; self.write(s); self.render(2)
    def test_s05_broken_source_link(self):
        s=fixture(); s['frames'][0]['body']='说明 {S99}'; self.write(s); self.render(2)
    def test_s06_dry_run(self): self.render(0,'--dry-run'); self.assertFalse(self.out.exists())
    def test_s07_template_contract(self):
        t=self.d/'bad.html'; t.write_text('<html></html>',encoding='utf-8'); self.render(3,'--template',t)
    def test_s08_static_is_readable(self):
        dom=DOM(self.render(0,'--static')); self.assertFalse(any(t=='script' for t,a in dom.tags))
        self.assertTrue(all('open' in a for t,a in dom.tags if t=='details'))
        self.assertIn('遗漏了内容可信度', ''.join(dom.text))
    def test_s09_no_external_resources(self):
        dom=DOM(self.render()); ids=[a['id'] for t,a in dom.tags if 'id' in a]; self.assertEqual(len(ids),len(set(ids)))
        for t,a in dom.tags:
            self.assertNotIn('src',a); self.assertTrue('href' not in a or a['href'].startswith('#'))
    # Consistency cases follow the public CLI from an unrelated working directory.
    def test_c01_index_line_numbers(self):
        p=self.runcli('flow_plan.py',self.src,'--topic','HTTPS','-o',self.s); self.assertEqual(p.returncode,0,p.stderr)
        idx=json.loads(self.s.with_suffix('.flow-index.json').read_text(encoding='utf-8'))
        self.assertEqual([(x['id'],x['line_start']) for x in idx['paragraphs']],[('P0001',1),('P0002',3),('P0003',5)])
        self.assertIn('frames',json.loads(self.s.read_text(encoding='utf-8')))
    def test_c02_probe_deterministic_target(self):
        a=self.runcli('lossy_perturb.py',self.s,'--target','F2','--seed','7')
        b=self.runcli('lossy_perturb.py',self.s,'--target','F2','--seed','7')
        self.assertEqual(a.returncode,0,a.stderr); self.assertEqual(a.stdout,b.stdout)
        probe=json.loads(a.stdout); self.assertEqual(probe['target'],'F2'); self.assertNotIn('证书验证',probe['prompt'])
    def test_c03_unknown_target(self):
        p=self.runcli('lossy_perturb.py',self.s,'--target','F99'); self.assertEqual(p.returncode,2,p.stderr)
    def test_c04_writeback_and_stale(self):
        v=self.verify(0,'--write-back','--log'); self.assertTrue(v['passed'])
        self.assertTrue(json.loads(self.s.read_text(encoding='utf-8'))['frames'][0]['claims'][0]['verified'])
        self.assertIn('已通过锚点核验', ''.join(DOM(self.render()).text))
        s=json.loads(self.s.read_text(encoding='utf-8')); s['frames'][0]['body']+='新增断言'; self.write(s)
        self.assertIn('未核验或内容已变更', ''.join(DOM(self.render()).text))
        self.assertTrue(self.s.with_suffix('.verification.jsonl').exists())
    def test_c05_schedule_and_stats(self):
        p=self.runcli('schedule.py','plan','--start','2026-10-13','--spec',self.s)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual([x['date'] for x in json.loads(p.stdout)['reviews']],['2026-10-14','2026-10-16','2026-10-20','2026-10-27','2026-11-12'])
        self.verify(0,'--log'); p=self.runcli('schedule.py','stats','--log',self.s.with_suffix('.verification.jsonl'))
        self.assertEqual(p.returncode,0,p.stderr); self.assertEqual(json.loads(p.stdout)['runs'],1)

def injection_case(payload):
    def test(self):
        s=fixture(); s['topic']=payload; s['frames'][0]['body']=payload+' {S1}'
        s['frames'][0]['claims'][0]['text']=payload; s['sources'][0]['text']=payload; self.write(s)
        dom=DOM(self.render()); self.assertEqual(sum(t=='script' for t,a in dom.tags),1)
        for t,a in dom.tags:
            self.assertFalse(any(k.lower().startswith('on') for k in a))
            self.assertFalse(t in ('iframe','svg','img','object','embed','base'))
            self.assertTrue('href' not in a or a['href'].startswith('#'))
        self.assertIn(payload, ''.join(dom.text))
    return test

for i,payload in enumerate(['<script>alert(1)</script>','</script><script>alert(2)</script>',
                           '<img src=x onerror=alert(3)>','<svg onload=alert(4)>',
                           '\" autofocus onfocus=alert(5) x=\"', '[点我](javascript:alert(6))',
                           '&lt;img src=x onerror=alert(7)&gt;', '${alert(8)} ` </textarea>'],1):
    setattr(Cases,f'test_i{i:02}_escape_payload',injection_case(payload))

if __name__=='__main__': unittest.main(verbosity=2)
