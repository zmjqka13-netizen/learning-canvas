#!/usr/bin/env python3
"""Build an addressable source index and an explicitly unfinished report skeleton."""
import argparse
import json
from pathlib import Path
import sys
from common import paragraphs, read_source, save_json

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source'); parser.add_argument('--topic'); parser.add_argument('-o','--out',default='spec.json')
    args=parser.parse_args()
    try:
        text,digest=read_source(args.source)
        index={'source':str(Path(args.source).resolve()),'sha256':digest,
               'line_number_basis':'PDF 为抽取文本行号；其他材料为原始文本行号。','paragraphs':paragraphs(text)}
        spec={'version':'1.0','topic':args.topic or Path(args.source).stem,'subtitle':'',
              'source':{'path':str(Path(args.source).resolve()),'sha256':digest},
              'frames':[{'id':f'F{i}','title':'','subtitle':'','body':'','why':'','claims':[]} for i in range(1,4)],
              'probes':[],'own_words':{'prompt':'合上知识帧，用自己的话重述。先自己标出漏帧与新增，再核对证据。'},
              'sources':[],'rationale':{'flow':'F 切帧 → L 有损探测 → O 自己的话 → W 来源走查。',
              'frame_method':'','theory_map':[],'prior_art':''}}
        if args.out=='-': print(json.dumps({'spec':spec,'index':index},ensure_ascii=False,indent=2))
        else:
            out=Path(args.out); save_json(out,spec); idx=out.with_suffix('.flow-index.json'); save_json(idx,index)
            print(json.dumps({'spec':str(out),'index':str(idx),'status':'需人工完成切帧和断言；骨架不可直接渲染'},ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f'摄取失败: {exc}',file=sys.stderr); return 2

if __name__=='__main__': sys.exit(main())

