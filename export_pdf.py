# -*- coding: utf-8 -*-
"""
يولّد ملف PDF بكل أسئلة البنك للمراجعة الورقية.

  python export_pdf.py

يستخدم نفس دالة mfix الموجودة في التطبيق، فما يظهر في الـPDF
هو تماماً ما يُعرض على الشاشة — أي أن مراجعة الـPDF تغطي
المحتوى واتجاه النص معاً.

الطباعة تتم عبر Chrome بلا واجهة، لأنه يشكّل العربية ويطبّق
قواعد الاتجاه كما يفعل متصفح الطالبة بالضبط.
"""
import io, json, os, re, subprocess, sys, tempfile, glob

SRC = r"C:\Users\mahbo\OneDrive\Cloud AI Dash\Qiyas\miqyas.html"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PDF = os.path.join(OUT_DIR, "miqyas-questions.pdf")

CHROME = None
for c in [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]:
    if os.path.exists(c):
        CHROME = c
        break

RENDER = r"""
const out=[];
const gname={}; SKILLS.forEach(s=>gname[s.id]=s);
const bySkill={}; Q.forEach((q,i)=>{ (bySkill[q.s]=bySkill[q.s]||[]).push([i,q]); });
let n=0;
SKILLS.forEach(s=>{
  const list=bySkill[s.id]||[]; if(!list.length) return;
  out.push({type:"head", grp:s.grp, name:s.name, count:list.length, weight:s.w, secs:s.t,
            sec: s.sec==="q"?"كمّي":"لفظي"});
  list.forEach(([idx,q])=>{
    n++;
    out.push({type:"q", n:n, id:"q#"+idx, skill:s.name, d:q.d,
      passage: q.p? mfix(q.p):null,
      cmp: cmpParts(q.q) ? {pre:mfix(cmpParts(q.q).pre), a:mfix(cmpParts(q.q).a), b:mfix(cmpParts(q.q).b)} : null,
      fig: q.f || null,
      stem: mfix(q.q),
      choices: q.c.map((c,j)=>({ t:mfix(c), ok:j===q.a, why:q.m[j]? (WHY[q.m[j]]||q.m[j]) : null })),
      expl: mfix(q.e)});
  });
});
console.log(JSON.stringify(out));
"""

HTML_HEAD = """<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>مِقياس — بنك الأسئلة</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Readex+Pro:wght@400;500;600&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap">
<style>
@page{size:A4;margin:14mm 13mm 16mm}
*{box-sizing:border-box}
body{margin:0;font-family:"IBM Plex Sans Arabic",Tahoma,sans-serif;font-size:10.5pt;line-height:1.75;color:#12201D}
.m{direction:ltr;unicode-bidi:isolate-override;font-variant-numeric:tabular-nums;background:#EFF3F1;border-radius:2.5pt;padding:0 2.5pt}
.s{direction:ltr;unicode-bidi:isolate}
h1{font-family:"Readex Pro";font-size:24pt;margin:0 0 4pt;letter-spacing:-.02em}
.sub{color:#5E6E6A;font-size:10pt;margin-bottom:18pt}
.cover{border-bottom:2px solid #0E6E63;padding-bottom:14pt;margin-bottom:16pt}
.legend{background:#EFF3F1;border-radius:6pt;padding:9pt 11pt;font-size:9pt;color:#3C4B47;line-height:1.9}
.legend b{color:#0E6E63}
h2{font-family:"Readex Pro";font-size:13pt;margin:20pt 0 3pt;padding:6pt 9pt;background:#E2EFEC;
   color:#0A4F47;border-radius:5pt;break-after:avoid;page-break-after:avoid}
h2 small{font-weight:400;font-size:8.5pt;color:#5E6E6A;float:left}
.q{break-inside:avoid;page-break-inside:avoid;margin:11pt 0;padding-bottom:9pt;border-bottom:1px solid #E4EAE7}
.qh{font-size:8.5pt;color:#5E6E6A;margin-bottom:3pt}
.qh b{color:#0E6E63;font-size:10pt}
.stem{font-weight:600;font-size:11pt;margin:0 0 5pt}
.passage{background:#F4F7F5;border-right:2pt solid #C6D6D0;padding:6pt 9pt;margin:0 0 6pt;font-size:9.5pt;line-height:1.95}
ol.ch{margin:0;padding:0 16pt 0 0;list-style:none;counter-reset:c}
ol.ch li{position:relative;padding:1.5pt 0 1.5pt 0;font-size:10pt}
ol.ch li::before{counter-increment:c;content:counter(c,arabic-indic);position:absolute;right:-15pt;
  color:#8fa39d;font-size:8.5pt;top:3pt}
ol.ch li.ok{font-weight:700;color:#1F6B50}
ol.ch li.ok::after{content:" ✔";color:#2E8B69}
.why{color:#9a8560;font-size:8pt}
.ex{margin-top:5pt;font-size:9.5pt;color:#3C4B47;background:#FAFBFA;border-radius:4pt;padding:5pt 8pt}
.ex b{color:#0E6E63}
.fig{margin:5pt 0 6pt;text-align:center;color:#12201D}
.fig svg{max-width:78%;height:auto}
table.cmp{border-collapse:collapse;width:100%;margin:4pt 0 6pt;border:0.5pt solid #C6D6D0;border-radius:3pt}
table.cmp td{border-bottom:0.5pt solid #DCE5E1;padding:4pt 8pt;font-size:10.5pt}
table.cmp tr:last-child td{border-bottom:0}
table.cmp td.lb{width:74pt;color:#5E6E6A;font-size:8.5pt;background:#F4F7F5}
table.cmp td.vl{font-weight:700}
</style></head><body>
"""


def esc_html(s):
    return s  # النص آتٍ من mfix وهو مُهرَّب أصلاً ويحمل وسوم span مقصودة


def main():
    if not CHROME:
        print("Chrome/Edge not found - cannot print PDF")
        return 1

    html = io.open(SRC, encoding="utf-8").read()
    js = html.split("<script>")[1].split("</script>")[0]

    def sl(a, b):
        i = js.index(a); return js[i:js.index(b, i)]

    prog = "\n".join([
        sl("const SKILLS = [", "const SK ="),
        sl("const WHY = {", "/* ══════════ 2."),
        sl("const Q = [", "Q.forEach((q,i)=>{q.id="),
        sl("const esc=", "const pct="),
    ]) + RENDER

    tmp_js = os.path.join(tempfile.gettempdir(), "miqyas_export.js")
    io.open(tmp_js, "w", encoding="utf-8").write(prog)
    r = subprocess.run(["node", tmp_js], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        print(r.stderr[:2000]); return 1
    items = json.loads(r.stdout)

    total = sum(1 for x in items if x["type"] == "q")
    parts = [HTML_HEAD]
    parts.append(
        '<div class="cover"><h1>مِقياس — بنك الأسئلة</h1>'
        '<div class="sub">%d سؤالاً على %d مهارة · للمراجعة قبل النشر</div>'
        '<div class="legend">'
        'الإجابة الصحيحة عليها <b>✔</b> وبخط عريض. '
        'تحت كل خيار خاطئ <b>سبب الخطأ</b> الذي يظهر للطالبة عند اختياره.<br>'
        '<b>مهم:</b> التعابير الرياضية معروضة هنا بنفس منطق التطبيق تماماً — '
        'فأي معادلة تراها مقلوبة في هذا الملف هي مقلوبة في التطبيق أيضاً.'
        '</div></div>' % (total, len([x for x in items if x["type"] == "head"]))
    )

    for x in items:
        if x["type"] == "head":
            parts.append('<h2><small>%s · الوزن %d/7 · الزمن المعياري %d ث · %d سؤالاً</small>%s — %s</h2>'
                         % (x["sec"], x["weight"], x["secs"], x["count"], x["name"], x["grp"]))
        else:
            b = ['<div class="q">']
            b.append('<div class="qh"><b>%d</b> · %s · صعوبة %d · <span style="color:#b9c4c0">%s</span></div>'
                     % (x["n"], x["skill"], x["d"], x["id"]))
            if x["passage"]:
                b.append('<div class="passage">%s</div>' % x["passage"])
            if x.get("cmp"):
                c = x["cmp"]
                if c["pre"]:
                    b.append('<p class="stem">%s</p>' % c["pre"])
                b.append('<table class="cmp"><tr><td class="lb">القيمة الأولى</td><td class="vl">%s</td></tr>'
                         '<tr><td class="lb">القيمة الثانية</td><td class="vl">%s</td></tr></table>'
                         % (c["a"], c["b"]))
            else:
                b.append('<p class="stem">%s</p>' % x["stem"])
            if x.get("fig"):
                b.append('<div class="fig">%s</div>' % x["fig"])
            b.append('<ol class="ch">')
            for c in x["choices"]:
                w = ' <span class="why">— %s</span>' % c["why"] if c["why"] else ""
                b.append('<li class="%s">%s%s</li>' % ("ok" if c["ok"] else "", c["t"], w))
            b.append('</ol>')
            b.append('<div class="ex"><b>الحل:</b> %s</div>' % x["expl"])
            b.append('</div>')
            parts.append("".join(b))

    parts.append("</body></html>")
    tmp_html = os.path.join(OUT_DIR, "_questions.html")
    io.open(tmp_html, "w", encoding="utf-8").write("".join(parts))

    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--virtual-time-budget=20000",
                    "--no-pdf-header-footer",
                    "--print-to-pdf-no-header",
                    "--print-to-pdf=" + OUT_PDF,
                    "file:///" + tmp_html.replace("\\", "/")],
                   capture_output=True, text=True, timeout=180)

    if os.path.exists(OUT_PDF):
        print("PDF: %s (%.1f KB, %d questions)" % (OUT_PDF, os.path.getsize(OUT_PDF) / 1024, total))
        return 0
    print("PDF was not produced")
    return 1


if __name__ == "__main__":
    sys.exit(main())
