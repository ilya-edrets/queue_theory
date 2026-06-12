#!/usr/bin/env python3
"""Валидация уроков курса и (опционально) собранного сайта.

Запуск из корня проекта:
    .venv/bin/python tools/validate_lessons.py          # проверить lessons/*.md
    .venv/bin/python tools/validate_lessons.py --site   # плюс проверить docs/

Проверяет в markdown-уроках:
- все картинки, на которые ссылается урок, существуют;
- формат квизов строгий (его парсит tools/build_site.py): у каждого
  «### Вопрос N» ровно один вариант «- [x]» и есть «> **Пояснение:**»;
- у задач есть решения в <details>;
- не осталось служебных пометок авторов (TODO, «на реальном сайте» и т.п.).

В собранном сайте (--site):
- квиз-JSON валиден, в каждом вопросе ровно один правильный вариант;
- нет невосстановленных MATH-токенов;
- все <img> ссылаются на существующие файлы.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / "lessons"
SITE = ROOT / "docs"

LEFTOVER_RE = re.compile(
    r"(TODO|FIXME|примечание для|на реальном сайте|note to self|placeholder|заглушк)",
    re.I,
)

errors = []


def err(msg: str):
    errors.append(msg)
    print(f"  !! {msg}")


def check_lessons():
    files = sorted(LESSONS.glob("0[0-9]-*.md"))
    if not files:
        err("не найдены файлы уроков lessons/0N-*.md")
        return
    for p in files:
        text = p.read_text(encoding="utf-8")

        imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
        for img in imgs:
            if not (p.parent / img).exists():
                err(f"{p.name}: нет картинки {img}")

        questions = re.split(r"^### Вопрос \d+\s*$", text, flags=re.M)[1:]
        for qi, block in enumerate(questions, 1):
            block = re.split(r"^#{2,3} ", block, maxsplit=1, flags=re.M)[0]
            correct = len(re.findall(r"^- \[x\] ", block, re.M))
            options = correct + len(re.findall(r"^- \[ \] ", block, re.M))
            expl = len(re.findall(r"^> \*\*Пояснение:\*\*", block, re.M))
            if correct != 1:
                err(f"{p.name}, вопрос {qi}: правильных вариантов {correct}, должен быть 1")
            if options < 2:
                err(f"{p.name}, вопрос {qi}: всего вариантов {options}")
            if expl != 1:
                err(f"{p.name}, вопрос {qi}: пояснений {expl}, должно быть 1")

        tasks = len(re.findall(r"^### Задача \d+", text, re.M))
        details = text.count("<details>")
        if tasks and details < tasks:
            err(f"{p.name}: задач {tasks}, а <details> с решениями {details}")

        for m in LEFTOVER_RE.finditer(text):
            err(f"{p.name}: служебная пометка автора: «{m.group(0)}»")

        nq = len(questions)
        words = len(re.findall(r"\w+", text))
        print(f"{p.name}: вопросов={nq}, задач={tasks}, картинок={len(imgs)}, слов={words}")


def check_site():
    pages = sorted(SITE.glob("lesson-*.html"))
    if not pages:
        err("docs/ пуст — сначала соберите сайт: .venv/bin/python tools/build_site.py")
        return
    for page in pages:
        t = page.read_text(encoding="utf-8")
        if re.search(r"MATH\d+", t):
            err(f"{page.name}: невосстановленные MATH-токены (сломалась защита формул)")
        m = re.search(r'<script type="application/json" id="quiz-data">(.*?)</script>', t, re.S)
        nq = 0
        if m:
            try:
                data = json.loads(m.group(1))
                nq = len(data["questions"])
                for qi, q in enumerate(data["questions"], 1):
                    if sum(o["correct"] for o in q["options"]) != 1:
                        err(f"{page.name}: вопрос {qi} — не ровно один правильный вариант")
                    if not q["explanation"]:
                        err(f"{page.name}: вопрос {qi} — пустое пояснение")
            except json.JSONDecodeError as e:
                err(f"{page.name}: квиз-JSON не парсится: {e}")
        for img in re.findall(r'<img[^>]+src="([^"]+)"', t):
            if not (SITE / img).exists():
                err(f"{page.name}: нет картинки {img}")
        print(f"{page.name}: вопросов в квизе={nq}")
    if not (SITE / "index.html").exists():
        err("нет docs/index.html")


def main():
    print("== Проверка lessons/*.md ==")
    check_lessons()
    if "--site" in sys.argv:
        print("== Проверка docs/ ==")
        check_site()
    print()
    if errors:
        print(f"ПРОБЛЕМ: {len(errors)}")
        sys.exit(1)
    print("OK — проблем не найдено")


if __name__ == "__main__":
    main()
