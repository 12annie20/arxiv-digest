"""
arXiv 每日文獻日報 v4
首頁：溫度計 + 今日推薦3篇 + Insight
深度頁：TOP5 + LLM×心理學
貓咪：固定角落漂浮
"""

from google import genai
from google.genai import types
import datetime, json, os, pathlib, re, subprocess, webbrowser, time
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET

# ── 設定區 ────────────────────────────────────────────────────────────
API_KEY       = "AIzaSyBHjh1rYSP6Uf5j30bKYKW7cqfOzvsn_oA"
OUTPUT_FOLDER = r"C:\Users\anlic\ArxivDigest"
TEMPLATE_PATH = pathlib.Path(__file__).parent / "digest_template.html"
# ──────────────────────────────────────────────────────────────────────

def get_today():    return datetime.date.today().strftime("%Y-%m-%d")
def get_datetime(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# ══════════════════════════════════════════════════════════════════════
# STEP 1：arXiv API 抓真實論文
# ══════════════════════════════════════════════════════════════════════
ARXIV_QUERIES = [
    'cat:cs.AI+AND+(psychology+OR+mental+health)',
    'cat:cs.AI+AND+(emotion+OR+counseling+OR+therapy)',
    'cat:cs.HC+AND+(psychology+OR+wellbeing+OR+emotion)',
    'cat:cs.CL+AND+(mental+health+OR+emotion+OR+affective)',
    'cat:cs.CY+AND+(psychology+OR+wellbeing)',
    'all:LLM+AND+(therapy+OR+counseling+OR+mental+health)',
    'all:AI+AND+(psychology+OR+emotion+OR+wellbeing)',
]
NS = 'http://www.w3.org/2005/Atom'

def fetch_arxiv(query, max_results=12):
    base = 'http://export.arxiv.org/api/query?'
    params = urllib.parse.urlencode({
        'search_query': query, 'start': 0,
        'max_results': max_results,
        'sortBy': 'submittedDate', 'sortOrder': 'descending',
    })
    try:
        req = urllib.request.Request(base + params, headers={'User-Agent': 'ArxivDigest/4.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            root = ET.fromstring(resp.read())
    except Exception as e:
        print(f"  ⚠ 查詢失敗: {e}")
        return []
    papers = []
    for entry in root.findall(f'{{{NS}}}entry'):
        try:
            raw_id   = entry.find(f'{{{NS}}}id').text.strip()
            arxiv_id = raw_id.split('/abs/')[-1]
            title    = ' '.join(entry.find(f'{{{NS}}}title').text.split())
            abstract = ' '.join(entry.find(f'{{{NS}}}summary').text.split())[:800]
            published= entry.find(f'{{{NS}}}published').text[:10]
            authors  = [a.find(f'{{{NS}}}name').text for a in entry.findall(f'{{{NS}}}author')][:3]
            doi_el   = entry.find('{http://arxiv.org/schemas/atom}doi')
            papers.append({
                'arxiv_id': arxiv_id, 'title': title, 'authors': authors,
                'abstract': abstract, 'published': published,
                'arxiv_url': f'https://arxiv.org/abs/{arxiv_id}',
                'doi': doi_el.text.strip() if doi_el is not None else None,
            })
        except Exception:
            continue
    return papers

def gather_papers():
    print("🔍 從 arXiv API 抓取真實論文...")
    seen, all_papers = set(), []
    for q in ARXIV_QUERIES:
        for p in fetch_arxiv(q, max_results=12):
            if p['arxiv_id'] not in seen:
                seen.add(p['arxiv_id'])
                all_papers.append(p)
        time.sleep(1)
    print(f"  ✅ 共抓到 {len(all_papers)} 篇候選論文")
    return all_papers[:30]

# ══════════════════════════════════════════════════════════════════════
# STEP 2：Gemini 分析
# ══════════════════════════════════════════════════════════════════════
def call_gemini(papers, today):
    client = genai.Client(api_key=API_KEY)
    papers_text = ""
    for i, p in enumerate(papers, 1):
        papers_text += f"\n[{i}] ID:{p['arxiv_id']} | 日期:{p['published']}\n標題:{p['title']}\n作者:{', '.join(p['authors'])}\n摘要:{p['abstract']}\n連結:{p['arxiv_url']}\n---"

    prompt = f"""
以下是 {today} 從 arXiv 抓取的 {len(papers)} 篇真實論文（AI × 心理學領域）：
{papers_text}

只輸出一個 JSON 物件，不加任何說明或 markdown 格式：
{{
  "thermometer": {{
    "hot": "熱門主題(繁中,3個用・分隔)",
    "new": "新興焦點(繁中,1-2個用・分隔)",
    "cold": "冷門但值得關注(繁中,1個)"
  }},
  "picks": [
    {{
      "arxiv_id": "真實arXiv ID",
      "title": "論文英文標題（完整複製）",
      "theme": "主題分類(從cs.AI/cs.HC/cs.CL/cs.CY選一)",
      "why": "為什麼今日值得讀(繁中,2句)",
      "authors": "主要作者"
    }}
  ],
  "papers": [
    {{
      "rank": "01",
      "arxiv_id": "真實arXiv ID",
      "title": "論文英文標題（完整複製）",
      "tags": ["cs.AI"],
      "date": "提交日期",
      "abstract": "中文摘要(繁中,3-5句完整改寫)",
      "question": "核心研究問題(繁中,30字內)",
      "review": ["深度點評1","深度點評2","深度點評3"],
      "contributions": ["研究貢獻1","研究貢獻2"],
      "limitations": ["研究限制1","研究限制2"]
    }}
  ],
  "llm_papers": [
    {{
      "rank": "01",
      "arxiv_id": "真實arXiv ID",
      "title": "論文英文標題（完整複製）",
      "tags": ["cs.AI","cs.CL"],
      "question": "LLM應用問題(繁中,1句)",
      "method": "方法亮點(繁中)",
      "implication": "心理學意涵(繁中,2-3句)",
      "verdict": "一句話犀利評語(繁中)"
    }}
  ],
  "summary": "今日日報總結(繁中,3-4句)",
  "tomorrow": "明日值得關注(繁中,1-2句)"
}}

規則：
1. picks 選 3 篇，主題各異（分別對應不同的 arXiv 分類）
2. papers 選 5 篇，llm_papers 選 3 篇
3. 所有 arxiv_id 必須來自上方論文清單，不可編造
4. 論文標題完整複製原文
5. 全部繁體中文
"""

    print("🤖 Gemini 分析論文中（約需 30–60 秒）...")
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=65536)
            )
            break  # 成功就跳出迴圈
        except Exception as e:
            err = str(e)
            if '503' in err or 'UNAVAILABLE' in err or 'high demand' in err:
                if attempt < max_retries:
                    wait = 30 * attempt  # 第1次等30秒，第2次60秒，依此類推
                    print(f"  ⚠ Gemini 忙碌中，{wait} 秒後自動重試（第 {attempt}/{max_retries} 次）...")
                    time.sleep(wait)
                else:
                    print("  ❌ 重試 5 次仍失敗，請稍後手動執行")
                    raise
            else:
                raise  # 其他錯誤直接拋出
    raw = re.sub(r"^```json\s*", "", response.text.strip())
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("  ⚠ JSON 不完整，嘗試自動修復...")
        for end in range(len(raw)-1, 0, -1):
            try:
                data = json.loads(raw[:end+1])
                break
            except json.JSONDecodeError:
                continue
        else:
            raise ValueError("JSON 無法修復，請重試")

    # 補回真實 URL
    id_map = {p['arxiv_id']: p for p in papers}
    for section in ['picks', 'papers', 'llm_papers']:
        for item in data.get(section, []):
            real = id_map.get(item.get('arxiv_id', ''))
            item['arxiv_url'] = real['arxiv_url'] if real else f"https://arxiv.org/abs/{item.get('arxiv_id','')}"
            item['doi'] = real.get('doi') if real else None
    return data

# ══════════════════════════════════════════════════════════════════════
# STEP 3：HTML 渲染
# ══════════════════════════════════════════════════════════════════════
THEME_CLASS = {'cs.AI':'t-ai','cs.HC':'t-hc','cs.CL':'t-cl','cs.CY':'t-cy'}

def tag_html(t):
    m = {"cs.AI":("cs.AI","tag-ai"),"cs.HC":("cs.HC","tag-hc"),
         "cs.CL":("cs.CL","tag-cl"),"cs.CY":("cs.CY","tag-cy")}
    label, cls = m.get(t,(t,"tag-date"))
    return f'<span class="tag {cls}">{label}</span>'

def link_html(item, label="→ 閱讀原文"):
    doi = item.get('doi')
    url = f'https://doi.org/{doi}' if doi else item.get('arxiv_url','#')
    badge = '<span style="font-size:.55rem;color:var(--m-sage);margin-left:.3rem">DOI</span>' if doi else '<span style="font-size:.55rem;color:var(--m-slate-light);margin-left:.3rem">arXiv</span>'
    return f'<a class="doi-link" href="{url}" target="_blank">{label}{badge}</a>'

def render_therm(th):
    return (f'<div><div class="th-label hot">熱門主題</div><div class="th-body">{th["hot"]}</div></div>'
            f'<div><div class="th-label new">新興焦點</div><div class="th-body">{th["new"]}</div></div>'
            f'<div><div class="th-label cold">冷門值得關注</div><div class="th-body">{th["cold"]}</div></div>')

def render_picks(picks):
    html = ""
    for p in picks:
        theme = p.get('theme','cs.AI')
        tcls = THEME_CLASS.get(theme, 't-ai')
        url = p.get('arxiv_url','#')
        html += f'''<div class="rec-card">
<span class="rec-theme {tcls}">{theme}</span>
<div class="rec-title">{p["title"]}</div>
<div class="rec-why">{p["why"]}</div>
<div class="rec-meta">{p.get("authors","")}</div>
<a class="rec-link" href="{url}" target="_blank">→ 閱讀原文 <span style="font-size:.55rem;color:var(--m-slate-light)">arXiv</span></a>
</div>'''
    return html

def render_papers(papers):
    html = ""
    for p in papers:
        tags = "".join(tag_html(t) for t in p.get("tags",[]))
        tags += f' <span class="tag tag-date">{p.get("date","")}</span>'
        ri = "\n".join(f"<li>{i}</li>" for i in p.get("review",[]))
        ci = "\n".join(f"<li>{i}</li>" for i in p.get("contributions",[]))
        li = "\n".join(f"<li>{i}</li>" for i in p.get("limitations",[]))
        html += f'''<div class="paper-card">
<div class="pc-head"><div class="pc-rank">No. {p["rank"]}</div>
<div class="pc-title">{p["title"]}</div><div class="paper-meta">{tags}</div></div>
<div class="pc-body">
<div class="pc-abs">{p["abstract"]}</div>
<div class="pc-q">{p["question"]}</div>
<div style="margin-bottom:.8rem"><div class="ins-label rv">深度點評</div><ul class="ins-list">{ri}</ul></div>
<div style="margin-bottom:.8rem"><div class="ins-label ct">研究貢獻</div><ul class="ins-list">{ci}</ul></div>
<div style="margin-bottom:.5rem"><div class="ins-label lm">研究限制</div><ul class="ins-list">{li}</ul></div>
{link_html(p)}
</div></div>'''
    return html

def render_llm(papers):
    html = ""
    for p in papers:
        tags = "".join(tag_html(t) for t in p.get("tags",[]))
        html += f'''<div class="llm-card"><div class="llm-stripe"></div><div>
<div class="llm-rank">LLM × 心理學 No.{p["rank"]}</div>
<div class="llm-title">{p["title"]}</div>
<div class="paper-meta" style="margin-bottom:.8rem">{tags}</div>
<div class="llm-row">
  <div><div class="fl-label">核心問題</div><div class="fl-body">{p["question"]}</div></div>
  <div><div class="fl-label">方法亮點</div><div class="fl-body">{p["method"]}</div></div>
</div>
<div style="margin-bottom:.5rem"><div class="fl-label">心理學意涵</div><div class="fl-body">{p["implication"]}</div></div>
<div class="llm-verdict">{p["verdict"]}</div>
{link_html(p)}
</div></div>'''
    return html

def build_html(data, today):
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (template
        .replace("{{DATE}}", today)
        .replace("{{DATETIME}}", get_datetime())
        .replace("{{THERMOMETER}}", render_therm(data["thermometer"]))
        .replace("{{PICKS}}", render_picks(data.get("picks",[])))
        .replace("{{PAPERS}}", render_papers(data["papers"]))
        .replace("{{LLM_PAPERS}}", render_llm(data["llm_papers"]))
        .replace("{{SUMMARY}}", data.get("summary",""))
        .replace("{{TOMORROW}}", data.get("tomorrow",""))
    )

def save_html(html, today):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    path = os.path.join(OUTPUT_FOLDER, f"digest_{today}.html")
    with open(path,"w",encoding="utf-8") as f: f.write(html)
    return path

def notify(title, msg):
    ps = f'''Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip(8000, "{title}", "{msg}", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 9
$n.Dispose()'''
    subprocess.run(["powershell","-Command",ps], capture_output=True)

def main():
    today = get_today()
    print(f"\n☀️  arXiv 文獻日報 v4 — {today}")
    print("─" * 44)
    papers = gather_papers()
    if not papers:
        print("❌ 無法取得論文，請確認網路連線")
        return
    data = call_gemini(papers, today)
    print("✅ 分析完成")
    print("🎨 渲染頁面...")
    html = build_html(data, today)
    path = save_html(html, today)
    print(f"✅ 已儲存：{path}")
    notify("☀️ 今日 arXiv 日報已就緒", f"{today} · {len(data.get('papers',[]))} 篇精選")
    webbrowser.open("file:///" + path.replace("\\","/"))
    print("🌐 已開啟瀏覽器\n🎉 享用你的文獻早餐 ☕\n")

if __name__ == "__main__":
    main()
