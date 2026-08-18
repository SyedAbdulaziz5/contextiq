from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup, NavigableString, Tag

from contextiq_ingestion.models import ContentBlock, Section

SKIP_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "button",
    "iframe",
}


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return value[:80] or "section"


def normalize_ws(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def table_to_block(table: Tag) -> ContentBlock:
    headers: list[str] = []
    rows: list[list[str]] = []

    thead = table.find("thead")
    if thead:
        header_cells = thead.find_all(["th", "td"])
        headers = [normalize_ws(c.get_text(" ", strip=True)) for c in header_cells]

    body = table.find("tbody") or table
    for tr in body.find_all("tr", recursive=False) or body.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        values = [normalize_ws(c.get_text(" ", strip=True)) for c in cells]
        if not any(values):
            continue
        # If no thead and first row looks like headers
        if not headers and tr.find("th"):
            headers = values
            continue
        rows.append(values)

    # Some AWS tables put headers only in first body row
    if not headers and rows:
        # keep as-is; still preserve structure
        pass

    md_lines: list[str] = []
    if headers:
        md_lines.append("| " + " | ".join(headers) + " |")
        md_lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        # pad/truncate to header length when present
        if headers:
            padded = row + [""] * max(0, len(headers) - len(row))
            padded = padded[: len(headers)]
            md_lines.append("| " + " | ".join(padded) + " |")
        else:
            md_lines.append("| " + " | ".join(row) + " |")

    return ContentBlock(
        type="table",
        headers=headers or None,
        rows=rows or None,
        markdown="\n".join(md_lines) if md_lines else None,
        text=None,
    )


def list_to_block(node: Tag) -> ContentBlock:
    items: list[str] = []
    for li in node.find_all("li", recursive=False):
        text = normalize_ws(li.get_text(" ", strip=True))
        if text:
            items.append(text)
    return ContentBlock(
        type="list",
        ordered=node.name == "ol",
        items=items,
    )


class SectionBuilder:
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        self.sections: list[Section] = []
        self._path: list[tuple[int, str]] = []
        self._seq = 0
        self._ensure_root()

    def _ensure_root(self) -> None:
        if not self.sections:
            self.sections.append(
                Section(
                    id=f"{self.source_id}__0000__intro",
                    heading=None,
                    heading_level=None,
                    heading_path=[],
                    content_blocks=[],
                )
            )

    def _current(self) -> Section:
        self._ensure_root()
        return self.sections[-1]

    def start_heading(self, level: int, text: str) -> None:
        text = normalize_ws(text)
        if not text:
            return
        while self._path and self._path[-1][0] >= level:
            self._path.pop()
        self._path.append((level, text))
        path = [t for _, t in self._path]
        self._seq += 1
        section_id = f"{self.source_id}__{self._seq:04d}__{slugify(text)}"
        self.sections.append(
            Section(
                id=section_id,
                heading=text,
                heading_level=level,
                heading_path=path,
                content_blocks=[],
            )
        )

    def add_block(self, block: ContentBlock) -> None:
        # Drop empty blocks
        if block.type in {"paragraph", "blockquote", "code"} and not (block.text or "").strip():
            return
        if block.type == "list" and not block.items:
            return
        if block.type == "table" and not (block.rows or block.headers or block.markdown):
            return
        self._current().content_blocks.append(block)

    def finalize(self) -> list[Section]:
        # drop empty intro if unused
        if (
            self.sections
            and self.sections[0].heading is None
            and not self.sections[0].content_blocks
            and len(self.sections) > 1
        ):
            return self.sections[1:]
        return self.sections


def iter_content_nodes(root: Tag) -> Iterable[Tag]:
    for child in root.children:
        if isinstance(child, NavigableString):
            continue
        if not isinstance(child, Tag):
            continue
        if child.name in SKIP_TAGS:
            continue
        yield child


def extract_main_html(soup: BeautifulSoup) -> Tag:
    """Prefer main/article content; fall back to body."""
    for selector in (
        "main",
        "article",
        "#main-content",
        "#main",
        ".main-content",
        "#content",
        ".awsdocs-content",
        "[role=main]",
    ):
        node = soup.select_one(selector)
        if node and normalize_ws(node.get_text(" ", strip=True)):
            return node
    return soup.body or soup


def walk_html_into_sections(root: Tag, source_id: str) -> list[Section]:
    builder = SectionBuilder(source_id)

    def handle(node: Tag) -> None:
        name = (node.name or "").lower()
        if name in SKIP_TAGS:
            return

        if re.fullmatch(r"h[1-6]", name):
            level = int(name[1])
            builder.start_heading(level, node.get_text(" ", strip=True))
            return

        if name == "table":
            builder.add_block(table_to_block(node))
            return

        if name in {"ul", "ol"}:
            builder.add_block(list_to_block(node))
            return

        if name == "pre":
            code = node.get_text("\n", strip=False)
            language = None
            code_el = node.find("code")
            if code_el and code_el.get("class"):
                for cls in code_el.get("class", []):
                    if cls.startswith("language-"):
                        language = cls.replace("language-", "", 1)
            builder.add_block(
                ContentBlock(type="code", text=collapse_blank_lines(code), language=language)
            )
            return

        if name in {"p", "blockquote"}:
            text = normalize_ws(node.get_text(" ", strip=True))
            if text:
                builder.add_block(
                    ContentBlock(type="blockquote" if name == "blockquote" else "paragraph", text=text)
                )
            return

        if name in {"div", "section", "article", "main", "span", "li"}:
            # Recurse into containers; avoid double-counting nested structured nodes
            for child in list(node.children):
                if isinstance(child, Tag):
                    handle(child)
                elif isinstance(child, NavigableString):
                    text = normalize_ws(str(child))
                    if text:
                        builder.add_block(ContentBlock(type="paragraph", text=text))
            return

        # Fallback: if element has meaningful direct text, keep it
        text = normalize_ws(node.get_text(" ", strip=True))
        if text and name not in {"a", "strong", "em", "code", "span"}:
            # Only keep leaf-ish unknown tags
            if not node.find(["p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "pre"]):
                builder.add_block(ContentBlock(type="paragraph", text=text))

    for child in iter_content_nodes(root):
        handle(child)

    return builder.finalize()
