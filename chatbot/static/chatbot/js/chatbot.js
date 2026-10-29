document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  // =====================================================
  // HANDS-ON HEALTH - CHATBOT
  // =====================================================

  const toggle = document.getElementById("chat-toggle");
  const close = document.getElementById("chat-close");
  const windowEl = document.getElementById("chat-window");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const messages = document.getElementById("chat-messages");
  const sendButton = document.getElementById("chat-send");

  if (!toggle || !windowEl || !form || !input || !messages || !sendButton) {
    return;
  }

  // =====================================================
  // OPEN / CLOSE CHATBOT
  // =====================================================

  function scrollToBottom() {
    messages.scrollTop = messages.scrollHeight;
  }

  function setOpen(open) {
    windowEl.hidden = !open;

    toggle.setAttribute("aria-expanded", String(open));

    if (open) {
      input.focus();
      scrollToBottom();
    }
  }

  toggle.addEventListener("click", (event) => {
    event.preventDefault();
    setOpen(windowEl.hidden);
  });

  if (close) {
    close.addEventListener("click", () => {
      setOpen(false);
      toggle.focus();
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !windowEl.hidden) {
      setOpen(false);
      toggle.focus();
    }
  });

  // =====================================================
  // RECOGNIZE ACTION LINKS
  // =====================================================

  function getLinkType(url, label = "") {
    const text = label.toLowerCase();

    let parsed;

    try {
      parsed = new URL(url, window.location.origin);
    } catch {
      return "other";
    }

    const host = parsed.hostname.toLowerCase();
    const path = parsed.pathname.toLowerCase();

    if (
      host === "wa.me" ||
      host === "www.wa.me" ||
      host === "api.whatsapp.com"
    ) {
      return "whatsapp";
    }

    if (path.includes("/appointment/") || text.includes("appointment")) {
      return "appointment";
    }

    if (path.includes("/home-care/") || text.includes("home care")) {
      return "homecare";
    }

    return "other";
  }

  function getLinkLabel(type, originalLabel) {
    if (type === "whatsapp") {
      return "Chat on WhatsApp";
    }

    if (type === "appointment") {
      return "Book Appointment";
    }

    if (type === "homecare") {
      return "Request Home Care";
    }

    return originalLabel || "Open Link";
  }

  // =====================================================
  // EXTRACT LINKS FROM CHATBOT RESPONSE
  // =====================================================

  function extractLinks(text, serverLinks = []) {
    const links = [];
    const seen = new Set();

    function addLink(url, label = "") {
      if (typeof url !== "string") return;

      let parsed;

      try {
        parsed = new URL(url, window.location.origin);

        if (!["http:", "https:"].includes(parsed.protocol)) {
          return;
        }

        // Do not accept arbitrary external
        // destinations from chatbot responses.
        const allowedExternal = ["wa.me", "www.wa.me", "api.whatsapp.com"];

        const isLocal = parsed.origin === window.location.origin;

        if (
          !isLocal &&
          !allowedExternal.includes(parsed.hostname.toLowerCase())
        ) {
          return;
        }
      } catch {
        return;
      }

      if (seen.has(parsed.href)) return;

      seen.add(parsed.href);

      const type = getLinkType(parsed.href, label);

      links.push({
        url: parsed.href,
        label: getLinkLabel(type, label),
        type: type,
      });
    }

    // Structured links from Django views.py
    if (Array.isArray(serverLinks)) {
      serverLinks.forEach((item) => {
        if (item && typeof item.url === "string") {
          addLink(item.url, item.label || "");
        }
      });
    }

    // URLs embedded in plain-text replies
    const urlPattern = /https?:\/\/[^\s<>"']+/g;

    const matches = text.match(urlPattern) || [];

    matches.forEach((url) => {
      const cleaned = url.replace(/[.,;!?)]+$/, "");

      addLink(cleaned);
    });

    return links;
  }

  // =====================================================
  // CREATE ACTION BUTTONS
  // =====================================================

  function createActionButtons(links) {
    const actions = document.createElement("div");

    actions.className = "chat-actions";

    links.forEach((link) => {
      const button = document.createElement("a");

      button.href = link.url;
      button.target = "_blank";
      button.rel = "noopener noreferrer";

      button.className = "chat-action-btn";

      if (link.type === "whatsapp") {
        button.classList.add("whatsapp-action");
      }

      const icon = document.createElement("i");

      if (link.type === "whatsapp") {
        icon.className = "fa-brands fa-whatsapp";
      } else if (link.type === "appointment") {
        icon.className = "fa-solid fa-calendar-check";
      } else if (link.type === "homecare") {
        icon.className = "fa-solid fa-house-medical";
      } else {
        icon.className = "fa-solid fa-arrow-up-right-from-square";
      }

      icon.setAttribute("aria-hidden", "true");

      const text = document.createElement("span");

      text.textContent = link.label;

      button.appendChild(icon);
      button.appendChild(text);

      actions.appendChild(button);
    });

    return actions;
  }

  // =====================================================
  // CLEAN RAW URLS FROM VISIBLE TEXT
  // =====================================================

  function cleanReplyText(text, links) {
    let cleaned = String(text || "");

    links.forEach((link) => {
      // Remove URL only, leaving the other
      // chatbot explanation intact.
      cleaned = cleaned.split(link.url).join("");
    });

    // Remove empty action headings.
    cleaned = cleaned.replace(
      /^\s*(Book Appointment|Request Home Care|WhatsApp):\s*$/gim,
      "",
    );

    // Collapse excessive empty lines.
    cleaned = cleaned.replace(/\n{3,}/g, "\n\n");

    return cleaned.trim();
  }

  // =====================================================
  // CREATE CHAT BUBBLE
  // =====================================================

  function addMessage(text, sender, serverLinks = []) {
    const bubble = document.createElement("div");

    bubble.className = `chat-bubble ${sender}`;

    if (sender === "bot") {
      const links = extractLinks(String(text || ""), serverLinks);

      const messageText = cleanReplyText(text, links);

      if (messageText) {
        const content = document.createElement("div");

        content.className = "chat-message-text";

        // Safe: no untrusted HTML injection.
        content.textContent = messageText;

        bubble.appendChild(content);
      }

      if (links.length > 0) {
        bubble.appendChild(createActionButtons(links));
      }
    } else {
      bubble.textContent = text;
    }

    messages.appendChild(bubble);

    scrollToBottom();

    return bubble;
  }

  // =====================================================
  // CSRF TOKEN
  // =====================================================

  function getCsrfToken() {
    const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');

    return csrfInput ? csrfInput.value : "";
  }

  // =====================================================
  // SEND MESSAGE
  // =====================================================

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const question = input.value.trim();

    if (!question || sendButton.disabled) {
      return;
    }

    addMessage(question, "user");

    input.value = "";
    input.disabled = true;
    sendButton.disabled = true;

    const loading = addMessage("Typing...", "bot");

    try {
      const formData = new FormData(form);

      formData.set("message", question);

      const response = await fetch(form.dataset.url, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.reply || "Unable to process your request.");
      }

      // Remove loading bubble.
      loading.remove();

      addMessage(
        data.reply || "No response available.",
        "bot",
        Array.isArray(data.links) ? data.links : [],
      );
    } catch (error) {
      loading.remove();

      addMessage(error.message || "Connection error. Please try again.", "bot");
    } finally {
      input.disabled = false;
      sendButton.disabled = false;

      input.focus();
      scrollToBottom();
    }
  });
});
