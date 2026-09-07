# -*- coding: utf-8 -*-
"""
فحص العرض البصري — يثبت أن كل تعبير رياضي يُطبع فعلياً من اليسار إلى اليمين
داخل النص العربي، بقياس إحداثيات الحروف على الصفحة لا بقراءة النص.

  python render_check.py

الحاجة إليه: الفحص البرمجي (validate.py) يتحقق من الوسوم فقط، وقد مرّ بنجاح
بينما كانت المعادلات تُعرض مقلوبة على الشاشة ثلاث مرات. هذا الفحص يطبع صفحة
حقيقية عبر Chrome ثم يقيس موضع كل حرف: إن لم تتصاعد إحداثيات الحروف
من اليسار إلى اليمين بترتيبها المنطقي، فالتعبير معكوس.

يُشغَّل يدوياً بعد أي تعديل يمسّ mfix أو تنسيق العرض.
"""
import io, json, os, re, subprocess, sys, tempfile

SRC = r"C:\Users\mahbo\OneDrive\Cloud AI Dash\Qiyas\miqyas.html"
OUT = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(OUT, "_render_check.pdf")
L, R = "\u2770", "\u2771"          # علامتان نادرتان تحدّان كل تعبير معزول

CHROME = next((c for c in [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
] if os.path.exists(c)), None)

CASES = [
    "أوجد ناتج: 5 + 7 × (11 − 8)² ÷ 3 − 4",
    "إذا كان 2س + 3 ≥ 11، فما أصغر قيمة ممكنة لـ س؟",
    "إذا كان أ > ب > 0، قارن بين: القيمة الأولى = أ − ب",
    "إذا كان −3س > 12، فما مجموعة الحل؟",
    "إذا كانت س : ص = 2 : 7، وكان مجموعهما 45، فما قيمة ص؟",
    "قارن بين: القيمة الأولى = 2/3 — القيمة الثانية = 0.7",
    "القيمة الثانية = عدد أضلاع المخمّس + 1",
    "المجموع = المتوسط × العدد = 14 × 4 = 56 سنة.",
    "س < −4",
    "إذا كان 5 ≤ س ≤ 9 و 2 ≤ ص ≤ 4، فما أكبر قيمة؟",
    "2س ≥ 8 ⇒ س ≥ 4. وبما أن التساوي مسموح، فأصغر قيمة هي 4.",
    "نسبة الأنشطة = 100 − (30+25+20) = 25%. العدد = 25% × 400 = 100 طالب.",
    "أعلى درجة 95 وأقل درجة 45. الفرق = 95 − 45 = 50.",
    "قارن بين: القيمة الأولى = 7 − 12 — القيمة الثانية = 12 − 7",
]

UNESC = [("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"), ("&quot;", '"')]


def unesc(s):
    for a, b in UNESC:
        s = s.replace(a, b)
    return s


def main():
    if not CHROME:
        print("Chrome not found"); return 1

    js = io.open(SRC, encoding="utf-8").read().split("<script>")[1].split("</script>")[0]
    i = js.index("const esc=")
    head = js[i:js.index("const pct=")]

    prog = head + "\nconst C=" + json.dumps(CASES, ensure_ascii=False) + ";\n" \
        "console.log(JSON.stringify(C.map(t=>mfix(t))));"
    tmp_js = os.path.join(tempfile.gettempdir(), "miqyas_render.js")
    io.open(tmp_js, "w", encoding="utf-8").write(prog)
    r = subprocess.run(["node", tmp_js], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        print(r.stderr[:1500]); return 1
    rendered = json.loads(r.stdout)

    # كل تعبير معزول في سطر مستقل: عندها يكفي ترتيب الحروف أفقياً لإثبات الاتجاه
    exprs = []
    for html in rendered:
        for sp in re.findall(r'<span class="m">(.*?)</span>', html):
            exprs.append(unesc(sp))

    body = ['<p class="line">%s</p>' % ('<span class="m">%s</span>' % e.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
            for e in exprs]
    page = ('<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            '<style>@page{size:A4;margin:12mm}'
            'body{font-family:Tahoma,"Segoe UI",sans-serif;font-size:14pt;line-height:3}'
            '.m{direction:ltr;unicode-bidi:isolate-override}'
            '.line{margin:0 0 12pt;break-inside:avoid}</style></head><body>'
            + "".join(body) + "</body></html>")
    tmp_html = os.path.join(OUT, "_render_check.html")
    io.open(tmp_html, "w", encoding="utf-8").write(page)

    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", "--virtual-time-budget=8000",
                    "--print-to-pdf=" + PDF, "file:///" + tmp_html.replace("\\", "/")],
                   capture_output=True, timeout=120)

    import fitz
    doc = fitz.open(PDF)
    lines = {}
    for pg in doc:
        for blk in pg.get_text("rawdict")["blocks"]:
            for ln in blk.get("lines", []):
                for sp in ln.get("spans", []):
                    for ch in sp["chars"]:
                        key = (pg.number, round(ch["bbox"][1]))
                        lines.setdefault(key, []).append((ch["bbox"][0], ch["c"]))
    doc.close()

    printed = ["".join(c for x, c in sorted(v)) for k, v in sorted(lines.items())]
    norm = lambda t: re.sub(r"\s+", "", t)

    fails = 0
    print("تعابير: %d   |   أسطر مطبوعة: %d\n" % (len(exprs), len(printed)))
    for k, exp in enumerate(exprs):
        got = printed[k] if k < len(printed) else "<مفقود>"
        ok = norm(got) == norm(exp)
        if not ok: fails += 1
        print("%s  «%s»%s" % ("سليم ✔" if ok else "معكوس ✘", exp,
                              "" if ok else "   ← طُبع: «%s»" % got))
    print("\nSUMMARY expressions=%d reversed=%d" % (len(exprs), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
