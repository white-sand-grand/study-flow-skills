#!/usr/bin/env python3
"""Build study-flow's fixed index, chapter or homework HTML from an authored JSON spec."""

import argparse
from html import escape
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit

from build_search_index import update_search_index

ASSETS = Path(__file__).resolve().parents[1] / "assets"
SECTIONS = {
    "index": [("overview", "学习总览"), ("chapters", "章节知识"), ("homework", "作业题库"), ("topics", "知识点与题型索引"), ("review", "期末复习入口")],
    "chapter": [("overview", "本章地图"), ("concepts", "核心概念"), ("theory", "公式、理论与适用条件"), ("types", "题型与解法"), ("examples", "例题解析"), ("exam", "考点与依据"), ("pitfalls", "易错点"), ("review", "自测与复习")],
}
PARTS = {
    "en": [("original", "原题", "en"), ("translation", "中文翻译", "zh-CN"), ("terms", "中英专业名词", "zh-CN"), ("solution_en", "English Solution", "en"), ("analysis_zh", "中文解析", "zh-CN"), ("theory", "公式定理 / 理论依据", "zh-CN"), ("pitfalls", "易错点", "zh-CN")],
    "zh": [("original", "原题", "zh-CN"), ("analysis_zh", "中文解题过程与解析", "zh-CN"), ("theory", "公式定理 / 理论依据", "zh-CN"), ("pitfalls", "易错点", "zh-CN")],
}
LABELS = {"index": "课程学习库", "chapter": "课程知识总结", "homework": "作业解析与复习"}


def required(mapping, key):
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing nonempty text field: {key}")
    return value


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*", value):
        raise ValueError(f"Invalid anchor identifier: {value!r}")
    return value


def build(spec, asset_prefix="assets/study-flow/v1"):
    kind = spec.get("kind")
    if kind not in LABELS:
        raise ValueError("kind must be index, chapter or homework")
    title, course = required(spec, "title"), required(spec, "course")
    parts, toc = [], []
    image_links = []
    omitted = spec.get("omit_sections", [])
    if omitted and not spec.get("user_omission_note"):
        raise ValueError("Omitting default sections requires user_omission_note")

    def panel(key, label, body, number=None):
        identifier(key)
        toc.append((key, label))
        prefix = f'<span class="section-number">{number:02}</span>' if number else ""
        exclude_search = ' data-no-search' if key == "original-images" else ''
        parts.append(f'<section class="panel" id="{key}"{exclude_search}><h2>{prefix}{escape(label)}</h2>{body}</section>')

    if kind in SECTIONS:
        sections = spec.get("sections", {})
        allowed = {key for key, _ in SECTIONS[kind]}
        if set(sections) - allowed or set(omitted) - allowed:
            raise ValueError("Unknown section keys")
        for number, (key, label) in enumerate(SECTIONS[kind], 1):
            if key not in omitted:
                panel(key, label, required(sections, key), number)
    else:
        if omitted:
            raise ValueError("Homework section omissions must be specified per problem")
        panel("overview", "本次作业", required(spec, "overview_html"))
        problems = spec.get("problems", [])
        if not problems:
            raise ValueError("Homework needs at least one problem")
        used = {"overview", "answers", "sources", "content", "page-nav", "study-sidebar", "original-images", "course-search"}
        for problem in problems:
            key = identifier(problem.get("id"))
            if key in used:
                raise ValueError(f"Duplicate or reserved problem id: {key}")
            used.add(key)
            language = problem.get("language")
            if language not in PARTS:
                raise ValueError("Each problem language must be zh or en")
            label = required(problem, "title")
            fields = problem.get("parts", {})
            allowed = {name for name, _, _ in PARTS[language]}
            skips = problem.get("omit_sections", [])
            if skips and not problem.get("user_omission_note"):
                raise ValueError("Problem omissions require user_omission_note")
            if set(fields) - allowed or set(skips) - allowed:
                raise ValueError(f"Unexpected fields for {language} problem {key}")
            toc.append((key, label))
            branch_label = "英文材料 · 完整双语流程" if language == "en" else "中文材料 · 中文流程"
            body = [f'<article class="problem" id="{key}" data-language="{language}"><h2>{escape(label)}</h2><span class="tag">{branch_label}</span>']
            for number, (name, heading, lang) in enumerate(PARTS[language], 1):
                if name not in skips:
                    text = required(fields, name)
                    body.append(f'<section class="problem-part" id="{key}-{name}" data-part="{name}" lang="{lang}"><h3><span class="step-label">{number:02}</span>{heading}</h3>{text}</section>')
            body.append(f'<div class="answer"><strong>答案 / 结论</strong>{required(problem, "answer_html")}</div></article>')
            parts.append("\n".join(body))
        answer_rows = "".join(f'<tr><td><a href="#{escape(p["id"], quote=True)}">{escape(p["title"])}</a></td><td>{p["answer_html"]}</td></tr>' for p in problems)
        panel("answers", "答案速查", '<div class="table-scroll"><table><thead><tr><th>题目</th><th>结论</th></tr></thead><tbody>' + answer_rows + '</tbody></table></div>')
        images = spec.get("source_images", [])
        if not images and not spec.get("source_images_note"):
            raise ValueError("Homework needs source_images, or source_images_note explaining why no images were supplied")
        if images:
            gallery = ['<p>原图保存在本学习库。点击侧栏入口前会记录阅读位置，可随时返回。</p><button type="button" class="source-return" data-source-return hidden>← 返回刚才的阅读位置</button>']
            for image in images:
                key = identifier(image.get("id"))
                if key in used:
                    raise ValueError(f"Duplicate or reserved image id: {key}")
                used.add(key)
                src, label = required(image, "src"), required(image, "label")
                url = urlsplit(src)
                if url.scheme or url.netloc or src.startswith(("/", "\\")):
                    raise ValueError("Source images must use relative local paths")
                image_links.append((key, label))
                gallery.append(f'<figure id="{key}"><img src="{escape(src, quote=True)}" alt="{escape(label, quote=True)}"><figcaption>{escape(label)}</figcaption><button type="button" class="source-return" data-source-return hidden>← 返回刚才的阅读位置</button></figure>')
            panel("original-images", "作业原图", "\n".join(gallery))

    panel("sources", "来源与核验记录", required(spec, "sources_html"))
    home = spec.get("home", "index.html")
    if not isinstance(home, str) or ":" in home or home.startswith(("/", "\\", "#")):
        raise ValueError("home must be a relative local file reference")
    nav = '<a href="#course-search">关键词搜索</a>' + "".join(f'<a href="#{key}"' + (' data-source-jump' if key == "original-images" else '') + f'>{escape(label)}</a>' for key, label in toc)
    source_shortcuts = ""
    source_mobile_link = ""
    if image_links:
        source_shortcuts = '<div class="source-shortcuts" aria-label="作业原图快捷入口"><strong>作业原图</strong><a href="#original-images" data-source-jump>查看全部原图 →</a>' + "".join(f'<a href="#{key}" data-source-jump>{escape(label)}</a>' for key, label in image_links) + '</div>'
        source_mobile_link = '<a class="source-mobile-link" href="#original-images" data-source-jump>查看作业原图</a>'
    tags = [course, LABELS[kind]] + spec.get("tags", [])
    meta = "".join(f'<span>{escape(str(tag))}</span>' for tag in tags)
    subtitle = escape(spec.get("subtitle", "知识、方法与解题资产，持续积累以备期末复习。"))
    content = "\n".join(parts)
    return f'''<!doctype html>
<html lang="zh-CN" data-study-kind="{kind}" data-template-version="1">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} · {escape(course)}</title>
  <link rel="stylesheet" href="{asset_prefix}/vendor/katex/katex.min.css">
  <link rel="stylesheet" href="{asset_prefix}/study-ui.css">
  <script defer src="{asset_prefix}/vendor/katex/katex.min.js"></script>
  <script defer src="{asset_prefix}/vendor/katex/mhchem.min.js"></script>
  <script defer src="{asset_prefix}/search-index.js"></script>
  <script defer src="{asset_prefix}/study-ui.js"></script>
</head>
<body>
<a class="skip-link" href="#content">跳转到正文</a>
<header class="hero"><div class="hero-inner">
  <p class="eyebrow">STUDY LIBRARY / 学习资产</p><h1>{escape(title)}</h1>
  <p class="subtitle">{subtitle}</p><div class="hero-meta">{meta}</div>
</div></header>
<div class="layout">
  <button class="sidebar-reopen" type="button" data-sidebar-open aria-expanded="false" aria-controls="study-sidebar" hidden>☰ 打开目录</button>
  <aside class="sidebar" id="study-sidebar" aria-label="页面目录"><div class="sidebar-heading"><h2>本页导航</h2><button type="button" class="sidebar-close" data-sidebar-close aria-label="关闭侧边目录">关闭 ×</button></div>
    <button class="menu-toggle" type="button" data-menu aria-expanded="false" aria-controls="page-nav">展开 / 收起目录</button>
    {source_shortcuts}
    <nav id="page-nav"><a class="home-link" href="{escape(home, quote=True)}">← 学习库总目录</a>{nav}</nav>
    <div class="toolbar"><button type="button" data-expand>展开 / 收起自测</button><button type="button" data-print>打印 / 保存 PDF</button></div>
  </aside>
  <main id="content"><section class="panel search-panel" id="course-search" data-no-search>
    <h2>关键词搜索</h2><form class="search-form" role="search">
      <label class="search-label" for="keyword-search">查找知识点、题号、中英文术语</label>
      <div class="search-controls"><input id="keyword-search" type="search" data-search-input placeholder="例如：条件概率、velocity、初值 积分" autocomplete="off">
      <select data-search-scope aria-label="搜索范围"><option value="course">全学习库</option><option value="page">本页</option></select>
      <button type="button" data-search-clear>清空</button></div>
    </form><p class="small" data-search-status role="status" aria-live="polite">支持中文、英文和多个关键词；点击结果直达内容。</p>
    <div data-search-results></div><button type="button" data-search-more hidden>显示更多结果</button>
  </section>{content}</main>
</div>
<footer class="footer"><a href="{escape(home, quote=True)}">学习库总目录</a><a href="#content">回到正文</a>以原始课程材料及题目条件为准。</footer>
{source_mobile_link}
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--page", required=True, help="HTML filename at library root")
    parser.add_argument("--replace", action="store_true", help="Replace a page after reviewing its existing contents")
    args = parser.parse_args()
    if Path(args.page).name != args.page or not args.page.endswith(".html"):
        parser.error("--page must be a plain .html filename, not a path")
    root = args.library.resolve()
    output = root / args.page
    if output.exists() and not args.replace:
        parser.error(f"Page exists; inspect it before using --replace: {output}")
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
        html = build(spec)
    except (ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    if not (ASSETS / "vendor/katex/katex.min.js").is_file():
        parser.error("Bundled local KaTeX runtime is missing")
    target = root / "assets/study-flow/v1"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("study-ui.css", "study-ui.js"):
        shutil.copy2(ASSETS / name, target / name)
    shutil.copytree(ASSETS / "vendor", target / "vendor", dirs_exist_ok=True)
    output.write_text(html, encoding="utf-8")
    count = update_search_index(root)
    print(f"Built {spec['kind']}: {output}")
    print(f"Updated offline search index: {count} blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
