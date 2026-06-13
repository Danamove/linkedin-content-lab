"""Render index.html from data/*.json. Pure presentation, no network.

Called at the end of refresh.py, or standalone: python build.py
"""
import glob
import html
import json
import os
from datetime import datetime, timezone


def collect(root):
    posts = []
    for path in sorted(glob.glob(os.path.join(root, "data", "*_posts.json"))):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for p in data.get("posts", []):
            posts.append(p)
    return posts


def render(root):
    posts = collect(root)
    authors = sorted({p.get("name", p.get("handle", "")) for p in posts})
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = json.dumps(posts, ensure_ascii=False)
    out = TEMPLATE.replace("__DATA__", payload)
    out = out.replace("__AUTHORS__", json.dumps(authors, ensure_ascii=False))
    out = out.replace("__GENERATED__", html.escape(generated))
    out = out.replace("__COUNT__", str(len(posts)))
    with open(os.path.join(root, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"  built index.html — {len(posts)} posts, {len(authors)} authors")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LinkedIn Content Lab</title>
<style>
  :root{
    --bg:#0d1117; --panel:#161b22; --line:#21262d; --ink:#e6edf3;
    --mut:#8b949e; --acc:#4493f8; --warm:#d29922; --hot:#db6d28; --fire:#f85149;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
    font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  header{padding:28px 32px 18px;border-bottom:1px solid var(--line)}
  h1{margin:0;font-size:20px;letter-spacing:-.01em}
  h1 span{color:var(--mut);font-weight:400}
  .sub{color:var(--mut);font-size:13px;margin-top:4px}
  .controls{display:flex;flex-wrap:wrap;gap:10px;padding:16px 32px;
    position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);z-index:5}
  select,input{background:var(--panel);color:var(--ink);border:1px solid var(--line);
    border-radius:8px;padding:8px 10px;font-size:13px}
  input{flex:1;min-width:180px}
  main{padding:22px 32px;display:grid;gap:14px;
    grid-template-columns:repeat(auto-fill,minmax(360px,1fr))}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:16px 18px;display:flex;flex-direction:column;gap:10px}
  .top{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--mut)}
  .pill{font-weight:600;font-size:11px;padding:2px 8px;border-radius:999px;
    text-transform:uppercase;letter-spacing:.04em}
  .b-breakout{background:rgba(248,81,73,.15);color:var(--fire)}
  .b-replicable{background:rgba(219,109,40,.15);color:var(--hot)}
  .b-working{background:rgba(210,153,34,.15);color:var(--warm)}
  .b-baseline{background:rgba(139,148,158,.12);color:var(--mut)}
  .b-na{background:rgba(139,148,158,.12);color:var(--mut)}
  .kind{font-size:11px;color:var(--mut);border:1px solid var(--line);
    border-radius:6px;padding:1px 6px;text-transform:lowercase}
  .ratio{margin-left:auto;font-variant-numeric:tabular-nums;font-weight:700;color:var(--ink)}
  .hook{font-size:16px;line-height:1.35;font-weight:600;letter-spacing:-.01em}
  .who{font-size:13px}
  .who b{color:var(--ink)} .who span{color:var(--mut)}
  .meta{display:flex;gap:16px;font-size:13px;color:var(--mut);
    font-variant-numeric:tabular-nums;align-items:center}
  .meta b{color:var(--ink)}
  .body{font-size:13px;color:#c9d1d9;white-space:pre-wrap;display:none;
    border-top:1px solid var(--line);padding-top:10px}
  .card.open .body{display:block}
  a.link{color:var(--acc);text-decoration:none;font-size:12px;margin-left:auto}
  .more{color:var(--mut);font-size:12px;cursor:pointer;user-select:none}
  .empty{color:var(--mut);padding:40px;text-align:center;grid-column:1/-1}
</style>
</head>
<body>
<header>
  <h1>LinkedIn Content Lab <span>— what overperforms, per author</span></h1>
  <div class="sub">__COUNT__ posts · generated __GENERATED__ · ratio = post engagement ÷ that author's median</div>
</header>
<div class="controls">
  <select id="sort">
    <option value="ratio">Sort: outlier ratio</option>
    <option value="engagement">Sort: total engagement</option>
    <option value="date">Sort: newest</option>
  </select>
  <select id="author"><option value="">All authors</option></select>
  <select id="band">
    <option value="">All bands</option>
    <option value="breakout">Breakout (≥15×)</option>
    <option value="replicable">Replicable (≥5×)</option>
    <option value="working">Working (≥2×)</option>
  </select>
  <select id="window">
    <option value="0">Any time</option>
    <option value="7">Last 7 days</option>
    <option value="14">Last 14 days</option>
    <option value="30">Last 30 days</option>
    <option value="90">Last 90 days</option>
  </select>
  <input id="q" placeholder="Search hook / text…">
</div>
<main id="grid"></main>
<script>
const POSTS = __DATA__;
const AUTHORS = __AUTHORS__;
const grid = document.getElementById('grid');
const $ = id => document.getElementById(id);

AUTHORS.forEach(a => { const o=document.createElement('option'); o.value=a; o.textContent=a; $('author').appendChild(o); });

function fmt(n){ return (n||0).toLocaleString('en-US'); }
function dateStr(iso){ return (iso||'').slice(0,10); }

function render(){
  const sort=$('sort').value, author=$('author').value, band=$('band').value, q=$('q').value.toLowerCase();
  const win=+$('window').value, cutoff = win ? Date.now()-win*86400000 : 0;
  let rows = POSTS.filter(p=>{
    if(author && (p.name||p.handle)!==author) return false;
    if(band && p.band!==band) return false;
    if(cutoff && (!p.date || new Date(p.date).getTime() < cutoff)) return false;
    if(q && !((p.hook||'')+' '+(p.text||'')).toLowerCase().includes(q)) return false;
    return true;
  });
  rows.sort((a,b)=>{
    if(sort==='date') return (b.date||'').localeCompare(a.date||'');
    if(sort==='engagement') return (b.engagement||0)-(a.engagement||0);
    return (b.ratio||0)-(a.ratio||0);
  });
  grid.innerHTML='';
  if(!rows.length){ grid.innerHTML='<div class="empty">No posts match.</div>'; return; }
  for(const p of rows){
    const band = p.band||'na';
    const ratio = p.ratio!=null ? p.ratio.toFixed(1)+'×' : '—';
    const card=document.createElement('div'); card.className='card';
    card.innerHTML = `
      <div class="top">
        <span class="pill b-${band}">${band}</span>
        <span class="kind">${p.kind||'post'}</span>
        <span>${dateStr(p.date)}</span>
        <span class="ratio">${ratio}</span>
      </div>
      <div class="hook">${esc(p.hook||'(no text)')}</div>
      <div class="who"><b>${esc(p.name||p.handle||'')}</b></div>
      <div class="meta">
        <span>👍 <b>${fmt(p.reactions)}</b></span>
        <span>💬 <b>${fmt(p.comments)}</b></span>
        <a class="link" href="${p.url}" target="_blank" rel="noopener">open ↗</a>
      </div>
      ${p.text && p.text!==p.hook ? '<div class="more">show full text ▾</div>' : ''}
      <div class="body">${esc(p.text||'')}</div>`;
    const more=card.querySelector('.more');
    if(more) more.onclick=()=>{ card.classList.toggle('open');
      more.textContent = card.classList.contains('open') ? 'hide full text ▴' : 'show full text ▾'; };
    grid.appendChild(card);
  }
}
function esc(s){ const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
['sort','author','band','window','q'].forEach(id=>$(id).addEventListener('input',render));
render();
</script>
</body>
</html>"""


if __name__ == "__main__":
    render(os.path.dirname(os.path.abspath(__file__)))
