from __future__ import annotations

from pathlib import Path

from contextiq_ingestion.models import DocumentType, SourceSpec
from contextiq_ingestion.parsers import parse_html_file, parse_markdown_file


def test_markdown_preserves_table_list_code(tmp_path: Path) -> None:
    md = """---
title: Quotas
---

# Quotas

Intro.

## Limits

| Resource | Quota |
| --- | --- |
| Timeout | 900 seconds |

- one
- two

```ts
 console.log("x")
```
"""
    path = tmp_path / "q.md"
    path.write_text(md, encoding="utf-8")
    source = SourceSpec(
        id="test-md",
        title="Quotas",
        url="https://example.com/q",
        format=DocumentType.MARKDOWN,
        family="test",
    )
    doc = parse_markdown_file(path, source)
    types = {b.type for s in doc.sections for b in s.content_blocks}
    assert "table" in types
    assert "list" in types
    assert "code" in types
    assert doc.section_count() >= 2
    assert "900 seconds" in doc.content_text()


def test_html_preserves_headings_and_table(tmp_path: Path) -> None:
    html = """
    <html><head><title>Lambda limits</title></head>
    <body>
      <main>
        <h1>Lambda quotas</h1>
        <p>Account quotas apply per Region.</p>
        <h2>Function configuration</h2>
        <table>
          <thead><tr><th>Resource</th><th>Quota</th></tr></thead>
          <tbody><tr><td>Function timeout</td><td>900 seconds (15 minutes)</td></tr></tbody>
        </table>
        <ul><li>Concurrent executions</li><li>Storage</li></ul>
      </main>
    </body></html>
    """
    path = tmp_path / "aws.html"
    path.write_text(html, encoding="utf-8")
    source = SourceSpec(
        id="test-html",
        title="Lambda quotas",
        url="https://example.com/limits",
        format=DocumentType.HTML,
        family="aws",
    )
    doc = parse_html_file(path, source)
    assert any(s.heading == "Function configuration" for s in doc.sections)
    assert any(b.type == "table" for s in doc.sections for b in s.content_blocks)
    assert "900 seconds" in doc.content_text()
    assert any(b.type == "list" for s in doc.sections for b in s.content_blocks)
