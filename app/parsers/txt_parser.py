"""TXT 小说解析 —— 智能分章 + 编码检测"""

import re
import chardet
from typing import List, Tuple

from app.core.chapter import Chapter
from app.utils.constants import CHAPTER_PATTERNS


def detect_encoding(filepath: str) -> str:
    """检测文件编码"""
    with open(filepath, "rb") as f:
        raw = f.read(100000)  # 读取前 100KB 检测
    result = chardet.detect(raw)
    encoding = result.get("encoding", "utf-8")
    confidence = result.get("confidence", 0)

    if encoding and confidence > 0.7:
        # 统一 GB 系列编码
        if encoding.upper() in ("GB2312", "GBK", "GB18030"):
            return "gbk"
        if encoding.upper() == "UTF-8":
            return "utf-8"
        return encoding.lower()
    return "utf-8"


def _is_chapter_title(line: str) -> Tuple[bool, int]:
    """判断一行是否为章节标题，返回 (是否匹配, 优先级)"""
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False, -1

    for pattern, priority in CHAPTER_PATTERNS:
        if re.match(pattern, stripped):
            return True, priority
    return False, -1


def parse_txt(filepath: str) -> Tuple[str, str, List[Chapter]]:
    """
    解析 TXT 小说文件

    Returns:
        (标题, 作者, 章节列表)
    """
    encoding = detect_encoding(filepath)

    with open(filepath, "r", encoding=encoding, errors="replace") as f:
        content = f.read()

    lines = content.split("\n")

    # 尝试从前几行提取标题和作者
    title = "未命名"
    author = ""
    for i, line in enumerate(lines[:20]):
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r"^(?:书名|小说名|作品名|标题)[：:]\s*(.+)", stripped)
        if m:
            title = m.group(1)
        else:
            m = re.match(r"^(?:作者|著|著者)[：:]\s*(.+)", stripped)
            if m:
                author = m.group(1)

    # 如果没有元信息，用文件名作为标题
    if title == "未命名":
        import os
        basename = os.path.splitext(os.path.basename(filepath))[0]
        title = basename

    # 扫描分章
    chapter_boundaries = []  # [(line_index, title_text, priority), ...]

    for i, line in enumerate(lines):
        is_chap, priority = _is_chapter_title(line)
        if is_chap:
            chapter_boundaries.append((i, line.strip(), priority))

    # 构建章节
    chapters = []

    if not chapter_boundaries:
        # 没有分章标记 → 整本书作为一章
        chapters.append(Chapter(
            index=0,
            title="全文",
            raw_text=content.strip(),
        ))
    else:
        # 第一章标题前的内容 → "前言"
        first_boundary = chapter_boundaries[0][0]
        preamble = "\n".join(lines[:first_boundary]).strip()
        if len(preamble) > 50:  # 有实质内容才创建前言
            chapters.append(Chapter(
                index=0,
                title="前言",
                raw_text=preamble,
            ))

        # 逐章提取
        for idx, (start_line, title_text, _) in enumerate(chapter_boundaries):
            # 正文从标题下一行开始
            content_start = start_line + 1

            # 找到下一章的起始行
            if idx + 1 < len(chapter_boundaries):
                content_end = chapter_boundaries[idx + 1][0]
            else:
                content_end = len(lines)

            chapter_text = "\n".join(lines[content_start:content_end]).strip()

            if chapter_text:
                chapters.append(Chapter(
                    index=len(chapters),
                    title=title_text,
                    raw_text=chapter_text,
                ))

    return title, author, chapters
