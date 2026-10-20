from pathlib import Path
import re, json, html

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "content.json"

def inline(s):
    s = html.escape(s)
    def link(m):
        label, target = m.group(1), html.unescape(m.group(2))
        if target.startswith("/"):
            return '<button class="pathlink" data-copy="' + html.escape(target, quote=True) + '">' + label + ' <span>复制路径 ↗</span></button>'
        if target.startswith("https://"):
            return '<a target="_blank" rel="noopener noreferrer" href="' + html.escape(target, quote=True) + '">' + label + '</a>'
        return label
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return s

def render_md(text):
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("~~~"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("~~~"):
                block.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(block)) + "</code></pre>")
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [x.strip() for x in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[:\-\s]+",x or " ") for x in cells):
                    rows.append(cells)
                i += 1
            if rows:
                head = "<tr>" + "".join("<th>"+inline(c)+"</th>" for c in rows[0]) + "</tr>"
                body = "".join("<tr>"+"".join("<td>"+inline(c)+"</td>" for c in row)+"</tr>" for row in rows[1:])
                out.append('<div class="tablewrap"><table><thead>'+head+"</thead><tbody>"+body+"</tbody></table></div>")
            continue
        h = re.match(r"^(#{1,6})\s+(.+)", line)
        if h:
            n = min(5, max(2,len(h.group(1))))
            out.append("<h"+str(n)+">"+inline(h.group(2))+"</h"+str(n)+">")
            i += 1
            continue
        ordered = re.match(r"^\d+\.\s+", line)
        if line.startswith("- ") or ordered:
            tag = "ol" if ordered else "ul"
            items = []
            pattern = r"^\d+\.\s+" if ordered else r"^-\s+"
            while i < len(lines) and re.match(pattern,lines[i].strip()):
                items.append("<li>"+inline(re.sub(pattern,"",lines[i].strip()))+"</li>")
                i += 1
            out.append("<"+tag+">"+"".join(items)+"</"+tag+">")
            continue
        if line.startswith(">"):
            out.append("<blockquote>"+inline(line.lstrip("> "))+"</blockquote>")
            i += 1
            continue
        out.append("<p>"+inline(line)+"</p>")
        i += 1
    return "\n".join(out)

if not DATA.exists():
    raise SystemExit("缺少 study-center/content.json，请获取完整仓库后再构建。")

data=json.loads(DATA.read_text())
data["projectHtml"]=(ROOT/"project-map.html").read_text()
for day in data["days"]:
    def ref_button(match):
        key=match.group(0)
        ref=data.get("codeRefs",{}).get(key)
        if not ref: return key
        return '<button class="pathlink" data-copy="'+html.escape(ref["path"],quote=True)+'">'+key+' · '+html.escape(ref["label"])+' <span>复制路径 ↗</span></button>'
    day["html"]=re.sub(r'\b[GW]\d{1,2}\b',ref_button,day["html"])
assert len(data["days"])==42
assert len(data["cards"])==110
assert len({c["id"] for c in data["cards"]})==110
for c in data["cards"]:
    assert c["q"] and c["answer"] and c["plain"], c
for q in data["quizzes"]:
    assert q[4] in {c["id"] for c in data["cards"]},q
payload=json.dumps(data,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")
template=(ROOT/"app.html").read_text()
assert template.count("__STUDY_DATA__")==1
output=template.replace("__STUDY_DATA__",payload)
(ROOT.parent/"index.html").write_text(output)
print(json.dumps({"days":len(data["days"]),"cards":len(data["cards"]),"quizQuestions":len(data["quizzes"]),"bytes":len(output.encode()),"output":str(ROOT.parent/"index.html")},ensure_ascii=False))

