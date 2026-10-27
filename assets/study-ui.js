"use strict";
document.documentElement.classList.add("js");

// TeX is stored in attributes, never executed as HTML. Errors remain conspicuous.
const formulas = [...document.querySelectorAll("[data-tex]")];
for (const element of formulas) {
  try {
    if (!window.katex) throw new Error("本地公式渲染器未加载");
    window.katex.render(element.dataset.tex, element, {
      displayMode: element.classList.contains("math-display"),
      throwOnError: true,
      trust: false,
      strict: "warn",
      output: "htmlAndMathml",
    });
    element.dataset.mathState = "rendered";
  } catch (error) {
    element.dataset.mathState = "error";
    const message = document.createElement("strong");
    message.className = "math-error";
    message.textContent = "公式尚未正确渲染，请核对原式：";
    const source = document.createElement("code");
    source.textContent = element.dataset.tex;
    element.replaceChildren(message, source);
  }
}
document.documentElement.dataset.mathReady = "true";
document.documentElement.dataset.mathErrors = String(document.querySelectorAll('[data-math-state="error"]').length);

const menu = document.querySelector("[data-menu]");
const nav = document.querySelector(".sidebar nav");
// Build a second-level index for each chapter block and each problem's steps.
const navigationTargets = [...document.querySelectorAll("main > section[id], main > article[id]")];
for (const section of [...navigationTargets]) {
  const parentLink = [...(nav?.querySelectorAll('a[href^="#"]') || [])].find(link => link.getAttribute("href") === `#${section.id}`);
  if (!parentLink) continue;
  let previous = parentLink;
  const subparts = section.matches("article") ? section.querySelectorAll(".problem-part") : section.querySelectorAll("h3");
  let index = 0;
  for (const subpart of subparts) {
    index += 1;
    if (!subpart.id) {
      let candidate = `${section.id}-sub-${index}`;
      while (document.getElementById(candidate)) candidate += "-item";
      subpart.id = candidate;
    }
    const heading = subpart.matches("h3") ? subpart : subpart.querySelector("h3");
    const link = document.createElement("a");
    link.className = "nav-sub";
    link.setAttribute("href", `#${subpart.id}`);
    link.textContent = heading?.textContent.trim() || "分块";
    previous.after(link);
    previous = link;
    navigationTargets.push(subpart);
  }
}
const layout = document.querySelector(".layout");
const reopen = document.querySelector("[data-sidebar-open]");
document.querySelector("[data-sidebar-close]")?.addEventListener("click", () => {
  layout.classList.add("sidebar-hidden");
  reopen.hidden = false;
  reopen.setAttribute("aria-expanded", "false");
  reopen.focus();
});
reopen?.addEventListener("click", () => {
  layout.classList.remove("sidebar-hidden");
  reopen.hidden = true;
  reopen.setAttribute("aria-expanded", "true");
  if (window.innerWidth <= 850) {
    nav?.classList.add("is-open");
    menu?.setAttribute("aria-expanded", "true");
  }
  document.querySelector("[data-sidebar-close]")?.focus();
});
menu?.addEventListener("click", () => {
  const open = menu.getAttribute("aria-expanded") !== "true";
  menu.setAttribute("aria-expanded", String(open));
  nav.classList.toggle("is-open", open);
});
nav?.addEventListener("click", (event) => {
  if (event.target.closest("a") && window.innerWidth <= 850) {
    nav.classList.remove("is-open");
    menu?.setAttribute("aria-expanded", "false");
  }
});

// Keep the document intact while searching: results navigate to exact blocks.
const searchInput = document.querySelector("[data-search-input]");
const searchScope = document.querySelector("[data-search-scope]");
const searchResults = document.querySelector("[data-search-results]");
const searchStatus = document.querySelector("[data-search-status]");
const searchMore = document.querySelector("[data-search-more]");
let searchLimit = 30;
const normalizeSearch = value => String(value).normalize("NFKC").toLocaleLowerCase();
const pageName = decodeURIComponent(location.pathname.split("/").pop());
function addHighlightedText(parent, text, words) {
  const normalized = normalizeSearch(text);
  const ranges = [];
  for (const word of words) {
    let start = 0;
    let position;
    while ((position = normalized.indexOf(word, start)) >= 0) {
      ranges.push([position, position + word.length]);
      start = position + word.length;
    }
  }
  ranges.sort((a, b) => a[0] - b[0]);
  let cursor = 0;
  for (const [start, end] of ranges) {
    if (start < cursor) continue;
    parent.append(document.createTextNode(text.slice(cursor, start)));
    const mark = document.createElement("mark");
    mark.textContent = text.slice(start, end);
    parent.append(mark);
    cursor = end;
  }
  parent.append(document.createTextNode(text.slice(cursor)));
}
function renderSearch() {
  if (!searchInput || !searchResults) return;
  const words = normalizeSearch(searchInput.value).trim().split(/\s+/).filter(Boolean);
  searchResults.replaceChildren();
  searchMore.hidden = true;
  if (!words.length) {
    searchStatus.textContent = "支持中文、英文和多个关键词；点击结果直达内容。";
    return;
  }
  const index = window.STUDY_FLOW_INDEX;
  if (!Array.isArray(index)) {
    searchStatus.textContent = "搜索索引尚未构建，请更新学习库搜索索引。";
    return;
  }
  const matches = index.filter(item => (searchScope.value !== "page" || item.page === pageName)
    && words.every(word => normalizeSearch(`${item.chapter} ${item.title} ${item.text} ${item.keywords || ""}`).includes(word)));
  searchStatus.textContent = matches.length ? `找到 ${matches.length} 条结果，显示前 ${Math.min(searchLimit, matches.length)} 条。` : "没有匹配结果，请尝试其他关键词或切换搜索范围。";
  for (const item of matches.slice(0, searchLimit)) {
    const card = document.createElement("article");
    card.className = "search-result";
    const chapter = document.createElement("p");
    chapter.className = "small";
    chapter.textContent = item.chapter;
    const link = document.createElement("a");
    link.href = item.url;
    addHighlightedText(link, item.title, words);
    const excerpt = document.createElement("p");
    const position = normalizeSearch(item.text).indexOf(words[0]);
    const start = Math.max(0, position - 35);
    const text = (start ? "…" : "") + item.text.slice(start, start + 170) + (item.text.length > start + 170 ? "…" : "");
    addHighlightedText(excerpt, text, words);
    card.append(chapter, link, excerpt);
    searchResults.append(card);
  }
  searchMore.hidden = matches.length <= searchLimit;
}
document.querySelector(".search-form")?.addEventListener("submit", event => { event.preventDefault(); renderSearch(); });
searchInput?.addEventListener("input", () => { searchLimit = 30; renderSearch(); });
searchScope?.addEventListener("change", () => { searchLimit = 30; renderSearch(); });
document.querySelector("[data-search-clear]")?.addEventListener("click", () => {
  searchInput.value = "";
  renderSearch();
  searchInput.focus();
});
searchMore?.addEventListener("click", () => { searchLimit += 30; renderSearch(); });

// Review mode reuses the same search, source return, formula and sidebar behavior.
const reviewRoot = document.documentElement;
const reviewButtons = [...document.querySelectorAll("[data-review-mode]")];
function setReviewMode(mode) {
  if (!reviewButtons.length) return;
  reviewRoot.dataset.reviewMode = mode;
  reviewButtons.forEach(button => button.setAttribute("aria-pressed", String(button.dataset.reviewMode === mode)));
}
reviewButtons.forEach(button => button.addEventListener("click", () => setReviewMode(button.dataset.reviewMode)));
if (reviewButtons.length) setReviewMode("full");

const progressChecks = [...document.querySelectorAll("[data-review-progress]")];
const reviewStorageKey = `study-flow-review:${location.pathname}`;
if (progressChecks.length) {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(reviewStorageKey) || "{}") || {}; } catch { /* Progress still works without persistent storage. */ }
  const updateReviewProgress = () => {
    const done = progressChecks.filter(check => check.checked).length;
    document.querySelector("[data-review-status]").textContent = `已掌握 ${done} / ${progressChecks.length}`;
    document.querySelector("[data-review-meter]").value = done;
  };
  for (const check of progressChecks) {
    check.checked = saved[check.dataset.reviewProgress] === true;
    check.addEventListener("change", () => {
      const values = Object.fromEntries(progressChecks.map(item => [item.dataset.reviewProgress, item.checked]));
      try { localStorage.setItem(reviewStorageKey, JSON.stringify(values)); } catch { /* Do not block learning when storage is unavailable. */ }
      updateReviewProgress();
    });
  }
  updateReviewProgress();
}

function revealHashTarget() {
  let id;
  try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
  const target = document.getElementById(id);
  if (!target) return;
  if (reviewButtons.length) {
    const mode = reviewRoot.dataset.reviewMode;
    if ((mode === "formulas" && (target.closest(".review-topic") || target.closest("#answers")))
        || (mode === "practice" && (target.closest(".problem-part:not([data-part='original']):not([data-part='translation']):not([data-part='terms'])") || target.closest(".answer, #answers")))) {
      setReviewMode("full");
    }
    if (target.closest("#quick-reference")) setReviewMode("formulas");
  }
  for (let element = target.parentElement; element; element = element.parentElement) {
    if (element.tagName === "DETAILS") element.open = true;
  }
  target.scrollIntoView({ behavior: "instant", block: "start" });
}
window.addEventListener("hashchange", revealHashTarget);
if (reviewButtons.length) document.addEventListener("click", event => {
  const link = event.target.closest("a[href]");
  if (!link) return;
  const url = new URL(link.href, location.href);
  if (url.pathname === location.pathname && url.hash && url.hash === location.hash) revealHashTarget();
});
if (location.hash) document.fonts.ready.then(() => requestAnimationFrame(revealHashTarget));

// A source round trip restores the actual reading offset, not just the page top.
let readingPosition = null;
document.querySelectorAll("[data-source-jump]").forEach(link => {
  link.addEventListener("click", () => {
    const gallery = document.getElementById("original-images");
    const rect = gallery?.getBoundingClientRect();
    if (!readingPosition || !rect || rect.top > 100 || rect.bottom < 0) {
      readingPosition = {
        x: scrollX, y: scrollY, hash: location.hash,
        navOpen: nav?.classList.contains("is-open"),
        reviewMode: reviewRoot.dataset.reviewMode,
        sidebarTop: document.querySelector(".sidebar")?.scrollTop || 0,
        focus: link,
      };
    }
    document.querySelectorAll("[data-source-return]").forEach(button => { button.hidden = false; });
  });
});
document.querySelectorAll("[data-source-return]").forEach(button => {
  button.addEventListener("click", () => {
    if (!readingPosition) return;
    const saved = readingPosition;
    nav?.classList.toggle("is-open", Boolean(saved.navOpen));
    menu?.setAttribute("aria-expanded", String(Boolean(saved.navOpen)));
    if (reviewButtons.length) setReviewMode(saved.reviewMode || "full");
    try { history.replaceState(history.state, "", location.pathname + location.search + saved.hash); } catch { /* Scroll restoration still works on restrictive file hosts. */ }
    document.querySelectorAll("[data-source-return]").forEach(control => { control.hidden = true; });
    saved.focus?.focus({ preventScroll: true });
    const sidebar = document.querySelector(".sidebar");
    if (sidebar) sidebar.scrollTop = saved.sidebarTop;
    scrollTo({ left: saved.x, top: saved.y, behavior: "instant" });
    readingPosition = null;
  });
});

document.querySelector("[data-print]")?.addEventListener("click", () => window.print());
document.querySelector("[data-expand]")?.addEventListener("click", () => {
  const details = [...document.querySelectorAll("details")];
  const shouldOpen = details.some((element) => !element.open);
  details.forEach((element) => { element.open = shouldOpen; });
});

const previousDetails = new Map();
window.addEventListener("beforeprint", () => {
  document.querySelectorAll("details").forEach((element) => {
    if (!previousDetails.has(element)) previousDetails.set(element, element.open);
    element.open = true;
  });
});
window.addEventListener("afterprint", () => {
  previousDetails.forEach((open, element) => { element.open = open; });
  previousDetails.clear();
});

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      nav?.querySelectorAll('a[href^="#"]').forEach((link) => {
        if (link.getAttribute("href") === `#${entry.target.id}`) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    }
  }, { rootMargin: "-5% 0px -70% 0px" });
  navigationTargets.forEach((element) => observer.observe(element));
}
