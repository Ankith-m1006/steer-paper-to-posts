"""Ingest: a research paper as a PDF file or a link, split into located chunks.

Every chunk keeps where it came from ("p. 4" for a PDF page, "Results, para 3" for a
full-text link), so each claim extracted later can be traced back to that spot.
"""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

UA = {"User-Agent": "steer-paper-pipeline/1.0 (research to social content)"}
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"


@dataclass
class Paper:
    title: str
    citation: str          # short form for slides: "Wilding et al., Diabetes Obes Metab 2022"
    url: str
    license: str
    chunks: list = field(default_factory=list)   # [{"loc": "p. 3", "text": "..."}]

    def full_text(self):
        return "\n\n".join(f"[{c['loc']}]\n{c['text']}" for c in self.chunks)


def _clean(text):
    text = text.replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"-\n(?=[a-z])", "", text)          # words split across lines
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _get(url, tries=4):
    import time
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
        except OSError:          # DNS hiccups and dropped connections: retry with a short backoff
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def _epmc_meta(query):
    d = json.loads(_get(f"{EPMC}/search?format=json&resultType=core&pageSize=1&query=" + urllib.parse.quote(query)))
    hits = d["resultList"]["result"]
    if not hits:
        raise ValueError(f"no Europe PMC record for {query}")
    return hits[0]


def _short_citation(meta):
    first = (meta.get("authorList", {}).get("author") or [{}])[0].get("lastName", "")
    journal = meta.get("journalInfo", {}).get("journal", {}).get("isoabbreviation") or meta.get("journalTitle", "")
    return f"{first} et al., {journal} {meta.get('pubYear', '')}".strip()


def from_pdf(path, query=None):
    """A PDF on disk. `query` (a DOI or title) fills in the citation from Europe PMC when given."""
    import pypdf
    reader = pypdf.PdfReader(path)
    chunks = [{"loc": f"p. {i + 1}", "text": _clean(page.extract_text() or "")} for i, page in enumerate(reader.pages)]
    chunks = [c for c in chunks if len(c["text"]) > 80]
    title, citation, url, lic = chunks[0]["text"].split("\n")[1][:200] if chunks else path, path, path, "unknown"
    if query:
        meta = _epmc_meta(query)
        title, citation, lic = meta["title"], _short_citation(meta), meta.get("license", "unknown")
        url = f"https://doi.org/{meta['doi']}" if meta.get("doi") else url
    return Paper(title=title, citation=citation, url=url, license=lic, chunks=chunks)


def _text(el):
    return _clean(" ".join("".join(el.itertext()).split()))


def from_link(link):
    """A PMC id, a DOI or a doi.org / europepmc / pmc link: full text through the Europe PMC API (open access only)."""
    m = re.search(r"PMC\d+", link, re.I)
    if m:
        meta = _epmc_meta(f"PMCID:{m.group(0).upper()}")
    else:
        doi = re.search(r"10\.\d{4,9}/\S+", link)
        if not doi:
            raise ValueError("give a PMC id or a DOI link")
        meta = _epmc_meta(f'DOI:"{doi.group(0).rstrip(".")}"')
    pmcid = meta.get("pmcid")
    if not pmcid or meta.get("isOpenAccess") != "Y":
        raise ValueError("this paper has no open-access full text; use the PDF instead")
    root = ET.fromstring(_get(f"{EPMC}/{pmcid}/fullTextXML"))
    chunks = []
    abstract = root.find(".//abstract")
    if abstract is not None:
        chunks.append({"loc": "Abstract", "text": _text(abstract)})
    for sec in root.findall(".//body/sec"):
        heading = _text(sec.find("title")) if sec.find("title") is not None else "Section"
        if heading.isupper():
            heading = heading.capitalize()       # "IS THE CONCERN JUSTIFIED?" -> "Is the concern justified?"
        heading = re.sub(r"^\d+(\.\d+)*\s*", "", heading)
        for i, p in enumerate(sec.iter("p"), 1):
            t = _text(p)
            if len(t) > 60:
                chunks.append({"loc": f"{heading[:40]}, para {i}", "text": t})
    url = f"https://doi.org/{meta['doi']}" if meta.get("doi") else f"https://europepmc.org/article/PMC/{pmcid}"
    return Paper(title=meta["title"], citation=_short_citation(meta), url=url,
                 license=meta.get("license", "unknown"), chunks=chunks)


def load(source, query=None):
    return from_pdf(source, query) if source.lower().endswith(".pdf") else from_link(source)
