/* Курс «Теория массового обслуживания» — логика квизов и прогресса.
 * Прогресс хранится в localStorage, никакого бэкенда. */

(function () {
  "use strict";

  var STORAGE_KEY = "qt-course-v1";

  function loadState() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || { lessons: {} };
    } catch (e) {
      return { lessons: {} };
    }
  }

  function saveState(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) { /* приватный режим — живём без сохранения */ }
  }

  function lessonState(state, id) {
    if (!state.lessons[id]) state.lessons[id] = { answers: {} };
    return state.lessons[id];
  }

  function renderMath(el) {
    if (window.renderMathInElement) {
      window.renderMathInElement(el, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false }
        ],
        throwOnError: false
      });
    }
  }

  /* ---------- Квиз на странице урока ---------- */

  function initQuiz() {
    var dataEl = document.getElementById("quiz-data");
    var mount = document.getElementById("quiz-mount");
    if (!dataEl || !mount) return;

    var quiz = JSON.parse(dataEl.textContent);
    var lessonId = document.body.dataset.lesson;
    var state = loadState();
    var ls = lessonState(state, lessonId);

    var summaryEl = document.createElement("div");

    quiz.questions.forEach(function (q, qi) {
      var card = document.createElement("div");
      card.className = "quiz-question";

      var num = document.createElement("div");
      num.className = "q-num";
      num.textContent = "Вопрос " + (qi + 1) + " из " + quiz.questions.length;
      card.appendChild(num);

      var text = document.createElement("div");
      text.className = "q-text";
      text.innerHTML = q.question;
      card.appendChild(text);

      var optsWrap = document.createElement("div");
      optsWrap.className = "quiz-options";
      card.appendChild(optsWrap);

      var explan = document.createElement("div");
      explan.className = "quiz-explanation";
      explan.hidden = true;

      var buttons = [];

      function reveal(chosenIdx, animate) {
        buttons.forEach(function (b, bi) {
          b.disabled = true;
          if (q.options[bi].correct) b.classList.add("correct");
          else if (bi === chosenIdx) b.classList.add("wrong");
        });
        var ok = q.options[chosenIdx] && q.options[chosenIdx].correct;
        explan.innerHTML =
          '<span class="verdict ' + (ok ? "ok" : "fail") + '">' +
          (ok ? "Верно. " : "Не совсем. ") + "</span>" + q.explanation;
        explan.hidden = false;
        renderMath(explan);
        if (animate) explan.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }

      q.options.forEach(function (opt, oi) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "quiz-option";
        btn.innerHTML = opt.html;
        btn.addEventListener("click", function () {
          ls.answers[qi] = oi;
          saveState(state);
          reveal(oi, true);
          updateSummary();
        });
        buttons.push(btn);
        optsWrap.appendChild(btn);
      });

      card.appendChild(explan);
      mount.appendChild(card);

      if (ls.answers[qi] !== undefined) reveal(ls.answers[qi], false);
    });

    summaryEl.className = "quiz-summary";
    mount.appendChild(summaryEl);

    function updateSummary() {
      var total = quiz.questions.length;
      var answered = 0, correct = 0;
      quiz.questions.forEach(function (q, qi) {
        if (ls.answers[qi] === undefined) return;
        answered++;
        if (q.options[ls.answers[qi]] && q.options[ls.answers[qi]].correct) correct++;
      });
      var score;
      if (answered === 0) {
        score = "Ответьте на вопросы, чтобы проверить себя.";
      } else if (answered < total) {
        score = "Отвечено " + answered + " из " + total + " · верно: " + correct;
      } else {
        score = "Результат: " + correct + " из " + total +
          (correct === total ? " — отлично!" : "");
      }
      summaryEl.innerHTML =
        '<span class="score">' + score + "</span>" +
        '<button type="button" class="ghost" id="quiz-reset">Сбросить ответы</button>';
      summaryEl.querySelector("#quiz-reset").addEventListener("click", function () {
        ls.answers = {};
        saveState(state);
        location.reload();
      });
    }

    updateSummary();
    renderMath(mount);
  }

  /* ---------- Прогресс на обложке ---------- */

  function initIndex() {
    var cards = document.querySelectorAll(".lesson-card[data-lesson]");
    if (!cards.length) return;

    var state = loadState();
    var doneCount = 0;

    cards.forEach(function (card) {
      var id = card.dataset.lesson;
      var total = parseInt(card.dataset.questions, 10) || 0;
      var ls = state.lessons[id];
      var statusEl = card.querySelector(".status");
      if (!ls || !Object.keys(ls.answers).length) {
        statusEl.textContent = total ? total + " вопросов · не начат" : "не начат";
        return;
      }
      var answered = 0, correct = 0;
      Object.keys(ls.answers).forEach(function (qi) {
        answered++;
        var corr = card.dataset["q" + qi];
        if (corr !== undefined && parseInt(corr, 10) === ls.answers[qi]) correct++;
      });
      if (answered >= total && total > 0) {
        doneCount++;
        card.classList.add("done");
        card.querySelector(".num").textContent = "✓";
        statusEl.innerHTML =
          'пройден · <span class="score-ok">' + correct + " из " + total + "</span>";
      } else {
        statusEl.textContent = "в процессе · отвечено " + answered + " из " + total;
      }
    });

    var fill = document.querySelector(".progress-bar .fill");
    var label = document.querySelector(".progress-label");
    if (fill) fill.style.width = Math.round((doneCount / cards.length) * 100) + "%";
    if (label) {
      label.textContent = doneCount === 0
        ? "Курс ещё не начат"
        : "Пройдено уроков: " + doneCount + " из " + cards.length;
    }

    var reset = document.getElementById("course-reset");
    if (reset) {
      reset.addEventListener("click", function () {
        if (confirm("Сбросить весь прогресс курса?")) {
          localStorage.removeItem(STORAGE_KEY);
          location.reload();
        }
      });
    }
  }

  function boot() {
    renderMath(document.body);
    initQuiz();
    initIndex();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
