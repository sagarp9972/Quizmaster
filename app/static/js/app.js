document.addEventListener("DOMContentLoaded", () => {
  const darkToggle = document.getElementById("darkToggle");
  if (darkToggle) {
    darkToggle.addEventListener("click", async () => {
      const res = await fetch("/toggle-dark-mode", { method: "POST" });
      const data = await res.json();
      document.documentElement.setAttribute("data-theme", data.dark_mode ? "dark" : "light");
      darkToggle.classList.toggle("on", data.dark_mode);
    });
  }

  const logoutBtn = document.getElementById("logoutBtn");
  const logoutModal = document.getElementById("logoutModal");
  const logoutCancel = document.getElementById("logoutCancel");
  if (logoutBtn && logoutModal) {
    logoutBtn.addEventListener("click", () => logoutModal.classList.remove("hidden"));
    logoutCancel.addEventListener("click", () => logoutModal.classList.add("hidden"));
  }
});
