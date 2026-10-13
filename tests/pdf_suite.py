#!/usr/bin/env python3
"""Optional PDF-ingestion integration tests, using locally generated harmless fixtures."""
import importlib.util
import unittest
from regression_suite import Cases, fixture

@unittest.skipUnless(importlib.util.find_spec('pypdf') and importlib.util.find_spec('reportlab'), 'dev PDF tests need pypdf and reportlab')
class PDFs(Cases):
    def make_pdf(self, lines, encrypt=None):
        from reportlab.pdfgen.canvas import Canvas
        self.src=self.d/'material.pdf'
        c=Canvas(str(self.src),encrypt=encrypt)
        for i,line in enumerate(lines): c.drawString(60,780-30*i,line)
        c.showPage(); c.save()
    def test_p01_text_pdf_index_and_gate(self):
        lines=['HTTPS protects data in transit.', 'Certificates help verify server identity.', 'HTTPS does not prove content is trustworthy.']
        self.make_pdf(lines); s=fixture()
        s['sources']=[{'id':f'S{i}','text':q} for i,q in enumerate(lines,1)]
        for i,f in enumerate(s['frames']): f['claims']=[{'text':lines[i],'anchor':lines[i],'source_id':f'S{i+1}'}]
        self.write(s); self.verify()
        p=self.runcli('flow_plan.py',self.src,'-o',self.d/'plan.json'); self.assertEqual(p.returncode,0,p.stderr)
    def test_p02_blank_pdf_fails(self): self.make_pdf([]); self.verify(10)
    def test_p03_encrypted_pdf_fails(self): self.make_pdf(['Private source.'],encrypt='sample-password'); self.verify(10)

for name in list(Cases.__dict__):
    if name.startswith('test_'): setattr(PDFs,name,None)

if __name__=='__main__': unittest.main(defaultTest='PDFs',verbosity=2)
