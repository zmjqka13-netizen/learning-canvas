"""Source ingestion and schema validation for planning/rendering (not evidence verification)."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def read_source(path):
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix.lower() == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError('读取 PDF 需要 pypdf；请安装可选依赖或先转换为 UTF-8 文本。') from exc
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError('不支持加密 PDF；请提供已解密材料。')
        text = '\n\n'.join(page.extract_text() or '' for page in reader.pages)
    else:
        text = raw.decode('utf-8-sig')
        if '\x00' in text:
            raise ValueError('源材料不是有效的 UTF-8 文本。')
    if not text.strip():
        raise ValueError('源材料为空或没有可提取文字；扫描 PDF 请先 OCR。')
    return text, hashlib.sha256(raw).hexdigest()

def paragraphs(text):
    result=[]; block=[]; start=1
    for line_no, line in enumerate(text.splitlines()+[''],1):
        if line.strip():
            if not block: start=line_no
            block.append(line)
        elif block:
            result.append({'id':f'P{len(result)+1:04}', 'line_start':start,
                           'line_end':line_no-1,'text':'\n'.join(block)})
            block=[]
    return result

def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def save_text(path, text):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd, name=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream: stream.write(text)
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)

def save_json(path, value):
    save_text(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def check_schema(value, schema, root=None, loc='$'):
    """Implement exactly the schema keywords used by report_spec.schema.json."""
    root = root or schema
    if '$ref' in schema:
        node=root
        for part in schema['$ref'][2:].split('/'): node=node[part]
        return check_schema(value,node,root,loc)
    kinds={'object':dict,'array':list,'string':str,'boolean':bool,'integer':int,'number':(int,float)}
    kind=schema.get('type')
    if kind and (not isinstance(value,kinds[kind]) or kind in ('integer','number') and isinstance(value,bool)):
        raise ValueError(f'{loc}: 应为 {kind}')
    if 'enum' in schema and value not in schema['enum']: raise ValueError(f'{loc}: 不在允许值中')
    if isinstance(value,dict):
        for key in schema.get('required',[]):
            if key not in value: raise ValueError(f'{loc}: 缺少 {key}')
        props=schema.get('properties',{})
        for key,item in value.items():
            if key in props: check_schema(item,props[key],root,f'{loc}.{key}')
            elif schema.get('additionalProperties') is False: raise ValueError(f'{loc}: 未知字段 {key}')
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',float('inf')):
            raise ValueError(f'{loc}: 数组长度不合规')
        for i,item in enumerate(value): check_schema(item,schema.get('items',{}),root,f'{loc}[{i}]')
    if isinstance(value,str):
        if len(value.strip())<schema.get('minLength',0): raise ValueError(f'{loc}: 文本不能为空')
        if 'pattern' in schema and not re.fullmatch(schema['pattern'],value): raise ValueError(f'{loc}: 格式不合规')
    if kind in ('integer','number') and value<schema.get('minimum',float('-inf')):
        raise ValueError(f'{loc}: 数值过小')

def validate_spec(spec):
    check_schema(spec,load_json(ROOT/'assets/report_spec.schema.json'))
    frames={}; sources={}; probe_ids=set()
    for frame in spec['frames']:
        if frame['id'] in frames: raise ValueError('帧 ID 重复')
        frames[frame['id']]=frame
    for source in spec['sources']:
        if source['id'] in sources: raise ValueError('来源 ID 重复')
        sources[source['id']]=source
        if ('line_start' in source)!=('line_end' in source): raise ValueError('行号必须成对出现')
        if source.get('line_start',1)>source.get('line_end',1): raise ValueError('来源行号倒置')
    for frame in spec['frames']:
        for claim in frame['claims']:
            if claim.get('ai_only',False):
                if claim.get('anchor') or claim.get('source_id'): raise ValueError('AI 补充不得伪装成来源断言')
            elif not claim.get('anchor','').strip() or claim.get('source_id') not in sources:
                raise ValueError('来源断言需要 anchor 和有效 source_id')
    for probe in spec['probes']:
        if probe['id'] in probe_ids: raise ValueError('探测 ID 重复')
        probe_ids.add(probe['id'])
        if probe['target'] not in frames: raise ValueError('探测目标帧不存在')
    def walk(node):
        if isinstance(node,str):
            for ref in re.findall(r'\{(S\d+)\}',node):
                if ref not in sources: raise ValueError(f'悬空来源引用 {ref}')
        elif isinstance(node,list):
            for item in node: walk(item)
        elif isinstance(node,dict):
            for key,item in node.items():
                if key!='verification': walk(item)
    walk(spec)

