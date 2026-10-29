"""Tingkat kepercayaan sumber untuk Nova (dipakai cek_ide.py dan Studio).

tier 1 = sumber primer: jurnal, universitas, lembaga pemerintah/riset, rilis resmi
tier 2 = media sains/teknologi/berita besar yang punya redaksi
tier 3 = petunjuk saja (blog, media sosial, Wikipedia, agregator) — tidak boleh jadi satu-satunya bukti
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

TIER1_SUFFIX = (".edu", ".ac.id", ".ac.uk", ".ac.jp", ".edu.au", ".edu.sg", ".gov", ".go.id", ".gov.uk", ".europa.eu", ".int", ".mil")
TIER1 = {
    "nature.com", "science.org", "sciencemag.org", "cell.com", "thelancet.com", "nejm.org", "pnas.org", "sciencedirect.com",
    "springer.com", "link.springer.com", "wiley.com", "onlinelibrary.wiley.com", "acs.org", "pubs.acs.org", "rsc.org", "iop.org",
    "ieee.org", "ieeexplore.ieee.org", "acm.org", "dl.acm.org", "arxiv.org", "biorxiv.org", "medrxiv.org", "plos.org", "frontiersin.org",
    "mdpi.com", "nih.gov", "ncbi.nlm.nih.gov", "who.int", "nasa.gov", "esa.int", "cern.ch", "mpg.de", "fraunhofer.de", "a-star.edu.sg",
    "kaist.ac.kr", "ethz.ch", "epfl.ch", "ox.ac.uk", "cam.ac.uk", "eurekalert.org", "brin.go.id", "fda.gov",
}
TIER2 = {
    "spectrum.ieee.org", "newscientist.com", "technologyreview.com", "scientificamerican.com", "wired.com", "theverge.com",
    "engadget.com", "techcrunch.com", "arstechnica.com", "bbc.com", "bbc.co.uk", "reuters.com", "apnews.com", "theguardian.com",
    "nytimes.com", "washingtonpost.com", "cnn.com", "cnbc.com", "bloomberg.com", "ft.com", "economist.com", "popsci.com",
    "sciencedaily.com", "phys.org", "newatlas.com", "smithsonianmag.com", "nationalgeographic.com", "livescience.com", "space.com",
    "zdnet.com", "cnet.com", "gizmodo.com", "fastcompany.com", "forbes.com", "time.com", "axios.com", "statnews.com",
    "kompas.com", "tekno.kompas.com", "kompas.id", "detik.com", "inet.detik.com", "cnnindonesia.com", "tempo.co", "antaranews.com",
    "liputan6.com", "katadata.co.id", "nikkei.com", "asia.nikkei.com", "scmp.com", "straitstimes.com", "theconversation.com",
    "interestingengineering.com", "designboom.com", "dezeen.com", "electrek.co", "notebookcheck.net", "tomshardware.com",
}
TIER3 = {"wikipedia.org", "medium.com", "blogspot.com", "wordpress.com", "substack.com", "youtube.com", "youtu.be", "tiktok.com",
         "facebook.com", "instagram.com", "x.com", "twitter.com", "reddit.com", "quora.com", "linkedin.com", "pinterest.com",
         "brainly.co.id", "kaskus.co.id", "kumparan.com", "idntimes.com", "boredpanda.com", "dailymail.co.uk", "thesun.co.uk", "msn.com"}


def domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return ""
    host = re.sub(r"^www\d?\.", "", host.split(":")[0])
    return host


def root(host: str) -> str:
    """kompas.com untuk tekno.kompas.com; cam.ac.uk untuk www.cam.ac.uk."""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("ac", "co", "go", "or", "edu", "gov", "com", "net") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def tier(url: str, jenis: str = "") -> int:
    """jenis 'resmi' = situs resmi perusahaan/organisasi pembuat teknologinya (Nova yang menandai)."""
    h = domain(url)
    if not h:
        return 3
    for d in (h, root(h)):
        if d in TIER3 or any(d.endswith("." + t) for t in TIER3):
            return 3
    if h in TIER1 or root(h) in TIER1 or h.endswith(TIER1_SUFFIX) or any(h.endswith("." + t) for t in TIER1):
        return 1
    if jenis in ("resmi", "rilis_resmi", "jurnal"):
        return 1
    if h in TIER2 or root(h) in TIER2:
        return 2
    return 2 if jenis in ("media",) else 3
