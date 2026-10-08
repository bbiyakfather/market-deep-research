"""참고문헌 자동 생성기 (APA 7판) — URL 목록 → 서지 항목 → 부록.md 의 '참고문헌' 절 교체.

사용법
  python make_references.py --src 원본.md --out 부록.md [--evidence evidence.jsonl] [--snapshot-root 디렉터리]
                             [--cache _refs_cache.json] [--style footnote|table] [--no-network] [--redo]
  python make_references.py --demo        # 네트워크 없이 내장 샘플 3건으로 자체 검증(통과 시 exit 0)

입력 형식 (--src; '## 참고문헌' 절이 있으면 그 절만, 없으면 파일 전체를 읽는다)
  ### 1.1 절 이름                     ← 절 제목은 유지된다(없으면 한 덩어리)
  | 라벨 | https://example.com/a |    ← 표 행(마지막 열이 URL)
  - https://example.com/b            ← 불릿 줄(앞에 라벨이 있어도 됨)
  --evidence: 줄마다 {"source_url": "...", "local": "상대경로"} 인 JSONL. local 은 --snapshot-root
  (기본: evidence 파일이 있는 폴더) 기준의 원문 스냅샷(html·pdf). 없으면 URL 로 직접 받아 메타를 읽는다.

출력 예 (footnote, 전체 일련번호)
  <sup>1)</sup> Example Corp. (2025). Global Outlook 2025. https://www.example.com/report
  <sup>2)</sup> Kim, H.-I., & Lee, J. (2024). Iridium thin films. Journal of Demo, 12(3), 45-67. https://doi.org/10.1234/demo.2024
  <sup>3)</sup> 전자신문. (2025). 수소 전해조 이리듐 저감 기술 개발. https://www.etnews.com/20250101000001

규칙 : 절 유지 / DOI→Crossref(DataCite) / OpenAlex / HTML·PDF 메타 / 캐시 'manual' 항목 최우선 / DOI 있으면 DOI 링크만 /
       같은 DOI 는 한 항목(학술 절 우선) / 라틴→가나다 정렬 / 해석 실패는 ' [확인 필요]' / 참고문헌 밖 절은 그대로 보존.
       외부로는 DOI·URL 만 보낸다(이메일·본문 등 다른 정보는 보내지 않음). 요청 사이 0.3초.
"""
import argparse
import hashlib
import json
import re
import sys
import tempfile
import time
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

TODO = " [확인 필요]"
NET = True  # --no-network 이면 False (api()/원문 내려받기가 캐시만 쓴다)
_d = date.today()
RETR_DATE = f"{_d.year}년 {_d.month}월 {_d.day}일"  # '접속일' 표기(변동 페이지용)
ACADEMIC = re.compile(r"학술|논문|academic|journal|paper|literature", re.I)  # 같은 DOI 중복 시 이 절을 우선
REF_H = re.compile(r"^##\s+(?:\d+\.\s*)?(참고\s?문헌|References?|Bibliography)", re.I)
ROW_RE = re.compile(r"^\|.*?\|\s*(https?://[^\s|]+)\s*\|\s*$")
BUL_RE = re.compile(r"^\s*[-*]\s+(?:.*?[\s:])?<?(https?://[^\s>)|]+)")
# 도메인에 노출되지 않게 접속일을 적어야 하는 변동 페이지(주소 일부) — 필요하면 추가
RETRIEVED = ("sfa-oxford.com", "connect.patsnap.com", "api.openalex.org/works?", "catalyst-coated-membrane-ccm")

ORG = {
    "hydrogen.energy.gov": "U.S. Department of Energy", "energy.gov": "U.S. Department of Energy",
    "www1.eere.energy.gov": "U.S. Department of Energy", "osti.gov": "U.S. Department of Energy, Office of Scientific and Technical Information",
    "pubs.usgs.gov": "U.S. Geological Survey", "d9-wret.s3.us-west-2.amazonaws.com": "U.S. Geological Survey",
    "matthey.com": "Johnson Matthey", "pmc.umicore.com": "Umicore", "fcs.umicore.com": "Umicore",
    "heraeus-precious-metals.com": "Heraeus Precious Metals", "nedo.go.jp": "NEDO", "kist.re.kr": "KIST",
    "clean-hydrogen.europa.eu": "Clean Hydrogen Partnership", "publications.jrc.ec.europa.eu": "European Commission, Joint Research Centre",
    "h2hub.or.kr": "H2Hub", "scienceon.kisti.re.kr": "KISTI ScienceON", "eiec.kdi.re.kr": "KDI 경제정보센터",
    "irena.org": "IRENA", "iea.blob.core.windows.net": "IEA", "sfa-oxford.com": "SFA (Oxford)", "ise.fraunhofer.de": "Fraunhofer ISE",
    "global.toshiba": "Toshiba", "news.toshiba.com": "Toshiba", "tokyo-gas.co.jp": "Tokyo Gas", "smoltek.com": "Smoltek",
    "inderes.dk": "Inderes", "vsparticle.com": "VSParticle", "spark-nano.com": "Spark Nano", "holdings.toppan.com": "Toppan Holdings",
    "newsis.com": "뉴시스", "thevc.kr": "THE VC", "h2news.kr": "수소경제신문", "h2.solarbe.com": "SolarBE", "sciencetimes.co.kr": "사이언스타임즈",
    "dailian.co.kr": "데일리안", "asiae.co.kr": "아시아경제", "dongascience.com": "동아사이언스", "etnews.com": "전자신문", "mt.co.kr": "머니투데이",
    "m.kw.ac.kr": "광운대학교", "lg.co.kr": "LG", "doosanfuelcell.com": "두산퓨얼셀", "hyundaimotorgroup.com": "현대자동차그룹",
    "kolonindustries.com": "코오롱인더스트리", "kopernikus-projekte.de": "Kopernikus-Projekte", "prosjektbanken.forskningsradet.no": "Research Council of Norway",
    "nanoge.org": "NanoGe", "epfl.ch": "EPFL", "zenodo.org": "Zenodo", "elib.dlr.de": "DLR", "ipa-news.com": "IPA News", "hydrogencouncil.com": "Hydrogen Council",
    "tno.nl": "TNO", "mottcorp.com": "Mott Corporation", "bekaert.com": "Bekaert", "impactcoatings.com": "Impact Coatings", "nano4energy.eu": "Nano4Energy",
    "plugpower.com": "Plug Power", "siemens-energy.com": "Siemens Energy", "ohmium.com": "Ohmium", "mtu-solutions.com": "MTU", "sinopecgroup.com": "Sinopec",
    "3m.com": "3M", "ammoniaenergy.org": "Ammonia Energy Association", "d-nb.info": "Deutsche Nationalbibliothek", "furuyametals.co.jp": "Furuya Metal",
    "news.rice.edu": "Rice University", "impact.ornl.gov": "Oak Ridge National Laboratory", "redi.anii.org.uy": "ANII", "cau.scholarworks.kr": "중앙대학교",
    "connect.patsnap.com": "PatSnap", "globalhydrogenreview.com": "Global Hydrogen Review", "hydrogentechworld.com": "Hydrogen Tech World",
    "businesswire.com": "Business Wire", "htech360.com": "Htech360", "lse.co.uk": "London Stock Exchange", "engineeringnews.co.za": "Engineering News",
    "hydrogen-central.com": "Hydrogen Central", "lajauneetlarouge.com": "La Jaune et la Rouge", "h2weilai.com": "氢未来", "news.eccn.com": "ECCN",
    "gasnews.com": "가스신문", "news.sina.com.cn": "新浪新闻", "finance.sina.com.cn": "新浪财经", "chemnews.com.cn": "中国化工报",
    "openalex.org": "OpenAlex", "escholarship.org": "eScholarship, University of California", "arxiv.org": "arXiv",
    "strathprints.strath.ac.uk": "University of Strathclyde", "api.openalex.org": "OpenAlex", "api.crossref.org": "Crossref", "ebi.ac.uk": "Europe PMC",
    "ncbi.nlm.nih.gov": "National Center for Biotechnology Information", "kim.or.kr": "한국금속재료학회",
}
PUBLISHER_HOSTS = ("doi.org", "nature.com", "iopscience.iop.org", "onlinelibrary.wiley.com", "pmc.ncbi.nlm.nih.gov", "ecs.confex.com", "pubs.acs.org",
                   "sciencedirect.com", "arxiv.org", "pubs.rsc.org", "link.springer.com", "mdpi.com", "researchsquare.com", "spiedigitallibrary.org",
                   "strathprints.strath.ac.uk", "escholarship.org", "ebi.ac.uk", "api.openalex.org", "api.crossref.org")
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>?#\\[\]]+")


# ---------------------------------------------------------------- 문자열 도우미
def clean(t):
    if not t:
        return ""
    import html
    t = html.unescape(t)  # Crossref 제목은 &lt;sub&gt; 처럼 이스케이프된 경우가 있어 태그 제거보다 먼저
    t = re.sub(r"\s*(<su[bp]>)\s*", r"\1", t)  # 아래·위첨자 둘레 공백 제거(RuO <sub>2</sub> → RuO2)
    t = re.sub(r"\s*(</su[bp]>)", r"\1", t)
    t = re.sub(r"<[^>]+>", "", t)  # <i>, <sub>, mml 태그 제거
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s*\|\s*", " - ", t)
    t = t.replace("‐", "-").replace("‑", "-").replace("−", "-")
    t = re.sub(r"\s[—–]\s", " - ", t)
    t = re.sub(r"[—–]", "-", t)
    t = t.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return t


def initials(given):
    parts = []
    for tok in re.split(r"\s+", clean(given)):
        if not tok:
            continue
        parts.append("-".join(p[0].upper() + "." for p in tok.split("-") if p))
    return " ".join(parts)


def name_fmt(fam, giv):
    fam = clean(fam)
    ini = initials(giv)
    return f"{fam}, {ini}" if ini else fam


def authors_fmt(authors):
    """authors: ['Family, G.', ...] 혹은 기관명 리스트 → APA 7 저자 구간(마침표 포함 끝 처리 전)"""
    n = len(authors)
    if n == 0:
        return ""
    if n == 1:
        return authors[0]
    if n <= 20:
        return ", ".join(authors[:-1]) + ", & " + authors[-1]
    return ", ".join(authors[:19]) + ", … " + authors[-1]


def with_period(s):
    s = s.rstrip()
    return s if s.endswith((".", "?", "!")) else s + "."


def read_text(p):
    b = Path(p).read_bytes()
    for enc in ("utf-8", "gb18030", "euc-kr", "cp949", "latin-1"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace")


def host_of(url):
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def org_of(url, soup=None):
    h = host_of(url)
    for k, v in ORG.items():
        if h == k or h.endswith("." + k):
            return v
    if soup is not None:
        og = soup.find("meta", attrs={"property": "og:site_name"})
        if og and og.get("content"):
            return clean(og["content"])
    return h


def year_of(s):
    m = re.search(r"(?<!\d)(19[89]\d|20[0-2]\d)(?!\d)", s or "")
    return m.group(1) if m else None


# ---------------------------------------------------------------- 레코드 해석
def rec_from_crossref(m, url):
    t = m.get("type", "")
    title = clean((m.get("title") or [""])[0])
    sub = (m.get("subtitle") or [""])[0]
    if sub and sub.lower() not in title.lower():
        title = title.rstrip(":") + ": " + clean(sub)
    auth = []
    for a in m.get("author", []) or []:
        if a.get("family"):
            auth.append(name_fmt(a["family"], a.get("given", "")))
        elif a.get("name"):
            auth.append(clean(a["name"]))
    y = None
    for k in ("issued", "published", "published-online", "published-print", "posted", "created"):
        dp = (m.get(k) or {}).get("date-parts", [[None]])[0]
        if dp and dp[0]:
            y = str(dp[0])
            break
    cont = clean((m.get("container-title") or [""])[0])
    kind = "journal"
    if t == "posted-content":
        kind = "preprint"
        inst = (m.get("institution") or [{}])[0].get("name") if m.get("institution") else None
        cont = clean(inst or m.get("group-title") or m.get("publisher") or "")
    elif "mtgabs" in (m.get("DOI") or "").lower() or t in ("proceedings-article",) and "Abstracts" in cont:
        kind = "conf"
    elif t in ("book", "monograph", "report", "report-component"):
        kind = "report"
        cont = cont or clean(m.get("publisher", ""))
    pages = m.get("page") or m.get("article-number") or ""
    pages = re.sub(r"^(\S+)-\1$", r"\1", clean(pages))  # 1881-1881 → 1881 (한 쪽짜리 초록)
    return dict(kind=kind, authors=auth, year=y or "n.d.", title=title, container=cont, volume=clean(m.get("volume", "")),
                issue=clean(m.get("issue", "")), pages=clean(pages), doi=m.get("DOI"), src="Crossref")


def rec_from_datacite(a, url):
    auth = [name_fmt(c.get("familyName"), c.get("givenName")) if c.get("familyName") else clean(c.get("name", ""))
            for c in a.get("creators", [])]
    title = clean((a.get("titles") or [{}])[0].get("title", ""))
    pub = clean(a.get("publisher", "")) if isinstance(a.get("publisher"), str) else clean((a.get("publisher") or {}).get("name", ""))
    return dict(kind="preprint", authors=auth, year=str(a.get("publicationYear") or "n.d."), title=title, container=pub,
                volume="", issue="", pages="", doi=a.get("doi"), src="Crossref")


def rec_from_openalex(j, url):
    auth = []
    for a in j.get("authorships", []) or []:
        n = clean((a.get("author") or {}).get("display_name", ""))
        if not n:
            continue
        p = n.split()
        auth.append(name_fmt(p[-1], " ".join(p[:-1])) if len(p) > 1 else n)
    src = ((j.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    bib = j.get("biblio") or {}
    pg = "-".join(x for x in (bib.get("first_page"), bib.get("last_page")) if x)
    doi = (j.get("doi") or "").replace("https://doi.org/", "") or None
    return dict(kind="journal", authors=auth, year=str(j.get("publication_year") or "n.d."), title=clean(j.get("title") or j.get("display_name")),
                container=clean(src), volume=clean(bib.get("volume") or ""), issue=clean(bib.get("issue") or ""), pages=pg, doi=doi, src="OpenAlex")


def title_match(a, b):
    ta = set(re.findall(r"[a-z0-9]{4,}", (a or "").lower()))
    tb = set(re.findall(r"[a-z0-9]{4,}", (b or "").lower()))
    return bool(ta) and len(ta & tb) / len(ta) >= 0.6


def get_html(path):
    from bs4 import BeautifulSoup
    return BeautifulSoup(read_text(path), "html.parser")


def metas(soup, *names):
    out = []
    for n in names:
        for m in soup.find_all("meta", attrs={"name": re.compile(f"^{re.escape(n)}$", re.I)}) + \
                soup.find_all("meta", attrs={"property": re.compile(f"^{re.escape(n)}$", re.I)}) + \
                soup.find_all("meta", attrs={"itemprop": re.compile(f"^{re.escape(n)}$", re.I)}):
            if m.get("content"):
                out.append(m["content"].strip())
    return out


def pdf_text(path, pages=2):
    import fitz
    d = fitz.open(path)
    meta = d.metadata or {}
    txt = "\n".join(d[i].get_text() for i in range(min(pages, len(d))))
    return meta, txt


def doi_from_url(url):
    u = unquote(url)
    h = host_of(url)
    m = re.match(r"https?://arxiv\.org/(?:abs|pdf)/([\w.\-/]+?)(?:v\d+)?(?:\.pdf)?$", url)
    if m:
        return "10.48550/arXiv." + m.group(1)
    m = re.search(r"zenodo\.org/(?:api/)?records?/(\d+)", url)
    if m:
        return "10.5281/zenodo." + m.group(1)
    if h == "nature.com":
        m = re.search(r"/articles/(s\d+-\d+-\d+-[\w]+|[\w.]+?)(?:\.pdf)?$", urlparse(url).path)
        if m:
            return "10.1038/" + m.group(1)
    m = DOI_RE.search(u)
    if m:
        d = m.group(0).rstrip(".,;)")
        d = re.sub(r"(\.pdf|/pdf|/full|/abstract|/epdf)$", "", d)
        return d
    return None


def candidate_dois(url, local):
    """(doi, 신뢰도) 목록. 신뢰도 'url'은 그대로 신뢰, 'body'는 제목 대조 필요."""
    out = []
    d = doi_from_url(url)
    if d:
        out.append((d, "url"))
    if local and Path(local).exists():
        ext = Path(local).suffix.lower()
        if ext in (".html", ".htm"):
            soup = get_html(local)
            for v in metas(soup, "citation_doi", "dc.identifier", "prism.doi", "dc.identifier.doi", "bepress_citation_doi"):
                m = DOI_RE.search(v)
                if m:
                    out.append((m.group(0).rstrip("."), "meta"))
        if ext in (".html", ".htm", ".xml"):
            m = re.search(r'pub-id-type="doi"[^>]*>\s*(10\.[^<\s]+)', read_text(local)[:400000])  # JATS(Europe PMC)
            if m:
                out.append((m.group(1), "meta"))
        if ext == ".xml":
            pass
        elif ext in (".json", ".txt") and '"DOI"' in read_text(local)[:200000]:
            m = re.search(r'"DOI"\s*:\s*"(10\.[^"]+)"', read_text(local))
            if m and "confex" in url:
                out.append((m.group(1), "meta"))
    return out


def body_dois(local):
    if not local or not Path(local).exists():
        return []
    ext = Path(local).suffix.lower()
    try:
        if ext == ".pdf":
            _, t = pdf_text(local, 2)
        elif ext in (".html", ".htm"):
            t = get_html(local).get_text(" ")[:60000]
        elif ext in (".md", ".txt", ".json"):
            t = read_text(local)[:20000]
        else:
            return []
    except Exception:
        return []
    return [m.group(0).rstrip(".,;)") for m in re.finditer(r"(?:doi\.org/|doi[:\s]\s*)(10\.\d{4,9}/[^\s\"'<>?#]+)", t, re.I) for m in [re.search(DOI_RE, m.group(0))]]


def page_title_guess(local):
    if not local or not Path(local).exists():
        return ""
    ext = Path(local).suffix.lower()
    try:
        if ext in (".html", ".htm"):
            s = get_html(local)
            return " ".join(metas(s, "citation_title", "og:title") + [s.title.get_text() if s.title else ""])
        if ext == ".pdf":
            meta, t = pdf_text(local, 1)
            return (meta.get("title") or "") + " " + t[:1500]
        if ext in (".md", ".txt", ".json"):
            return read_text(local)[:20000]
    except Exception:
        pass
    return ""


def strip_site(t):
    t = clean(t)
    for sep in (" | ", " :: ", " - ", " : "):
        if sep in t:
            head, tail = t.rsplit(sep, 1)
            if len(head) >= 15 and len(tail) <= 40:
                t = head
    return t.strip()


def rec_html(url, local):
    soup = get_html(local)
    t = (metas(soup, "citation_title") or metas(soup, "og:title", "twitter:title") or [soup.title.get_text() if soup.title else ""])[0]
    title = strip_site(t)
    y = None
    for v in metas(soup, "citation_publication_date", "citation_date", "article:published_time", "dc.date", "dc.date.issued", "datePublished", "date", "pubdate", "publishdate", "og:updated_time"):
        y = year_of(v)
        if y:
            break
    if not y:
        for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
            m = re.search(r'"datePublished"\s*:\s*"(\d{4})', s.string or "")
            if m:
                y = m.group(1)
                break
    if not y:
        y = year_of(unquote(urlparse(url).path))
    if not y:
        y = year_of(soup.get_text(" ")[:3000]) if False else None  # 본문 날짜는 오탐이 많아 쓰지 않음(수기 단계에서 확인)
    auth = [a for a in (n for n in metas(soup, "citation_author")) if a]
    authors = []
    for a in auth:
        if "," in a:
            f, g = a.split(",", 1)
            authors.append(name_fmt(f, g))
        else:
            p = a.split()
            authors.append(name_fmt(p[-1], " ".join(p[:-1])) if len(p) > 1 else a)
    return dict(kind="web", authors=authors or [org_of(url, soup)], year=y or "n.d.", title=title, container="", volume="", issue="", pages="",
                doi=None, src="HTML", pubhtml=bool(auth))


def pdf_font_title(path):
    import fitz
    pg = fitz.open(path)[0]
    H = pg.rect.height
    lines = []
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = "".join(sp["text"] for sp in l["spans"]).strip()
            if len(t) >= 4 and l["bbox"][1] < H * 0.7:
                lines.append((t, max(sp["size"] for sp in l["spans"])))
    if not lines:
        return ""
    mx = max(z for _, z in lines)
    i = next(i for i, (_, z) in enumerate(lines) if z >= mx - 0.5)
    out = []
    for t, z in lines[i:i + 4]:
        if z < mx - 0.5:
            break
        out.append(t)
    return clean(" ".join(out))


def rec_pdf(url, local):
    meta, txt = pdf_text(local, 2)
    t = clean(meta.get("title") or "")
    if len(t) < 8 or re.search(r"\.(docx?|pdf|indd|pptx?)$|^(microsoft|untitled|slide|document)", t, re.I) or re.fullmatch(r"[\w\-. ]*\d{5,}[\w\-. ]*", t):
        t = ""
    if not t:
        ft = pdf_font_title(local)
        if 10 <= len(ft) <= 250:
            t = ft
    if not t:
        for line in txt.splitlines():
            line = line.strip()
            if len(line) >= 15 and not re.match(r"^(page|www\.|http|\d+$)", line, re.I):
                t = clean(line)
                break
    y = year_of(unquote(urlparse(url).path)) or year_of(txt[:1500])
    if not y:
        y = year_of((meta.get("creationDate") or "")[2:6]) if meta.get("creationDate") else None
    return dict(kind="web", authors=[org_of(url)], year=y or "n.d.", title=t, container="", volume="", issue="", pages="", doi=None, src="PDF")


def rec_patent(url, local):
    num = re.search(r"/patent/([A-Z0-9]+)", url).group(1)
    appl = title = y = ""
    if local and Path(local).exists():
        if Path(local).suffix.lower() in (".html", ".htm"):
            soup = get_html(local)
            title = clean((metas(soup, "DC.title") or [""])[0])
            ds = metas(soup, "DC.date")
            y = year_of(ds[-1]) if ds else ""
            cs = [clean(c) for c in metas(soup, "DC.contributor")]
            org = [c for c in cs if re.search(r"\b(Co|GmbH|AB|B\.V\.|Ltd|Inc|Corp|KG|AG|SA|Organisatie|Universit|Institut|Kabushiki|Holding|Technologies)\b|Co\.", c)]
            appl = org[-1] if org else ""
            authors = [appl] if appl else [name_fmt(c.split()[-1], " ".join(c.split()[:-1])) for c in cs if len(c.split()) > 1]
        else:
            m = re.search(r"\(([^()]*)\)\s*청구항", read_text(local)[:300])
            appl = m.group(1).strip() if m else ""
            appl = appl.title() if appl.isupper() else appl
            authors = [appl] if appl else []
    else:
        authors = []
    if not y:
        m = re.match(r"(?:WO|US)(\d{4})", num)
        y = m.group(1) if m else "n.d."
    return dict(kind="patent", authors=authors, year=y, title=title, container=num, volume="", issue="", pages="", doi=None, src="HTML")


def rec_openalex_search(url, local):
    return dict(kind="web", authors=["OpenAlex"], year="n.d.", title="OpenAlex API 검색 결과: " + clean(unquote(url.split("?", 1)[1]))[:90] if "?" in url else "OpenAlex API", container="",
                volume="", issue="", pages="", doi=None, src="HTML")


def resolve(url, local, cache):
    if url in cache["manual"]:
        r = dict(cache["manual"][url])
        if r.get("title") is None and r.get("doi"):  # 수기로 DOI 만 지정 → Crossref 로 서지 해석
            m = api(cache, "crossref", r["doi"])
            r = rec_from_crossref(m, url) if m else r
        r["src"] = "수기"
        return r
    # (b) OpenAlex works/<id>
    h = host_of(url)
    # (a) DOI
    cands = candidate_dois(url, local)
    tried = set()
    guess = None
    for d, conf in cands:
        d = d.rstrip("/")
        if d.lower() in tried:
            continue
        tried.add(d.lower())
        m = api(cache, "crossref", d)
        r = rec_from_crossref(m, url) if m else None
        if not r:
            dc = api(cache, "datacite", d)
            r = rec_from_datacite(dc, url) if dc else None
        if r and r["title"]:
            return r
    # 본문 DOI: 제목 일치할 때만
    guess = page_title_guess(local)
    for d in body_dois(local):
        if d.lower() in tried:
            continue
        tried.add(d.lower())
        m = api(cache, "crossref", d)
        if m and title_match(clean((m.get("title") or [""])[0]), guess):
            return rec_from_crossref(m, url)
    # (b) OpenAlex JSON
    if h in ("api.openalex.org", "openalex.org") and local and Path(local).exists():
        try:
            j = json.loads(read_text(local))
            if j.get("title") or j.get("display_name"):
                return rec_from_openalex(j, url)
        except Exception:
            pass
        if "?" in url:
            return rec_openalex_search(url, local)
    if "patents.google.com" in url:
        return rec_patent(url, local)
    if local and Path(local).exists():
        ext = Path(local).suffix.lower()
        try:
            if ext == ".pdf":
                return rec_pdf(url, local)
            if ext in (".html", ".htm"):
                return rec_html(url, local)
        except Exception as e:
            print("  파싱 실패", url, e)
    return None


# ---------------------------------------------------------------- 서식
def _fmt(url, r):
    """레코드 → 참고문헌 한 줄. 반환 (문자열, 정렬키)"""
    if r is None:
        # 대비책: 기관(도메인). (n.d.). URL 경로의 문서명. URL
        path = unquote(urlparse(url).path).rstrip("/").split("/")[-1] or host_of(url)
        path = re.sub(r"\.(pdf|html?|aspx?|do)$", "", path)
        org = org_of(url)
        return f"{org}. (n.d.). {path}. {url}{TODO}", org
    k = r["kind"]
    auth = r["authors"]
    pre = authors_fmt(auth)
    key = auth[0] if auth else r["title"]
    year = r["year"]
    title = r["title"]
    if not auth:
        pre = title
        key = title
    doi_link = f"https://doi.org/{r['doi']}" if r.get("doi") else None
    link = doi_link or url  # DOI 가 있으면 DOI 만(원본 URL 생략)
    retr = any(s in url for s in RETRIEVED)
    tail = f"Retrieved {RETR_DATE}, from {link}" if retr else link
    head = f"{with_period(pre)} ({year})."
    if not r["title"] and k != "patent":
        return f"{head} {tail}{TODO}", key
    if k in ("journal", "conf", "preprint"):
        t = with_period(title + (" [Conference abstract]" if k == "conf" else ""))
        if k == "conf" and False:
            pass
        c = r["container"]
        vol = r["volume"] + (f"({r['issue']})" if r["issue"] else "")
        body = ", ".join(x for x in (c, vol, r["pages"]) if x)
        mid = f"{t} {with_period(body)}" if body else t
        if not auth:
            head = f"{with_period(title)} ({year})."
            mid = with_period(body) if body else ""
        return f"{head} {mid + ' ' if mid else ''}{tail}".replace("  ", " "), key
    if k == "patent":
        t = title or ""
        mid = (t.rstrip(".") + " ") if t else ""
        no = r["container"]
        flag = "" if t and auth else TODO
        return f"{head} {mid}({no}). {tail}{flag}".replace("  ", " "), key
    # web·report
    if not auth:
        return f"{with_period(title)} ({year}). {tail}", key
    pub = r.get("publisher")  # 수기 항목의 발행처(저자와 다를 때만)
    return f"{head} {with_period(title)} {with_period(pub) + ' ' if pub else ''}{tail}", key


def fmt(url, r):
    s, key = _fmt(url, r)
    if r and r.get("src") in ("HTML", "PDF") and r["kind"] != "patent" and TODO not in s:
        t, a = r["title"], r["authors"]
        # 약한 제목(짧음·미완·점선 목차·숫자뿐)이나 저자 자리에 도메인이 남은 경우는 사람이 확인하도록 표시
        if len(t) < 12 or t.endswith((":", " for", " of", " and", " the", " in", " to")) or "···" in t or re.fullmatch(r"[\w\- ]{0,12}", t)                 or (len(a) == 1 and re.fullmatch(r"[\w\-]+(\.[\w\-]+)+", a[0])):
            s += TODO
    return s, key


def sort_key(item):
    s, key = item
    k = re.sub(r"^[\W_]+", "", key or s)
    g = 0 if re.match(r"[A-Za-z0-9]", k) else (1 if re.match(r"[가-힣]", k) else 2)
    return (g, k.casefold(), s.casefold())


# ---------------------------------------------------------------- 캐시·네트워크 (외부에는 DOI·URL 만 보낸다)
UA = {"User-Agent": "Mozilla/5.0 (compatible; make_references/1.0)"}  # 이메일 등 식별 정보 없음
_FIELDS = ("type", "title", "subtitle", "author", "issued", "published", "published-online", "published-print", "posted", "created",
           "container-title", "volume", "issue", "page", "article-number", "DOI", "institution", "group-title", "publisher")


def load_cache(path):
    c = json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else {}
    for k in ("records", "api", "manual"):  # records: 해석 결과, api: DOI 응답, manual: 수기(최우선)
        c.setdefault(k, {})
    return c


def api(cache, kind, doi):
    key = f"{kind}:{doi.lower()}"
    if key in cache["api"] or not NET:
        return cache["api"].get(key)
    base = {"crossref": "https://api.crossref.org/works/", "datacite": "https://api.datacite.org/dois/"}[kind]
    try:
        time.sleep(0.3)
        j = json.load(urllib.request.urlopen(urllib.request.Request(base + quote(doi, safe="/()"), headers=UA), timeout=25))
        val = j.get("message") or j.get("data", {}).get("attributes")
        if val and "DOI" in val:  # 캐시 용량 절감: 서식에 필요한 필드만 보관
            val = {k: val[k] for k in _FIELDS if k in val}
        elif val:
            val = {k: val[k] for k in ("doi", "creators", "titles", "publisher", "publicationYear") if k in val}
    except Exception as e:  # 404 등: 없는 것도 캐시(재실행 시 재요청 방지)
        val = None
        print("  api 실패", kind, doi, str(e)[:60])
    cache["api"][key] = val
    return val


def fetch_local(url, tmpdir):
    """스냅샷이 없을 때 URL 을 직접 받아 임시 파일로 저장(html/pdf 만). 실패하면 None."""
    if not NET:
        return None
    try:
        time.sleep(0.3)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            data, ct = r.read(8_000_000), r.headers.get("Content-Type", "").lower()
    except Exception as e:
        print("  내려받기 실패", url, str(e)[:60])
        return None
    ext = ".pdf" if "pdf" in ct or urlparse(url).path.lower().endswith(".pdf") else ".html" if "html" in ct else None
    if not ext:
        return None
    p = Path(tmpdir) / (hashlib.md5(url.encode()).hexdigest() + ext)
    p.write_bytes(data)
    return str(p)


# ---------------------------------------------------------------- 입력 파싱·출력 조립
def refs_span(lines):
    """'## 참고문헌' 절의 (시작 줄, 끝 줄[배타]). 없으면 (None, None). 끝 = 다음 '## ' 제목."""
    for i, l in enumerate(lines):
        if REF_H.match(l):
            j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
            return i, j
    return None, None


def parse_src(text):
    """→ [(절 제목, [url...])]. '### ' 가 없으면 제목 '' 한 덩어리."""
    lines = text.splitlines()
    a, b = refs_span(lines)
    if a is not None:
        lines = lines[a + 1:b]
    secs = []
    for l in lines:
        if l.startswith("### "):
            secs.append((l[4:].strip(), []))
            continue
        m = ROW_RE.match(l) or BUL_RE.match(l)
        if m:
            if not secs:
                secs.append(("", []))
            secs[-1][1].append(m.group(1))
    return secs


def render(secs, style):
    """secs: [(제목, [항목 문자열])] → 마크다운 줄. footnote 는 절을 넘어 일련번호 이어짐."""
    out = ["", "❍ **(작성 기준)** 본문 인용 자료를 APA 7판 형식으로 정리함", "- 같은 절 안에서는 제1저자(기관) 알파벳·가나다 순", ""]
    n = 0
    for head, rows in secs:
        if head:
            out += [f"### {head}", ""]
        if style == "table":
            out += ([f"<표> 표 {head}", ""] if head else []) + ["| 참고문헌 |", "| --- |"]
            out += [f"| {s.replace('|', '%7C')} |" for s in rows] + [""]
        else:
            for s in rows:
                n += 1
                out += [f"<sup>{n})</sup> {s}", ""]
    return out


def build(src, out, evidence=None, snapshot_root=None, cache_path=None, style="footnote", no_network=False, redo=False):
    global NET
    NET = not no_network
    src, out = Path(src), Path(out)
    cache_path = Path(cache_path) if cache_path else out.parent / "_refs_cache.json"
    cache = load_cache(cache_path)
    ev = {}
    if evidence:
        root = Path(snapshot_root) if snapshot_root else Path(evidence).parent
        for l in Path(evidence).read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(l)
            except ValueError:
                continue
            if r.get("local") and (root / r["local"]).exists():
                ev.setdefault(unquote(r["source_url"]), str(root / r["local"]))
    secs = parse_src(src.read_text(encoding="utf-8"))
    items, stats = [], {}  # items: (절 번호, url, 레코드, 문장, 정렬키, 중복키)
    with tempfile.TemporaryDirectory() as tmp:
        for si, (head, urls) in enumerate(secs):
            for u in urls:
                if u in cache["records"] and not redo and u not in cache["manual"]:
                    r = cache["records"][u]
                else:
                    try:
                        local = ev.get(unquote(u)) or (None if u in cache["manual"] else fetch_local(u, tmp))
                        r = resolve(u, local, cache)
                    except Exception as e:
                        print("  해석 오류", u, e)
                        r = None
                    cache["records"][u] = r
                src_name = "수기" if u in cache["manual"] else (r or {}).get("src", "미해결")
                stats[src_name] = stats.get(src_name, 0) + 1
                s, key = fmt(u, r)
                doi = ((r or {}).get("doi") or "").lower()
                items.append((si, u, r, s, key, doi or u.lower()))
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    # 같은 DOI(·URL)는 한 항목: 학술 절이 있으면 그쪽, 없으면 먼저 나온 절
    win = {}
    for it in items:
        k = it[5]
        if k not in win or (ACADEMIC.search(secs[it[0]][0]) and not ACADEMIC.search(secs[win[k][0]][0])):
            win[k] = it
    rows = [[] for _ in secs]
    for it in win.values():
        rows[it[0]].append((it[3], it[4]))
    for rs in rows:
        rs.sort(key=sort_key)
    body = render([(secs[i][0], [s for s, _ in rs]) for i, rs in enumerate(rows)], style)
    old = out.read_text(encoding="utf-8").splitlines() if out.exists() else []
    a, b = refs_span(old)
    if a is None:  # 참고문헌 절이 없으면 파일 끝에 새로 붙인다
        res = old + ([""] if old else []) + ["## 참고문헌"] + body
    else:  # 절 제목 줄과 그 밖의 절(용어 해설 등)은 그대로
        res = old[:a + 1] + body + old[b:]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(res).rstrip("\n") + "\n", encoding="utf-8")
    n_todo = sum(TODO in it[3] for it in win.values())
    print("출처별:", stats, "| 항목:", len(win), "| 확인 필요:", n_todo)
    return stats


# ---------------------------------------------------------------- 자체 검증 (--demo)
def demo():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # 샘플 2: 웹 문서, 샘플 3: 한국어 기사 — 원문 스냅샷 html
        (td / "web.html").write_text('<html><head><title>x</title><meta property="og:title" content="Global Outlook 2025 | Example">'
                                     '<meta property="og:site_name" content="Example Corp">'
                                     '<meta property="article:published_time" content="2025-03-01"></head></html>', encoding="utf-8")
        (td / "kr.html").write_text('<html><head><meta property="og:title" content="수소 전해조 이리듐 저감 기술 개발 - 전자신문">'
                                    '<meta property="article:published_time" content="2025-01-01T09:00:00"></head></html>', encoding="utf-8")
        web, kr = "https://www.example.com/report", "https://www.etnews.com/20250101000001"
        dup, bad = "https://example.org/x/10.1234/demo.2024", "https://unreachable.example.net/files/some-report.pdf"
        (td / "evidence.jsonl").write_text("\n".join(json.dumps({"source_url": u, "local": f}) for u, f in ((web, "web.html"), (kr, "kr.html"))), encoding="utf-8")
        # 샘플 1: DOI — Crossref 응답을 캐시에 주입(네트워크 없음)
        cache = {"api": {"crossref:10.1234/demo.2024": {
            "type": "journal-article", "title": ["Iridium thin films"], "DOI": "10.1234/demo.2024", "issued": {"date-parts": [[2024, 5]]},
            "author": [{"family": "Kim", "given": "Hyung-il"}, {"family": "Lee", "given": "Jae"}],
            "container-title": ["Journal of Demo"], "volume": "12", "issue": "3", "page": "45-67"}}}
        (td / "cache.json").write_text(json.dumps(cache), encoding="utf-8")
        (td / "src.md").write_text(f"## 참고문헌\n\n### 1.1 웹 자료\n\n| 라벨 | URL |\n| --- | --- |\n| 보고서 | {web} |\n- {dup}\n- {bad}\n\n"
                                   f"### 1.2 학술 논문\n\n| 논문 | https://doi.org/10.1234/demo.2024 |\n\n### 1.3 언론 기사\n\n- {kr}\n", encoding="utf-8")
        doi = "Kim, H.-I., & Lee, J. (2024). Iridium thin films. Journal of Demo, 12(3), 45-67. https://doi.org/10.1234/demo.2024"
        wb = "Example Corp. (2025). Global Outlook 2025. " + web
        kor = "전자신문. (2025). 수소 전해조 이리듐 저감 기술 개발. " + kr
        for style in ("footnote", "table"):
            (td / "out.md").write_text("# 부록\n\n## 1. 참고문헌\n\n(옛 내용)\n\n## 2. 용어 해설\n\n본문 보존\n", encoding="utf-8")
            build(td / "src.md", td / "out.md", td / "evidence.jsonl", None, td / "cache.json", style, no_network=True)
            t = (td / "out.md").read_text(encoding="utf-8")
            assert "## 2. 용어 해설\n\n본문 보존" in t and "(옛 내용)" not in t and t.startswith("# 부록\n\n## 1. 참고문헌"), "절 보존 실패"
            assert "example.org" not in t, "같은 DOI 중복 제거 실패"
            if style == "footnote":
                ls = [l for l in t.splitlines() if l.startswith("<sup>")]
                assert [l.split(")")[0] for l in ls] == [f"<sup>{i}" for i in range(1, 5)], ls  # 전체 일련번호
                assert ls[0] == f"<sup>1)</sup> {wb}" and ls[2] == f"<sup>3)</sup> {doi}" and ls[3] == f"<sup>4)</sup> {kor}", ls
                assert ls[1].endswith(TODO) and bad in ls[1], ls[1]  # 라틴 정렬 → 실패 항목은 [확인 필요]
            else:
                rows = [l for l in t.splitlines() if l.startswith("| ") and l not in ("| 참고문헌 |", "| --- |")]
                assert len(rows) == 4 and rows[0] == f"| {wb} |" and rows[2] == f"| {doi} |" and rows[3] == f"| {kor} |", rows
                assert rows[1].endswith(TODO + " |") and "<표> 표 1.2 학술 논문" in t
    print("demo 통과: footnote·table 두 형식, 샘플 4건(DOI·웹·한국어 기사·실패) 모두 일치")


def main():
    ap = argparse.ArgumentParser(description="URL 목록 → APA 7판 참고문헌 (부록.md 의 참고문헌 절 교체)")
    ap.add_argument("--src", help="원본 md (| 라벨 | URL | 표 또는 - URL 줄)")
    ap.add_argument("--out", help="결과 부록.md (있으면 참고문헌 절만 교체, 없으면 새로 만듦)")
    ap.add_argument("--evidence", help="evidence.jsonl (source_url→local 스냅샷 대장). 없으면 URL 만으로 해석")
    ap.add_argument("--snapshot-root", help="evidence 의 local 상대경로 기준 폴더(기본: evidence 파일 폴더)")
    ap.add_argument("--cache", help="해석 캐시 json (기본: <out 폴더>/_refs_cache.json). 'manual' 항목이 최우선")
    ap.add_argument("--style", choices=("footnote", "table"), default="footnote")
    ap.add_argument("--no-network", action="store_true", help="외부 요청 없이 캐시·스냅샷만 사용")
    ap.add_argument("--redo", action="store_true", help="해석 캐시 무시(API 응답 캐시는 재사용)")
    ap.add_argument("--demo", action="store_true", help="내장 샘플로 자체 검증 후 종료")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if not (a.src and a.out):
        ap.error("--src 와 --out 이 필요합니다 (--demo 제외)")
    build(a.src, a.out, a.evidence, a.snapshot_root, a.cache, a.style, a.no_network, a.redo)


if __name__ == "__main__":
    main()
