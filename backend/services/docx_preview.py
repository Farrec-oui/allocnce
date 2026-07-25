"""DOCX → HTML fragment for browser preview.

Iterates document body in order (paragraphs and tables), preserving
WD_COLOR_INDEX highlights as inline background-color spans.
"""
import html as _html

from docx import Document

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _q(tag: str) -> str:
    return f"{{{_W}}}{tag}"


# XML w:highlight w:val → CSS background-color
_HL_CSS: dict[str, str] = {
    "yellow":  "#FFF176",
    "green":   "#CCFF90",
    "cyan":    "#80DEEA",
    "magenta": "#F48FB1",
}

_P   = _q("p")
_TBL = _q("tbl")
_TR  = _q("tr")
_TC  = _q("tc")
_R   = _q("r")
_RPR = _q("rPr")
_HL  = _q("highlight")
_T   = _q("t")
_BR  = _q("br")
_VAL = _q("val")


def _run_html(r_el) -> str:
    parts: list[str] = []
    for child in r_el:
        if child.tag == _T:
            parts.append(_html.escape(child.text or ""))
        elif child.tag == _BR:
            parts.append("<br>")
    text = "".join(parts)
    if not text:
        return ""

    rpr = r_el.find(_RPR)
    bg: str | None = None
    if rpr is not None:
        hl = rpr.find(_HL)
        if hl is not None:
            bg = _HL_CSS.get(hl.get(_VAL) or "")

    if bg:
        return f'<span style="background-color:{bg}">{text}</span>'
    return text


def _para_html(p_el) -> str:
    runs = "".join(_run_html(c) for c in p_el if c.tag == _R)
    if not runs.strip():
        return "<p>&nbsp;</p>"
    return f"<p>{runs}</p>"


def _cell_html(tc_el) -> str:
    paras: list[str] = []
    for child in tc_el:
        if child.tag == _P:
            runs = "".join(_run_html(r) for r in child if r.tag == _R)
            paras.append(runs or "&nbsp;")
    return "<br>".join(paras)


def _table_html(tbl_el) -> str:
    rows: list[str] = []
    row_els = [c for c in tbl_el if c.tag == _TR]
    for i, tr_el in enumerate(row_els):
        cells: list[str] = []
        for tc_el in tr_el:
            if tc_el.tag != _TC:
                continue
            content = _cell_html(tc_el)
            tag = "th" if i == 0 else "td"
            cells.append(f"<{tag}>{content}</{tag}>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table>{''.join(rows)}</table>"


def docx_to_html(path: str) -> str:
    """Return an HTML fragment (no <html>/<body> wrapper) for browser embed."""
    doc = Document(path)
    parts: list[str] = []
    for child in doc.element.body:
        tag = child.tag
        if tag == _P:
            parts.append(_para_html(child))
        elif tag == _TBL:
            parts.append(_table_html(child))
    return "\n".join(parts)
