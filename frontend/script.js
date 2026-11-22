(() => {
  const config = window.RESEARCHER_HU_CONFIG || {};
  const apiBase = (config.API_BASE_URL || "").replace(/\/$/, "");
  const supabaseReady = Boolean(config.SUPABASE_URL && config.SUPABASE_ANON_KEY && window.supabase);
  const supabaseClient = supabaseReady
    ? window.supabase.createClient(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)
    : null;

  const names = {
    general:"Academic Assistant", abstract:"Abstract Generator", introduction:"Introduction Writer",
    literature:"Literature Review Writer", methodology:"Research Methodology Writer",
    results:"Results & Discussion Writer", conclusion:"Conclusion & Recommendations",
    paraphrase:"Academic Paraphrasing", language:"Academic Language Improver",
    paper:"Research Paper Builder", thesis:"Thesis Chapter Writer",
    peer_review:"Peer Review Assistant", data_analysis:"Data Analysis Assistant",
    citation:"Citation & Reference Assistant", research_gap:"Research Gap Analysis"
  };
  let selectedModule = "general";
  let authMode = "signup";

  const $ = (id) => document.getElementById(id);
  $("year").textContent = new Date().getFullYear();

  function chooseModule(id) {
    selectedModule = id;
    $("selectedTitle").textContent = names[id] || "Academic Assistant";
    document.querySelectorAll(".tool-tab").forEach(btn => btn.classList.toggle("active", btn.dataset.module === id));
    $("prompt").focus();
  }
  document.querySelectorAll(".tool-tab").forEach(btn => btn.addEventListener("click", () => chooseModule(btn.dataset.module)));

  function openAuth(mode) {
    authMode = mode;
    $("authTitle").textContent = mode === "signup" ? "Create your account" : "Welcome back";
    $("authIntro").textContent = mode === "signup" ? "Sign up to begin your research workspace." : "Log in to continue to your workspace.";
    $("authSubmit").textContent = mode === "signup" ? "Create account" : "Log in";
    $("authSwitch").innerHTML = mode === "signup"
      ? 'Already registered? <button type="button" id="switchAuth">Log in</button>'
      : 'New to RESEARCHER HU? <button type="button" id="switchAuth">Create account</button>';
    $("authMessage").textContent = "";
    $("authModal").classList.add("show");
    $("authModal").setAttribute("aria-hidden","false");
    $("switchAuth").addEventListener("click", () => openAuth(authMode === "signup" ? "login" : "signup"));
  }
  function closeAuth() {
    $("authModal").classList.remove("show");
    $("authModal").setAttribute("aria-hidden","true");
  }
  $("navLogin").addEventListener("click", () => openAuth("login"));
  $("navSignup").addEventListener("click", () => openAuth("signup"));
  $("heroStart").addEventListener("click", () => {
    if (supabaseClient) openAuth("signup");
    else document.querySelector("#tools").scrollIntoView({behavior:"smooth"});
  });
  $("closeModal").addEventListener("click", closeAuth);
  $("authModal").addEventListener("click", e => { if (e.target === $("authModal")) closeAuth(); });

  $("authForm").addEventListener("submit", async e => {
    e.preventDefault();
    if (!supabaseClient) {
      $("authMessage").textContent = "Authentication setup pending. Add Supabase URL and anon key in frontend/config.js.";
      return;
    }
    const email = $("authEmail").value.trim();
    const password = $("authPassword").value;
    $("authSubmit").disabled = true;
    $("authMessage").textContent = "Please wait...";
    try {
      const result = authMode === "signup"
        ? await supabaseClient.auth.signUp({email,password})
        : await supabaseClient.auth.signInWithPassword({email,password});
      if (result.error) throw result.error;
      $("authMessage").textContent = authMode === "signup"
        ? "Account request submitted. Check your email if confirmation is enabled."
        : "Logged in successfully. You can now use your workspace.";
      if (authMode === "login") setTimeout(closeAuth, 900);
    } catch (err) {
      $("authMessage").textContent = err.message || "Authentication failed.";
    } finally {
      $("authSubmit").disabled = false;
    }
  });

  $("runBtn").addEventListener("click", async () => {
    const prompt = $("prompt").value.trim();
    if (prompt.length < 2) {
      $("runStatus").textContent = "Please enter your research question or instructions.";
      return;
    }
    if (!apiBase || apiBase.includes("YOUR-RENDER-SERVICE")) {
      $("runStatus").textContent = "Add your deployed Render API URL in frontend/config.js first.";
      return;
    }
    $("runBtn").disabled = true;
    $("runStatus").textContent = "Generating response...";
    $("output").textContent = "Working on your request...";
    try {
      const response = await fetch(`${apiBase}/api/chat`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          module:selectedModule,
          prompt,
          language:$("language").value,
          length:$("length").value,
          model_route:$("route").value
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "The request could not be completed.");
      $("output").textContent = data.answer || "No response was returned.";
      $("runStatus").textContent = `Completed · ${data.route} route · ${data.model}`;
    } catch (err) {
      $("output").textContent = "The request could not be completed.";
      $("runStatus").textContent = err.message;
    } finally {
      $("runBtn").disabled = false;
    }
  });

  $("copyBtn").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("output").textContent);
      $("copyBtn").textContent = "Copied";
      setTimeout(() => $("copyBtn").textContent = "Copy output", 1200);
    } catch {
      $("copyBtn").textContent = "Select and copy";
    }
  });
})();