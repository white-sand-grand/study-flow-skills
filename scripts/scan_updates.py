#!/usr/bin/env python3
"""Find new/changed course inputs; record only sources actually processed and checked."""

import argparse
import hashlib
import json
from pathlib import Path

EXTENSIONS = {".pdf", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".docx", ".md", ".txt"}
IGNORED = {".git", ".venv", "node_modules", "assets", "sources", "page-specs", "__pycache__"}


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_key(path, course):
    try:
        return path.resolve().relative_to(course.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_state(library):
    path = library / "source-index.json"
    if not path.exists():
        return {"version": 1, "sources": []}
    state = json.loads(path.read_text(encoding="utf-8-sig"))
    if state.get("version") != 1 or not isinstance(state.get("sources"), list):
        raise ValueError("Unsupported source-index.json; inspect the existing index")
    return state


def scan(course, library, explicit_sources=None, scope=None):
    state = load_state(library)
    candidates = explicit_sources if explicit_sources else course.rglob("*")
    result = []
    for source in sorted(set(path.resolve() for path in candidates)):
        if not source.is_file():
            if explicit_sources:
                raise ValueError(f"Not a source file: {source}")
            continue
        if not explicit_sources:
            if source == library or library in source.parents:
                continue
            relative_parts = source.relative_to(course).parts
            if any(part in IGNORED or part.startswith(".") for part in relative_parts):
                continue
            if source.name in {"AGENTS.md", "CLAUDE.md"} or source.suffix.lower() not in EXTENSIONS:
                continue
        key, sha = source_key(source, course), fingerprint(source)
        previous = [entry for entry in state["sources"] if entry.get("file") == key]
        same_content = [entry for entry in previous if entry.get("sha256") == sha]
        matching = [entry for entry in same_content if scope is None or entry.get("scope") == scope]
        status = "new"
        if matching:
            complete = [entry for entry in matching if entry.get("status") == "complete"]
            unresolved = [entry for entry in (previous if scope is None else matching) if entry.get("status") != "complete"]
            status = "unchanged" if complete and not unresolved else "pending"
            if status == "unchanged" and not all(all((library / page.split("#")[0]).is_file() for page in entry.get("pages", [])) and entry.get("pages") for entry in complete):
                status = "needs-rebuild"
        elif same_content:
            status = "new-selection"
        elif previous:
            status = "changed"
        result.append({"file": key, "sha256": sha, "status": status, "scope": scope})
    return result


def record(course, library, source, scope, sha, pages, status):
    if fingerprint(source) != sha:
        raise ValueError("Source changed since scan; re-read it before recording completion")
    for page in pages:
        target = (library / page.split("#")[0]).resolve()
        if library not in target.parents or not target.is_file():
            raise ValueError(f"Output page must exist inside the library: {page}")
    state = load_state(library)
    key = source_key(source, course)
    state["sources"] = [entry for entry in state["sources"] if not (entry.get("file") == key and entry.get("scope") == scope)]
    state["sources"].append({"file": key, "sha256": sha, "scope": scope, "status": status, "pages": pages})
    library.mkdir(parents=True, exist_ok=True)
    (library / "source-index.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["scan", "record"])
    parser.add_argument("--course", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--source", type=Path, action="append")
    parser.add_argument("--scope", help="Explicit task selection, e.g. ch03-p58-62; omit for general reruns")
    parser.add_argument("--sha256", help="Source hash observed before processing")
    parser.add_argument("--page", action="append")
    parser.add_argument("--status", choices=["complete", "partial", "needs-source"], default="complete")
    args = parser.parse_args()
    course, library = args.course.resolve(), args.library.resolve()
    if not course.is_dir():
        parser.error("--course must be an existing course directory")
    try:
        if args.action == "scan":
            print(json.dumps(scan(course, library, args.source, args.scope), ensure_ascii=False, indent=2))
        else:
            if not args.source or len(args.source) != 1 or not args.sha256 or not args.page or not args.scope:
                parser.error("record requires one --source, --scope, --sha256, and at least one --page")
            record(course, library, args.source[0].resolve(), args.scope, args.sha256, args.page, args.status)
            print("Recorded the processed source; unprocessed inputs were not marked complete.")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
