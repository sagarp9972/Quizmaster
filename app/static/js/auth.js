document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".pw-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.target);
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.textContent = showing ? "👁️" : "🙈";
      btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  });
});
