"""The setup page HTML/CSS/JS. The __TOKEN__ placeholder is replaced at serve time."""

PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gateway setup</title>
<style>
:root{
  --paper:#eceef2; --card:#ffffff; --ink:#14181f; --muted:#6b7280;
  --rule:#d4d9e0; --accent:#1f3fd8; --ok:#0d7a52; --bad:#a33018; --wait:#8a6a12;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto;padding:40px 20px 72px}
header{margin-bottom:28px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);margin:0 0 8px}
h1{font-size:27px;line-height:1.15;letter-spacing:-.02em;margin:0 0 8px;font-weight:640}
header p{margin:0;color:var(--muted);max-width:52ch}

/* signature: the request path, lit hop by hop */
.route{display:flex;align-items:stretch;gap:0;margin:0 0 26px;border:1px solid var(--rule);
  background:var(--card);border-radius:10px;overflow:hidden}
.hop{flex:1;padding:12px 10px;text-align:center;position:relative;min-width:0}
.hop + .hop{border-left:1px solid var(--rule)}
.hop b{display:block;font-family:var(--mono);font-size:12px;font-weight:600;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hop span{display:block;font-size:10.5px;color:var(--muted);letter-spacing:.06em;text-transform:uppercase;margin-top:3px}
.hop::after{content:"";position:absolute;left:0;right:0;bottom:0;height:3px;background:var(--rule);
  transition:background .35s ease}
.hop.live::after{background:var(--ok)}
.hop.fail::after{background:var(--bad)}
.hop.pending::after{background:var(--wait)}

.card{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:22px 22px 24px;margin-bottom:18px}
.card h2{font-size:12px;font-family:var(--mono);letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);margin:0 0 16px;font-weight:600}
label{display:block;font-size:13px;font-weight:600;margin:0 0 5px}
.hint{font-size:12.5px;color:var(--muted);margin:5px 0 0}
input[type=text],input[type=password],select{width:100%;padding:9px 11px;border:1px solid var(--rule);
  border-radius:7px;font-family:var(--mono);font-size:13.5px;background:#fbfcfd;color:var(--ink)}
input:focus,select:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:transparent}
.field{margin-bottom:16px}
.row{display:flex;gap:12px;flex-wrap:wrap}
.row .field{flex:1;min-width:200px}
.check{display:flex;gap:9px;align-items:flex-start;padding:9px 0;border-top:1px solid var(--rule)}
.check:first-of-type{border-top:none}
.check input{margin-top:3px;accent-color:var(--accent)}
.check label{margin:0;font-weight:600}
.check code{font-family:var(--mono);font-size:12px;color:var(--muted);display:block;font-weight:400;margin-top:2px}
.actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:4px}
button{font:inherit;font-weight:600;font-size:14px;padding:9px 17px;border-radius:7px;cursor:pointer;border:1px solid transparent}
button.primary{background:var(--accent);color:#fff}
button.primary:hover{background:#1733ab}
button.ghost{background:transparent;border-color:var(--rule);color:var(--ink)}
button.ghost:hover{background:#f3f5f8}
button:disabled{opacity:.5;cursor:not-allowed}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.msg{margin-top:14px;padding:11px 13px;border-radius:7px;font-size:13.5px;border:1px solid var(--rule);
  background:#f7f8fa;white-space:pre-wrap;font-family:var(--mono);display:none}
.msg.show{display:block}
.msg.ok{border-color:#a9d8c3;background:#eefaf4;color:var(--ok)}
.msg.bad{border-color:#e6bcb0;background:#fdf1ee;color:var(--bad)}
.tool{display:flex;align-items:center;gap:12px;padding:12px 0;border-top:1px solid var(--rule);flex-wrap:wrap}
.tool:first-child{border-top:none;padding-top:0}
.tool .who{flex:1;min-width:180px}
.tool .who b{display:block;font-size:14px}
.tool .who code{font-family:var(--mono);font-size:12px;color:var(--muted)}
.chip{font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;
  padding:3px 8px;border-radius:20px;border:1px solid var(--rule);white-space:nowrap}
.chip.yes{color:var(--ok);border-color:#a9d8c3;background:#eefaf4}
.chip.no{color:var(--muted)}
.tool button{padding:6px 13px;font-size:13px}
pre.log{margin:0;font-family:var(--mono);font-size:12px;line-height:1.45;max-height:230px;
  overflow:auto;white-space:pre-wrap;word-break:break-word}
ul.files{list-style:none;margin:0;padding:0;font-family:var(--mono);font-size:12.5px}
ul.files li{display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-top:1px solid var(--rule)}
ul.files li:first-child{border-top:none}
ul.files .no{color:var(--muted)}
ul.files .yes{color:var(--ok)}
footer{margin-top:22px;font-size:12.5px;color:var(--muted)}
footer code{font-family:var(--mono)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style></head><body>
<div class="wrap">
<header>
  <p class="eyebrow">Internal LLM gateway</p>
  <h1>Set up Claude Code and Qwen Code</h1>
  <p>Enter your gateway address and key once. Both CLIs will use them in every project directory, in every new terminal.</p>
</header>

<div class="route" id="route">
  <div class="hop" data-hop="cli"><b>CLI</b><span>claude / qwen</span></div>
  <div class="hop" data-hop="net"><b>Tailscale</b><span>network</span></div>
  <div class="hop" data-hop="gw"><b>LiteLLM</b><span>gateway</span></div>
  <div class="hop" data-hop="model"><b id="hopModel">Qwen</b><span>vLLM</span></div>
</div>

<div class="card">
  <h2>Command-line tools</h2>
  <div id="tools"><p class="hint">Checking what's installed…</p></div>
  <p class="hint" id="pathWarn" style="display:none"></p>
  <div class="msg" id="installMsg"></div>
</div>

<div class="card">
  <h2>Connection</h2>
  <div class="field">
    <label for="url">Gateway URL</label>
    <input id="url" type="text" placeholder="https://litellm.your-tailnet.ts.net" autocomplete="off" spellcheck="false">
    <p class="hint">Your Tailscale address for LiteLLM. Leave off <code>/v1</code> — it's added where each tool needs it.</p>
  </div>
  <div class="field">
    <label for="key">API key</label>
    <input id="key" type="password" placeholder="sk-…" autocomplete="off" spellcheck="false">
    <p class="hint">Your personal LiteLLM virtual key.</p>
  </div>
  <div class="row">
    <div class="field">
      <label for="model">Model</label>
      <input id="model" type="text" placeholder="qwen3-coder" autocomplete="off" spellcheck="false" list="modelList">
      <datalist id="modelList"></datalist>
    </div>
    <div class="field">
      <label for="small">Fast model <span style="font-weight:400;color:var(--muted)">(background tasks)</span></label>
      <input id="small" type="text" placeholder="same as above" autocomplete="off" spellcheck="false" list="modelList">
    </div>
  </div>
  <div class="check" style="border-top:1px solid var(--rule)">
    <input type="checkbox" id="insecure">
    <div><label for="insecure">Skip certificate check</label>
    <code>only if your gateway uses a self-signed cert</code></div>
  </div>
  <div class="actions">
    <button class="ghost" id="testBtn" type="button">Test connection</button>
  </div>
  <div class="msg" id="testMsg"></div>
</div>

<div class="card">
  <h2>Where to write it</h2>
  <div class="check"><input type="checkbox" id="t_claude" checked>
    <div><label for="t_claude">Claude Code</label><code>~/.claude/settings.json</code></div></div>
  <div class="check"><input type="checkbox" id="t_qwen" checked>
    <div><label for="t_qwen">Qwen Code</label><code>~/.qwen/.env</code></div></div>
  <div class="check"><input type="checkbox" id="t_env" checked>
    <div><label for="t_env">Shared shell variables</label><code>~/.config/internal-llm/env</code></div></div>
  <div class="check"><input type="checkbox" id="t_rc" checked>
    <div><label for="t_rc">Load on every new terminal</label><code>adds one line to ~/.zshrc and ~/.bashrc</code></div></div>
  <div class="actions" style="margin-top:14px">
    <button class="primary" id="applyBtn" type="button">Save configuration</button>
    <span class="hint" style="margin:0">Existing files are backed up first.</span>
  </div>
  <div class="msg" id="applyMsg"></div>
</div>

<div class="card">
  <h2>Current state</h2>
  <ul class="files" id="files"></ul>
</div>

<footer>
  Open a new terminal, then run <code>claude</code> or <code>qwen</code> from any project.
  Stop this page with Ctrl-C in the terminal where you started it.
</footer>
</div>

<script>
const TOKEN = "__TOKEN__";
const $ = id => document.getElementById(id);

async function api(path, body){
  const r = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: {"Content-Type":"application/json","X-Setup-Token":TOKEN},
    body: body ? JSON.stringify(body) : undefined
  });
  return r.json();
}

function setMsg(el, text, kind){
  el.textContent = text;
  el.className = "msg show" + (kind ? " " + kind : "");
}

function hops(state){
  document.querySelectorAll(".hop").forEach(h => h.className = "hop" + (state ? " " + state : ""));
}

let installing = false;

function detect(){
  api("/api/detect").then(d => {
    const nodeInfo = d.node.found
      ? `Node.js ${d.node.major}` + (d.node.major < 22 ? " — too old for the npm route" : "")
      : "Node.js not installed";
    $("tools").innerHTML = d.tools.map(t => `
      <div class="tool">
        <div class="who"><b>${t.label}</b><code>${t.found ? (t.version || t.path) : t.note}</code></div>
        <span class="chip ${t.found?'yes':'no'}">${t.found ? 'installed' : 'missing'}</span>
        ${t.found ? '' : `<button class="ghost" data-install="${t.id}" data-method="native">Install</button>
                          <button class="ghost" data-install="${t.id}" data-method="npm">via npm</button>`}
      </div>`).join("") +
      `<div class="tool"><div class="who"><b style="font-weight:400;color:var(--muted);font-size:13px">${nodeInfo}</b></div></div>`;
    document.querySelectorAll("[data-install]").forEach(b => b.onclick = () => install(b.dataset.install, b.dataset.method));
    if(d.on_path_warning){ $("pathWarn").textContent = d.on_path_warning; $("pathWarn").style.display = "block"; }
    const missing = d.tools.filter(t => !t.found).length;
    if(missing && !installing) setMsg($("installMsg"),
      "You can still save the configuration now — it will be waiting when you install.", "");
  });
}

async function install(tool, method){
  installing = true;
  document.querySelectorAll("[data-install]").forEach(b => b.disabled = true);
  const start = await api("/api/install", {tool, method});
  if(!start.ok){
    installing = false;
    document.querySelectorAll("[data-install]").forEach(b => b.disabled = false);
    return setMsg($("installMsg"), start.error, "bad");
  }
  const el = $("installMsg");
  el.className = "msg show";
  el.innerHTML = '<pre class="log" id="log"></pre>';
  const poll = setInterval(async () => {
    const s = await api("/api/install?job=" + start.job);
    const log = $("log");
    if(log){ log.textContent = s.lines.join("\n"); log.scrollTop = log.scrollHeight; }
    if(s.done){
      clearInterval(poll);
      installing = false;
      const ok = s.code === 0 && s.verified;
      el.className = "msg show " + (ok ? "ok" : "bad");
      el.insertAdjacentHTML("afterbegin",
        (ok ? "Installed. Open a new terminal so your shell picks up the new command.\n\n"
            : `Install did not complete (exit ${s.code}). Output below.\n\n`));
      detect();
    }
  }, 900);
}

function refresh(){
  api("/api/status").then(s => {
    if(s.url && !$("url").value) $("url").value = s.url;
    if(s.model && !$("model").value) $("model").value = s.model;
    if(s.key_masked) $("key").placeholder = s.key_masked + "  (saved — leave blank to keep)";
    $("files").innerHTML = s.files.map(f =>
      `<li><span>${f.path}</span><span class="${f.exists?'yes':'no'}">${f.exists?'configured':'not set'}</span></li>`
    ).join("");
  });
}

$("testBtn").onclick = async () => {
  const btn = $("testBtn"); btn.disabled = true; btn.textContent = "Testing…";
  hops("pending");
  setMsg($("testMsg"), "Contacting gateway…", "");
  const res = await api("/api/test", {
    url: $("url").value, key: $("key").value, insecure: $("insecure").checked
  });
  btn.disabled = false; btn.textContent = "Test connection";
  if(res.ok){
    hops("live");
    const list = res.models.length ? "\n\n" + res.models.join("\n") : "";
    setMsg($("testMsg"), `Reachable in ${res.ms} ms. ${res.models.length} model(s) available.` + list, "ok");
    $("modelList").innerHTML = res.models.map(m => `<option value="${m}">`).join("");
    if(!$("model").value && res.models.length) $("model").value = res.models[0];
    if($("model").value) $("hopModel").textContent = $("model").value.split("/").pop();
  } else {
    document.querySelectorAll(".hop").forEach((h,i) => h.className = "hop " + (i < res.reached ? "live" : "fail"));
    setMsg($("testMsg"), res.error, "bad");
  }
};

$("applyBtn").onclick = async () => {
  const btn = $("applyBtn"); btn.disabled = true; btn.textContent = "Saving…";
  const res = await api("/api/apply", {
    url: $("url").value, key: $("key").value,
    model: $("model").value, small: $("small").value,
    targets: {
      claude: $("t_claude").checked, qwen: $("t_qwen").checked,
      env: $("t_env").checked, rc: $("t_rc").checked
    }
  });
  btn.disabled = false; btn.textContent = "Save configuration";
  if(res.ok){
    const lines = res.results.map(r =>
      `${r.action.padEnd(22)} ${r.path}` + (r.backup ? `\n${"backup".padEnd(22)} ${r.backup}` : "")
    ).join("\n");
    setMsg($("applyMsg"), "Saved.\n\n" + lines + "\n\nOpen a new terminal to pick this up.", "ok");
    $("key").value = "";
    refresh();
  } else {
    setMsg($("applyMsg"), res.error, "bad");
  }
};

refresh();
detect();
</script>
</body></html>

"""
