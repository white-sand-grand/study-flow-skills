#!/usr/bin/env python3
"""Build an offline search index from actual course HTML, including legacy pages."""

import argparse
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from urllib.parse import quote


class SearchParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.main_depth = None
        self.ignored_depth = None
        self.blocks = []
        self.entries = []
        self.title = []
        self.in_title = False
        self.all_text = []
        self.all_math = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.depth += 1
        if tag == "main":
            self.main_depth = self.depth
        if self.main_depth is None:
            return
        if self.ignored_depth is not None:
            return
        if tag in {"script", "style", "nav"} or "data-no-search" in attrs:
            self.ignored_depth = self.depth
            return
        if tag in {"article", "section"} and attrs.get("id"):
            context = ["".join(block["heading"]).strip() for block in self.blocks]
            self.blocks.append({"id": attrs["id"], "depth": self.depth, "text": [], "own_text": [], "math": [], "heading": [], "heading_depth": None, "context": " · ".join(filter(None, context)), "child": False})
            if len(self.blocks) > 1:
                self.blocks[-2]["child"] = True
        if tag in {"h1", "h2", "h3", "h4"}:
            for block in self.blocks:
                if not block["heading"] and block["heading_depth"] is None:
                    block["heading_depth"] = self.depth
        if attrs.get("data-tex"):
            self.add_text(" [公式] ")
            self.all_math.append(attrs["data-tex"])
            for block in self.blocks:
                block["math"].append(attrs["data-tex"])
        if tag == "img" and attrs.get("alt"):
            self.add_text(" " + attrs["alt"] + " ")

    def add_text(self, text):
        self.all_text.append(text)
        for block in self.blocks:
            block["text"].append(text)
        if self.blocks:
            self.blocks[-1]["own_text"].append(text)

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if self.main_depth is None or self.ignored_depth is not None:
            return
        self.add_text(data)
        for block in self.blocks:
            if block["heading_depth"] is not None:
                block["heading"].append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if self.ignored_depth is not None:
            if self.depth == self.ignored_depth:
                self.ignored_depth = None
        else:
            for block in self.blocks:
                if block["heading_depth"] == self.depth:
                    block["heading_depth"] = None
            if self.blocks and self.blocks[-1]["depth"] == self.depth:
                block = self.blocks.pop()
                if block["child"]:
                    block["text"] = block["own_text"]
                self.entries.append(block)
        if tag == "main":
            self.main_depth = None
        self.depth = max(0, self.depth - 1)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.handle_endtag(tag)


def update_search_index(library):
    rows = []
    for page in sorted(library.glob("*.html")):
        parser = SearchParser()
        parser.feed(page.read_text(encoding="utf-8-sig"))
        title = " ".join("".join(parser.title).split()) or page.stem
        blocks = parser.entries or [{"id": "", "heading": [], "text": parser.all_text, "math": parser.all_math, "context": ""}]
        for block in blocks:
            raw_text = " ".join(block["text"])
            text = " ".join(re.sub(r"\\\[.*?\\\]|\\\(.*?\\\)", " [公式] ", raw_text, flags=re.DOTALL).split())
            if not text:
                continue
            heading = " ".join("".join(block["heading"]).split())
            label = " · ".join(filter(None, [block["context"], heading])) or title
            url = quote(page.name) + ("#" + quote(block["id"]) if block["id"] else "")
            rows.append({"page": page.name, "chapter": title, "title": label, "text": text, "keywords": " ".join(block.get("math", [])) + " " + raw_text, "url": url})
    target = library / "assets/study-flow/v1/search-index.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    target.write_text("window.STUDY_FLOW_INDEX = " + serialized + ";\n", encoding="utf-8")
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", type=Path)
    args = parser.parse_args()
    if not args.library.is_dir():
        parser.error("Library directory does not exist")
    print(f"Indexed {update_search_index(args.library.resolve())} course blocks")


if __name__ == "__main__":
    main()
