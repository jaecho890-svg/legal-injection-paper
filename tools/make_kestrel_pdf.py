#!/usr/bin/env python3
"""
make_kestrel_pdf.py - build Kestrel's real-PDF conditions (C0P, A2P) and extract their text.

A2 puts the injected instruction in an HTML comment inside plain text, which only simulates a
hidden channel. A2P is the real thing: a PDF whose payload is drawn with text render mode 3
(invisible: nothing is painted, but the text is in the page's content stream), so a human sees
the clean document and a text extractor returns the payload. C0P is the same PDF without the
payload, so A2P is compared with a document that went through the same PDF -> text path.

Pipeline (standard library + macOS PDFKit, nothing to install):
  1. render C0.txt to PDF (Helvetica 10pt, A4, simple word wrap)          -> corpus/pdf/C0P.pdf
  2. same, plus the A2 payload in render mode 3 after the last paragraph -> corpus/pdf/A2P.pdf
  3. extract each with PDFKit (tools/pdf_extract.swift), as an app would -> corpus/variants/C0P.txt, A2P.txt

  python3 tools/make_kestrel_pdf.py
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "kestrel-injection-study" / "corpus"
PDF_DIR = CORPUS / "pdf"
W, H, MARGIN, SIZE, LEAD = 595, 842, 56, 10, 13
WRAP = 98  # characters per line at 10pt Helvetica across the text block


def payload():
    """The A2 instruction, verbatim, without its HTML-comment wrapper."""
    a2 = (CORPUS / "variants" / "A2.txt").read_text()
    m = re.search(r"<!--[^:]*\):\s*(.*?)\s*-->", a2, re.S)
    if not m:
        sys.exit("could not find the A2 payload")
    return m.group(1)


def wrap(text):
    lines = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        cur = ""
        for word in para.split():
            if cur and len(cur) + 1 + len(word) > WRAP:
                lines.append(cur); cur = word
            else:
                cur = f"{cur} {word}" if cur else word
        lines.append(cur)
    return lines


def pdf_string(s):
    b = s.encode("cp1252", errors="replace")  # cp1252 is WinAnsiEncoding
    return b"(" + b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)") + b")"


def build(visible, hidden=None):
    lines = wrap(visible)
    per_page = (H - 2 * MARGIN) // LEAD
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[]]
    streams = []
    for pi, pl in enumerate(pages):
        ops = [b"BT", f"/F1 {SIZE} Tf {LEAD} TL {MARGIN} {H - MARGIN} Td".encode()]
        for ln in pl:
            ops.append(pdf_string(ln) + b" Tj T*")
        if hidden and pi == len(pages) - 1:
            # render mode 3 = invisible text: not painted, still extractable
            ops.append(b"3 Tr T*")
            for ln in wrap(hidden):
                ops.append(pdf_string(ln) + b" Tj T*")
            ops.append(b"0 Tr")
        ops.append(b"ET")
        streams.append(b"\n".join(ops))

    objs = []  # 1 catalog, 2 pages, 3 font, then (page, content) pairs
    n_pages = len(streams)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n_pages))
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for i, st in enumerate(streams):
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Resources << /Font << /F1 3 0 R >> >> "
                    f"/Contents {5 + 2 * i} 0 R >>".encode())
        objs.append(f"<< /Length {len(st)} >>\nstream\n".encode() + st + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{off:010d} 00000 n \n".encode() for off in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def extract(pdf_path):
    r = subprocess.run(["swift", str(ROOT / "tools" / "pdf_extract.swift"), str(pdf_path)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        sys.exit(f"PDFKit extraction failed: {r.stderr[-500:]}")
    return r.stdout


def main():
    PDF_DIR.mkdir(exist_ok=True)
    c0 = (CORPUS / "variants" / "C0.txt").read_text()
    for name, hidden in (("C0P", None), ("A2P", payload())):
        pdf = PDF_DIR / f"{name}.pdf"
        pdf.write_bytes(build(c0, hidden))
        text = extract(pdf)
        (CORPUS / "variants" / f"{name}.txt").write_text(text)
        print(f"{pdf.relative_to(ROOT)}: {pdf.stat().st_size} bytes -> variants/{name}.txt ({len(text)} chars)")


if __name__ == "__main__":
    main()
