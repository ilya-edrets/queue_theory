#!/usr/bin/env python3
"""Сборка статического сайта курса из markdown-уроков.

Запуск из корня проекта:
    .venv/bin/python tools/build_site.py

Что делает:
- читает lessons/NN-*.md;
- вырезает раздел «## Проверь себя» и превращает его в JSON для интерактивного
  квиза (рендерится на клиенте, см. docs/assets/app.js);
- конвертирует остальной markdown в HTML (python-markdown), защищая
  LaTeX-формулы от искажения (их рендерит KaTeX в браузере);
- генерирует docs/lesson-NN.html и docs/index.html;
- копирует картинки в docs/images/.
"""

import html
import json
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
LESSONS_DIR = ROOT / "lessons"
SITE_DIR = ROOT / "docs"

KATEX_VERSION = "0.16.21"

COURSE_TITLE = "Основы теории массового обслуживания для Highload-систем"
COURSE_SUBTITLE = (
    "Откуда берутся задержки в ML-инференсе и Kafka — и что с ними делать. "
    "Семь уроков теории с графиками, квизами и задачами плюс итоговый практикум."
)

# Модули курса: (заголовок, [номера уроков])
MODULES = [
    ("Модуль 1 · Базовые законы и природа задержек", ["01", "02"]),
    ("Модуль 2 · Моделирование и распределения", ["03", "04"]),
    ("Модуль 3 · Практические эффекты и масштабирование", ["05", "06", "07"]),
    ("Финал", ["08"]),
]

MD_EXTENSIONS = ["extra", "sane_lists", "md_in_html"]


# ---------- Защита LaTeX от markdown-конвертера ----------

MATH_TOKEN = "MATH{}"


def protect_math(text: str):
    """Заменяет $$...$$ и $...$ на токены; возвращает (текст, список формул)."""
    stash = []

    def repl(match):
        stash.append(match.group(0))
        return MATH_TOKEN.format(len(stash) - 1)

    text = re.sub(r"\$\$.+?\$\$", repl, text, flags=re.S)
    text = re.sub(r"(?<![\\$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)", repl, text)
    return text, stash


def restore_math(html_text: str, stash):
    """Возвращает формулы на место, экранируя <, >, & для KaTeX."""
    for i, formula in enumerate(stash):
        html_text = html_text.replace(MATH_TOKEN.format(i), html.escape(formula, quote=False))
    return html_text


def md_to_html(md_text: str) -> str:
    protected, stash = protect_math(md_text)
    rendered = markdown.markdown(protected, extensions=MD_EXTENSIONS)
    return restore_math(rendered, stash)


def md_inline_to_html(md_text: str) -> str:
    """Для текста вопроса/варианта/пояснения: без обёртки <p>, если абзац один."""
    out = md_to_html(md_text).strip()
    if out.count("<p>") == 1 and out.startswith("<p>") and out.endswith("</p>"):
        out = out[3:-4]
    return out


# ---------- Парсинг урока ----------

QUESTION_RE = re.compile(r"^### Вопрос \d+\s*$", re.M)
OPTION_RE = re.compile(r"^- \[([ x])\] (.+)$")


def parse_quiz(section: str):
    """Парсит раздел «Проверь себя» в список вопросов."""
    questions = []
    blocks = QUESTION_RE.split(section)
    for block in blocks[1:]:
        lines = block.strip("\n").split("\n")
        q_lines, options, expl_lines = [], [], []
        mode = "question"
        for line in lines:
            m = OPTION_RE.match(line)
            if m:
                mode = "options"
                options.append({"html": md_inline_to_html(m.group(2).strip()),
                                "correct": m.group(1) == "x"})
                continue
            if line.startswith(">"):
                mode = "explanation"
                expl_lines.append(re.sub(r"^>\s?", "", line))
                continue
            if mode == "question":
                q_lines.append(line)
            elif mode == "explanation" and line.strip() == "":
                continue
        expl = "\n".join(expl_lines).strip()
        expl = re.sub(r"^\*\*Пояснение:\*\*\s*", "", expl)
        questions.append({
            "question": md_inline_to_html("\n".join(q_lines).strip()),
            "options": options,
            "explanation": md_inline_to_html(expl),
        })
    return questions


def split_lesson(md_text: str):
    """Делит урок: контент до квиза, раздел квиза, контент после (задачи и пр.)."""
    quiz_start = re.search(r"^## Проверь себя\s*$", md_text, re.M)
    if not quiz_start:
        return md_text, "", ""
    head = md_text[: quiz_start.start()]
    rest = md_text[quiz_start.end():]
    next_h2 = re.search(r"^## ", rest, re.M)
    if next_h2:
        quiz_section = rest[: next_h2.start()]
        tail = rest[next_h2.start():]
    else:
        quiz_section, tail = rest, ""
    return head, quiz_section, tail


def prepare_details(md_text: str) -> str:
    """Включает markdown-обработку внутри <details> (решения задач)."""
    md_text = md_text.replace("<details>", '<details markdown="1">')
    return md_text


def extract_title(md_text: str) -> str:
    m = re.search(r"^# (.+)$", md_text, re.M)
    return m.group(1).strip() if m else "Урок"


# ---------- Шаблоны ----------

def page_shell(title: str, body: str, lesson_id: str = "") -> str:
    data_attr = f' data-lesson="{lesson_id}"' if lesson_id else ""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="assets/style.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/contrib/auto-render.min.js"></script>
<script defer src="assets/app.js"></script>
</head>
<body{data_attr}>
{body}
</body>
</html>
"""


def build_lesson_page(lesson, prev_lesson, next_lesson, index, total):
    nav_prev = (
        f'<a class="prev" href="{prev_lesson["page"]}"><div class="dir">← Назад</div>'
        f'<div class="name">{html.escape(prev_lesson["short"])}</div></a>'
        if prev_lesson else ""
    )
    nav_next = (
        f'<a class="next" href="{next_lesson["page"]}"><div class="dir">Дальше →</div>'
        f'<div class="name">{html.escape(next_lesson["short"])}</div></a>'
        if next_lesson else ""
    )

    quiz_block = ""
    if lesson["quiz"]:
        quiz_json = json.dumps({"questions": lesson["quiz"]}, ensure_ascii=False)
        quiz_json = quiz_json.replace("</", "<\\/")  # защита </script>
        quiz_block = f"""
<h2>Проверь себя</h2>
<div id="quiz-mount"></div>
<script type="application/json" id="quiz-data">{quiz_json}</script>
"""

    body = f"""<header class="site-header"><div class="inner">
<a class="home" href="index.html">← К курсу</a>
<span class="lesson-pos">Урок {index} из {total}</span>
</div></header>
<main>
{lesson["head_html"]}
{quiz_block}
{lesson["tail_html"]}
<div class="lesson-nav">{nav_prev}{nav_next}</div>
</main>"""
    return page_shell(lesson["title"], body, lesson_id=lesson["id"])


def build_index(lessons):
    by_id = {l["id"]: l for l in lessons}
    sections = []
    for module_title, ids in MODULES:
        cards = []
        for lid in ids:
            lesson = by_id.get(lid)
            if not lesson:
                continue
            # data-qN — индекс правильного ответа, чтобы обложка считала баллы
            correct_attrs = " ".join(
                f'data-q{qi}="{next(i for i, o in enumerate(q["options"]) if o["correct"])}"'
                for qi, q in enumerate(lesson["quiz"])
            )
            cards.append(f"""<a class="lesson-card" href="{lesson["page"]}" data-lesson="{lesson["id"]}"
   data-questions="{len(lesson["quiz"])}" {correct_attrs}>
  <div class="num">{int(lesson["id"])}</div>
  <div class="info">
    <div class="title">{html.escape(lesson["short"])}</div>
    <div class="status"></div>
  </div>
</a>""")
        if cards:
            sections.append(
                f'<div class="module-title">{html.escape(module_title)}</div>\n'
                + "\n".join(cards)
            )

    body = f"""<main>
<div class="course-hero">
<h1>{html.escape(COURSE_TITLE)}</h1>
<p class="subtitle">{html.escape(COURSE_SUBTITLE)}</p>
<div class="progress-bar"><div class="fill"></div></div>
<div class="progress-label"></div>
</div>
{"".join(sections)}
<p style="margin-top:2rem"><button type="button" class="ghost danger" id="course-reset">Сбросить прогресс</button></p>
</main>"""
    return page_shell(COURSE_TITLE, body)


# ---------- Сборка ----------

def short_title(full_title: str) -> str:
    """«Урок 5. Эффект …» → «Эффект …» (для карточек и навигации)."""
    return re.sub(r"^(Урок \d+\.|Итоговая практическая работа:)\s*", "", full_title)


def main():
    lesson_files = sorted(LESSONS_DIR.glob("0[0-9]-*.md"))
    if not lesson_files:
        raise SystemExit("Не найдены файлы уроков в lessons/")

    lessons = []
    for path in lesson_files:
        lid = path.name[:2]
        md_text = path.read_text(encoding="utf-8")
        title = extract_title(md_text)
        head, quiz_section, tail = split_lesson(md_text)
        lessons.append({
            "id": lid,
            "page": f"lesson-{lid}.html",
            "title": title,
            "short": short_title(title),
            "head_html": md_to_html(prepare_details(head)),
            "tail_html": md_to_html(prepare_details(tail)),
            "quiz": parse_quiz(quiz_section),
        })

    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / "assets").mkdir(exist_ok=True)

    # картинки
    img_src = LESSONS_DIR / "images"
    img_dst = SITE_DIR / "images"
    if img_dst.exists():
        shutil.rmtree(img_dst)
    shutil.copytree(img_src, img_dst)

    total = len(lessons)
    for i, lesson in enumerate(lessons):
        prev_lesson = lessons[i - 1] if i > 0 else None
        next_lesson = lessons[i + 1] if i + 1 < total else None
        page = build_lesson_page(lesson, prev_lesson, next_lesson, i + 1, total)
        (SITE_DIR / lesson["page"]).write_text(page, encoding="utf-8")
        print(f"  {lesson['page']}: «{lesson['short']}», вопросов: {len(lesson['quiz'])}")

    (SITE_DIR / "index.html").write_text(build_index(lessons), encoding="utf-8")
    print(f"  index.html: {total} уроков")
    print("Готово: docs/")


if __name__ == "__main__":
    main()
