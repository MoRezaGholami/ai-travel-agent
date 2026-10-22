(() => {
  const STORAGE_KEY = "travel_agent_thread_id";

  const logEl = document.getElementById("log");
  const form = document.getElementById("composer");
  const messageEl = document.getElementById("message");
  const sendBtn = document.getElementById("sendBtn");
  const statusLine = document.getElementById("statusLine");
  const liveStatus = document.getElementById("liveStatus");
  const liveStatusText = document.getElementById("liveStatusText");
  const threadChip = document.getElementById("threadChip");
  const chatTitle = document.getElementById("chatTitle");
  const approval = document.getElementById("approval");
  const pendingBox = document.getElementById("pendingBox");
  const approveBtn = document.getElementById("approveBtn");
  const rejectBtn = document.getElementById("rejectBtn");
  const newChatBtn = document.getElementById("newChatBtn");
  const threadList = document.getElementById("threadList");
  const threadEmpty = document.getElementById("threadEmpty");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebarBackdrop = document.getElementById("sidebarBackdrop");

  let threadId = localStorage.getItem(STORAGE_KEY) || null;
  let busy = false;
  let streamBubble = null;
  let streamText = "";

  function setThread(id, title) {
    threadId = id;
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
    threadChip.textContent = id ? `thread ${id.slice(0, 8)}…` : "new thread";
    threadChip.title = id || "No thread yet";
    if (title) chatTitle.textContent = title;
    else if (!id) chatTitle.textContent = "New chat";
    highlightActiveThread();
  }

  function setBusy(on, label = "") {
    busy = on;
    sendBtn.disabled = on;
    approveBtn.disabled = on;
    rejectBtn.disabled = on;
    messageEl.disabled = on;
    statusLine.classList.toggle("error", false);
    if (!on) {
      liveStatus.hidden = true;
      statusLine.textContent = label;
    } else if (label) {
      statusLine.textContent = label;
    }
  }

  function setLive(label) {
    if (!label) {
      liveStatus.hidden = true;
      return;
    }
    liveStatus.hidden = false;
    liveStatusText.textContent = label;
    statusLine.classList.toggle("error", false);
    statusLine.textContent = label;
  }

  function setError(msg) {
    liveStatus.hidden = true;
    statusLine.classList.add("error");
    statusLine.textContent = msg;
  }

  function lightMarkdown(text) {
    const escaped = String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return escaped
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");
  }

  function clearLog() {
    logEl.innerHTML = "";
    streamBubble = null;
    streamText = "";
  }

  function addBubble(role, text) {
    const div = document.createElement("div");
    div.className = `bubble ${role}`;
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = role === "user" ? "You" : "Assistant";
    const body = document.createElement("div");
    body.className = "body";
    body.innerHTML = lightMarkdown(text || "");
    div.append(who, body);
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
    return div;
  }

  function ensureStreamBubble() {
    if (streamBubble) return streamBubble;
    streamBubble = addBubble("assistant", "");
    streamBubble.classList.add("streaming");
    streamText = "";
    return streamBubble;
  }

  function appendStreamToken(text) {
    ensureStreamBubble();
    streamText += text;
    streamBubble.querySelector(".body").innerHTML = lightMarkdown(streamText);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function setStreamPartial(text) {
    ensureStreamBubble();
    streamText = text || "";
    streamBubble.querySelector(".body").innerHTML = lightMarkdown(streamText);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function finishStreamBubble() {
    if (streamBubble) {
      streamBubble.classList.remove("streaming");
      if (!streamText.trim()) streamBubble.remove();
    }
    streamBubble = null;
    streamText = "";
  }

  function showWelcome() {
    clearLog();
    addBubble(
      "assistant",
      "Hi — ask me to search flights or hotels, build an itinerary, or book after you confirm.\n\nTry: Find flights Tehran to Istanbul on 2026-11-10"
    );
  }

  function showPending(pending) {
    if (!pending || !pending.length) {
      approval.hidden = true;
      pendingBox.textContent = "";
      return;
    }
    pendingBox.textContent = pending
      .map((p) => {
        const args = JSON.stringify(p.args || {}, null, 2);
        return `tool: ${p.tool}\nargs: ${args}${p.description ? `\nnote: ${p.description}` : ""}`;
      })
      .join("\n\n---\n\n");
    approval.hidden = false;
  }

  function closeSidebar() {
    document.body.classList.remove("sidebar-open");
    sidebarBackdrop.hidden = true;
  }

  function openSidebar() {
    document.body.classList.add("sidebar-open");
    sidebarBackdrop.hidden = false;
  }

  async function api(path, options = {}) {
    const res = await fetch(path, {
      method: options.method || (options.body ? "POST" : "GET"),
      headers: options.body ? { "Content-Type": "application/json" } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error(`HTTP ${res.status}`);
    }
    if (!res.ok) {
      const detail = data.detail || data.error;
      throw new Error(typeof detail === "string" ? detail : `HTTP ${res.status}`);
    }
    return data;
  }

  async function streamApi(path, body, onEvent) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const data = await res.json();
        detail = data.detail || data.error || detail;
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : `HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        const line = part
          .split("\n")
          .map((l) => l.trim())
          .find((l) => l.startsWith("data:"));
        if (!line) continue;
        const raw = line.slice(5).trim();
        if (!raw) continue;
        onEvent(JSON.parse(raw));
      }
    }
  }

  function highlightActiveThread() {
    threadList.querySelectorAll(".thread-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.threadId === threadId);
    });
  }

  async function refreshThreadList() {
    try {
      const items = await api("/v1/threads");
      threadList.innerHTML = "";
      threadEmpty.hidden = items.length > 0;
      for (const item of items) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "thread-item";
        btn.dataset.threadId = item.thread_id;
        btn.innerHTML = `
          <span class="t-title"></span>
          <span class="t-meta"></span>
        `;
        btn.querySelector(".t-title").textContent = item.title;
        const meta = btn.querySelector(".t-meta");
        meta.textContent = `${item.message_count} messages`;
        if (item.needs_approval) {
          const badge = document.createElement("span");
          badge.className = "badge";
          badge.textContent = "approve";
          meta.appendChild(badge);
        }
        btn.addEventListener("click", () => openThread(item.thread_id, item.title));
        threadList.appendChild(btn);
      }
      highlightActiveThread();
    } catch (err) {
      threadEmpty.hidden = false;
      threadEmpty.textContent = `Could not load chats: ${err.message}`;
    }
  }

  async function openThread(id, title) {
    if (busy) return;
    setBusy(true, "Loading chat…");
    try {
      const data = await api(`/v1/threads/${encodeURIComponent(id)}`);
      setThread(data.thread_id, title || "Chat");
      clearLog();
      for (const msg of data.messages || []) {
        addBubble(msg.role === "user" ? "user" : "assistant", msg.content);
      }
      if (!(data.messages || []).length) showWelcome();
      showPending(data.pending || []);
      if (data.status === "needs_approval") {
        setBusy(false, "Waiting for your approval…");
      } else {
        setBusy(false, "");
      }
      closeSidebar();
      messageEl.focus();
    } catch (err) {
      setBusy(false);
      setError(err.message || String(err));
    }
  }

  function handleDone(data) {
    finishStreamBubble();
    if (data.thread_id) setThread(data.thread_id);

    if (data.status === "error") {
      setBusy(false);
      setError(data.error || "Something went wrong");
      showPending([]);
      refreshThreadList();
      return;
    }

    if (data.status === "needs_approval") {
      showPending(data.pending || []);
      setBusy(false, "Waiting for your approval…");
      refreshThreadList();
      return;
    }

    showPending([]);
    setBusy(false, "");
    refreshThreadList();
  }

  async function runStream(path, body) {
    setBusy(true, "Starting…");
    setLive("Starting…");
    streamBubble = null;
    streamText = "";
    let sawText = false;

    try {
      await streamApi(path, body, (event) => {
        const type = event.type;
        if (type === "meta" && event.thread_id) {
          setThread(event.thread_id);
          return;
        }
        if (type === "status") {
          setLive(event.label || "Working…");
          return;
        }
        if (type === "token") {
          sawText = true;
          appendStreamToken(event.text || "");
          return;
        }
        if (type === "reply_partial") {
          sawText = true;
          setStreamPartial(event.text || "");
          return;
        }
        if (type === "done") {
          if (event.reply) {
            if (sawText && streamBubble) {
              streamText = event.reply;
              streamBubble.querySelector(".body").innerHTML = lightMarkdown(streamText);
            } else if (!sawText) {
              addBubble("assistant", event.reply);
            }
          }
          handleDone(event);
        }
      });
    } catch (err) {
      finishStreamBubble();
      setBusy(false);
      setError(err.message || String(err));
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (busy) return;
    const message = messageEl.value.trim();
    if (!message) return;

    addBubble("user", message);
    messageEl.value = "";
    if (!threadId) chatTitle.textContent = message.slice(0, 48) || "New chat";
    await runStream("/v1/chat/stream", { message, thread_id: threadId });
  });

  messageEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  approveBtn.addEventListener("click", async () => {
    if (busy || !threadId) return;
    await runStream("/v1/approve/stream", { thread_id: threadId });
  });

  rejectBtn.addEventListener("click", async () => {
    if (busy || !threadId) return;
    await runStream("/v1/reject/stream", {
      thread_id: threadId,
      reason: "User rejected from chat UI",
    });
  });

  newChatBtn.addEventListener("click", () => {
    if (busy) return;
    setThread(null);
    showWelcome();
    showPending([]);
    setBusy(false, "New conversation — send a message to start.");
    closeSidebar();
    messageEl.focus();
  });

  sidebarToggle.addEventListener("click", openSidebar);
  sidebarBackdrop.addEventListener("click", closeSidebar);

  setThread(threadId);
  refreshThreadList().then(() => {
    if (threadId) openThread(threadId);
    else showWelcome();
  });
})();
