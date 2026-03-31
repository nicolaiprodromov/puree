"""
Lightweight Markdown-to-containers renderer for Puree.

Public API:
    from puree.markdown import render_markdown
    render_markdown(container, text, fonts=None, classes=None)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

DEFAULT_CLASSES = {
    "paragraph": "md_paragraph",
    "heading_1": "md_h1",
    "heading_2": "md_h2",
    "heading_3": "md_h3",
    "heading_n": "md_heading",
    "code_block": "md_code_block",
    "code_inline": "md_code_inline",
    "list_item": "md_list_item",
    "blockquote": "md_blockquote",
    "divider": "md_divider",
    "inline_row": "md_inline_row",
    "bold": "md_bold",
    "text_span": "md_text_span",
}


@dataclass
class Block:
    type: str
    text: str = ""
    level: int = 1
    spans: list = field(default_factory=list)


_INLINE_RE = re.compile(
    r"(\*\*(.+?)\*\*"
    r"|__(.+?)__"
    r"|`(.+?)`)"
)


def _parse_inline(text: str) -> list:
    """Return list of (span_type, text) tuples. span_type: 'text'|'bold'|'code'."""
    spans = []
    last = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > last:
            spans.append(("text", text[last : m.start()]))
        if m.group(2):
            spans.append(("bold", m.group(2)))
        elif m.group(3):
            spans.append(("bold", m.group(3)))
        elif m.group(4):
            spans.append(("code", m.group(4)))
        last = m.end()
    if last < len(text):
        spans.append(("text", text[last:]))
    return spans


def parse_markdown(text: str) -> List[Block]:
    """Parse *text* into a flat list of Block objects."""
    blocks: List[Block] = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(Block(type="code_block", text="\n".join(code_lines)))
            i += 1
            continue

        if re.match(r"^\s*---+\s*$", line):
            blocks.append(Block(type="divider"))
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            blocks.append(Block(type="heading", text=m.group(2).strip(), level=level))
            i += 1
            continue

        m = re.match(r"^[-*]\s+(.*)", line)
        if m:
            blocks.append(Block(type="list_item", text=m.group(1)))
            i += 1
            continue

        m = re.match(r"^>\s?(.*)", line)
        if m:
            blocks.append(Block(type="blockquote", text=m.group(1)))
            i += 1
            continue

        if line.strip() == "":
            i += 1
            continue

        spans = _parse_inline(line)
        has_markup = any(t != "text" for t, _ in spans)
        if has_markup:
            blocks.append(Block(type="inline_row", text=line, spans=spans))
        else:
            blocks.append(Block(type="paragraph", text=line))
        i += 1

    return blocks


def _heading_class_key(level: int) -> str:
    return f"heading_{level}" if level <= 3 else "heading_n"


def _build_children(parent, blocks: List[Block], fonts: dict, cls: dict) -> None:
    """Append Container objects for each block directly into *parent.children*."""
    from .components.container import Container

    pid = parent.id or "md"

    for i, block in enumerate(blocks):
        block_id = f"{pid}_md_{i}"

        if block.type == "divider":
            c = Container()
            c.id = block_id
            c.classes = [cls.get("divider", DEFAULT_CLASSES["divider"])]
            c.parent = parent
            parent.children.append(c)

        elif block.type == "heading":
            c = Container()
            c.id = block_id
            c.text = block.text
            key = _heading_class_key(block.level)
            c.classes = [cls.get(key, DEFAULT_CLASSES.get(key, DEFAULT_CLASSES["heading_n"]))]
            c.font = fonts.get("bold", "NeueMontreal-Bold")
            c.parent = parent
            parent.children.append(c)

        elif block.type == "code_block":
            c = Container()
            c.id = block_id
            c.text = block.text
            c.classes = [cls.get("code_block", DEFAULT_CLASSES["code_block"])]
            c.font = fonts.get("mono", fonts.get("regular", "default"))
            c.parent = parent
            parent.children.append(c)

        elif block.type == "list_item":
            c = Container()
            c.id = block_id
            c.text = "• " + block.text
            c.classes = [cls.get("list_item", DEFAULT_CLASSES["list_item"])]
            c.font = fonts.get("regular", "default")
            c.parent = parent
            parent.children.append(c)

        elif block.type == "blockquote":
            c = Container()
            c.id = block_id
            c.text = block.text
            c.classes = [cls.get("blockquote", DEFAULT_CLASSES["blockquote"])]
            c.font = fonts.get("regular", "default")
            c.parent = parent
            parent.children.append(c)

        elif block.type == "paragraph":
            c = Container()
            c.id = block_id
            c.text = block.text
            c.classes = [cls.get("paragraph", DEFAULT_CLASSES["paragraph"])]
            c.font = fonts.get("regular", "default")
            c.parent = parent
            parent.children.append(c)

        elif block.type == "inline_row":
            row = Container()
            row.id = block_id
            row.classes = [cls.get("inline_row", DEFAULT_CLASSES["inline_row"])]
            row.parent = parent
            parent.children.append(row)

            for j, (span_type, span_text) in enumerate(block.spans):
                span = Container()
                span.id = f"{row.id}_span_{j}"
                span.text = span_text
                span.parent = row

                if span_type == "bold":
                    span.font = fonts.get("bold", "NeueMontreal-Bold")
                    span.classes = [cls.get("bold", DEFAULT_CLASSES["bold"])]
                elif span_type == "code":
                    span.font = fonts.get("mono", fonts.get("regular", "default"))
                    span.classes = [cls.get("code_inline", DEFAULT_CLASSES["code_inline"])]
                else:
                    span.font = fonts.get("regular", "default")
                    span.classes = [cls.get("text_span", DEFAULT_CLASSES["text_span"])]

                row.children.append(span)


def render_markdown(
    container,
    text: str,
    app=None,
    fonts: dict = None,
    classes: dict = None,
) -> None:
    """Clear *container*'s children and populate them with rendered markdown.

    Args:
        container: The Container to render into (children will be replaced).
        text:      Markdown source string.
        app:       Optional UI/app reference (accepted for API compatibility;
                   the rebuild uses dynamic_manager internally).
        fonts:     Optional font overrides. Keys: 'regular', 'bold', 'mono'.
        classes:   Optional CSS class overrides. Keys match DEFAULT_CLASSES.
    """
    if fonts is None:
        fonts = {}
    if classes is None:
        classes = {}

    cls = {**DEFAULT_CLASSES, **classes}

    blocks = parse_markdown(text)

    for child in container.children:
        child.parent = None
    container.children.clear()

    _build_children(container, blocks, fonts, cls)

    from .dynamic import dynamic_manager

    ui = dynamic_manager._ui
    if ui is not None:
        ui._rebuild_after_structural_change()
    else:
        logger.warning(
            "render_markdown: dynamic_manager._ui is None — "
            "children populated but layout rebuild deferred until UI loads."
        )
