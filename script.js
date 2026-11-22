(() => {
  "use strict";
  const config = window.RESEARCHER_HU_CONFIG || {};
  const apiBase = String(config.API_BASE_URL || "").replace(/\/$/, "");
  const supabaseReady = Boolean(config.SUPABASE_URL && config.SUPABASE_ANON_KEY && window.supabase);
  const supabaseClient = supabaseReady ? window.supabase.createClient(config.SUPABASE_URL, config.SUPABASE_ANON_KEY) : null;
  const names = {
    general: "Academic Research Assistant", topic_selection: "Research Topic Selection", abstract: "Abstract Writer", introduction: "Introduction Writer", literature: "Literature Review Writer",
    theoretical_framework: "Theoretical Framework Assistant", objectives_hypotheses: "Objectives & Hypotheses Assistant", methodology: "Research Methodology Assistant", questionnaire: "Questionnaire Developer", data_analysis: "Data Analysis Assistant", results: "Results & Discussion Assistant", conclusion: "Conclusion & Recommendations",
    research_paper: "Research Paper Builder", thesis: "Thesis & Dissertation Support", synopsis: "Research Synopsis Builder", peer_review: "Peer Review Assistant", proofreading: "Academic Proofreading", other: "Other Academic Work"
  };
  const $ = id => document.getElementById(id);
  let selectedModule = "general";
  let authMode = "signup";
  if ($("year")) $("year").textContent = new Date().getFullYear();

  function chooseModule(id) {
    selectedModule = id;
    if ($("selectedTitle")) $("selectedTitle").textContent = names[id] || names.general;
    document.querySelectorAll(".tool-tab").forEach(button => {
      const active = button.dataset.module === id;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });
  }
  document.querySelectorAll(".tool-tab").forEach(button => button.addEventListener("click", () => chooseModule(button.dataset.module)));

  function openAuth(mode) {
    authMode = mode;
    $("authTitle").textContent = mode === "signup" ? "Create your account" : "Welcome back";
    $("authIntro").textContent = mode === "signup" ? "Sign up to begin your research workspace." : "Log in to continue to your workspace.";
    $("authSubmit").textContent = mode === "signup" ? "Create account" : "Log in";
    $("authSwitch").innerHTML = mode === "signup" ? 'Already registered? <button type="button" id="switchAuth">Log in</button>' : 'New to RESEARCHER HU? <button type="button" id="switchAuth">Create account</button>';
    $("authMessage").textContent = "";
    $("authModal").classList.add("show");
    $("authModal").setAttribute("aria-hidden", "false");
    $("switchAuth").addEventListener("click", () => openAuth(authMode === "signup" ? "login" : "signup"));
  }
  function closeAuth() {
    $("authModal").classList.remove("show");
    $("authModal").setAttribute("aria-hidden", "true");
  }
  ["navLogin", "footerLogin"].forEach(id => $(id)?.addEventListener("click", () => openAuth("login")));
  ["navSignup", "ctaStart"].forEach(id => $(id)?.addEventListener("click", () => openAuth("signup")));
  $("heroStart")?.addEventListener("click", () => $("workspace").scrollIntoView({ behavior: "smooth" }));
  $("closeModal")?.addEventListener("click", closeAuth);
  $("authModal")?.addEventListener("click", event => { if (event.target.classList.contains("modal-backdrop")) closeAuth(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape") closeAuth(); });
  $("menuToggle")?.addEventListener("click", () => document.querySelector(".desktop-nav")?.classList.toggle("nav-open"));
  document.querySelectorAll(".desktop-nav a").forEach(link => link.addEventListener("click", () => document.querySelector(".desktop-nav")?.classList.remove("nav-open")));

  $("authForm")?.addEventListener("submit", async event => {
    event.preventDefault();
    if (!supabaseClient) {
      $("authMessage").textContent = "Account login is not configured yet. Add the Supabase project URL and publishable/anon key in frontend/config.js.";
      return;
    }
    const email = $("authEmail").value.trim();
    const password = $("authPassword").value;
    $("authSubmit").disabled = true;
    $("authMessage").textContent = "Please wait...";
    try {
      const result = authMode === "signup"
        ? await supabaseClient.auth.signUp({ email, password })
        : await supabaseClient.auth.signInWithPassword({ email, password });
      if (result.error) throw result.error;
      $("authMessage").textContent = authMode === "signup" ? "Account request submitted. Check your email if confirmation is enabled." : "Login successful.";
      if (authMode === "login") window.setTimeout(closeAuth, 1000);
    } catch (error) {
      $("authMessage").textContent = error.message || "Authentication failed.";
    } finally {
      $("authSubmit").disabled = false;
    }
  });

  $("runBtn")?.addEventListener("click", async () => {
    const prompt = $("prompt").value.trim();
    if (prompt.length < 2) {
      $("runStatus").textContent = "Please describe your research task first.";
      $("prompt").focus();
      return;
    }
    if (!apiBase || apiBase.includes("YOUR-RENDER")) {
      $("runStatus").textContent = "Backend URL is missing in frontend/config.js.";
      return;
    }
    const button = $("runBtn");
    button.disabled = true;
    button.textContent = "Generating...";
    $("runStatus").textContent = "Connecting to RESEARCHER HU...";
    $("output").textContent = "Working on your request. Please wait.";
    try {
      const response = await fetch(`${apiBase}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          module: selectedModule,
          prompt,
          language: $("language").value,
          writing_length: $("length").value,
          citation_style: $("citationStyle").value,
          provider: $("provider").value
        })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Server error (${response.status}).`);
      $("output").textContent = data.reply || data.response || data.content || "The server returned an empty response.";
      $("runStatus").textContent = `Completed${data.provider ? ` · ${data.provider}` : ""}${data.model ? ` · ${data.model}` : ""}`;
    } catch (error) {
      $("output").textContent = "The request could not be completed. Check the message below and try again.";
      $("runStatus").textContent = error.message || "Connection error. Check Render status and API configuration.";
    } finally {
      button.disabled = false;
      button.innerHTML = 'Generate response <span>→</span>';
    }
  });

  async function saveOutput(format) {
    const content = $("output")?.textContent || "";
    if (!content.trim() || content.startsWith("Your response will appear")) { alert("There is no generated content to download yet."); return; }
    const button = format === "docx" ? $("downloadDocx") : $("downloadPdf");
    button.disabled = true;
    try {
      const response = await fetch(`${apiBase}/export/${format}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: "RESEARCHER HU Document", content }) });
      if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.detail || "Download could not be prepared."); }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a"); link.href = url; link.download = `researcher-hu-output.${format}`; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    } catch (error) { alert(error.message || "Download failed."); }
    finally { button.disabled = false; }
  }
  $("downloadDocx")?.addEventListener("click", () => saveOutput("docx"));
  $("downloadPdf")?.addEventListener("click", () => saveOutput("pdf"));

  $("uploadBtn")?.addEventListener("click", async () => {
    const file = $("documentUpload")?.files?.[0];
    if (!file) { $("runStatus").textContent = "Please choose a DOCX, PDF or TXT file first."; return; }
    if (!apiBase) { $("runStatus").textContent = "Backend URL is missing in frontend/config.js."; return; }
    const form = new FormData(); form.append("file", file);
    $("uploadBtn").disabled = true; $("runStatus").textContent = "Uploading and extracting text...";
    try {
      const response = await fetch(`${apiBase}/api/upload`, { method: "POST", body: form });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Upload failed (${response.status}).`);
      $("prompt").value = data.text; $("prompt").dispatchEvent(new Event("input"));
      $("runStatus").textContent = `Added ${data.word_count} extracted words from ${data.filename} to your message. Review it and press Send to AI.`;
    } catch (error) { $("runStatus").textContent = error.message || "Upload failed."; }
    finally { $("uploadBtn").disabled = false; }
  });

  const humaniseInput = $("humaniseInput");
  const humaniseCount = $("humaniseCount");
  humaniseInput?.addEventListener("input", () => {
    const count = humaniseInput.value.trim() ? humaniseInput.value.trim().split(/\s+/).length : 0;
    if (humaniseCount) humaniseCount.textContent = `${count} / 500 words`;
    if (humaniseCount) humaniseCount.classList.toggle("over-limit", count > 500);
  });
  $("humaniseBtn")?.addEventListener("click", async () => {
    const text = humaniseInput?.value.trim() || "";
    const words = text ? text.split(/\s+/).length : 0;
    if (!text) { $("runStatus").textContent = "Paste text in the Humanise Text box first."; humaniseInput?.focus(); return; }
    if (words > 500) { $("runStatus").textContent = `Limit is 500 words. Your text has ${words} words.`; return; }
    const button = $("humaniseBtn"); button.disabled = true; button.textContent = "Humanising...";
    $("humaniseOutput").textContent = "Revising your text. Please wait...";
    try {
      const response = await fetch(`${apiBase}/api/humanise`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, language: $("language")?.value || "English", provider: $("provider")?.value || "auto" }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Server error (${response.status}).`);
      $("humaniseOutput").textContent = data.reply || data.content || "No revised text was returned.";
      $("runStatus").textContent = `Humanised ${data.word_count || words} words${data.provider ? ` · ${data.provider}` : ""}${data.model ? ` · ${data.model}` : ""}`;
    } catch (error) { $("humaniseOutput").textContent = "The text could not be processed."; $("runStatus").textContent = error.message || "Humanising failed."; }
    finally { button.disabled = false; button.textContent = "Humanise text"; }
  });
  $("copyHumanise")?.addEventListener("click", async () => { try { await navigator.clipboard.writeText($("humaniseOutput").textContent); $("copyHumanise").textContent = "Copied ✓"; } catch { $("copyHumanise").textContent = "Select and copy"; } });

  $("citationBtn")?.addEventListener("click", async () => {
    const details = $("citationInput")?.value.trim() || "";
    if (!details) { $("runStatus").textContent = "Enter the source details first."; $("citationInput")?.focus(); return; }
    const type = $("citationType").value;
    const style = $("citationStyleTool").value;
    const prompt = `Format the following user-supplied source information in ${style}. Requested output: ${type}. Provide an in-text citation and/or reference entry as requested. Do not invent missing authors, dates, titles, journal details, page numbers, publishers, URLs or DOIs. Clearly flag any missing information. Source details:\n${details}`;
    const button = $("citationBtn"); button.disabled = true; button.textContent = "Generating...";
    $("citationOutput").textContent = "Formatting source details...";
    try {
      const response = await fetch(`${apiBase}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ module: "references", prompt, language: $("language")?.value || "English", writing_length: "Medium", citation_style: style, provider: $("provider")?.value || "auto" }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Server error (${response.status}).`);
      $("citationOutput").textContent = data.reply || data.response || data.content || "No citation was returned.";
      $("runStatus").textContent = `Citation formatted${data.provider ? ` · ${data.provider}` : ""}${data.model ? ` · ${data.model}` : ""}`;
    } catch (error) { $("citationOutput").textContent = "Citation formatting failed."; $("runStatus").textContent = error.message || "Citation generation failed."; }
    finally { button.disabled = false; button.textContent = "Generate citation"; }
  });
  $("copyCitation")?.addEventListener("click", async () => { try { await navigator.clipboard.writeText($("citationOutput").textContent); $("copyCitation").textContent = "Copied ✓"; } catch { $("copyCitation").textContent = "Select and copy"; } });

  $("copyBtn")?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("output").textContent);
      $("copyBtn").textContent = "Copied ✓";
      window.setTimeout(() => { $("copyBtn").textContent = "Copy output"; }, 1400);
    } catch {
      $("copyBtn").textContent = "Select and copy";
    }
  });
})();
