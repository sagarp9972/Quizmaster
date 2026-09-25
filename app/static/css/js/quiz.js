(() => {
  const $ = (id) => document.getElementById(id);
  const LETTERS = ["A", "B", "C", "D"];

  let total = 0;
  let current = 0;
  let hintsRemaining = 0;
  let elapsed = 0;
  let timerId = null;
  let paused = false;
  let finished = false;
  let lastQuestion = null; // the most recently rendered question payload

  function fmtTime(s) {
    const m = Math.floor(s / 60), sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  }

  function startTimer() {
    if (timerId) return;
    timerId = setInterval(() => {
      if (!paused && !finished) {
        elapsed += 1;
        $("statTime").textContent = fmtTime(elapsed);
      }
    }, 1000);
  }

  function todayLabel() {
    const d = new Date();
    return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
  }

  async function api(url, opts) {
    const res = await fetch(url, Object.assign({
      headers: { "Content-Type": "application/json" },
    }, opts));
    return res.json();
  }

  function renderOptions(q) {
    const wrap = $("optionsWrap");
    wrap.innerHTML = "";
    const answered = q.answered;
    const revealed = q.correct_option; // set once answered or a hint was used

    LETTERS.forEach((letter) => {
      const text = q.options[letter];
      if (text === undefined || text === null || text === "") return;
      const div = document.createElement("div");
      div.className = "opt";
      div.innerHTML = `<span class="letter">${letter}</span><span>${text}</span>`;

      if (answered || revealed) {
        div.classList.add("disabled");
        if (revealed && letter === q.correct_option) div.classList.add("correct");
        if (answered && answered.option === letter && letter !== q.correct_option) div.classList.add("wrong");
      } else {
        div.addEventListener("click", () => selectOption(letter));
      }
      wrap.appendChild(div);
    });
  }

  function renderSolution(q) {
    const box = $("solutionBox");
    if (q.explanation) {
      $("solutionText").textContent = q.explanation;
      box.classList.remove("hidden");
    } else {
      box.classList.add("hidden");
    }
  }

  function renderQuestion(q) {
    lastQuestion = q;
    current = q.index;
    total = q.total; // null => unlimited (Normal Quiz 1 / 2)
    $("qText").textContent = q.question;
    $("statQuestion").textContent = (total === null) ? `${q.index + 1}` : `${q.index + 1} of ${q.total}`;
    renderOptions(q);
    renderSolution(q);

    $("btnPrev").disabled = q.index === 0;
    const isLast = (total !== null) && (q.index === total - 1);
    $("btnNext").textContent = isLast ? "Finish Quiz →" : "Next Question →";
  }

  async function loadQuestion(index) {
    const data = await api(`/api/quiz/question/${index}`);
    if (data.ok) renderQuestion(data.question);
  }

  async function selectOption(letter) {
    const data = await api("/api/quiz/answer", {
      method: "POST", body: JSON.stringify({ index: current, option: letter }),
    });
    if (!data.ok) return;
    $("statCorrect").textContent = data.correct;
    $("statWrong").textContent = data.wrong;
    $("statScore").textContent = data.score;
    // The response already carries the answered/correct/explanation state --
    // render it directly instead of re-fetching, so the result and
    // explanation appear immediately with no extra round trip.
    renderQuestion(data.question);
  }

  async function useHint() {
    if (hintsRemaining <= 0) return;
    const data = await api("/api/quiz/hint", { method: "POST", body: JSON.stringify({ index: current }) });
    if (!data.ok) { alert(data.error || "No hints remaining."); return; }
    hintsRemaining = data.hints_remaining;
    $("statHints").textContent = hintsRemaining;
    renderQuestion(data.question);
  }

  function goPrev() {
    if (current > 0) loadQuestion(current - 1);
  }

  function goNext() {
    // Checked against the locally-held state from the last render -- no
    // network round trip here, so there's no window for a race where the
    // question looks answered on screen but this check disagrees.
    if (!lastQuestion || (!lastQuestion.answered && !lastQuestion.hint_used)) {
      alert("Please answer the question (or use a hint) before continuing.");
      return;
    }
    if (total === null || current + 1 < total) {
      loadQuestion(current + 1);
    } else {
      finishQuiz();
    }
  }

  async function finishQuiz() {
    finished = true;
    clearInterval(timerId);
    const data = await api("/api/quiz/finish", {
      method: "POST", body: JSON.stringify({ time_seconds: elapsed }),
    });
    if (!data.ok) { alert(data.error || "Could not save quiz."); return; }
    const r = data.result;
    $("resScore").textContent = r.score;
    $("resCorrect").textContent = r.correct;
    $("resWrong").textContent = r.wrong;
    $("resTime").textContent = fmtTime(r.time_seconds);
    $("resultSub").textContent = `${r.category_name} • Game #${r.game_no} • ${r.questions_played} questions played`;
    $("resultModal").classList.remove("hidden");
  }

  function togglePause() {
    paused = !paused;
    $("btnPause").textContent = paused ? "▶️ Resume" : "⏸️ Pause";
    if (paused) $("pauseModal").classList.remove("hidden");
  }

  function resumeFromModal() {
    paused = false;
    $("btnPause").textContent = "⏸️ Pause";
    $("pauseModal").classList.add("hidden");
  }

  async function doExit() {
    finished = true;
    clearInterval(timerId);
    await api("/api/quiz/exit", { method: "POST" });
    window.location.href = "/";
  }

  function wireButtons() {
    if (window.ALLOW_HINTS) $("btnHint").addEventListener("click", useHint);
    $("btnPrev").addEventListener("click", goPrev);
    $("btnNext").addEventListener("click", goNext);
    $("btnPause").addEventListener("click", togglePause);
    $("btnResume").addEventListener("click", resumeFromModal);
    $("btnFinish").addEventListener("click", finishQuiz);
    $("btnExit").addEventListener("click", () => $("exitModal").classList.remove("hidden"));
    $("exitCancel").addEventListener("click", () => $("exitModal").classList.add("hidden"));
    $("exitConfirm").addEventListener("click", doExit);
  }

  async function init() {
    $("dateLabel").textContent = "📅 " + todayLabel();
    wireButtons();

    const body = { type: window.QUIZ_MODE };
    if (window.QUIZ_CATEGORY_KEY) body.category = window.QUIZ_CATEGORY_KEY;

    const data = await api("/api/quiz/start", { method: "POST", body: JSON.stringify(body) });
    if (!data.ok) {
      $("blockedMsg").textContent = data.error || "This quiz isn't available right now.";
      $("blockedModal").classList.remove("hidden");
      return;
    }
    hintsRemaining = data.max_hints;
    if (window.ALLOW_HINTS) $("statHints").textContent = hintsRemaining;
    $("catNameLabel").textContent = "🧩 " + data.category_name;
    renderQuestion(data.question);
    startTimer();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
