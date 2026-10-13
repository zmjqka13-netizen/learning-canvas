#!/usr/bin/env python3
"""Deterministically omit one frame; never create a learner's own-words response."""
import argparse
import json
import random
import sys
from common import load_json, save_json

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('spec'); p.add_argument('--target')
    p.add_argument('--seed',type=int,default=0); p.add_argument('-o','--out',default='-'); args=p.parse_args()
    try:
        spec=load_json(args.spec); frames=spec['frames']
        if not 3<=len(frames)<=5 or any(not f.get('title') or not f.get('claims') for f in frames):
            raise ValueError('请先完成 3–5 帧及断言')
        target=args.target or random.Random(args.seed).choice(frames)['id']
        match=[f for f in frames if f['id']==target]
        if len(match)!=1: raise ValueError('目标帧不存在或 ID 重复')
        chosen=match[0]
        lossy=' '.join(c['text'] for f in frames if f['id']!=target for c in f['claims'])
        probe={'id':'L1','target':target,'kind':'drop','prompt':lossy+'\n\n这个压缩版遗漏了哪一个必要知识单元？遗漏会造成什么误解？',
               'answer':f"遗漏 {target}：{chosen['title']}。",'explanation':chosen['why'],
               'seed':args.seed}
        if args.out=='-': print(json.dumps(probe,ensure_ascii=False,indent=2))
        else: save_json(args.out,probe)
        return 0
    except Exception as exc: print(f'探测生成失败: {exc}',file=sys.stderr); return 2

if __name__=='__main__': sys.exit(main())

