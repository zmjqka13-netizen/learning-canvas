#!/usr/bin/env python3
"""Optional text/layout invariant check on the HTTPS browser-smoke print fixture."""
import sys
from pypdf import PdfReader

reader=PdfReader(sys.argv[1])
text='\n'.join(page.extract_text() or '' for page in reader.pages)
assert '传输保密' in reader.pages[0].extract_text(), 'first page wastes the learning area by pushing the entire first frame away'
assert '遗漏 F4' in text, 'concealed quiz answer was omitted from print'
assert '用你自己的话' in text and '证据锚点' in text and '为什么这样设计' in text, 'a learning stage disappeared from print'
assert all((page.extract_text() or '').strip() for page in reader.pages), 'blank print page'
print(f'Print checks passed: {len(reader.pages)} pages, all learning stages and answer included.')
