# -*- coding: utf-8 -*-
"""
يبني نسخة الويب المستقلة من ملف التطبيق المصدر.

  python build.py            بناء عادي
  python build.py --bump     بناء + رفع رقم نسخة الـ Service Worker

ارفع رقم النسخة عند أي تغيير في index.html، وإلا بقي من ثبّتوا
التطبيق على النسخة القديمة المخزّنة في متصفحاتهم.
"""
import io, os, re, sys

SRC = r"C:\Users\mahbo\OneDrive\Cloud AI Dash\Qiyas\miqyas.html"
OUT = os.path.dirname(os.path.abspath(__file__))

HEAD = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="تدريب على اختبار قياس (القدرات العامة) مع تشخيص نقاط الضعف على مستوى المهارة وسبب الخطأ.">
<meta name="theme-color" content="#0E6E63" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0C1412" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="مِقياس">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png" sizes="192x192">
<link rel="apple-touch-icon" href="icon-192.png">
<style>
:root{color-scheme:light dark}
*{-webkit-tap-highlight-color:transparent}
img{max-width:100%}
[hidden]{display:none!important}
</style>
'''

TAIL = '''
<script>
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("sw.js").catch(function () {});
  });
}
</script>
</body>
</html>
'''


def main():
    if "--skip-validate" not in sys.argv:
        import validate
        if validate.main() != 0:
            print("\nBUILD ABORTED: validation failed. Fix the errors above.")
            print("(--skip-validate to override, only when you know why.)")
            sys.exit(1)

    src = io.open(SRC, encoding="utf-8").read()
    head, body = src.split("</style>", 1)
    doc = HEAD + head + "</style>\n</head>\n<body>\n" + body.strip() + TAIL
    io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(doc)

    n_q = len(re.findall(r'\{s:"[a-z]+",(?:p:|q:)', doc))
    print("index.html : %d chars | %d questions" % (len(doc), n_q))

    if "--bump" in sys.argv:
        p = os.path.join(OUT, "sw.js")
        sw = io.open(p, encoding="utf-8").read()
        m = re.search(r'CACHE = "miqyas-v(\d+)"', sw)
        old = int(m.group(1))
        sw = sw.replace('miqyas-v%d' % old, 'miqyas-v%d' % (old + 1))
        io.open(p, "w", encoding="utf-8").write(sw)
        print("sw.js      : cache v%d -> v%d" % (old, old + 1))


if __name__ == "__main__":
    main()
