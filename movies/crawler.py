from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class CrawledMovie:
    title: str
    year: int | None
    detail_url: str
    poster_url: str


_YEAR_RE = re.compile(r"(19\\d{2}|20\\d{2})")


def _clean_title(text: str) -> str:
    text = re.sub(r"\\s+", " ", (text or "").strip())
    text = re.sub(r"\\(\\s*(19\\d{2}|20\\d{2})\\s*\\)$", "", text).strip()
    return text


def _guess_year(text: str) -> int | None:
    m = _YEAR_RE.search(text or "")
    if not m:
        return None
    year = int(m.group(1))
    return year if 1900 <= year <= 2100 else None


def crawl_movies(url: str, limit: int = 50, timeout_s: int = 15) -> list[CrawledMovie]:
    """
    通用"简易爬虫"：从 HTML 中抽取可能的电影条目（链接文本/标题属性），并做简单清洗去重。
    不同站点结构差异很大，效果取决于页面 HTML（建议使用列表页/搜索结果页）。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    resp = requests.get(url, timeout=timeout_s, headers=headers, verify=False)
    resp.raise_for_status()
    
    # 自动检测编码
    resp.encoding = resp.apparent_encoding
    
    soup = BeautifulSoup(resp.text, "lxml")

    candidates: list[tuple[str, str, str]] = []  # (text, href, poster)
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        if not href or href.startswith("#"):
            continue

        text = a.get_text(" ", strip=True) or a.get("title") or ""
        if not text:
            continue
        if len(text) < 2 or len(text) > 120:
            continue
        lowered = text.lower()
        if any(x in lowered for x in ("login", "sign", "register", "privacy", "cookie", "help")):
            continue

        poster = ""
        img = a.find("img")
        if img and img.get("src"):
            poster = str(img.get("src"))
        candidates.append((text, href, poster))

    def normalize(items: Iterable[tuple[str, str, str]]) -> list[CrawledMovie]:
        out: list[CrawledMovie] = []
        seen: set[tuple[str, int | None, str]] = set()
        for text, href, poster in items:
            abs_url = urljoin(url, href)
            year = _guess_year(text)
            title = _clean_title(text)
            if not title:
                continue
            key = (title.lower(), year, abs_url)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                CrawledMovie(
                    title=title,
                    year=year,
                    detail_url=abs_url,
                    poster_url=urljoin(url, poster) if poster else "",
                )
            )
            if len(out) >= limit:
                break
        return out

    preferred = [c for c in candidates if _guess_year(c[0]) or len(c[0]) >= 6]
    movies = normalize(preferred)
    if len(movies) < limit:
        movies2 = normalize(candidates)
        merged: list[CrawledMovie] = []
        seen = set()
        for m in movies + movies2:
            k = (m.title.lower(), m.year, m.detail_url)
            if k in seen:
                continue
            seen.add(k)
            merged.append(m)
            if len(merged) >= limit:
                break
        movies = merged

    return movies

