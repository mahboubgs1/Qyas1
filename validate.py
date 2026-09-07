# -*- coding: utf-8 -*-
"""
فاحص بنك الأسئلة — يُشغَّل تلقائياً من build.py قبل كل بناء.

  python validate.py

يفشل البناء إذا وُجد أي خطأ (ERROR). التحذيرات (WARN) تُعرض ولا توقف البناء.
الغرض: منع الأخطاء من الوصول للنشر عند التوسع إلى آلاف الأسئلة،
حيث تستحيل المراجعة اليدوية.
"""
import io, os, re, subprocess, sys, tempfile

SRC = r"C:\Users\mahbo\OneDrive\Cloud AI Dash\Qiyas\miqyas.html"

CHECKS = r"""
const E=[], W=[];
const err=(c,m)=>E.push("["+c+"] "+m);
const warn=(c,m)=>W.push("["+c+"] "+m);
const cut=s=>String(s).slice(0,58).replace(/\s+/g," ");
const SKIDS=new Set(SKILLS.map(s=>s.id));

/* 1) البنية */
Q.forEach((q,i)=>{
  const at="q#"+i+" ("+q.s+") «"+cut(q.q)+"»";
  if(!SKIDS.has(q.s))              err("SKILL", at+" مهارة غير معرّفة");
  if(!Array.isArray(q.c)||q.c.length!==4) err("CHOICES", at+" عدد الخيارات ليس 4");
  if(!Array.isArray(q.m)||q.m.length!==4) err("TAGS", at+" وسوم m ليست 4");
  if(new Set(q.c).size!==q.c.length)      err("DUPCHOICE", at+" خياران متطابقان");
  if(typeof q.a!=="number"||q.a<0||q.a>3) err("ANSWER", at+" رقم الإجابة خارج المدى");
  if(q.m && q.m[q.a]!==null)              err("TAGS", at+" وسم الإجابة الصحيحة ليس null");
  (q.m||[]).forEach((t,j)=>{ if(t!==null && !(t in WHY)) err("TAGS", at+" وسم مجهول: "+t); });
  if(!q.e || q.e.length<15)               warn("EXPL", at+" الشرح قصير جداً");
});

/* 2) توزيع موضع الإجابة الصحيحة بعد الخلط */
const pos=[0,0,0,0];
for(let r=0;r<200;r++) Q.forEach(q=>{ pos[prep(q).a]++; });
const tot=pos.reduce((a,b)=>a+b,0);
pos.forEach((n,i)=>{ const p=100*n/tot;
  if(p<18||p>32) err("DISTRIB","موضع الإجابة «"+"أبجد"[i]+"» = "+p.toFixed(1)+"% (المطلوب ~25%)");
});

/* 3) سلامة الخلط: النص والوسوم تنتقل مع الإجابة */
Q.forEach((q,i)=>{
  for(let r=0;r<8;r++){
    const d=prep(q);
    if(d.c[d.a]!==q.c[q.a])        err("SHUFFLE","q#"+i+" نص الإجابة تغيّر بعد الخلط");
    if(d.m[d.a]!==null)            err("SHUFFLE","q#"+i+" وسم الإجابة لم ينتقل");
    if([...d.c].sort().join("|")!==[...q.c].sort().join("|")) err("SHUFFLE","q#"+i+" ضاع خيار");
  }
});

/* 4) اتجاه النص: لا فقدان نص + عزل كل تعبير رياضي */
const strip=s=>s.replace(/<[^>]+>/g,"").replace(/&lt;/g,"<").replace(/&gt;/g,">")
                .replace(/&amp;/g,"&").replace(/&quot;/g,'"');
const NEEDS=/[0-9٠-٩][^\S\n]*[+\-−×÷=<>≥≤][^\S\n]*[0-9٠-٩(]|[0-9٠-٩][سص]|[سص][^\S\n]*[<>≥≤=]/;
Q.forEach((q,i)=>{
  const fields=[["q",q.q],["e",q.e]].concat(q.c.map((c,j)=>["c"+j,c])).concat(q.p?[["p",q.p]]:[]);
  fields.forEach(([f,t])=>{
    const o=mfix(t);
    if(strip(o)!==t) err("BIDI-LOSS","q#"+i+"."+f+" فقدان نص بعد mfix: «"+cut(t)+"»");
    if(NEEDS.test(t) && o.indexOf('class="m"')<0)
      warn("BIDI-UNWRAPPED","q#"+i+"."+f+" تعبير رياضي غير معزول: «"+cut(t)+"»");
    /* إشارة مقارنة خارج العزل = خطر انعكاس ≥ إلى ≤ */
    const outside=o.replace(/<span class="m">[\s\S]*?<\/span>/g,"");
    if(/[≥≤]|&lt;|&gt;/.test(outside))
      err("BIDI-SIGN","q#"+i+"."+f+" إشارة مقارنة خارج العزل (ستنعكس): «"+cut(t)+"»");
  });
});

/* 4ب) حالات اختبار ثابتة — كل واحدة خطأ حقيقي ظهر للمستخدم من قبل */
const GOLD=[
 ["المخمّس + 1 (حرف آخر الكلمة لا يدخل العزل)",
  "القيمة الثانية = عدد أضلاع المخمّس + 1", null],
 ["= 0.7 (العامل الثنائي يبقى خارج العزل)",
  "القيمة الثانية = 0.7", null],
 ["العدد = 14 × 4 (كلمة تنتهي بحرفين)",
  "المجموع = المتوسط × العدد = 14 × 4 = 56 سنة.", "14 × 4 = 56"],
 ["معادلة بلا متغيّرات", "أوجد ناتج: 5 + 7 × (11 − 8)² ÷ 3 − 4", "5 + 7 × (11 − 8)² ÷ 3 − 4"],
 ["متباينة بمتغيّر عربي", "إذا كان 2س + 3 ≥ 11، فما أصغر قيمة؟", "2س + 3 ≥ 11"],
 ["مقارنة بحروف تسمية", "إذا كان أ > ب > 0، قارن", "أ &gt; ب &gt; 0"],
 ["نسبة", "س : ص = 2 : 7 وكان", "س : ص = 2 : 7"],
];
GOLD.forEach(([name,input,expect])=>{
  const o=mfix(input);
  const got=(o.match(/<span class="m">([\s\S]*?)<\/span>/)||[])[1] || null;
  if(expect===null){ if(got!==null) err("GOLD",name+" ← عُزل ما لا يجب عزله: «"+got+"»"); }
  else if(got!==expect) err("GOLD",name+" ← المتوقع «"+expect+"» والناتج «"+got+"»");
});

/* 4ج) كل سؤال مقارنة يجب أن ينقسم إلى صفّين (الشرطة بينهما تُقرأ إشارة طرح) */
Q.forEach((q,i)=>{
  const isCmp = q.c.some(c=>c.indexOf("القيمة الأولى أكبر")>=0);
  const p = (typeof cmpParts==="function") ? cmpParts(q.q) : null;
  if(isCmp && !p) err("CMP-SPLIT","q#"+i+" سؤال مقارنة لم ينقسم إلى صفّين: «"+cut(q.q)+"»");
  if(!isCmp && p)  err("CMP-SPLIT","q#"+i+" قُسِّم سؤال ليس مقارنة: «"+cut(q.q)+"»");
  if(p && (!p.a || !p.b)) err("CMP-SPLIT","q#"+i+" إحدى القيمتين فارغة");
});

/* 4د) أي سؤال يشير إلى شكل يجب أن يحمل رسماً فعلياً */
const FIGWORDS=["في الشكل","الشكل المجاور","من الشكل","الرسم البياني","القطاع الدائري","يوضّح القطاع","الجدول التالي"];
Q.forEach((q,i)=>{
  const refers=FIGWORDS.some(k=>q.q.indexOf(k)>=0);
  if(refers && !q.f) err("FIGURE","q#"+i+" يشير إلى شكل غير موجود: «"+cut(q.q)+"»");
  if(q.f && q.f.indexOf("<svg")!==0) err("FIGURE","q#"+i+" حقل الشكل ليس SVG صالحاً");
});

/* 5) الصياغة العربية */
const MASC=/\b(حدّد|حدد|أوجدْ|اختر|أكمل الجملة التالية|قارنْ)\s/;
Q.forEach((q,i)=>{
  if(/(^|\s)(حدّد|اختر)(\s)/.test(q.q)) err("GENDER","q#"+i+" صيغة مذكّر في نص السؤال: «"+cut(q.q)+"»");
  if(/\s{2,}/.test(q.q))                warn("SPACING","q#"+i+" مسافات مكررة");
  if(/[a-zA-Z]{3,}/.test(q.q))          warn("LATIN","q#"+i+" كلمات لاتينية في نص عربي");
});

/* 6) تكرار فعلي (نفس النص + نفس الخيارات) */
const seen=new Map();
Q.forEach((q,i)=>{
  const k=q.q+"||"+[...q.c].sort().join("|");
  if(seen.has(k)) err("DUPLICATE","q#"+i+" مكرر تماماً مع q#"+seen.get(k)+": «"+cut(q.q)+"»");
  else seen.set(k,i);
});

/* 7) تغطية المهارات */
const per={}; Q.forEach(q=>per[q.s]=(per[q.s]||0)+1);
SKILLS.forEach(s=>{
  const n=per[s.id]||0;
  if(n===0)  err("COVERAGE","مهارة بلا أسئلة: "+s.name);
  else if(n<4) warn("COVERAGE","مهارة بأقل من 4 أسئلة: "+s.name+" ("+n+")");
});

console.log("questions="+Q.length+" skills="+SKILLS.length+
            " answer_pos="+pos.map(n=>(100*n/tot).toFixed(0)+"%").join("/"));
E.forEach(x=>console.log("ERROR "+x));
W.forEach(x=>console.log("WARN  "+x));
console.log("SUMMARY errors="+E.length+" warnings="+W.length);
process.exit(E.length?1:0);
"""


def slice_between(js, start, end):
    i = js.index(start)
    j = js.index(end, i)
    return js[i:j]


def main():
    html = io.open(SRC, encoding="utf-8").read()
    js = html.split("<script>")[1].split("</script>")[0]

    parts = [
        slice_between(js, "const SKILLS = [", "const SK ="),
        slice_between(js, "const WHY = {", "/* ══════════ 2."),
        slice_between(js, "const Q = [", "Q.forEach((q,i)=>{q.id="),
        slice_between(js, "const CMP_ORDER", "function pickQuestions"),
        slice_between(js, "const esc=", "const pct="),
    ]
    prog = "\n".join(parts) + CHECKS

    tmp = os.path.join(tempfile.gettempdir(), "miqyas_validate.js")
    io.open(tmp, "w", encoding="utf-8").write(prog)

    r = subprocess.run(["node", tmp], capture_output=True, text=True, encoding="utf-8")
    out = (r.stdout or "") + (r.stderr or "")
    sys.stdout.write(out if out.endswith("\n") else out + "\n")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
