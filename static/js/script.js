(function () {
  const { sendUrl, newSessionUrl, deleteUrlBase, csrfToken } = window.UPCHAR_SATHI;
  let activeSessionId = window.UPCHAR_SATHI.activeSessionId;

  const chatWindow = document.getElementById("chatWindow");
  const welcomeCard = document.getElementById("welcomeCard");
  const form = document.getElementById("composerForm");
  const input = document.getElementById("symptomInput");
  const sendBtn = document.getElementById("sendBtn");
  const typingTemplate = document.getElementById("typingTemplate");
  const sidebar = document.getElementById("sidebar");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const newChatBtn = document.getElementById("newChatBtn");
  const themeToggle = document.getElementById("themeToggle");
  const chips = document.querySelectorAll(".chip");
  const historyList = document.getElementById("historyList");

  /* ---------------- Theme toggle ---------------- */

  themeToggle?.addEventListener("click", () => {
    const html = document.documentElement;
    const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    localStorage.setItem("upchar-theme", next);
  });

  /* ---------------- Chat rendering ---------------- */

  function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function hideWelcome() {
    if (welcomeCard) welcomeCard.style.display = "none";
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function renderContent(text) {
    const escaped = escapeHtml(text);
    const bolded = escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return bolded.replace(/\n/g, "<br>");
  }

  function appendMessage(role, text) {
    hideWelcome();
    const wrapper = document.createElement("div");
    wrapper.className = "msg " + (role === "user" ? "msg-user" : "msg-bot");

    if (role !== "user") {
      const avatar = document.createElement("span");
      avatar.className = "msg-avatar";
      avatar.textContent = "🌿";
      wrapper.appendChild(avatar);
    }

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";

    const textEl = document.createElement("div");
    textEl.className = "msg-text";
    textEl.innerHTML = renderContent(text);
    bubble.appendChild(textEl);

    if (role !== "user") {
      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.className = "copy-btn";
      copyBtn.title = "Copy response";
      copyBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 14 14" fill="none"><rect x="5" y="5" width="7.5" height="7.5" rx="1.3" stroke="currentColor" stroke-width="1.2"/><path d="M9 5V2.8A1.3 1.3 0 0 0 7.7 1.5H2.8A1.3 1.3 0 0 0 1.5 2.8v4.9A1.3 1.3 0 0 0 2.8 9H5" stroke="currentColor" stroke-width="1.2"/></svg>';
      copyBtn.addEventListener("click", () => copyText(text, copyBtn));
      bubble.appendChild(copyBtn);
    }

    wrapper.appendChild(bubble);
    chatWindow.appendChild(wrapper);
    scrollToBottom();
    return wrapper;
  }

  function copyText(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
      btn.classList.add("copied");
      setTimeout(() => btn.classList.remove("copied"), 1400);
    });
  }

  // Wire up copy buttons already rendered server-side (history on page load)
  document.querySelectorAll(".msg-bot .copy-btn").forEach((btn) => {
    const textEl = btn.closest(".msg-bubble")?.querySelector(".msg-text");
    if (textEl) {
      btn.addEventListener("click", () => copyText(textEl.innerText, btn));
    }
  });

  function showTyping() {
    const node = typingTemplate.content.cloneNode(true);
    chatWindow.appendChild(node);
    scrollToBottom();
    return chatWindow.lastElementChild;
  }

  function autoGrow() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  }

  input.addEventListener("input", autoGrow);

  /* ---------------- Sending messages ---------------- */

  async function sendMessage(text) {
    appendMessage("user", text);
    input.value = "";
    autoGrow();
    sendBtn.disabled = true;

    const typingEl = showTyping();

    try {
      const res = await fetch(sendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ message: text, session_id: activeSessionId }),
      });

      const data = await res.json();
      typingEl.remove();

      if (!res.ok) {
        const el = appendMessage("bot", data.error || "Something went wrong. Please try again.");
        el.classList.add("msg-error");
        return;
      }

      appendMessage("bot", data.reply);

      if (!activeSessionId && data.session_id) {
        activeSessionId = data.session_id;
        history.replaceState(null, "", "/chat/" + activeSessionId + "/");
        prependHistoryItem(activeSessionId, data.session_title);
      } else if (activeSessionId) {
        updateHistoryTitle(activeSessionId, data.session_title);
      }
    } catch (err) {
      typingEl.remove();
      const el = appendMessage(
        "bot",
        "I couldn't connect just now. Please check your connection and try again."
      );
      el.classList.add("msg-error");
    } finally {
      sendBtn.disabled = false;
    }
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    sendMessage(text);
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      sendMessage(chip.dataset.prompt);
      if (window.innerWidth <= 860) sidebar.classList.remove("open");
    });
  });

  sidebarToggle?.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });

  /* ---------------- New chat ---------------- */

  newChatBtn.addEventListener("click", async () => {
    try {
      const res = await fetch(newSessionUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
      });
      const data = await res.json();
      activeSessionId = data.session_id;
      history.replaceState(null, "", "/chat/" + activeSessionId + "/");
    } catch (err) {
      activeSessionId = null;
    }

    document.querySelectorAll(".msg").forEach((el) => el.remove());
    if (welcomeCard) welcomeCard.style.display = "block";
    document.querySelectorAll(".history-item").forEach((el) => el.classList.remove("active"));
    input.focus();
  });

  /* ---------------- History list helpers ---------------- */

  function prependHistoryItem(id, title) {
    document.querySelectorAll(".history-item").forEach((el) => el.classList.remove("active"));
    const empty = historyList.querySelector(".history-empty");
    if (empty) empty.remove();

    const item = document.createElement("div");
    item.className = "history-item active";
    item.dataset.id = id;
    item.innerHTML =
      '<a href="/chat/' + id + '/" class="history-link">' +
      '<span class="history-title"></span><span class="history-date">Just now</span></a>' +
      '<button class="history-delete" type="button" data-id="' + id + '" aria-label="Delete conversation">' +
      '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 4h10M5.5 4V2.5h3V4M3.5 4l.5 8h6l.5-8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></button>';
    item.querySelector(".history-title").textContent = title;
    historyList.prepend(item);
    wireDeleteButton(item.querySelector(".history-delete"));
  }

  function updateHistoryTitle(id, title) {
    const item = historyList.querySelector('.history-item[data-id="' + id + '"] .history-title');
    if (item) item.textContent = title;
  }

  function wireDeleteButton(btn) {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const id = btn.dataset.id;
      if (!confirm("Delete this conversation?")) return;
      try {
        await fetch(deleteUrlBase + id + "/delete/", {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken },
        });
      } catch (err) { /* ignore */ }

      const item = btn.closest(".history-item");
      const wasActive = item.classList.contains("active");
      item.remove();

      if (!historyList.querySelector(".history-item")) {
        historyList.innerHTML = '<p class="history-empty">No conversations yet — say hello below!</p>';
      }

      if (wasActive) {
        window.location.href = "/";
      }
    });
  }

  document.querySelectorAll(".history-delete").forEach(wireDeleteButton);
})();
