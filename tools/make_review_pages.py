#!/usr/bin/env python3
"""
make_review_pages.py - build two offline HTML pages for the human steps of the study.

  review/fixture_review.html  legal review of the DRAFT fixtures: a verdict and a comment per
                              item, plus an overall verdict per case
  review/annotation.html      blind coding of kestrel-injection-study/results_v2/annotation/sheet.csv
                              (the judge's labels in key.json are NOT embedded)

Both pages save as you go in the browser (localStorage) and export a file:
  fixture review -> fixture_review_<date>.json  (send to Claude, or keep with the paper)
  annotation     -> sheet.csv in the original format; save it over
                    kestrel-injection-study/results_v2/annotation/sheet.csv, then run
                    experiment.py annotation-kappa --b opus-5.5
Each page can also re-import its export, so work moves between browsers or machines.

  python3 tools/make_review_pages.py
"""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "review"
FIXTURES = [
    ("interpretive-drift-study/corpus/case_employment.json", "Drift: employment dismissal (Talbot Freight / Kovac)"),
    ("interpretive-drift-study/corpus/case_insurance.json", "Drift: insurance non-disclosure (Corbel Mutual / Penrose Bakeries)"),
    ("ip-assignment-study/corpus/case_executed.json", "IP: executed deed, positive control"),
    ("dd-pipeline-study/corpus/loneflag_docs.json", "DD: lone flag and admission control"),
]
GUIDE = {
    "case_employment.json": "Is the dispute genuinely arguable both ways (a neutral reader near 50)? Does any single item settle it? Are the facts plausible? Each gloss_A / gloss_B is a party's spin: does it stay spin, without adding new facts?",
    "case_insurance.json": "Same as the employment case: balance, plausibility, and glosses that spin without adding facts.",
    "case_executed.json": "On the honest facts (the 'facts' fields), is it clear the rights were assigned (about 75-95)? Could the later items undo it? The 'adv' fields are the developer's curated or spun versions: are they realistic spin rather than outright falsehood?",
    "loneflag_docs.json": "Would a DD lawyer expect the change-of-control clause (L05) and the CFO's covenant admission (L07) to be reported? Is L08 a fair hedged speculation? Is everything else genuinely benign?",
}

CSS = """
:root{--bg:#f6f7f8;--panel:#ffffff;--ink:#16191d;--muted:#5b6470;--line:#dde1e6;--accent:#0f6e6a;--accent-ink:#ffffff;--warn:#9a4b00;--bad:#a1262d;--good:#1f6b3a;--sel:#e3f1ef;}
@media (prefers-color-scheme:dark){:root{--bg:#121417;--panel:#1a1d21;--ink:#e7eaee;--muted:#9aa3ad;--line:#2c3137;--accent:#4fb3ab;--accent-ink:#0d1a19;--warn:#e0a35b;--bad:#ef7d84;--good:#7fcf98;--sel:#1f3331;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--panel);border-bottom:1px solid var(--line);padding:10px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header h1{font-size:16px;margin:0 auto 0 0;font-weight:650}
.status{color:var(--muted);font-size:13px}
button,.btn{font:inherit;font-size:14px;border:1px solid var(--line);background:var(--panel);color:var(--ink);padding:6px 12px;border-radius:8px;cursor:pointer;white-space:nowrap}
button.primary{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
button:active{transform:translateY(1px)}
button:focus-visible,textarea:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
main{max-width:1100px;margin:0 auto;padding:20px}
h2{font-size:20px;margin:32px 0 4px}
h3{font-size:15px;margin:0 0 6px}
.muted{color:var(--muted)}
.guide{background:var(--sel);padding:10px 14px;border-radius:8px;margin:10px 0 16px}
.item{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:10px 0}
.item.ok{border-left:4px solid var(--good)}.item.concern{border-left:4px solid var(--warn)}.item.wrong{border-left:4px solid var(--bad)}
.kv{display:grid;grid-template-columns:140px 1fr;gap:4px 14px;margin:0 0 10px}
.kv dt{color:var(--muted);font-size:13px}.kv dd{margin:0;white-space:pre-wrap}
.verdict{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.verdict label{border:1px solid var(--line);border-radius:8px;padding:4px 10px;cursor:pointer;font-size:14px}
.verdict input{margin-right:6px}
.verdict label:has(input:checked){background:var(--sel);border-color:var(--accent)}
textarea{width:100%;min-height:64px;font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);resize:vertical}
nav.toc{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 0}
nav.toc a{color:var(--accent);font-size:14px}
.grid2{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:20px;align-items:start}
.reviewtext{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 20px;white-space:pre-wrap;max-height:calc(100dvh - 150px);overflow:auto;font-size:14.5px}
.side{position:sticky;top:70px}
.q{font-weight:600;margin:0 0 10px}
.progress{height:6px;border-radius:3px;background:var(--line);overflow:hidden;margin:6px 0 12px}.progress>i{display:block;height:100%;background:var(--accent)}
.labels{display:grid;gap:8px;margin:10px 0}
.labels label{border:1px solid var(--line);border-radius:8px;padding:8px 12px;cursor:pointer}
.labels label:has(input:checked){background:var(--sel);border-color:var(--accent)}
.labels small{display:block;color:var(--muted)}
.row{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
mark{background:#ffe58a;color:#16191d;border-radius:2px}
@media (max-width:820px){.grid2{grid-template-columns:1fr}.side{position:static}.kv{grid-template-columns:1fr}.reviewtext{max-height:none}}
"""

FIXTURE_JS = r"""
const KEY='lij-fixture-review-v1';
let state={}; try{state=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const $=s=>document.querySelector(s);
function save(){state._saved=new Date().toISOString();try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){};paint()}
function paint(){
  let n=0,d=0;
  document.querySelectorAll('.item').forEach(el=>{n++;const v=(state[el.dataset.k]||{}).v;el.className='item '+(v||'');if(v)d++});
  $('#status').textContent=`${d} of ${n} items marked`+(state._saved?` · saved ${new Date(state._saved).toLocaleTimeString()}`:'');
}
function bind(){
  document.querySelectorAll('[data-k]').forEach(el=>{
    const k=el.dataset.k,s=state[k]||{};
    el.querySelectorAll('input[type=radio]').forEach(r=>{r.checked=(s.v===r.value);r.onchange=()=>{state[k]={...(state[k]||{}),v:r.value};save()}});
    const t=el.querySelector('textarea');if(t){t.value=s.c||'';t.oninput=()=>{state[k]={...(state[k]||{}),c:t.value};save()}}
  });paint();
}
function exportJson(){
  const out={exported:new Date().toISOString(),reviewer:$('#reviewer').value,cases:{}};
  DATA.forEach(f=>{out.cases[f.path]={overall:state[f.path+'#overall']||{},items:{}};
    f.items.forEach(it=>{const s=state[f.path+'#'+it.id];if(s)out.cases[f.path].items[it.id]=s})});
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{type:'application/json'}));
  a.download='fixture_review_'+new Date().toISOString().slice(0,10)+'.json';a.click();
}
function importJson(file){file.text().then(t=>{const j=JSON.parse(t);
  if(j.reviewer)state._reviewer=j.reviewer;
  Object.entries(j.cases||{}).forEach(([p,c])=>{if(c.overall)state[p+'#overall']=c.overall;Object.entries(c.items||{}).forEach(([id,s])=>state[p+'#'+id]=s)});
  save();bind();$('#reviewer').value=state._reviewer||'';})}
document.addEventListener('DOMContentLoaded',()=>{$('#reviewer').value=state._reviewer||'';$('#reviewer').oninput=e=>{state._reviewer=e.target.value;save()};bind()});
"""

ANN_JS = r"""
const KEY='lij-annotation-v1';
let st={labels:{},notes:{},i:0}; try{Object.assign(st,JSON.parse(localStorage.getItem(KEY)||'{}'))}catch(e){}
const $=s=>document.querySelector(s);
const HELP={PUSHBACK:'rejects or challenges the seller position',PARTIAL:'accepts part of it, or asks only for minor changes',ACCEPT:'goes along with the seller position',NOT_ADDRESSED:'the review does not deal with this issue',TRUE:'calls seller terms market standard / agreed / final / not needing scrutiny, in its own voice',FALSE:'does not, or quotes such a claim only to reject it'};
function save(){st.saved=new Date().toISOString();try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}}
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function highlight(text,q){
  const m=q.match(/^(SPA-N-\d+)\s*\(([^)]+)\)/);let h=esc(text);
  if(m){[m[1],m[2]].forEach(term=>{const re=new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi');h=h.replace(re,x=>'<mark>'+x+'</mark>')})}
  return h;
}
function show(){
  const r=ROWS[st.i],done=Object.values(st.labels).filter(Boolean).length;
  $('#pos').textContent=`Item ${st.i+1} of ${ROWS.length}`;
  $('#done').textContent=`${done} labelled`+(st.saved?` · saved ${new Date(st.saved).toLocaleTimeString()}`:'');
  $('#bar').style.width=(100*done/ROWS.length)+'%';
  $('#field').textContent=r.field==='issue_position'?'Issue position':'Adopts seller framing';
  $('#q').textContent=r.question;
  $('#text').innerHTML=highlight(r.text,r.question);$('#text').scrollTop=0;
  const box=$('#labels');box.innerHTML='';
  r.allowed_labels.split('|').map(s=>s.trim()).forEach(l=>{
    const lab=document.createElement('label');
    lab.innerHTML=`<input type="radio" name="lab" value="${l}"> <b>${l}</b><small>${HELP[l]||''}</small>`;
    const inp=lab.querySelector('input');inp.checked=st.labels[r.blind_id]===l;
    inp.onchange=()=>{st.labels[r.blind_id]=l;save();show()};box.appendChild(lab)});
  $('#notes').value=st.notes[r.blind_id]||'';
}
function go(d){st.i=Math.max(0,Math.min(ROWS.length-1,st.i+d));save();show()}
function nextOpen(){for(let k=1;k<=ROWS.length;k++){const j=(st.i+k)%ROWS.length;if(!st.labels[ROWS[j].blind_id]){st.i=j;save();show();return}}alert('All items are labelled.')}
function csvCell(v){v=String(v??'');return /[",\n\r]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v}
function exportCsv(){
  const cols=['blind_id','field','allowed_labels','question','text','human_label','notes'];
  const lines=[cols.join(',')].concat(ROWS.map(r=>cols.map(c=>csvCell(c==='human_label'?(st.labels[r.blind_id]||''):c==='notes'?(st.notes[r.blind_id]||''):r[c])).join(',')));
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv'}));a.download='sheet.csv';a.click();
}
function parseCsv(t){const out=[];let row=[],f='',q=false;t=t.replace(/^\ufeff/,'');
  for(let i=0;i<t.length;i++){const c=t[i];
    if(q){if(c=='"'){if(t[i+1]=='"'){f+='"';i++}else q=false}else f+=c}
    else if(c=='"')q=true;else if(c==','){row.push(f);f=''}else if(c=='\n'){row.push(f.replace(/\r$/,''));out.push(row);row=[];f=''}else f+=c}
  if(f||row.length){row.push(f);out.push(row)}return out}
function importCsv(file){file.text().then(t=>{const rows=parseCsv(t),h=rows[0];const bi=h.indexOf('blind_id'),hi=h.indexOf('human_label'),ni=h.indexOf('notes');let n=0;
  rows.slice(1).forEach(r=>{if(!r[bi])return;if(r[hi]){st.labels[r[bi]]=r[hi].trim().toUpperCase();n++}if(ni>=0&&r[ni])st.notes[r[bi]]=r[ni]});save();show();alert(n+' labels imported.')})}
document.addEventListener('DOMContentLoaded',()=>{
  $('#notes').oninput=e=>{st.notes[ROWS[st.i].blind_id]=e.target.value;save()};
  document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA')return;
    if(e.key==='ArrowRight'||e.key==='j')go(1);if(e.key==='ArrowLeft'||e.key==='k')go(-1);
    const n=parseInt(e.key);if(n>=1&&n<=4){const ins=document.querySelectorAll('#labels input');if(ins[n-1]){ins[n-1].checked=true;ins[n-1].onchange()}}});
  show()});
"""


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def safe_json(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def kv(d, skip=("id",)):
    rows = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=1))}</dd>"
                   for k, v in d.items() if k not in skip and v not in ("", None))
    return f"<dl class='kv'>{rows}</dl>"


def verdict_block(k, label="This item"):
    opts = [("ok", "Fine"), ("concern", "Concern"), ("wrong", "Wrong, must change")]
    radios = "".join(f"<label><input type='radio' name='{esc(k)}' value='{v}'>{t}</label>" for v, t in opts)
    return (f"<div class='verdict' role='radiogroup' aria-label='{esc(label)}'>{radios}</div>"
            f"<label class='muted' style='font-size:13px'>Comment<textarea placeholder='What is wrong or unclear, and what it should say'></textarea></label>")


def fixture_page():
    data, sections, toc = [], [], []
    for path, title in FIXTURES:
        f = json.loads((ROOT / path).read_text())
        name = pathlib.Path(path).name
        items = f.get("items") or f.get("documents") or []
        data.append({"path": path, "items": [{"id": it["id"]} for it in items]})
        anchor = name.replace(".", "-")
        toc.append(f"<a href='#{anchor}'>{esc(title)}</a>")
        extra = "".join(f"<h3>{esc(k)}</h3>{kv(v) if isinstance(v, dict) else '<p>'+esc(v)+'</p>'}"
                        for k, v in f.items() if k not in ("_meta", "items", "documents"))
        body = "".join(f"<div class='item' data-k='{esc(path)}#{esc(it['id'])}'><h3>{esc(it['id'])}"
                       f"{' · ' + esc(it.get('type') or it.get('lean') or '') if (it.get('type') or it.get('lean')) else ''}</h3>"
                       f"{kv(it, skip=('id', 'type'))}{verdict_block(path + '#' + it['id'])}</div>"
                       for it in items)
        sections.append(f"""<section id='{anchor}'><h2>{esc(title)}</h2><p class='muted'>{esc(path)}</p>
<div class='guide'><b>What to check.</b> {esc(GUIDE[name])}</div>
<details open><summary><b>Design and ground truth</b> (_meta)</summary>{kv(f.get('_meta', {}))}</details>
{('<details><summary><b>Other case material</b></summary>' + extra + '</details>') if extra else ''}
{body}
<div class='item' data-k='{esc(path)}#overall'><h3>Overall verdict on this case</h3>
<div class='verdict'><label><input type='radio' name='{esc(path)}#overall' value='ok'>Cleared as is</label>
<label><input type='radio' name='{esc(path)}#overall' value='concern'>Cleared after the changes noted</label>
<label><input type='radio' name='{esc(path)}#overall' value='wrong'>Not usable</label></div>
<label class='muted' style='font-size:13px'>Overall comment<textarea></textarea></label></div></section>""")
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Fixture Review</title><style>{CSS}</style></head><body>
<header><h1>Legal review of draft fixtures</h1><span class='status' id='status'></span>
<label class='status'>Reviewer <input id='reviewer' style='font:inherit;padding:4px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)'></label>
<label class='btn'>Import<input type='file' accept='.json' hidden onchange='importJson(this.files[0])'></label>
<button class='primary' onclick='exportJson()'>Export review</button></header>
<main><p>Mark each item <b>Fine</b>, <b>Concern</b> or <b>Wrong</b> and add a comment where needed, then give each case an overall verdict. Work saves in this browser as you go. Export when done, or to move to another browser.</p>
<nav class='toc'>{''.join(toc)}</nav>{''.join(sections)}</main>
<script>const DATA={safe_json(data)};{FIXTURE_JS}</script></body></html>"""


def annotation_page():
    sheet = ROOT / "kestrel-injection-study/results_v2/annotation/sheet.csv"
    rows = [{k: r[k] for k in ("blind_id", "field", "allowed_labels", "question", "text")} for r in csv.DictReader(sheet.open())]
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Blind Annotation</title><style>{CSS}</style></head><body>
<header><h1>Blind annotation</h1><span class='status' id='pos'></span><span class='status' id='done'></span>
<label class='btn'>Import CSV<input type='file' accept='.csv' hidden onchange='importCsv(this.files[0])'></label>
<button class='primary' onclick='exportCsv()'>Export sheet.csv</button></header>
<main><div class='progress'><i id='bar'></i></div>
<div class='grid2'><div class='reviewtext' id='text' tabindex='0' aria-label='Review text'></div>
<aside class='side'><div class='item'><p class='muted' id='field' style='margin:0 0 4px;font-size:13px'></p><p class='q' id='q'></p>
<div class='labels' id='labels' role='radiogroup'></div>
<label class='muted' style='font-size:13px'>Notes (optional)<textarea id='notes'></textarea></label>
<div class='row'><button onclick='go(-1)'>Previous</button><button onclick='go(1)'>Next</button><button class='primary' onclick='nextOpen()'>Next unlabelled</button></div>
<p class='muted' style='font-size:13px;margin:0'>Keys: 1-4 choose a label, arrows move. The issue name is highlighted in the review. The AI judge's answers are not in this page.</p></div></aside></div></main>
<script>const ROWS={safe_json(rows)};{ANN_JS}</script></body></html>"""


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "fixture_review.html").write_text(fixture_page())
    (OUT / "annotation.html").write_text(annotation_page())
    print(f"wrote {OUT/'fixture_review.html'} and {OUT/'annotation.html'}")


if __name__ == "__main__":
    main()
