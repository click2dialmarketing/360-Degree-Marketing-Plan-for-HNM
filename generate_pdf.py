from textwrap import wrap

INPUT = 'YKBI_Premium_Digital_Marketing_Roadmap_90_Days.md'
OUTPUT = 'YKBI_Premium_Digital_Marketing_Roadmap_90_Days.pdf'

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT = 50
TOP = 800
BOTTOM = 50
LINE_HEIGHT = 14
FONT_SIZE = 10


def escape_pdf_text(s: str) -> str:
    return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def paginate_lines(text_lines, max_chars=92):
    out = []
    for line in text_lines:
        if not line.strip():
            out.append('')
            continue
        # Preserve heading emphasis a bit
        indent = ''
        content = line
        if line.startswith('    '):
            indent = '    '
            content = line[4:]
        wrapped = wrap(content, width=max_chars, break_long_words=False, replace_whitespace=False)
        if not wrapped:
            out.append('')
        else:
            for w in wrapped:
                out.append(indent + w)
    return out


def make_content_stream(page_lines):
    y = TOP
    parts = ["BT", f"/F1 {FONT_SIZE} Tf", f"{LEFT} {y} Td"]
    first = True
    for ln in page_lines:
        if not first:
            parts.append(f"0 -{LINE_HEIGHT} Td")
        first = False
        txt = escape_pdf_text(ln)
        parts.append(f"({txt}) Tj")
    parts.append("ET")
    return "\n".join(parts).encode('latin-1', errors='replace')


def build_pdf(pages):
    objs = []

    # 1 Catalog, 2 Pages
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")

    # Placeholder pages object
    objs.append(None)

    # 3 Font
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_obj_ids = []
    content_obj_ids = []

    # create page + content objects
    for _ in pages:
        content_obj_ids.append(len(objs) + 1)
        objs.append(None)  # content placeholder
        page_obj_ids.append(len(objs) + 1)
        objs.append(None)  # page placeholder

    # fill content objects
    for i, stream in enumerate(pages):
        cid = content_obj_ids[i]
        objs[cid - 1] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode('latin-1')
            + stream
            + b"\nendstream"
        )

    # fill page objects
    for i, pid in enumerate(page_obj_ids):
        cid = content_obj_ids[i]
        objs[pid - 1] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {cid} 0 R >>"
        ).encode('latin-1')

    kids = " ".join([f"{pid} 0 R" for pid in page_obj_ids])
    objs[1] = f"<< /Type /Pages /Count {len(page_obj_ids)} /Kids [ {kids} ] >>".encode('latin-1')

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    offsets = [0]
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n".encode('latin-1'))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objs)+1}\n".encode('latin-1'))
    pdf.extend(b"0000000000 65535 f \n")
    for i in range(1, len(objs)+1):
        pdf.extend(f"{offsets[i]:010d} 00000 n \n".encode('latin-1'))

    pdf.extend(
        f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode('latin-1')
    )

    with open(OUTPUT, 'wb') as f:
        f.write(pdf)


with open(INPUT, 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

wrapped = paginate_lines(lines)
max_lines_per_page = (TOP - BOTTOM) // LINE_HEIGHT
pages = [wrapped[i:i + max_lines_per_page] for i in range(0, len(wrapped), max_lines_per_page)]
streams = [make_content_stream(p) for p in pages]
build_pdf(streams)

print(f"Generated {OUTPUT} with {len(pages)} pages")
