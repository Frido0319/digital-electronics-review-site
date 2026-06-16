from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path

from . import config


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def _js(value: str) -> str:
    return json.dumps(value or "", ensure_ascii=False)


MATH_CHARS = r"A-Za-z0-9\u03b2\u03a9\u03bc\u03c9\u221a\u0394()\+\-*/.'\u00b7\u00d7\u2225"
RELATION_PATTERN = r"=|\u2248|\u2264|\u2265|\u2261|>|<|\uff1e|\uff1c|\uff1d"
MATH_EXPR_RE = re.compile(
    rf"(?<![A-Za-z0-9])"
    rf"([{MATH_CHARS}][{MATH_CHARS}\s]*(?:{RELATION_PATTERN})"
    rf"[{MATH_CHARS}\s]+(?:\s*(?:{RELATION_PATTERN})\s*[{MATH_CHARS}\s]+)*)"
)
PARALLEL_EXPR_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9]*\s*//\s*[A-Za-z][A-Za-z0-9]*(?:\s*//\s*[A-Za-z][A-Za-z0-9]*)*)")
RELATION_RE = re.compile(rf"\s*({RELATION_PATTERN})\s*")
TOKEN_RE = re.compile(r"U\([A-Za-z]+\)[A-Za-z0-9]*|[ui][+-]|[A-Za-z]+[A-Za-z0-9]*")


def _format_token(token: str) -> str:
    sign = ""
    if len(token) == 2 and token[0] in {"u", "i"} and token[-1] in "+-":
        token, sign = token[:-1], token[-1]
    if token in {"sin", "cos", "tan", "log", "ln"}:
        base, sub = token, ""
    elif token.startswith("U("):
        base, sub = "U", token[1:]
    elif len(token) == 4 and token[0] in "UIR" and token[2] in "UIR" and token[1].isupper() and token[3].isupper():
        return _format_token(token[:2]) + _format_token(token[2:])
    elif token == "rbe":
        base, sub = "r", "be"
    elif token in {"ri", "ro", "ui", "uo"}:
        base, sub = token[0], token[1:]
    elif len(token) == 1:
        base, sub = token, ""
    elif token[0].islower() and token[1:].isalpha():
        base, sub = token[0], token[1:]
    elif token[0].isupper() and (token[1:].isalpha() or any(char.isdigit() for char in token[1:])):
        base, sub = token[0], token[1:]
    else:
        base, sub = token, ""
    result = _esc(base)
    if sub:
        result += f"<sub>{_esc(sub)}</sub>"
    if sign:
        result += f"<sup>{_esc(sign)}</sup>"
    return result


def _escape_math_text(value: str) -> str:
    return _esc(value).replace("\u2032", "<sup>&prime;</sup>")


def _single_division_index(value: str) -> int:
    for index, char in enumerate(value):
        if char != "/":
            continue
        prev_is_slash = index > 0 and value[index - 1] == "/"
        next_is_slash = index + 1 < len(value) and value[index + 1] == "/"
        if not prev_is_slash and not next_is_slash:
            return index
    return -1


def _format_math_text(value: str) -> str:
    normalized = (
        value.strip()
        .replace("//", "\u2225")
        .replace("*", "\u00b7")
        .replace("\u00d7", "\u00b7")
        .replace("'", "\u2032")
    )
    pieces: list[str] = []
    last = 0
    for match in TOKEN_RE.finditer(normalized):
        pieces.append(_escape_math_text(normalized[last : match.start()]))
        pieces.append(_format_token(match.group(0)))
        last = match.end()
    pieces.append(_escape_math_text(normalized[last:]))
    return "".join(pieces)


def _format_math_part(value: str) -> str:
    value = value.strip()
    division_index = _single_division_index(value)
    if division_index != -1:
        numerator = value[:division_index].strip()
        denominator = value[division_index + 1 :].strip()
        if numerator and denominator:
            return (
                f'<span class="frac"><span>{_format_math_text(numerator)}</span>'
                f"<span>{_format_math_text(denominator)}</span></span>"
            )
    return _format_math_text(value)


def _format_relation(operator: str) -> str:
    normalized = {
        "\uff1d": "=",
        "\uff1e": ">",
        "\uff1c": "<",
    }.get(operator, operator)
    return _esc(normalized)


def _format_math(raw: str) -> str:
    raw = (raw or "").strip()
    pieces: list[str] = []
    last = 0
    for match in RELATION_RE.finditer(raw):
        part = raw[last : match.start()].strip()
        if part:
            pieces.append(_format_math_part(part))
        pieces.append(f" {_format_relation(match.group(1))} ")
        last = match.end()
    tail = raw[last:].strip()
    if tail:
        pieces.append(_format_math_part(tail))
    return "".join(pieces).strip() or _format_math_part(raw)


def _math_block(raw: str, label: str | None = None) -> str:
    label_html = f'<div class="math-label">{_esc(label)}</div>' if label else ""
    return (
        f'<div class="math-block" data-raw="{_esc(raw)}">'
        f'{label_html}<div class="math-line">{_format_math(raw)}</div></div>'
    )


def _iter_math_matches(text: str):
    matches = sorted(
        list(MATH_EXPR_RE.finditer(text or "")) + list(PARALLEL_EXPR_RE.finditer(text or "")),
        key=lambda match: match.start(),
    )
    cursor = 0
    for match in matches:
        if match.start() < cursor:
            continue
        yield match
        cursor = match.end()


def _render_mixed_text(text: str) -> str:
    text = text or ""
    parts: list[str] = []
    last = 0
    math_separators = "，,。；;、"
    for match in _iter_math_matches(text):
        before = text[last:match.start()].strip()
        if before and before not in math_separators:
            parts.append(f"<p>{_esc(before)}</p>")
        expression = match.group(1).strip(f" {math_separators}")
        if expression:
            parts.append(_math_block(expression))
        trailing = text[match.end() : match.end() + 1]
        last = match.end() + 1 if trailing in math_separators else match.end()
    rest = text[last:].strip()
    if rest and rest not in math_separators:
        parts.append(f"<p>{_esc(rest)}</p>")
    if not parts:
        return f"<p>{_esc(text)}</p>"
    return "".join(parts)


def _modal_button_attrs(image: str, caption: str) -> str:
    return (
        'type="button" '
        'onclick="openImageModal(this.dataset.modalSrc, this.dataset.modalCaption)" '
        f'data-modal-src="{_esc(image)}" '
        f'data-modal-caption="{_esc(caption)}"'
    )


def _formula_label(point: dict, formula: str) -> str:
    special_labels = {
        "rectifier_bridge": "桥式整流",
        "ideal_op_amp_rules": "虚短虚断",
        "bjt_static_operating_point": "静态工作点",
        "bjt_small_signal_model": "微变等效",
        "boolean_simplification": "逻辑代数",
    }
    return f"{special_labels.get(point['id'], point['title'])}：{formula}"


def _source_pages_html(source_pages: list[dict]) -> str:
    if not source_pages:
        return '<p class="muted">来源页待补充。</p>'
    parts = []
    for page in source_pages:
        image = page["image_path"]
        label = f'{page["file"]} p.{page["page"]}'
        parts.append(
            '<figure class="source-page">'
            f'<button {_modal_button_attrs(image, label)}>'
            f'<img src="{_esc(image)}" alt="{_esc(label)}" loading="lazy" decoding="async" '
            "onerror=\"this.closest('figure').classList.add('image-missing')\">"
            f"</button><figcaption>{_esc(label)}</figcaption></figure>"
        )
    return "".join(parts)


def _official_answer_pages_html(question: dict) -> str:
    pages = question.get("official_answer_pages", [])
    if not pages:
        return '<p class="muted">这份参考答案 PDF 暂未覆盖本题；当前保留已有解析或待核对状态。</p>'
    parts = []
    for page in pages:
        image = page["image_path"]
        label = f'{question["id"]} 官方参考答案 p.{page["page"]}'
        parts.append(
            '<figure class="official-answer-page">'
            f'<button {_modal_button_attrs(image, label)}>'
            f'<img src="{_esc(image)}" alt="{_esc(label)}" loading="lazy" decoding="async" '
            "onerror=\"this.closest('figure').classList.add('image-missing')\">"
            f"</button><figcaption>{_esc(label)}</figcaption></figure>"
        )
    return "".join(parts)


def _knowledge_card(point: dict) -> str:
    formulas = "".join(f"<li>{_math_block(item)}</li>" for item in point["formulas"]) or "<li>本知识点无固定公式。</li>"
    prerequisites = "".join(f"<li>{_render_mixed_text(item)}</li>" for item in point.get("prerequisites", [])) or "<li>无额外前置知识。</li>"
    pitfalls = "".join(f"<li>{_render_mixed_text(item)}</li>" for item in point["pitfalls"])
    related = " ".join(f'<a href="#question-{_esc(qid)}">{_esc(qid)}</a>' for qid in point["related_questions"])
    return f"""
    <article class="knowledge-card searchable" id="knowledge-{_esc(point["id"])}" data-search="{_esc(point["title"])} {_esc(point["summary"])} {_esc(" ".join(point["related_questions"]))}">
      <header>
        <p class="eyebrow">第 {_esc(point["chapter"])} 章知识点</p>
        <h3>{_esc(point["title"])}</h3>
        <p class="summary">{_esc(point["summary"])}</p>
      </header>
      <div class="card-grid">
        <section><h4>必须掌握</h4>{_render_mixed_text(point["must_know"])}</section>
        <section><h4>从零理解</h4>{_render_mixed_text(point["intuition"])}</section>
        <section><h4>前置知识</h4><ul>{prerequisites}</ul></section>
        <section><h4>公式/规则</h4><ul class="formula-list">{formulas}</ul></section>
        <section><h4>关联作业</h4><p class="link-row">{related}</p></section>
      </div>
      <details>
        <summary>来源课件页</summary>
        <div class="source-strip">{_source_pages_html(point["source_pages"])}</div>
      </details>
      <section class="pitfalls"><h4>易错点</h4><ul>{pitfalls}</ul></section>
    </article>
    """


def _question_card(question: dict) -> str:
    images = "".join(
        '<figure class="homework-image">'
        f'<button {_modal_button_attrs(path, question["id"] + " 原题图")}>'
        f'<img src="{_esc(path)}" alt="{_esc(question["id"])} 原题图" loading="lazy" decoding="async" '
        "onerror=\"this.closest('figure').classList.add('image-missing')\">"
        f'</button><figcaption>{_esc(question["id"])} 原题图</figcaption></figure>'
        for path in question["image_paths"]
    )
    knowledge = " ".join(f'<a href="#knowledge-{_esc(kid)}">{_esc(kid)}</a>' for kid in question["knowledge_ids"])
    subquestions = "".join(
        f"""
        <section class="subquestion">
          <h4>{_esc(sub["id"])}</h4>
          <div class="subquestion-prompt">{_render_mixed_text(sub["prompt"])}</div>
          <ol>{''.join(f'<li>{_render_mixed_text(step)}</li>' for step in sub["solution_steps"])}</ol>
          <div class="answer"><strong>答案：</strong>{_render_mixed_text(sub["answer"])}</div>
        </section>
        """
        for sub in question["subquestions"]
    )
    official_answer_section = f"""
      <section class="official-answer-section">
        <h4>官方参考答案页截图</h4>
        <p class="muted">来自《电子技术部分章节作业参考答案to中德.pdf》。截图保留原手写/公式版面，点击可放大，放大后可用左右箭头翻页。</p>
        <div class="official-answer-strip">{_official_answer_pages_html(question)}</div>
      </section>
    """
    return f"""
    <article class="question-card searchable" id="question-{_esc(question["id"])}" data-search="{_esc(question["id"])} {_esc(question["title"])} {_esc(question["prompt"])} {_esc(question["answer_source"])}">
      <header>
        <p class="eyebrow">第 {_esc(question["chapter"])} 章作业题</p>
        <h3>{_esc(question["id"])} | {_esc(question["title"])}</h3>
        {_render_mixed_text(question["prompt"])}
      </header>
      <div class="homework-strip">{images}</div>
      <section><h4>考点定位</h4><p class="link-row">{knowledge}</p></section>
      <section><h4>来源课件页</h4><div class="source-strip">{_source_pages_html(question["source_pages"])}</div></section>
      {official_answer_section}
      <section><h4>子题级解析</h4>{subquestions}</section>
      <p class="answer-source">答案来源：{_esc(question["answer_source"])}</p>
    </article>
    """


def _methods_html(knowledge: list[dict]) -> str:
    method_items = []
    for point in knowledge:
        if point["formulas"]:
            formulas = "".join(
                f'<li><span class="formula-topic">{_esc(_formula_label(point, ""))}</span>{_math_block(formula)}</li>'
                for formula in point["formulas"]
            )
        else:
            formulas = f'<li>{_render_mixed_text(point["title"] + "：无固定公式，重点按判断步骤做题。")}</li>'
        method_items.append(
            f"""
            <article class="quick-card">
              <h3>{_esc(point["title"])}</h3>
              <ul class="formula-list">{formulas}</ul>
              <div class="muted">使用场景：{_render_mixed_text(point["must_know"])}</div>
            </article>
            """
        )
    return f"""
      <section class="scope" id="methods">
        <h2>公式和方法速查</h2>
        <p>这里按知识点自动汇总公式、规则和使用场景。复习时先看公式，再回到对应章节卡片确认前置知识和来源页。</p>
        <div class="quick-grid">{''.join(method_items)}</div>
      </section>
    """


def _checklist_html(knowledge: list[dict]) -> str:
    pitfall_items = []
    for point in knowledge:
        for pitfall in point["pitfalls"]:
            pitfall_items.append(f"<li><strong>{_esc(point['title'])}</strong>{_render_mixed_text(pitfall)}</li>")
    pitfall_items.append(f"<li><strong>整流题通用提醒</strong>{_render_mixed_text('不要把有效值和平均值混用，题目给出的 U2 通常是交流有效值。')}</li>")
    return f"""
      <section class="scope" id="checklist">
        <h2>易错点与考前清单</h2>
        <p>考前清单按章节知识点汇总。每做一道题后，回到这里确认自己没有踩同类错误。</p>
        <ul class="checklist">{''.join(pitfall_items)}</ul>
      </section>
    """


def _answer_status_html(questions: list[dict]) -> str:
    status_counts: dict[str, int] = defaultdict(int)
    for question in questions:
        status_counts[question["answer_source"]] += 1
    items = "".join(
        f"<li><strong>{_esc(status)}</strong>：{count} 题</li>"
        for status, count in sorted(status_counts.items())
    )
    official_count = sum(1 for question in questions if question.get("official_answer_pages"))
    return f"""
      <section class="scope" id="answer-status">
        <h2>答案状态</h2>
        <p>当前页面保留了每道题的解析入口和答案来源标记。已接入的参考答案 PDF 覆盖 {official_count} 道题；未覆盖的第 5、7 章题目继续保留推导答案或待核对状态。</p>
        <ul>{items}</ul>
      </section>
    """


def _lecture_page_classes(page: dict) -> str:
    classes = ["lecture-page"]
    if page.get("is_key_page"):
        classes.append("is-key-page")
    if page.get("is_super_key_page"):
        classes.append("is-super-key-page")
    return " ".join(classes)


def _lecture_page_badges(page: dict) -> str:
    badges = []
    if page.get("is_super_key_page"):
        badges.append(
            f'<span class="super-key-page-badge">{_esc(page.get("super_key_reason") or "重点中的重点")}</span>'
        )
    if page.get("is_key_page") and page.get("key_reason"):
        badges.append(f'<span class="key-page-badge">{_esc(page["key_reason"])}</span>')
    return (" ".join(badges) + " ") if badges else ""


def _lecture_gallery_html(gallery: list[dict]) -> str:
    if not gallery:
        return ""
    groups = []
    for source in gallery:
        pages = "".join(
            f"""
            <figure class="{_lecture_page_classes(page)}">
              <button {_modal_button_attrs(page["image_path"], source["title"] + " p." + str(page["page"]))}>
                <img src="{_esc(page["image_path"])}" alt="{_esc(source["title"])} 第 {_esc(str(page["page"]))} 页截图" loading="lazy" decoding="async"
                  onerror="this.closest('figure').classList.add('image-missing')">
              </button>
              <figcaption>{_lecture_page_badges(page)}{_esc(source["title"])} p.{_esc(str(page["page"]))}</figcaption>
            </figure>
            """
            for page in source["pages"]
        )
        groups.append(
            f"""
            <details class="lecture-source">
              <summary>第 {_esc(source["chapter"])} 章 | {_esc(source["title"])} | {len(source["pages"])} 页截图</summary>
              <div class="lecture-grid">{pages}</div>
            </details>
            """
        )
    return f"""
      <section class="scope" id="lecture-gallery">
        <h2>原讲义 PDF 截图库</h2>
        <p>这里集中放更多原讲义截图，方便你从整理版回到老师原 PDF 页面核对。每份 PDF 默认折叠，打开后再按页查看截图。</p>
        {''.join(groups)}
      </section>
    """


def _write_outline(knowledge: list[dict], questions: list[dict]) -> None:
    by_chapter_questions = defaultdict(list)
    by_chapter_points = defaultdict(list)
    for point in knowledge:
        by_chapter_points[point["chapter"]].append(point)
    for question in questions:
        by_chapter_questions[question["chapter"]].append(question)

    lines = [
        "# 数电复习网站目录",
        "",
        "## 使用方式",
        "- 章节知识是主入口，作业题号是查漏补缺入口。",
        "- 每个知识点保留前置知识、来源课件页和相关作业。",
        "- 官方答案状态：当前区分为“官方答案”“推导答案”“待核对”，后续可接入正式答案文件。",
        "",
    ]
    for chapter in ["1", "2", "3", "4", "5", "7"]:
        lines.append(f"## 第{chapter}章")
        lines.append("")
        lines.append("### 知识点")
        for point in by_chapter_points[chapter]:
            lines.append(f"- {point['title']}：{point['summary']}")
        lines.append("")
        lines.append("### 作业题")
        for question in by_chapter_questions[chapter]:
            lines.append(f"- {question['id']} {question['title']}（{question['answer_source']}）")
        lines.append("")
    config.OUTLINE_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_site() -> None:
    knowledge = _load_json(config.KNOWLEDGE_MAP_JSON)["knowledge_points"]
    questions = _load_json(config.QUESTION_BANK_JSON)["questions"]
    exclusions = _load_json(config.EXCLUSIONS_JSON)
    manifest = _load_json(config.SOURCE_MANIFEST_JSON)

    chapter_points = defaultdict(list)
    chapter_questions = defaultdict(list)
    for point in knowledge:
        chapter_points[point["chapter"]].append(point)
    for question in questions:
        chapter_questions[question["chapter"]].append(question)

    nav_chapters = "".join(f'<a href="#chapter-{chapter}">第 {chapter} 章</a>' for chapter in ["1", "2", "3", "4", "5", "7"])
    question_links = "".join(f'<a href="#question-{_esc(question["id"])}">{_esc(question["id"])}</a>' for question in questions)
    exclusion_items = "".join(
        f'<li>第 {_esc(item["chapter"])} 章 {_esc(item["section"])}：{_esc(item["reason"])}</li>'
        for item in exclusions["excluded_sections"]
    )
    chapter_sections = []
    for chapter in ["1", "2", "3", "4", "5", "7"]:
        points_html = "".join(_knowledge_card(point) for point in chapter_points[chapter])
        questions_html = "".join(_question_card(question) for question in chapter_questions[chapter])
        chapter_sections.append(
            f"""
            <section class="chapter-section" id="chapter-{chapter}">
              <h2>第 {chapter} 章</h2>
              <div class="knowledge-list">{points_html}</div>
              <h3>本章相关作业</h3>
              <div class="question-list">{questions_html or '<p class="muted">本章题目待补充。</p>'}</div>
            </section>
            """
        )

    methods_html = _methods_html(knowledge)
    checklist_html = _checklist_html(knowledge)
    answer_status_html = _answer_status_html(questions)
    lecture_gallery_html = _lecture_gallery_html(manifest.get("lecture_gallery", []))
    _write_outline(knowledge, questions)

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230f766e'/%3E%3Cpath d='M7 16h18M10 10h12M10 22h12' stroke='white' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E">
  <title>数电复习网站</title>
  <style>
    :root {{ color-scheme: light; --ink:#1c2430; --muted:#5d6878; --line:#d8dee8; --paper:#f7f8fb; --panel:#ffffff; --accent:#0f766e; --accent-2:#8a5a00; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--ink); background:var(--paper); line-height:1.55; }}
    button, input {{ font:inherit; }}
    .password-screen {{ min-height:100vh; display:grid; place-items:center; padding:24px; }}
    .login-panel {{ width:min(420px, 100%); background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:24px; box-shadow:0 16px 40px rgba(28,36,48,.08); }}
    .login-panel input {{ width:100%; padding:11px 12px; border:1px solid var(--line); border-radius:6px; margin:10px 0; }}
    .login-panel button, .tool-button {{ border:0; border-radius:6px; padding:10px 14px; background:var(--accent); color:white; cursor:pointer; }}
    .app-shell {{ display:grid; grid-template-columns:280px minmax(0,1fr); min-height:100vh; }}
    aside {{ position:sticky; top:0; height:100vh; overflow:auto; padding:18px; border-right:1px solid var(--line); background:#eef4f3; }}
    main {{ padding:24px clamp(16px, 3vw, 44px); }}
    nav a, .link-row a {{ display:inline-flex; margin:4px 6px 4px 0; color:#075985; text-decoration:none; border-bottom:1px solid transparent; }}
    nav a:hover, .link-row a:hover {{ border-bottom-color:currentColor; }}
    .search-box {{ display:flex; gap:8px; margin:18px 0; }}
    .search-box input {{ width:100%; padding:10px 12px; border:1px solid var(--line); border-radius:6px; }}
    .scope, .knowledge-card, .question-card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:18px; margin:18px 0; }}
    .eyebrow {{ color:var(--accent-2); font-size:.86rem; margin:0 0 4px; }}
    h1, h2, h3, h4 {{ line-height:1.25; }}
    .summary {{ color:var(--muted); }}
    .card-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px; }}
    .source-strip, .homework-strip, .official-answer-strip {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 260px)); gap:12px; align-items:start; }}
    .lecture-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 320px)); gap:14px; align-items:start; margin-top:14px; }}
    .lecture-source {{ border-top:1px solid var(--line); padding-top:10px; margin-top:10px; }}
    .lecture-source summary {{ cursor:pointer; font-weight:650; }}
    .official-answer-section {{ border-top:1px solid var(--line); padding-top:12px; margin-top:12px; }}
    .official-answer-page button {{ border:2px solid #0f766e; box-shadow:0 0 0 3px rgba(15,118,110,.09); }}
    .lecture-page.is-key-page button {{ border:3px solid #dc2626; box-shadow:0 0 0 3px rgba(220,38,38,.13); }}
    .lecture-page.is-super-key-page button {{ border:4px double #b91c1c; box-shadow:0 0 0 4px rgba(185,28,28,.14), inset 0 0 0 2px rgba(185,28,28,.08); }}
    .key-page-badge {{ display:inline-flex; align-items:center; border:1px solid #dc2626; border-radius:999px; padding:1px 6px; margin-right:4px; color:#b91c1c; font-weight:700; background:#fff1f2; }}
    .super-key-page-badge {{ display:inline-flex; align-items:center; border:1px solid #b91c1c; border-radius:999px; padding:1px 6px; margin-right:4px; color:#7f1d1d; font-weight:800; background:#fee2e2; }}
    .quick-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px; }}
    .quick-card {{ border:1px solid var(--line); border-radius:8px; padding:14px; background:#fbfcfd; }}
    .formula-list {{ list-style:none; padding-left:0; margin:10px 0 0; }}
    .formula-list li {{ margin:0 0 12px; }}
    .formula-topic {{ display:block; margin-bottom:6px; color:var(--muted); font-weight:650; }}
    .math-block {{ margin:10px 0 14px; padding:10px 12px; overflow-x:auto; border:1px solid #d5e5e1; border-radius:6px; background:#f8fcfb; text-align:center; }}
    .math-label {{ margin-bottom:6px; color:var(--muted); font-size:.86rem; text-align:left; }}
    .math-line {{ display:inline-flex; align-items:center; justify-content:center; gap:.26em; min-width:max-content; font-family:"Times New Roman", "Cambria Math", Georgia, serif; font-size:1.14rem; line-height:1.8; white-space:nowrap; }}
    .frac {{ display:inline-grid; grid-template-rows:auto auto; align-items:center; min-width:2.3em; margin:0 .16em; vertical-align:middle; line-height:1.1; }}
    .frac > span {{ display:block; padding:.08em .36em; text-align:center; }}
    .frac > span:first-child {{ border-bottom:1.5px solid currentColor; }}
    .math-line sub {{ font-size:.68em; vertical-align:sub; }}
    .math-line sup {{ font-size:.68em; vertical-align:super; }}
    .subquestion-prompt .math-block, .answer .math-block, .checklist .math-block {{ background:#fff; }}
    .checklist li {{ margin-bottom:8px; }}
    figure {{ margin:0; }}
    figure button {{ display:block; width:100%; padding:0; border:1px solid var(--line); border-radius:6px; background:white; cursor:zoom-in; overflow:hidden; }}
    img {{ display:block; max-width:100%; height:auto; }}
    figcaption {{ font-size:.82rem; color:var(--muted); margin-top:5px; }}
    .image-missing::after {{ content:"图片待生成"; display:block; padding:10px; color:#a33; }}
    .subquestion {{ border-top:1px solid var(--line); padding-top:12px; margin-top:12px; }}
    .answer {{ background:#edf7f4; padding:10px 12px; border-radius:6px; }}
    .answer-source, .muted {{ color:var(--muted); }}
    .hidden {{ display:none !important; }}
    .modal {{ position:fixed; inset:0; background:rgba(11,18,32,.82); display:grid; place-items:center; padding:20px; z-index:20; }}
    .modal figure {{ max-width:min(1100px, 96vw); max-height:92vh; }}
    .modal img {{ max-height:82vh; background:white; }}
    .modal button {{ margin-top:10px; border:0; border-radius:6px; padding:9px 12px; }}
    .modal-nav {{ position:absolute; top:50%; transform:translateY(-50%); width:52px; height:72px; display:grid; place-items:center; margin:0; border-radius:8px; background:rgba(255,255,255,.92); color:#0b1220; font-size:2.2rem; line-height:1; cursor:pointer; box-shadow:0 10px 28px rgba(0,0,0,.24); }}
    .modal-nav:disabled {{ opacity:.32; cursor:not-allowed; }}
    .modal-prev {{ left:18px; }}
    .modal-next {{ right:18px; }}
    mark {{ background:#fff1a6; }}
    @media (max-width: 820px) {{
      .app-shell {{ grid-template-columns:1fr; }}
      aside {{ position:relative; height:auto; max-height:45vh; }}
      main {{ padding:16px; }}
    }}
  </style>
</head>
<body>
  <section class="password-screen" id="password-screen">
    <form class="login-panel" onsubmit="return unlockCourse(event)">
      <h1>数电复习网站</h1>
      <p>输入统一访问密码后进入。</p>
      <label for="course-password">访问密码</label>
      <input id="course-password" type="password" autocomplete="current-password">
      <button type="submit">进入复习</button>
      <p class="muted" id="password-message" role="status"></p>
    </form>
  </section>
  <div class="app-shell hidden" id="course-app">
    <aside>
      <h2>目录</h2>
      <nav>
        <p class="nav-hint">建议顺序：先看考试范围，再按章节过知识点，最后按题号索引查漏补缺。</p>
        <p class="current-location">当前位置：<span id="current-location">考试范围</span></p>
        <a href="#scope" aria-current="page">考试范围</a>
        <h3>章节知识主线</h3>
        {nav_chapters}
        <h3>作业题号索引</h3>
        <div>{question_links}</div>
        <a href="#lecture-gallery">原讲义 PDF 截图库</a>
        <a href="#answer-status">答案状态</a>
        <a href="#methods">公式和方法速查</a>
        <a href="#checklist">易错点与考前清单</a>
      </nav>
    </aside>
    <main>
      <header>
        <h1>数电复习网站</h1>
        <p>章节知识为主线，作业题号可直接索引。每个知识点追溯到课件来源页，每道题保留原题图并拆到子题级解析。</p>
        <div class="search-box">
          <input id="search-input" aria-label="搜索题号或知识点" placeholder="搜索：5.1.8、桥式整流、卡诺图、虚短虚断">
          <button class="tool-button" type="button" onclick="clearSearch()">清除</button>
        </div>
        <p id="search-status" class="muted"></p>
      </header>
      <section class="scope" id="scope">
        <h2>考试范围</h2>
        <p>{_esc(exclusions["policy"])}</p>
        <ul>{exclusion_items}</ul>
        <p>{_esc(exclusions["homework_policy"])}</p>
      </section>
      <section class="scope" id="beginner-route">
        <h2>初学者学习路线</h2>
        <ol>
          <li>先读每章的前置知识，确认自己知道相关电路、公式或逻辑规则的入口概念。</li>
          <li>再看“必须掌握”和“从零理解”，只抓会做题必须用到的判断规则。</li>
          <li>打开来源课件页，对照原 PPT/PDF 图和公式，避免只背整理版。</li>
          <li>最后进入相关作业题，按“解题路线 -> 子题级解析 -> 最终答案”核对。</li>
        </ol>
      </section>
      {''.join(chapter_sections)}
      {lecture_gallery_html}
      {answer_status_html}
      {methods_html}
      {checklist_html}
    </main>
  </div>
  <div class="modal hidden" id="image-modal" onclick="closeImageModal()">
    <button class="modal-nav modal-prev" type="button" aria-label="上一张图片" onclick="event.stopPropagation(); showAdjacentImage(-1)">‹</button>
    <figure onclick="event.stopPropagation()">
      <img id="modal-image" alt="">
      <figcaption id="modal-caption"></figcaption>
      <button type="button" onclick="closeImageModal()">关闭</button>
    </figure>
    <button class="modal-nav modal-next" type="button" aria-label="下一张图片" onclick="event.stopPropagation(); showAdjacentImage(1)">›</button>
  </div>
  <script>
    const PASSWORD_HASH = "{config.DEFAULT_PASSWORD_SHA256}";
    const PASSWORD_STORAGE_KEY = "digital-electronics-review-unlocked";
    async function sha256(value) {{
      const data = new TextEncoder().encode(value);
      const digest = await crypto.subtle.digest("SHA-256", data);
      return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, "0")).join("");
    }}
    function showCourse() {{
      document.getElementById("password-screen").classList.add("hidden");
      document.getElementById("course-app").classList.remove("hidden");
    }}
    async function unlockCourse(event) {{
      event.preventDefault();
      const input = document.getElementById("course-password");
      const message = document.getElementById("password-message");
      if (await sha256(input.value) === PASSWORD_HASH) {{
        localStorage.setItem(PASSWORD_STORAGE_KEY, "1");
        showCourse();
      }} else {{
        message.textContent = "密码不正确。";
      }}
      return false;
    }}
    if (localStorage.getItem(PASSWORD_STORAGE_KEY) === "1") showCourse();
    const searchInput = document.getElementById("search-input");
    searchInput.addEventListener("input", () => {{
      const query = searchInput.value.trim().toLowerCase();
      let count = 0;
      document.querySelectorAll(".searchable").forEach(card => {{
        const text = card.dataset.search.toLowerCase();
        const hit = !query || text.includes(query);
        card.classList.toggle("hidden", !hit);
        if (hit && query) count += 1;
      }});
      document.getElementById("search-status").textContent = query ? `找到 ${{count}} 个匹配项。` : "";
    }});
    function clearSearch() {{
      searchInput.value = "";
      searchInput.dispatchEvent(new Event("input"));
      searchInput.focus();
    }}
    const navLinks = Array.from(document.querySelectorAll("aside nav a[href^='#']"));
    const locationLabel = document.getElementById("current-location");
    function updateCurrentLocation(hash) {{
      const activeHash = hash || "#scope";
      navLinks.forEach(link => {{
        if (link.getAttribute("href") === activeHash) {{
          link.setAttribute("aria-current", "page");
          if (locationLabel) locationLabel.textContent = link.textContent.trim();
        }} else {{
          link.removeAttribute("aria-current");
        }}
      }});
    }}
    navLinks.forEach(link => link.addEventListener("click", () => updateCurrentLocation(link.getAttribute("href"))));
    window.addEventListener("hashchange", () => updateCurrentLocation(window.location.hash));
    updateCurrentLocation(window.location.hash || "#scope");
    let currentModalIndex = -1;
    function getModalItems() {{
      return Array.from(document.querySelectorAll("[data-modal-src][data-modal-caption]")).map(button => ({{
        src: button.dataset.modalSrc,
        caption: button.dataset.modalCaption
      }}));
    }}
    function setModalImage(item, index) {{
      currentModalIndex = index;
      document.getElementById("modal-image").src = item.src;
      document.getElementById("modal-image").alt = item.caption;
      document.getElementById("modal-caption").textContent = item.caption;
      const items = getModalItems();
      document.querySelector(".modal-prev").disabled = currentModalIndex <= 0;
      document.querySelector(".modal-next").disabled = currentModalIndex >= items.length - 1;
    }}
    function openImageModal(src, caption) {{
      const items = getModalItems();
      const index = Math.max(0, items.findIndex(item => item.src === src && item.caption === caption));
      setModalImage({{ src, caption }}, index);
      document.getElementById("image-modal").classList.remove("hidden");
    }}
    function showAdjacentImage(direction) {{
      const modal = document.getElementById("image-modal");
      if (modal.classList.contains("hidden")) return;
      const items = getModalItems();
      const nextIndex = currentModalIndex + direction;
      if (nextIndex < 0 || nextIndex >= items.length) return;
      setModalImage(items[nextIndex], nextIndex);
    }}
    function closeImageModal() {{
      document.getElementById("image-modal").classList.add("hidden");
    }}
    document.addEventListener("keydown", event => {{
      if (document.getElementById("image-modal").classList.contains("hidden")) return;
      if (event.key === "ArrowLeft") showAdjacentImage(-1);
      if (event.key === "ArrowRight") showAdjacentImage(1);
      if (event.key === "Escape") closeImageModal();
    }});
  </script>
</body>
</html>
"""
    config.INDEX_HTML.write_text(html_text, encoding="utf-8")
