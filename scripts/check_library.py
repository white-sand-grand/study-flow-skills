#!/usr/bin/env python3
"""Check local HTML links, fragments and assets without modifying the library."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors = set()
        self.references = []
        self.has_base = False
        self.is_study_page = False
        self.formula_issues = []
        self.remote_assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html" and attrs.get("data-template-version"):
            self.is_study_page = True
        if "data-tex" in attrs or "formula-image" in attrs.get("class", "").split():
            for key in ("data-formula-id", "data-source"):
                if not attrs.get(key, "").strip():
                    self.formula_issues.append(f"line {self.getpos()[0]}: formula missing {key}")
            if "data-tex" in attrs and not attrs["data-tex"].strip():
                self.formula_issues.append(f"line {self.getpos()[0]}: empty TeX formula")
        if attrs.get("id"):
            self.anchors.add(attrs["id"])
        if tag == "a" and attrs.get("name"):
            self.anchors.add(attrs["name"])
        if tag == "base" and attrs.get("href"):
            self.has_base = True
        keys = []
        if tag in {"a", "link", "area"}:
            keys.append("href")
        if tag in {"img", "script", "iframe", "audio", "video", "source", "embed", "input", "track"}:
            keys.append("src")
        if tag == "video":
            keys.append("poster")
        if tag == "object":
            keys.append("data")
        for key in keys:
            if attrs.get(key):
                self.references.append((attrs[key], self.getpos()[0]))
                if tag not in {"a", "area"} and (re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", attrs[key]) or attrs[key].startswith("//")):
                    self.remote_assets.append(f"line {self.getpos()[0]}: nonlocal asset: {attrs[key]}")

    handle_startendtag = handle_starttag


def check_library(root):
    pages = sorted(p for p in root.rglob("*") if p.suffix.lower() in {".html", ".htm"})
    errors = []
    cache = {}

    def parse(path):
        path = path.resolve()
        if path not in cache:
            parser = PageParser()
            parser.feed(path.read_text(encoding="utf-8-sig"))
            parser.close()
            cache[path] = parser
        return cache[path]

    if not pages:
        errors.append("No HTML pages found")
    for page in pages:
        label = page.relative_to(root)
        try:
            parsed = parse(page)
        except (OSError, UnicodeError) as exc:
            errors.append(f"{label}: cannot read HTML: {exc}")
            continue
        if parsed.has_base:
            errors.append(f"{label}: base href is unsupported; use relative local references")
            continue
        if parsed.is_study_page:
            errors.extend(f"{label}: {issue}" for issue in parsed.formula_issues + parsed.remote_assets)
        for value, line in parsed.references:
            try:
                url = urlsplit(value)
            except ValueError as exc:
                errors.append(f"{label}:{line}: invalid URL {value!r}: {exc}")
                continue
            if url.scheme or url.netloc:
                continue
            local_path = unquote(url.path)
            if local_path.startswith("/"):
                errors.append(f"{label}:{line}: root-relative reference is not portable: {value}")
                continue
            target = (page.parent / local_path).resolve() if local_path else page.resolve()
            if not target.exists():
                errors.append(f"{label}:{line}: missing target: {value}")
                continue
            if target.is_dir():
                errors.append(f"{label}:{line}: directory link needs an explicit file: {value}")
                continue
            fragment = unquote(url.fragment)
            if fragment and not fragment.startswith(":~:text=") and target.suffix.lower() in {".html", ".htm"}:
                try:
                    if fragment not in parse(target).anchors:
                        errors.append(f"{label}:{line}: missing anchor: {value}")
                except (OSError, UnicodeError) as exc:
                    errors.append(f"{label}:{line}: cannot check target: {exc}")
    return len(pages), errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", type=Path, help="Course library directory")
    args = parser.parse_args()
    root = args.library.resolve()
    if not root.is_dir():
        parser.error(f"Not a directory: {root}")
    count, errors = check_library(root)
    if errors:
        print(f"FAIL: {len(errors)} issue(s) in {count} HTML page(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS: local references checked in {count} HTML page(s)")
    print("Not checked: remote URLs, CSS URLs, srcset, visual layout, or academic correctness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
