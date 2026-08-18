from __future__ import annotations

import re
from pathlib import Path

import frontmatter
from bs4 import BeautifulSoup

from contextiq_ingestion.models import CleanDocument, ContentBlock, DocumentType, SourceSpec
from contextiq_ingestion.parsers.html_structure import (
    SectionBuilder,
    collapse_blank_lines,
    normalize_ws,
)


MDX_IMPORT_RE = re.compile(r"^import\s+.+from\s+.+;?\s*$", re.MULTILINE)
MDX_EXPORT_RE = re.compile(r"^export\s+(default\s+)?(const|function|async\s+function).*$", re.MULTILINE)
JSX_TAG_RE = re.compile(r"</?[A-Z][A-Za-z0-9]*(\s[^>]*)?/?>")
JSX_SELF_CLOSING_LOWER_RE = re.compile(
    r"</?(?:AppOnly|PagesOnly|Image|Tabs|TabItem|Cards|Card|Check|Cross|ACME|Steps|Step)(\s[^>]*)?/?>",
    re.IGNORECASE,
)


def strip_mdx(text: str) -> str:
    """Best-effort MDX → markdown so structure parsers can run."""
    text = MDX_IMPORT_RE.sub("", text)
    text = MDX_EXPORT_RE.sub("", text)
    # Remove common Next.js docs JSX wrappers but keep inner markdown
    text = JSX_SELF_CLOSING_LOWER_RE.sub("", text)
    text = JSX_TAG_RE.sub("", text)
    # Remove bare JSX expressions like {`...`} lightly
    text = re.sub(r"\{`([\s\S]*?)`\}", r"\1", text)
    text = re.sub(r"\{/\*[\s\S]*?\*/\}", "", text)
    return collapse_blank_lines(text)


def parse_markdown_table(lines: list[str]) -> ContentBlock | None:
    if len(lines) < 2:
        return None
    if not all("|" in line for line in lines[:2]):
        return None

    def split_row(line: str) -> list[str]:
        raw = line.strip().strip("|")
        return [normalize_ws(c) for c in raw.split("|")]

    headers = split_row(lines[0])
    # separator row
    sep = lines[1].replace(":", "-")
    if not re.match(r"^\|?[\s\-|]+\|?$", sep):
        return None
    rows = [split_row(line) for line in lines[2:] if line.strip()]
    md = "\n".join(lines)
    return ContentBlock(type="table", headers=headers, rows=rows, markdown=md)


def parse_markdown_to_sections(text: str, source_id: str, title_fallback: str) -> tuple[str, list]:
    post = frontmatter.loads(text)
    meta = dict(post.metadata or {})
    body = str(post.content or "")
    title = str(meta.get("title") or title_fallback)

    builder = SectionBuilder(source_id)
    lines = body.splitlines()
    i = 0
    paragraph_buf: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_buf
        if paragraph_buf:
            text_p = normalize_ws(" ".join(paragraph_buf))
            if text_p:
                builder.add_block(ContentBlock(type="paragraph", text=text_p))
            paragraph_buf = []

    while i < len(lines):
        line = lines[i]
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            builder.start_heading(level, heading.group(2))
            i += 1
            continue

        # fenced code
        fence = re.match(r"^```([\w-]*)\s*$", line)
        if fence:
            flush_paragraph()
            lang = fence.group(1) or None
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines) and lines[i].startswith("```"):
                i += 1
            builder.add_block(
                ContentBlock(type="code", language=lang, text="\n".join(code_lines).rstrip())
            )
            continue

        # table block
        if "|" in line and i + 1 < len(lines) and re.search(r"\|?\s*-{3,}", lines[i + 1]):
            flush_paragraph()
            table_lines = [line]
            i += 1
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i])
                i += 1
            block = parse_markdown_table(table_lines)
            if block:
                builder.add_block(block)
            continue

        # list block
        if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
            flush_paragraph()
            items: list[str] = []
            ordered = bool(re.match(r"^\s*\d+\.\s+", line))
            while i < len(lines) and re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i]):
                item = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", lines[i]).strip()
                items.append(item)
                i += 1
            builder.add_block(ContentBlock(type="list", ordered=ordered, items=items))
            continue

        # blockquote
        if line.startswith(">"):
            flush_paragraph()
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].startswith(">"):
                quote_lines.append(lines[i].lstrip("> ").rstrip())
                i += 1
            builder.add_block(
                ContentBlock(type="blockquote", text=normalize_ws(" ".join(quote_lines)))
            )
            continue

        if not line.strip():
            flush_paragraph()
            i += 1
            continue

        paragraph_buf.append(line.strip())
        i += 1

    flush_paragraph()
    sections = builder.finalize()

    # If no H1 and title exists, keep title on document; sections unchanged
    if not any(s.heading_level == 1 for s in sections if s.heading_level):
        # ensure document title is available via metadata
        pass

    return title, sections


def parse_markdown_file(path: Path, source: SourceSpec) -> CleanDocument:
    raw = path.read_text(encoding="utf-8")
    if source.format == DocumentType.MDX or path.suffix.lower() == ".mdx":
        raw = strip_mdx(raw)
        doc_type = DocumentType.MDX
        parser_name = "markdown_mdx_structure_v1"
    else:
        doc_type = DocumentType.MARKDOWN
        parser_name = "markdown_structure_v1"

    title, sections = parse_markdown_to_sections(raw, source.id, source.title)
    doc = CleanDocument(
        source_id=source.id,
        title=title or source.title,
        source_url=source.url,
        family=source.family,
        document_type=doc_type,
        topics=list(source.topics),
        sections=sections,
        raw_path=str(path),
        parser=parser_name,
        metadata={"frontmatter_title": title},
    )
    doc.stats = {
        "section_count": doc.section_count(),
        "block_counts": doc.block_counts(),
        "char_count": len(doc.content_text()),
    }
    return doc


def parse_html_file(path: Path, source: SourceSpec) -> CleanDocument:
    from contextiq_ingestion.parsers.html_structure import extract_main_html, walk_html_into_sections

    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")

    # Drop noisy chrome before selecting main
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    title = source.title
    if soup.title and soup.title.string:
        title = normalize_ws(soup.title.get_text())
    # AWS docs often have og:title / h1
    h1 = soup.find("h1")
    if h1:
        title = normalize_ws(h1.get_text(" ", strip=True)) or title

    last_updated = None
    for meta_name in ("last-modified", "date", "DC.date"):
        tag = soup.find("meta", attrs={"name": meta_name})
        if tag and tag.get("content"):
            last_updated = tag["content"]
            break

    main = extract_main_html(soup)
    sections = walk_html_into_sections(main, source.id)

    doc = CleanDocument(
        source_id=source.id,
        title=title,
        source_url=source.url,
        family=source.family,
        document_type=DocumentType.HTML,
        last_updated=last_updated,
        topics=list(source.topics),
        sections=sections,
        raw_path=str(path),
        parser="html_structure_v1",
        metadata={"html_title": title},
    )
    doc.stats = {
        "section_count": doc.section_count(),
        "block_counts": doc.block_counts(),
        "char_count": len(doc.content_text()),
    }
    return doc


def parse_pdf_file(path: Path, source: SourceSpec) -> CleanDocument:
    from pypdf import PdfReader

    from contextiq_ingestion.models import Section

    reader = PdfReader(str(path))
    sections: list[Section] = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = collapse_blank_lines(page.extract_text() or "")
        blocks = (
            [ContentBlock(type="paragraph", text=normalize_ws(text))] if text.strip() else []
        )
        sections.append(
            Section(
                id=f"{source.id}__page-{page_index}",
                heading=f"Page {page_index}",
                heading_level=2,
                heading_path=[f"Page {page_index}"],
                page_number=page_index,
                content_blocks=blocks,
            )
        )
    doc = CleanDocument(
        source_id=source.id,
        title=source.title,
        source_url=source.url,
        family=source.family,
        document_type=DocumentType.PDF,
        topics=list(source.topics),
        sections=sections,
        raw_path=str(path),
        parser="pdf_pypdf_v1",
        metadata={"page_count": len(reader.pages)},
    )
    doc.stats = {
        "section_count": doc.section_count(),
        "block_counts": doc.block_counts(),
        "char_count": len(doc.content_text()),
        "page_count": len(reader.pages),
    }
    return doc


def parse_raw_file(path: Path, source: SourceSpec) -> CleanDocument:
    suffix = path.suffix.lower()
    if source.format == DocumentType.PDF or suffix == ".pdf":
        return parse_pdf_file(path, source)
    if source.format in {DocumentType.MARKDOWN, DocumentType.MDX} or suffix in {".md", ".mdx"}:
        return parse_markdown_file(path, source)
    return parse_html_file(path, source)
