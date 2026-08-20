#!/usr/bin/env python3
"""quota_desk.html_page — the full HTML page with CSS and JS."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quota Desk</title>
<style>
  :root{
    --paper:#E9EBEF;      /* cool instrument grey */
    --card:#FDFDFE;
    --ink:#14161B;
    --muted:#6A7180;
    --line:#C9CFD9;
    --live:#1F6F4A;       /* signal green, dialled down */
    --dead:#B03030;
    --meter:#2B4EE6;      /* electric blue, used only in the meters */
    --near:#B26A00;       /* amber for keys close to their ceiling */
    --mono:ui-monospace,"JetBrains Mono","SF Mono",Menlo,Consolas,monospace;
    --sans:system-ui,-apple-system,"Segoe UI",Inter,sans-serif;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
       font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
  .wrap{max-width:1120px;margin:0 auto;padding:28px 20px 80px}

  header{display:flex;flex-wrap:wrap;gap:18px;align-items:flex-end;
         justify-content:space-between;padding-bottom:18px;
         border-bottom:2px solid var(--ink)}
  h1{font-size:26px;margin:0;letter-spacing:-.02em;font-weight:640}
  .sub{font-family:var(--mono);font-size:11.5px;color:var(--muted);
       text-transform:uppercase;letter-spacing:.12em;margin-top:4px}

  .rail{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  .pill{display:flex;align-items:center;gap:7px;background:var(--card);
        border:1px solid var(--line);border-radius:999px;padding:5px 12px;
        font-family:var(--mono);font-size:11.5px}
  .dot{width:7px;height:7px;border-radius:50%;background:var(--muted)}
  .pill.up .dot{background:var(--live);box-shadow:0 0 0 3px rgba(31,111,74,.16)}
  .pill.down .dot{background:var(--dead);box-shadow:0 0 0 3px rgba(176,48,48,.16)}
  .pill.down{color:var(--dead);cursor:help}

  button{font:inherit;cursor:pointer;border-radius:7px;border:1px solid var(--ink);
         background:var(--ink);color:#fff;padding:9px 16px;font-weight:530}
  button:hover{opacity:.88}
  button.ghost{background:transparent;color:var(--ink);border-color:var(--line)}
  button.ghost:hover{border-color:var(--ink);opacity:1}
  button.tiny{padding:4px 10px;font-size:12.5px;font-family:var(--mono)}
  button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible
    {outline:2px solid var(--meter);outline-offset:2px}

  .cols{display:grid;grid-template-columns:340px 1fr;gap:22px;margin-top:24px;align-items:start}
  @media(max-width:860px){.cols{grid-template-columns:1fr}}

  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px}
  h2{font-size:12px;font-family:var(--mono);text-transform:uppercase;
     letter-spacing:.13em;color:var(--muted);margin:0 0 16px;font-weight:600}

  label{display:block;font-size:12.5px;color:var(--muted);margin:14px 0 5px}
  label:first-of-type{margin-top:0}
  input,select{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:7px;
               background:#fff;font-family:var(--mono);font-size:13.5px;color:var(--ink)}
  .hint{font-size:12px;color:var(--muted);margin-top:6px}
  .hint b{font-family:var(--mono);font-weight:500;color:var(--ink)}

  /* the meter: the one thing this page is built around */
  .person{border-top:1px solid var(--line);padding:16px 0}
  .person:first-of-type{border-top:none;padding-top:0}
  .who{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
  .name{font-weight:600;font-size:15.5px}
  .keyid{font-family:var(--mono);font-size:11.5px;color:var(--muted)}
  .meter{position:relative;height:14px;background:#E4E7ED;border-radius:3px;
         margin:11px 0 7px;overflow:hidden}
  .fill{position:absolute;inset:0 auto 0 0;background:var(--meter);border-radius:3px;
        transition:width .5s cubic-bezier(.22,1,.36,1)}
  .fill.near{background:var(--near)}
  .fill.over{background:var(--dead)}
  .ticks{position:absolute;inset:0;display:flex;pointer-events:none}
  .ticks i{flex:1;border-right:1px solid rgba(255,255,255,.55)}
  .ticks i:last-child{border:none}
  .readout{display:flex;justify-content:space-between;gap:12px;
           font-family:var(--mono);font-size:12px;color:var(--muted);flex-wrap:wrap}
  .readout b{color:var(--ink);font-weight:600}
  .acts{display:flex;gap:7px;margin-top:10px}

  table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:12.5px}
  th{text-align:left;color:var(--muted);font-weight:500;padding:0 10px 8px 0;
     border-bottom:1px solid var(--line);white-space:nowrap}
  td{padding:8px 10px 8px 0;border-bottom:1px solid #EDEFF3;white-space:nowrap}
  .num{text-align:right}

  details{margin-top:22px}
  summary{cursor:pointer;font-family:var(--mono);font-size:12px;color:var(--muted);
          text-transform:uppercase;letter-spacing:.12em}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}
  @media(max-width:600px){.grid2{grid-template-columns:1fr}}

  .empty{color:var(--muted);font-size:14px;padding:6px 0}
  .toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);
         background:var(--ink);color:#fff;padding:11px 18px;border-radius:8px;
         font-size:14px;max-width:90vw;box-shadow:0 6px 24px rgba(0,0,0,.22);z-index:9}
  .toast.bad{background:var(--dead)}
  .newkey{margin-top:14px;padding:12px;border:1px dashed var(--ink);border-radius:8px;
          font-family:var(--mono);font-size:12.5px;word-break:break-all;background:#F6F7FA}
  @media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div>
    <h1>Quota Desk</h1>
    <div class="sub" id="stackline">LiteLLM · vLLM · loading</div>
  </div>
  <div class="rail" id="rail"></div>
</header>

<div class="cols">

  <section class="card">
    <h2>Issue a key</h2>
    <label for="uid">Who is this for</label>
    <input id="uid" placeholder="priya" autocomplete="off">

    <label for="tokens">Tokens per period</label>
    <input id="tokens" type="number" value="10000000" min="1" step="1000000">
    <div class="hint">Becomes a budget of <b id="asdollars">$1.00</b> at the current rate.</div>

    <label for="dur">Resets every</label>
    <select id="dur">
      <option value="30d" selected>30 days</option>
      <option value="7d">7 days</option>
      <option value="1d">1 day</option>
      <option value="">Never — one fixed allowance</option>
    </select>

    <label for="model">Allowed model</label>
    <input id="model" value="qwen35b">

    <div style="margin-top:18px"><button id="make">Issue key</button></div>
    <div id="fresh"></div>
  </section>

  <section class="card">
    <h2>Keys in circulation</h2>
    <div id="people"><div class="empty">Reading from LiteLLM…</div></div>
  </section>

</div>

<section class="card" style="margin-top:22px">
  <h2>Users</h2>
  <div id="users"><div class="empty">Loading…</div></div>
</section>

<details>
  <summary>Connection settings</summary>
  <div class="card" style="margin-top:12px">
    <div class="grid2">
      <div>
        <label for="c_lite">LiteLLM address</label>
        <input id="c_lite">
        <label for="c_vllm">vLLM address</label>
        <input id="c_vllm">
      </div>
      <div>
        <label for="c_key">Master key</label>
        <input id="c_key" type="password" placeholder="leave blank to keep current">
        <label for="c_cost">Cost per token (must match litellm_config.yaml)</label>
        <input id="c_cost">
      </div>
    </div>
    <div class="hint" style="margin-top:12px">If this rate does not match
      <b>input_cost_per_token</b> in your config, the token figures on this page will lie.</div>
    <div style="margin-top:16px"><button id="savecfg" class="ghost">Save settings</button></div>
  </div>
</details>

</div>

<script>
var cfg = {cost_per_token: 0.0000001};

function api(path, opts){
  return fetch(path, opts).then(function(r){ return r.json(); });
}
function lite(method, path, body){
  return api('/api/lite', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({method:method, path:path, body:body})});
}
function toast(msg, bad){
  var t = document.createElement('div');
  t.className = 'toast' + (bad ? ' bad' : '');
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(function(){ t.remove(); }, bad ? 6000 : 3000);
}
function commas(n){ return Math.round(n).toLocaleString('en-US'); }
function short(n){
  if (n >= 1e9) return (n/1e9).toFixed(1).replace(/\.0$/,'') + 'B';
  if (n >= 1e6) return (n/1e6).toFixed(1).replace(/\.0$/,'') + 'M';
  if (n >= 1e3) return (n/1e3).toFixed(1).replace(/\.0$/,'') + 'K';
  return String(Math.round(n));
}
function daysUntil(iso){
  if (!iso) return null;
  var d = (new Date(iso) - new Date()) / 86400000;
  return d > 0 ? Math.ceil(d) : 0;
}

/* --- settings ------------------------------------------------------- */
function loadConfig(){
  return api('/api/config').then(function(c){
    cfg = c;
    document.getElementById('c_lite').value = c.litellm_url;
    document.getElementById('c_vllm').value = c.vllm_url;
    document.getElementById('c_cost').value = c.cost_per_token;
    document.getElementById('model').value = c.model_name;
    document.getElementById('stackline').textContent =
      'LiteLLM ' + c.litellm_url.replace(/^https?:\/\//,'') +
      ' · vLLM ' + c.vllm_url.replace(/^https?:\/\//,'') + ' · ' + c.model_name;
    priceHint();
  });
}
document.getElementById('savecfg').onclick = function(){
  api('/api/config', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      litellm_url: document.getElementById('c_lite').value,
      vllm_url: document.getElementById('c_vllm').value,
      master_key: document.getElementById('c_key').value,
      cost_per_token: document.getElementById('c_cost').value
    })}).then(function(){
      document.getElementById('c_key').value = '';
      toast('Settings saved.');
      loadConfig().then(refresh);
    });
};

/* --- status rail ---------------------------------------------------- */
function drawStatus(){
  api('/api/status').then(function(r){
    var rail = document.getElementById('rail');
    rail.innerHTML = '';
    r.services.forEach(function(s){
      var el = document.createElement('span');
      el.className = 'pill ' + (s.up ? 'up' : 'down');
      el.innerHTML = '<span class="dot"></span>' + s.name + ':' + s.port;
      if (!s.up) el.title = 'Not answering. Start it with:  ' + s.fix;
      rail.appendChild(el);
    });
    var b = document.createElement('button');
    b.className = 'ghost tiny';
    b.textContent = 'Recheck';
    b.onclick = function(){ drawStatus(); refresh(); };
    rail.appendChild(b);
  });
}

/* --- keys ----------------------------------------------------------- */
function priceHint(){
  var tokens = parseFloat(document.getElementById('tokens').value || 0);
  var dollars = tokens * parseFloat(cfg.cost_per_token);
  document.getElementById('asdollars').textContent = '$' + dollars.toFixed(4).replace(/0+$/,'0');
}
document.getElementById('tokens').oninput = priceHint;

document.getElementById('make').onclick = function(){
  var uid = document.getElementById('uid').value.trim();
  var tokens = parseFloat(document.getElementById('tokens').value);
  if (!uid) { toast('Give the key an owner first.', true); return; }
  if (!(tokens > 0)) { toast('Set a token allowance above zero.', true); return; }
  var body = {
    user_id: uid,
    max_budget: tokens * parseFloat(cfg.cost_per_token),
    models: [document.getElementById('model').value.trim()]
  };
  var dur = document.getElementById('dur').value;
  if (dur) body.budget_duration = dur;

  lite('POST', '/key/generate', body).then(function(r){
    if (r.status >= 300 || !r.data.key){
      toast(describe(r), true); return;
    }
    document.getElementById('fresh').innerHTML =
      '<div class="newkey"><div style="color:var(--muted);margin-bottom:6px">' +
      'Copy this now — LiteLLM will not show it again.</div>' + r.data.key + '</div>';
    document.getElementById('uid').value = '';
    toast('Key issued for ' + uid + '.');
    refresh();
  });
};

function describe(r){
  var d = r.data || {};
  var m = (d.error && (d.error.message || d.error)) || d.detail || d.message;
  if (typeof m === 'object') m = JSON.stringify(m);
  return m ? String(m).slice(0, 300) : ('LiteLLM answered ' + r.status + '.');
}

function drawPeople(){
  lite('GET', '/key/list?return_full_object=true&size=100').then(function(r){
    var box = document.getElementById('people');
    if (r.status >= 300){
      box.innerHTML = '<div class="empty">' + describe(r) + '</div>';
      return;
    }
    var keys = r.data.keys || r.data.data || [];
    keys = keys.filter(function(k){ return typeof k === 'object' && k.token; });
    if (!keys.length){
      box.innerHTML = '<div class="empty">No keys yet. Issue one on the left and it appears here.</div>';
      return;
    }
    var rate = parseFloat(cfg.cost_per_token);
    box.innerHTML = '';
    keys.sort(function(a,b){ return (b.spend||0) - (a.spend||0); });
    keys.forEach(function(k){
      var spend = k.spend || 0;
      var cap = k.max_budget;
      var used = spend / rate;
      var allowed = cap ? cap / rate : null;
      var pct = allowed ? Math.min(100, (used / allowed) * 100) : 0;
      var tone = pct >= 100 ? 'over' : (pct >= 80 ? 'near' : '');
      var left = allowed ? Math.max(0, allowed - used) : null;
      var days = daysUntil(k.budget_reset_at);

      var el = document.createElement('div');
      el.className = 'person';
      el.innerHTML =
        '<div class="who"><span class="name">' + (k.user_id || 'unassigned') + '</span>' +
        '<span class="keyid">' + (k.key_alias ? k.key_alias + ' · ' : '') +
        '…' + String(k.token).slice(-8) + '</span></div>' +
        (allowed
          ? '<div class="meter"><div class="fill ' + tone + '" style="width:' + pct + '%"></div>' +
            '<div class="ticks"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div>'
          : '<div style="height:11px"></div>') +
        '<div class="readout"><span><b>' + short(used) + '</b> used' +
          (allowed ? ' of ' + short(allowed) + ' tokens' : ' tokens · no ceiling') + '</span>' +
        '<span>' + (allowed ? (left > 0 ? short(left) + ' left' : 'spent — calls are being rejected') : '') +
          (days !== null ? ' · resets in ' + days + 'd' : '') + '</span></div>';

      var acts = document.createElement('div');
      acts.className = 'acts';
      var edit = document.createElement('button');
      edit.className = 'ghost tiny'; edit.textContent = 'Change allowance';
      edit.onclick = function(){ changeQuota(k, allowed); };
      var kill = document.createElement('button');
      kill.className = 'ghost tiny'; kill.textContent = 'Revoke';
      kill.onclick = function(){ revoke(k); };
      acts.appendChild(edit); acts.appendChild(kill);
      el.appendChild(acts);
      box.appendChild(el);
    });
  });
}

function changeQuota(k, allowed){
  var ans = prompt('New token allowance for ' + (k.user_id || 'this key') + ':',
                   allowed ? String(Math.round(allowed)) : '10000000');
  if (ans === null) return;
  var tokens = parseFloat(ans);
  if (!(tokens > 0)) { toast('That is not a token count.', true); return; }
  lite('POST', '/key/update',
       {key: k.token, max_budget: tokens * parseFloat(cfg.cost_per_token)}).then(function(r){
    if (r.status >= 300) { toast(describe(r), true); return; }
    toast('Allowance updated.');
    refresh();
  });
}

function revoke(k){
  if (!confirm('Revoke this key? ' + (k.user_id || '') +
               ' loses access immediately and cannot get the same key back.')) return;
  lite('POST', '/key/delete', {keys: [k.token]}).then(function(r){
    if (r.status >= 300) { toast(describe(r), true); return; }
    toast('Key revoked.');
    refresh();
  });
}

function drawUsers(){
  api('/api/users').then(function(r){
    var box = document.getElementById('users');
    if (r.status >= 300){
      box.innerHTML = '<div class="empty">Could not load users.</div>';
      return;
    }
    var users = r.users || [];
    if (!users.length){
      box.innerHTML = '<div class="empty">No users registered yet.</div>';
      return;
    }
    var html = '<table><thead><tr><th>User ID</th><th class="num">Keys</th>' +
      '<th class="num">Spend</th><th class="num">Used Pct</th>' +
      '<th class="num">Tokens</th></tr></thead><tbody>';
    users.forEach(function(u){
      var uid = u.user_id || '—';
      var keys = u.keys ? u.keys.length : 0;
      var spend = u.spend || 0;
      var tokens = spend / parseFloat(cfg.cost_per_token);
      var pct = u.max_budget ? Math.min(100, (spend / u.max_budget) * 100) : 0;
      var tone = pct >= 100 ? 'over' : (pct >= 80 ? 'near' : '');
      html += '<tr><td>' + uid + '</td>' +
        '<td class="num">' + keys + '</td>' +
        '<td class="num">' + spend.toFixed(6) + '</td>' +
        '<td class="num"><b class="' + tone + '">' + pct.toFixed(1) + '%</b></td>' +
        '<td class="num">' + commas(tokens) + '</td></tr>';
    });
    box.innerHTML = html + '</tbody></table>';
  });
}

function refresh(){ drawPeople(); drawUsers(); }

loadConfig().then(function(){ drawStatus(); refresh(); });
setInterval(drawStatus, 30000);
setInterval(refresh, 20000);
</script>
</body>
</html>
"""
