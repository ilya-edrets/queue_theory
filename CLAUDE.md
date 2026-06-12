# CLAUDE.md

Учебный курс «Основы теории массового обслуживания для Highload-систем»:
markdown-уроки + генерируемый из них статический сайт. Язык всего проекта —
русский (контент, подписи на графиках, сообщения в коде сборки).

План курса — `study_plan.md`. При сомнениях о глубине/охвате темы сверяйся с ними.

## Структура

```
study_plan.md            # исходный план курса (источник истины по охвату тем)
lessons/NN-<slug>.md     # уроки 01–08 (08 — итоговый практикум про SelfPing)
lessons/STYLE_GUIDE.md   # ОБЯЗАТЕЛЬНЫЙ формат урока: структура, квизы, графики
lessons/scripts/         # lessonNN_charts.py — генерация графиков (matplotlib)
lessons/images/          # PNG-графики (генерируются скриптами, в уроках — относительные пути)
docs/                    # собранный сайт; lesson-NN.html и index.html НЕ редактировать руками
docs/assets/             # style.css и app.js — единственные руками написанные файлы сайта
tools/build_site.py      # сборка сайта из lessons/*.md
tools/validate_lessons.py# валидация уроков и сайта
```

## Команды

Всё запускается из корня проекта через venv:

```bash
.venv/bin/python tools/validate_lessons.py          # проверить уроки
.venv/bin/python tools/build_site.py                # пересобрать сайт
.venv/bin/python tools/validate_lessons.py --site   # проверить уроки + сайт
.venv/bin/python lessons/scripts/lessonNN_charts.py # перегенерировать графики урока NN
```

Если venv нет: `python3 -m venv .venv`, затем установить `matplotlib numpy markdown`.
ВАЖНО: на этой машине pip ломается из-за прокси в env (без схемы) и внутреннего
PyPI Avito. Рабочая установка:

```bash
HTTP_PROXY=http://localhost:7897 HTTPS_PROXY=http://localhost:7897 \
PIP_INDEX_URL=https://pypi.org/simple PIP_TRUSTED_HOST= \
.venv/bin/pip install <пакеты>
```

## Жёсткие инварианты

- **Формат квизов в уроках строгий** — его парсит `tools/build_site.py`:
  `### Вопрос N`, варианты `- [ ]` / `- [x]` (ровно один `[x]`),
  затем `> **Пояснение:** ...`. Любое отклонение ломает квиз на сайте.
  Полный формат — в `lessons/STYLE_GUIDE.md`.
- **`docs/*.html` — генерируемые файлы.** Правки контента — только в `lessons/*.md`
  с последующим `build_site.py`. Руками правятся только `docs/assets/*`.
- **Графики не редактируются как PNG** — меняй скрипт в `lessons/scripts/` и перезапускай.
- Формулы — LaTeX в `$...$` / `$$...$$`; на сайте их рендерит KaTeX (CDN).
  В тексте уроков — «ё», десятичная запятая в формулах как `0{,}8`.

## Рабочий цикл правки урока

1. Правишь `lessons/NN-*.md` (и при необходимости `lessons/scripts/lessonNN_charts.py`).
2. Если менял скрипт — перезапусти его, проверь PNG.
3. `.venv/bin/python tools/validate_lessons.py`
4. `.venv/bin/python tools/build_site.py`
5. `.venv/bin/python tools/validate_lessons.py --site`

Визуальная проверка без сервера (headless Chrome установлен):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
  --disable-gpu --window-size=1280,3000 --screenshot=/tmp/shot.png \
  "file://$PWD/docs/lesson-05.html"
```

Сайт открывается напрямую с file:// — сервер не нужен (это требование проекта:
никакого бэкенда, сборки фронтенда и авторизации; интерактив — ванильный JS,
прогресс — localStorage).
