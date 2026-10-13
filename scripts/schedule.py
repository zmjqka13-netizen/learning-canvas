#!/usr/bin/env python3
"""Print a review proposal or summarize evidence logs. Does not create system reminders."""
import argparse
from collections import defaultdict
from datetime import date, timedelta
import json
from pathlib import Path
import sys
from common import load_json, save_json

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    plan=sub.add_parser('plan'); plan.add_argument('--start',required=True); plan.add_argument('--spec',required=True)
    plan.add_argument('--out'); plan.add_argument('--intervals',default='1,3,7,14,30')
    stats=sub.add_parser('stats'); stats.add_argument('--log',required=True)
    args=p.parse_args()
    try:
        if args.cmd=='plan':
            start=date.fromisoformat(args.start); spec=load_json(args.spec)
            days=[int(x) for x in args.intervals.split(',')]
            if not days or days!=sorted(set(days)) or any(x<=0 for x in days): raise ValueError('复习间隔应为递增、去重的正整数')
            result={'topic':spec['topic'],'start':start.isoformat(),'status':'proposal_only',
                    'note':'这是可调整的复习提案，尚未建立提醒；这些间隔不是个体最优值。',
                    'reviews':[{'date':(start+timedelta(days=d)).isoformat(),'day_offset':d,
                                'task':'先不看报告做有损探测与自己的话，再核对漏帧、新增和证据。'} for d in days]}
            if args.out: save_json(args.out,result)
        else:
            groups=defaultdict(lambda:{'runs':0,'failed_runs':0,'last_coverage':0.0})
            rows=[]
            for n,line in enumerate(Path(args.log).read_text(encoding='utf-8-sig').splitlines(),1):
                if not line.strip(): continue
                try: row=json.loads(line)
                except json.JSONDecodeError as exc: raise ValueError(f'台账第 {n} 行损坏') from exc
                if not isinstance(row.get('passed'),bool) or not isinstance(row.get('coverage'),(int,float)): raise ValueError(f'台账第 {n} 行缺少核验结果')
                rows.append(row); g=groups[row.get('topic','未命名')]; g['runs']+=1
                g['failed_runs']+=not row['passed']; g['last_coverage']=row['coverage']
            result={'runs':len(rows),'topics':[dict(topic=k,**v,rework_recommended=v['last_coverage']<.9 or any(not r['passed'] for r in rows if r.get('topic','未命名')==k and r==next((x for x in reversed(rows) if x.get('topic','未命名')==k),{}))) for k,v in groups.items()],
                    'note':'统计的是来源核验，不代表学习者掌握度。'}
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    except Exception as exc: print(f'排期/台账失败: {exc}',file=sys.stderr); return 2

if __name__=='__main__': sys.exit(main())
