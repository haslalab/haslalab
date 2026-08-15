#!/usr/bin/env node
/* ─────────────────────────────────────────────────────────────────────────
   build_seo.js — regenerates sitemap.xml and the two problem-index pages
   from the DATA block inside index.html, so they can never drift out of it.

       node build_seo.js

   The site is a single page with hash routes (#/ipho/2017).  A crawler sees
   a fragment as the same URL, so those routes cannot be indexed on their own
   — the only URLs a search engine can hold are index.html, the simulator
   pages under sim/, and the PDFs.  problems.html exists to give crawlers a
   real HTML path to every one of them, and to put all 131 problem titles
   somewhere they can be read without running JavaScript.
   ───────────────────────────────────────────────────────────────────────── */
const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const ORIGIN = "https://haslalab.org";
const TODAY = new Date().toISOString().slice(0, 10);

/* ── pull DATA and UI out of index.html by evaluating just that slice ── */
function loadData() {
  const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
  const start = html.indexOf("const REL =");
  const marker = "\nconst DATA={";
  const dataAt = html.indexOf(marker);
  if (start < 0 || dataAt < 0) throw new Error("could not find the DATA block");
  // walk to the brace that closes DATA
  let i = dataAt + marker.length - 1, depth = 0;
  for (; i < html.length; i++) {
    if (html[i] === "{") depth++;
    else if (html[i] === "}") { depth--; if (depth === 0) break; }
  }
  const src = html.slice(start, i + 1) + ";\nreturn DATA;";
  return new Function(src)();
}

const DATA = loadData();
const exists = p => fs.existsSync(path.join(ROOT, p));

/* ── walk the catalogue once ── */
const rows = [];          // one per problem
const simPages = new Set();
const docs = new Set();   // pdfs that are actually on disk

for (const [key, c] of Object.entries(DATA)) {
  if (c.general) for (const v of Object.values(c.general)) if (exists(v)) docs.add(v);
  for (const y of c.years) {
    for (const p of y.problems || []) {
      const f = p.files || {};
      const released = !p.hold && !!(f.sim || f.exe);
      if (!p.hold && f.sim && exists(f.sim)) simPages.add(f.sim);
      for (const k of ["pdf", "sol"]) {
        const v = f[k];
        if (!v) continue;
        (typeof v === "string" ? [v] : Object.values(v)).forEach(x => { if (exists(x)) docs.add(x); });
      }
      rows.push({
        comp: c.abbr, key, year: y.y,
        host: y.host || null,
        id: p.id,
        en: p.title ? p.title.en : p.en,
        ko: p.title ? p.title.ko : p.ko,
        theory: !!p.theory,
        released,
        sim: released && f.sim && exists(f.sim) ? f.sim : null,
        pdf: f.pdf && typeof f.pdf === "object"
             ? Object.values(f.pdf).find(exists) || null
             : (typeof f.pdf === "string" && exists(f.pdf) ? f.pdf : null),
        sol: typeof f.sol === "string" && exists(f.sol) ? f.sol : null,
      });
    }
  }
}

/* ── sitemap.xml ── */
const urls = [
  { loc: "/", pri: "1.0", freq: "weekly" },
  { loc: "/problems.html", pri: "0.8", freq: "weekly" },
  { loc: "/problems-en.html", pri: "0.8", freq: "weekly" },
  ...[...simPages].sort().map(s => ({ loc: "/" + s, pri: "0.9", freq: "monthly" })),
  ...[...docs].sort().map(d => ({ loc: "/" + d, pri: "0.5", freq: "yearly" })),
];

const enc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const sitemap =
`<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.w3.org/1999/xhtml/sitemap" xmlns:xhtml="http://www.w3.org/1999/xhtml">
</urlset>`;
// (built properly below — the placeholder above is replaced)
const body = urls.map(u => {
  const loc = ORIGIN + u.loc;
  let alt = "";
  if (u.loc === "/" || u.loc.startsWith("/sim/")) {
    alt = `\n    <xhtml:link rel="alternate" hreflang="ko" href="${enc(loc)}${u.loc === "/" ? "?lang=ko" : "?lang=ko"}"/>` +
          `\n    <xhtml:link rel="alternate" hreflang="en" href="${enc(loc)}?lang=en"/>` +
          `\n    <xhtml:link rel="alternate" hreflang="x-default" href="${enc(loc)}"/>`;
  }
  if (u.loc === "/problems.html")
    alt = `\n    <xhtml:link rel="alternate" hreflang="ko" href="${ORIGIN}/problems.html"/>` +
          `\n    <xhtml:link rel="alternate" hreflang="en" href="${ORIGIN}/problems-en.html"/>`;
  if (u.loc === "/problems-en.html")
    alt = `\n    <xhtml:link rel="alternate" hreflang="ko" href="${ORIGIN}/problems.html"/>` +
          `\n    <xhtml:link rel="alternate" hreflang="en" href="${ORIGIN}/problems-en.html"/>`;
  return `  <url>\n    <loc>${enc(loc)}</loc>\n    <lastmod>${TODAY}</lastmod>` +
         `\n    <changefreq>${u.freq}</changefreq>\n    <priority>${u.pri}</priority>${alt}\n  </url>`;
}).join("\n");

fs.writeFileSync(path.join(ROOT, "sitemap.xml"),
`<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
${body}
</urlset>
`);

/* ── robots.txt ── */
fs.writeFileSync(path.join(ROOT, "robots.txt"),
`User-agent: *
Allow: /

# Naver
User-agent: Yeti
Allow: /

# Daum
User-agent: Daumoa
Allow: /

Sitemap: ${ORIGIN}/sitemap.xml
`);

/* ── problems.html / problems-en.html ── */
const T = {
  ko: {
    lang: "ko", other: "problems-en.html", otherLabel: "English",
    title: "실험 문제 전체 목록 — 국제물리올림피아드 실험 시뮬레이터 · HaslaLab",
    desc: "IPhO · APhO · EuPhO · NBPhO · ISPhO · RMPh의 실험 문제 131개를 연도별로 정리했습니다. 브라우저에서 바로 실행되는 가상 실험 장치와 문제지 PDF로 이어집니다.",
    h1: "실험 문제 전체 목록",
    lede: "국제 물리올림피아드 여섯 개 대회의 실험 문제를 연도순으로 모았습니다. 「실행」이 붙은 문제는 브라우저에서 실제 계측기와 같은 방식으로 조작할 수 있고, 어떤 물리량도 대신 계산해 주지 않습니다.",
    run: "실행", sheet: "문제지", sol: "해설", theory: "이론", soon: "준비 중",
    home: "홈으로", counts: (y, p) => `${y}개 연도 · 실험 문제 ${p}개`,
  },
  en: {
    lang: "en", other: "problems.html", otherLabel: "한국어",
    title: "Every experimental problem — Physics Olympiad simulators · HaslaLab",
    desc: "All 131 experimental problems from IPhO, APhO, EuPhO, NBPhO, ISPhO and RMPh, indexed by year, linking to browser simulators and problem sheets.",
    h1: "Every experimental problem",
    lede: "The experimental problems of six international physics olympiads, by year. Anything marked Run opens as working apparatus in the browser — it shows what the instruments show and computes nothing for you.",
    run: "Run", sheet: "Sheet", sol: "Solution", theory: "Theory", soon: "In preparation",
    home: "Home", counts: (y, p) => `${y} years · ${p} experimental problems`,
  },
};

const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                          .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function page(L) {
  const t = T[L];
  const byComp = {};
  rows.forEach(r => { (byComp[r.key] ||= []).push(r); });

  const sections = Object.entries(DATA).map(([key, c]) => {
    const list = byComp[key] || [];
    const years = [...new Set(list.map(r => r.year))].sort((a, b) => b - a);
    const items = years.map(yr => {
      const ys = list.filter(r => r.year === yr);
      const host = ys[0].host ? esc(ys[0].host[L]) : "";
      const lis = ys.map(r => {
        const name = esc(L === "ko" ? (r.ko || r.en) : (r.en || r.ko));
        const links = [];
        if (r.sim) links.push(`<a href="${esc(r.sim)}?lang=${L}">${t.run}</a>`);
        if (r.pdf) links.push(`<a href="${esc(r.pdf)}">${t.sheet}</a>`);
        if (r.sol) links.push(`<a href="${esc(r.sol)}">${t.sol}</a>`);
        const tag = r.theory ? ` <span class="tag">${t.theory}</span>` : "";
        const state = links.length ? links.join(" · ") : `<span class="soon">${t.soon}</span>`;
        return `      <li><b>${esc(r.id)}</b> ${name}${tag} <span class="lk">${state}</span></li>`;
      }).join("\n");
      return `    <h3>${esc(c.abbr)} ${yr}${host ? ` <span class="host">${host}</span>` : ""}</h3>\n    <ul>\n${lis}\n    </ul>`;
    }).join("\n");
    return `  <section>\n    <h2>${esc(c.abbr)} — ${esc(c.full[L])}</h2>\n` +
           `    <p class="meta">${esc(c.scope[L])} · ${t.counts(years.length, list.length)}</p>\n${items}\n  </section>`;
  }).join("\n\n");

  const ld = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: t.h1,
    description: t.desc,
    inLanguage: L === "ko" ? "ko-KR" : "en",
    url: `${ORIGIN}/${L === "ko" ? "problems.html" : "problems-en.html"}`,
    isPartOf: { "@type": "WebSite", name: "HaslaLab", url: ORIGIN + "/" },
    about: Object.values(DATA).map(c => ({ "@type": "Thing", name: c.full[L] })),
  };

  return `<!DOCTYPE html>
<html lang="${t.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(t.title)}</title>
<meta name="description" content="${esc(t.desc)}">
<link rel="canonical" href="${ORIGIN}/${L === "ko" ? "problems.html" : "problems-en.html"}">
<link rel="alternate" hreflang="ko" href="${ORIGIN}/problems.html">
<link rel="alternate" hreflang="en" href="${ORIGIN}/problems-en.html">
<link rel="alternate" hreflang="x-default" href="${ORIGIN}/problems.html">
<meta property="og:site_name" content="HaslaLab">
<meta property="og:type" content="website">
<meta property="og:title" content="${esc(t.title)}">
<meta property="og:description" content="${esc(t.desc)}">
<meta property="og:url" content="${ORIGIN}/${L === "ko" ? "problems.html" : "problems-en.html"}">
<meta property="og:image" content="${ORIGIN}/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="${ORIGIN}/og.png">
<meta name="theme-color" content="#2E3945">
<link rel="icon" type="image/png" href="data:image/png;base64,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">
<link rel="apple-touch-icon" href="data:image/png;base64,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">
<script type="application/ld+json">${JSON.stringify(ld)}</script>
<style>
:root{--ink:#16212E;--graphite:#5C6B7A;--rule:#B4CADC;--paper:#FBFCFD;--laser:#E02424}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);line-height:1.65;
 font:16px/1.65 "IBM Plex Sans","Apple SD Gothic Neo","Malgun Gothic",-apple-system,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:40px 20px 80px}
h1{font-size:clamp(1.7rem,4vw,2.4rem);margin:0 0 10px;letter-spacing:-.02em}
.lede{color:var(--graphite);margin:0 0 8px;max-width:62ch}
nav{margin:22px 0 34px;font-size:14px}
nav a{color:var(--ink);margin-right:14px}
h2{font-size:1.15rem;margin:38px 0 4px;padding-top:16px;border-top:1px solid var(--rule)}
.meta{color:var(--graphite);font-size:13px;margin:0 0 14px}
h3{font-size:.95rem;font-weight:600;margin:20px 0 6px}
.host{color:var(--graphite);font-weight:400;font-size:.85em}
ul{list-style:none;padding:0;margin:0}
li{padding:5px 0;border-bottom:1px dotted var(--rule);font-size:14.5px}
li b{font-family:ui-monospace,Consolas,monospace;font-size:13px;color:var(--graphite);margin-right:8px}
.lk{white-space:nowrap;font-size:13px}
.lk a{color:var(--laser);text-decoration:none;border-bottom:1px solid currentColor}
.lk a:hover{background:#fdeaea}
.soon{color:var(--graphite);font-size:12.5px}
.tag{font-size:11px;color:var(--graphite);border:1px solid var(--rule);border-radius:3px;padding:0 4px}
footer{margin-top:50px;padding-top:16px;border-top:1px solid var(--rule);
 color:var(--graphite);font-size:13px}
a{color:var(--ink)}
</style>
</head>
<body>
<div class="wrap">
<h1>${t.h1}</h1>
<p class="lede">${t.lede}</p>
<nav><a href="./">${t.home}</a><a href="${t.other}">${t.otherLabel}</a></nav>

${sections}

<footer>HaslaLab · MinGyuSong · HaslaEdu</footer>
</div>
</body>
</html>
`;
}

fs.writeFileSync(path.join(ROOT, "problems.html"), page("ko"));
fs.writeFileSync(path.join(ROOT, "problems-en.html"), page("en"));

console.log(`sitemap.xml   ${urls.length} URLs (${simPages.size} simulators, ${docs.size} documents)`);
console.log(`robots.txt    written`);
console.log(`problems.html / problems-en.html   ${rows.length} problems across ${new Set(rows.map(r => r.key + r.year)).size} years`);
