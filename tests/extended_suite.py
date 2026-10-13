#!/usr/bin/env python3
"""Additional boundary cases found while walking the public workflow."""
import json
from pathlib import Path
import sys
import unittest
from regression_suite import Cases, DOM, fixture

class Extended(Cases):
    # Inherit only fixtures/helpers, not the original test methods.
    def test_e01_source_change_invalidates_render(self):
        self.verify(0,'--write-back'); self.src.write_text('新版本材料完全改变。',encoding='utf-8')
        self.assertIn('未核验或内容已变更',''.join(DOM(self.render()).text))
    def test_e02_template_tokens_are_literal_data(self):
        s=fixture(); s['topic']='@@SCRIPT@@'; self.write(s); dom=DOM(self.render())
        self.assertIn('@@SCRIPT@@',''.join(dom.text)); self.assertEqual(sum(t=='script' for t,a in dom.tags),1)
    def test_e03_location_must_be_true(self):
        s=fixture(); s['sources'][0]['line_start']=3; s['sources'][0]['line_end']=3; self.write(s); self.verify(10)
    def test_e04_empty_spec_fails(self): self.write({}); self.verify(10)
    def test_e05_invalid_json_fails(self): self.s.write_text('{broken',encoding='utf-8'); self.verify(10)
    def test_e06_ai_below_threshold_is_visible(self):
        s=fixture()
        for f in s['frames']:
            f['claims']*=3
        s['frames'][0]['claims'].append({'text':'这是单独标记的设计联想。','ai_only':True}); self.write(s)
        v=self.verify(0,'--write-back'); self.assertEqual(v['total'],13); self.assertEqual(v['verified'],12)
        self.assertIn('AI 补充，无来源',''.join(DOM(self.render()).text))
    def test_e07_failed_minor_item_still_blocks(self):
        s=fixture()
        for f in s['frames']: f['claims']*=5
        s['frames'][0]['claims'].append({'text':'虚构断言','anchor':'完全不存在的引句','source_id':'S1'})
        self.write(s); v=self.verify(10); self.assertGreater(v['coverage'],.9); self.assertEqual(v['failed'],1)
    def test_e08_whitespace_normalization(self):
        self.src.write_text('HTTPS 使用 TLS 保护传输中的 HTTP 数据。\n\n证书验证帮助客户端核验服务器身份。\n\nHTTPS 不保证网站内容可信。\n',encoding='utf-8')
        s=fixture(); s['frames'][0]['claims'][0]['anchor']='HTTPS使用TLS保护传输中的HTTP数据。'; self.write(s); self.verify()
    def test_e09_stdout_plan_is_json(self):
        p=self.runcli('flow_plan.py',self.src,'--topic','主题','-o','-'); self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['spec']['topic'],'主题')
    def test_e10_bom_and_crlf_ingestion(self):
        self.src.write_bytes(('\ufeff'+self.src.read_text(encoding='utf-8').replace('\n','\r\n')).encode('utf-8'))
        self.verify()
    def test_e11_english_negation(self):
        self.src.write_text('There is not any safety guarantee.\n',encoding='utf-8')
        s=fixture(); s['sources']=[{'id':'S1','text':'any safety guarantee.'}]
        for f in s['frames']:
            f['claims']=[{'text':'Guarantee exists','anchor':'any safety guarantee.','source_id':'S1'}]
        self.write(s); self.verify(10)
    def test_e12_full_negative_quote_accepted(self):
        self.src.write_text('There is not any safety guarantee.\n',encoding='utf-8')
        s=fixture(); s['sources']=[{'id':'S1','text':'There is not any safety guarantee.'}]
        for f in s['frames']:
            f['claims']=[{'text':'No guarantee','anchor':'There is not any safety guarantee.','source_id':'S1'}]
        self.write(s); self.verify()
    def test_e13_bad_schedule_intervals(self):
        p=self.runcli('schedule.py','plan','--start','2026-10-13','--spec',self.s,'--intervals','1,-2,3'); self.assertEqual(p.returncode,2)
    def test_e14_bad_log_reported(self):
        log=self.d/'bad.jsonl'; log.write_text('{broken\n',encoding='utf-8')
        p=self.runcli('schedule.py','stats','--log',log); self.assertEqual(p.returncode,2)
    def test_e15_schema_rejects_learner_prefill(self):
        s=fixture(); s['own_words']['answer']='我替学习者回答。'; self.write(s); self.render(2)
    def test_e16_unverified_items_are_flagged(self):
        dom=DOM(self.render()); self.assertTrue(any('unverified' in a.get('class','') for t,a in dom.tags))
        self.assertTrue(all(not a.get('value') for t,a in dom.tags if t=='textarea'))

# Do not duplicate the original 31 tests when running this suite.
for name in list(Cases.__dict__):
    if name.startswith('test_'):
        setattr(Extended,name,None)

if __name__=='__main__': unittest.main(defaultTest='Extended',verbosity=2)
