#!/usr/bin/env python3
"""WebAssetX core logic."""
from __future__ import annotations

from .config import load_tool_data


import argparse
import hashlib
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .utils import (
    console,
    format_bytes,
    make_table,
    print_error,
    print_info,
    print_success,
    print_tool_header,
    print_warning,
    prompt_confirm,
    prompt_menu,
    prompt_text,
    safe_filename,
    unique_path,
)

ALL_CATEGORIES = ("images", "svgs", "fonts", "css", "js")

def _load_tool_data(filename: str) -> dict:
    """Thin alias: load this tool's own config via core/config.py."""
    return load_tool_data(filename)


@dataclass
class DiscoveredAsset:
    category: str  # images | svgs | fonts | css | js
    url: str
    inline_content: Optional[bytes] = None
    suggested_name: Optional[str] = None


@dataclass
class AssetDownloadRecord:
    category: str
    source: str
    status: str  # downloaded | skipped | failed
    saved_path: Optional[str] = None
    size_bytes: int = 0
    reason: str = ""


@dataclass
class ExtractionSummary:
    target_url: str
    output_dir: Path
    selected_categories: List[str]
    discovered_by_category: Dict[str, int] = field(default_factory=dict)
    downloaded_by_category: Dict[str, int] = field(default_factory=dict)
    skipped_by_category: Dict[str, int] = field(default_factory=dict)
    failed_by_category: Dict[str, int] = field(default_factory=dict)
    records: List[AssetDownloadRecord] = field(default_factory=list)
    total_bytes: int = 0

    @property
    def total_discovered(self) -> int:
        return sum(self.discovered_by_category.values())

    @property
    def total_downloaded(self) -> int:
        return sum(self.downloaded_by_category.values())

    @property
    def total_skipped(self) -> int:
        return sum(self.skipped_by_category.values())

    @property
    def total_failed(self) -> int:
        return sum(self.failed_by_category.values())


TOOL_DATA = _load_tool_data("asset_types.json")
IMAGE_EXTENSIONS: Set[str] = set(TOOL_DATA.get("image_extensions", []))
FONT_EXTENSIONS: Set[str] = set(TOOL_DATA.get("font_extensions", []))
SVG_EXTENSIONS: Set[str] = set(TOOL_DATA.get("svg_extensions", []))
CSS_EXTENSIONS: Set[str] = set(TOOL_DATA.get("css_extensions", []))
JS_EXTENSIONS: Set[str] = set(TOOL_DATA.get("js_extensions", []))

CSS_URL_PATTERN = re.compile(r"""url\(\s*['"]?([^'"\)\s]+)['"]?\s*\)""", re.IGNORECASE)
CSS_IMPORT_PATTERN = re.compile(
    r"""@import\s+(?:url\()?['"]?([^'"\)\s;]+)['"]?\)?""", re.IGNORECASE
)

DEFAULT_HEADERS = {
    "User-Agent": TOOL_DATA.get("user_agent", "WebAssetX/1.0"),
    "Accept": "*/*",
}
DEFAULT_OUTPUT_DIR = TOOL_DATA.get("default_output_dir", "extracted_assets")
DEFAULT_WORKERS = int(TOOL_DATA.get("default_workers", 6))
DEFAULT_TIMEOUT = int(TOOL_DATA.get("default_timeout", 15))
MAX_CSS_FETCH = int(TOOL_DATA.get("max_css_fetch", 15))


def normalize_url(base_url: str, raw_url: str) -> Optional[str]:
    """Resolve relative URLs against base_url and strip fragments."""
    if not raw_url:
        return None
    raw_url = raw_url.strip()
    if raw_url.startswith(("data:", "javascript:", "mailto:", "tel:", "about:", "#")):
        return None
    joined = urljoin(base_url, raw_url)
    parsed = urlparse(joined)
    if parsed.scheme not in ("http", "https"):
        return None
    cleaned = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, "")
    )
    return cleaned


def _get_extension(url: str) -> str:
    path = unquote(urlparse(url).path)
    return os.path.splitext(path)[1].lower()


def classify_url_by_extension(url: str, fallback: Optional[str] = None) -> Optional[str]:
    ext = _get_extension(url)
    if ext in SVG_EXTENSIONS:
        return "svgs"
    if ext in FONT_EXTENSIONS:
        return "fonts"
    if ext in IMAGE_EXTENSIONS:
        return "images"
    if ext in CSS_EXTENSIONS:
        return "css"
    if ext in JS_EXTENSIONS:
        return "js"
    return fallback


def parse_srcset(srcset_value: str) -> List[str]:
    """Extract candidate URLs from an HTML srcset attribute."""
    urls: List[str] = []
    for part in srcset_value.split(","):
        tokens = part.strip().split()
        if tokens:
            urls.append(tokens[0])
    return urls


def extract_css_references(css_text: str, css_base_url: str) -> List[DiscoveredAsset]:
    """Extract fonts, SVGs, images, and @import stylesheets from CSS text."""
    discovered: List[DiscoveredAsset] = []

    for match in CSS_IMPORT_PATTERN.finditer(css_text):
        ref = normalize_url(css_base_url, match.group(1))
        if ref:
            discovered.append(DiscoveredAsset(category="css", url=ref))

    for match in CSS_URL_PATTERN.finditer(css_text):
        ref = normalize_url(css_base_url, match.group(1))
        if not ref:
            continue
        cat = classify_url_by_extension(ref)
        if cat in ("fonts", "svgs", "images", "css"):
            discovered.append(DiscoveredAsset(category=cat, url=ref))
    return discovered


def discover_assets_from_html(
    html_text: str,
    base_url: str,
    session: Optional[requests.Session] = None,
    fetch_external_css: bool = True,
    timeout: int = 10,
) -> List[DiscoveredAsset]:
    """Discover images, SVGs, fonts, CSS, and JS assets from an HTML document."""
    soup = BeautifulSoup(html_text, "html.parser")
    assets: List[DiscoveredAsset] = []
    external_css_urls: List[str] = []

    # 1. Images & SVGs from <img>, <picture><source>, <input type="image">, <meta property="og:image">
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            val = img.get(attr)
            if val:
                norm = normalize_url(base_url, str(val))
                if norm:
                    cat = "svgs" if _get_extension(norm) == ".svg" else "images"
                    assets.append(DiscoveredAsset(category=cat, url=norm))
        srcset = img.get("srcset") or img.get("data-srcset")
        if srcset:
            for candidate in parse_srcset(str(srcset)):
                norm = normalize_url(base_url, candidate)
                if norm:
                    cat = "svgs" if _get_extension(norm) == ".svg" else "images"
                    assets.append(DiscoveredAsset(category=cat, url=norm))

    for source in soup.find_all("source"):
        for attr in ("src", "srcset"):
            val = source.get(attr)
            if val:
                for candidate in parse_srcset(str(val)):
                    norm = normalize_url(base_url, candidate)
                    if norm:
                        cat = classify_url_by_extension(norm, fallback="images")
                        if cat:
                            assets.append(DiscoveredAsset(category=cat, url=norm))

    # OpenGraph / Twitter images
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        content = meta.get("content")
        if content and prop in ("og:image", "twitter:image", "msapplication-tileimage"):
            norm = normalize_url(base_url, str(content))
            if norm:
                cat = "svgs" if _get_extension(norm) == ".svg" else "images"
                assets.append(DiscoveredAsset(category=cat, url=norm))

    # 2. Inline <svg> elements
    for idx, svg_tag in enumerate(soup.find_all("svg"), start=1):
        svg_str = str(svg_tag)
        if "xmlns=" not in svg_str:
            svg_str = svg_str.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
        svg_id = svg_tag.get("id") or svg_tag.get("aria-label") or f"inline_svg_{idx}"
        name = f"{safe_filename(str(svg_id))}.svg"
        assets.append(
            DiscoveredAsset(
                category="svgs",
                url=f"{base_url}#inline-svg-{idx}",
                inline_content=svg_str.encode("utf-8"),
                suggested_name=name,
            )
        )

    # <object> / <embed> / <use> referencing SVGs or images
    for tag in soup.find_all(["object", "embed", "use"]):
        ref = tag.get("data") or tag.get("src") or tag.get("href") or tag.get("xlink:href")
        if ref:
            norm = normalize_url(base_url, str(ref))
            if norm:
                cat = classify_url_by_extension(norm)
                if cat:
                    assets.append(DiscoveredAsset(category=cat, url=norm))

    # 3. <link> tags (stylesheets, preload fonts/images/scripts, icons)
    for link in soup.find_all("link"):
        href = link.get("href")
        if not href:
            continue
        norm = normalize_url(base_url, str(href))
        if not norm:
            continue
        rels = [r.lower() for r in (link.get("rel") or [])] if isinstance(link.get("rel"), list) else [str(link.get("rel") or "").lower()]
        as_attr = str(link.get("as") or "").lower()
        type_attr = str(link.get("type") or "").lower()

        if "stylesheet" in rels or type_attr == "text/css" or _get_extension(norm) == ".css":
            assets.append(DiscoveredAsset(category="css", url=norm))
            external_css_urls.append(norm)
        elif as_attr == "font" or type_attr.startswith("font/") or _get_extension(norm) in FONT_EXTENSIONS:
            assets.append(DiscoveredAsset(category="fonts", url=norm))
        elif any("icon" in r for r in rels):
            cat = "svgs" if _get_extension(norm) == ".svg" else "images"
            assets.append(DiscoveredAsset(category=cat, url=norm))
        elif as_attr == "script" or _get_extension(norm) in JS_EXTENSIONS:
            assets.append(DiscoveredAsset(category="js", url=norm))
        elif as_attr == "image":
            cat = "svgs" if _get_extension(norm) == ".svg" else "images"
            assets.append(DiscoveredAsset(category=cat, url=norm))
        else:
            cat = classify_url_by_extension(norm)
            if cat:
                assets.append(DiscoveredAsset(category=cat, url=norm))

    # 4. <script src="..."> tags
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            norm = normalize_url(base_url, str(src))
            if norm:
                assets.append(DiscoveredAsset(category="js", url=norm))

    # 5. Direct anchor links pointing to fonts, images, SVGs, CSS, or JS
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if href:
            norm = normalize_url(base_url, str(href))
            if norm:
                cat = classify_url_by_extension(norm)
                if cat:
                    assets.append(DiscoveredAsset(category=cat, url=norm))

    # 6. Inline <style> blocks and style="..." attributes
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            assets.extend(extract_css_references(style_tag.string, base_url))

    for styled_tag in soup.find_all(style=True):
        style_val = styled_tag.get("style")
        if style_val:
            assets.extend(extract_css_references(str(style_val), base_url))

    # 7. Optionally inspect discovered external stylesheets for fonts, SVGs, and background images
    if fetch_external_css and external_css_urls:
        sess = session or requests.Session()
        seen_css: Set[str] = set()
        for css_url in external_css_urls[:MAX_CSS_FETCH]:
            if css_url in seen_css:
                continue
            seen_css.add(css_url)
            try:
                resp = sess.get(css_url, headers=DEFAULT_HEADERS, timeout=timeout)
                if resp.ok and "text" in resp.headers.get("Content-Type", "text/css"):
                    assets.extend(extract_css_references(resp.text, css_url))
            except requests.RequestException:
                pass

    return assets


def _derive_asset_filename(asset: DiscoveredAsset, content_type: str = "") -> str:
    if asset.suggested_name:
        return safe_filename(asset.suggested_name)
    parsed = urlparse(asset.url)
    basename = os.path.basename(unquote(parsed.path))
    if not basename or basename == "/":
        basename = f"asset_{hashlib.md5(asset.url.encode('utf-8')).hexdigest()[:8]}"

    name, ext = os.path.splitext(basename)
    name = safe_filename(name, default="asset")
    ext = ext.lower()

    if not ext:
        # Infer extension from category or Content-Type
        ct = content_type.lower()
        if asset.category == "svgs" or "svg" in ct:
            ext = ".svg"
        elif asset.category == "css" or "css" in ct:
            ext = ".css"
        elif asset.category == "js" or "javascript" in ct:
            ext = ".js"
        elif asset.category == "fonts":
            if "woff2" in ct:
                ext = ".woff2"
            elif "woff" in ct:
                ext = ".woff"
            elif "ttf" in ct:
                ext = ".ttf"
            elif "otf" in ct:
                ext = ".otf"
            else:
                ext = ".woff2"
        elif asset.category == "images":
            if "png" in ct:
                ext = ".png"
            elif "webp" in ct:
                ext = ".webp"
            elif "gif" in ct:
                ext = ".gif"
            elif "avif" in ct:
                ext = ".avif"
            else:
                ext = ".jpg"

    return f"{name}{ext}"


def extract_website_assets(
    url: str,
    output_dir: Path | str = "extracted_assets",
    categories: Optional[Iterable[str]] = None,
    max_workers: int = 6,
    timeout: int = 15,
    session: Optional[requests.Session] = None,
    show_progress: bool = True,
) -> ExtractionSummary:
    """Discover and download website assets into organized category subfolders."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    selected = [c.lower() for c in (categories or ALL_CATEGORIES) if c.lower() in ALL_CATEGORIES]
    if not selected:
        selected = list(ALL_CATEGORIES)

    out_path = Path(output_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    summary = ExtractionSummary(
        target_url=url,
        output_dir=out_path,
        selected_categories=selected,
        discovered_by_category={cat: 0 for cat in selected},
        downloaded_by_category={cat: 0 for cat in selected},
        skipped_by_category={cat: 0 for cat in selected},
        failed_by_category={cat: 0 for cat in selected},
    )

    sess = session or requests.Session()
    resp = sess.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    resp.raise_for_status()
    final_base_url = resp.url or url

    all_discovered = discover_assets_from_html(
        resp.text,
        base_url=final_base_url,
        session=sess,
        fetch_external_css=True,
        timeout=timeout,
    )

    # Filter to selected categories
    filtered_assets = [a for a in all_discovered if a.category in selected]

    # Create organized category folders
    for cat in selected:
        (out_path / cat).mkdir(parents=True, exist_ok=True)

    # Count total discovered per category and deduplicate URLs
    seen_urls: Set[str] = set()
    seen_hashes: Set[str] = set()
    unique_queue: List[DiscoveredAsset] = []

    for asset in filtered_assets:
        summary.discovered_by_category[asset.category] = (
            summary.discovered_by_category.get(asset.category, 0) + 1
        )
        if asset.url in seen_urls:
            summary.skipped_by_category[asset.category] += 1
            summary.records.append(
                AssetDownloadRecord(
                    category=asset.category,
                    source=asset.url,
                    status="skipped",
                    reason="Duplicate URL",
                )
            )
            continue
        seen_urls.add(asset.url)
        unique_queue.append(asset)

    def _fetch_single(asset: DiscoveredAsset) -> Tuple[DiscoveredAsset, Optional[bytes], str, str]:
        """Return (asset, content_bytes, content_type, error_message)."""
        if asset.inline_content is not None:
            return (asset, asset.inline_content, "image/svg+xml", "")
        try:
            r = sess.get(asset.url, headers=DEFAULT_HEADERS, timeout=timeout)
            if not r.ok:
                return (asset, None, "", f"HTTP {r.status_code}")
            return (asset, r.content, r.headers.get("Content-Type", ""), "")
        except Exception as exc:
            return (asset, None, "", str(exc))

    results: List[Tuple[DiscoveredAsset, Optional[bytes], str, str]] = []
    if unique_queue:
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                console=console,
                transient=True,
            ) as progress:
                task_id = progress.add_task("Downloading discovered assets...", total=len(unique_queue))
                with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
                    futures = {pool.submit(_fetch_single, item): item for item in unique_queue}
                    for fut in as_completed(futures):
                        results.append(fut.result())
                        progress.advance(task_id)
        else:
            with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
                for res in pool.map(_fetch_single, unique_queue):
                    results.append(res)

    for asset, content, content_type, err in results:
        if content is None or err:
            summary.failed_by_category[asset.category] += 1
            summary.records.append(
                AssetDownloadRecord(
                    category=asset.category,
                    source=asset.url,
                    status="failed",
                    reason=err or "Empty response",
                )
            )
            continue

        content_hash = hashlib.sha256(content).hexdigest()
        if content_hash in seen_hashes:
            summary.skipped_by_category[asset.category] += 1
            summary.records.append(
                AssetDownloadRecord(
                    category=asset.category,
                    source=asset.url,
                    status="skipped",
                    reason="Duplicate content (SHA-256 match)",
                )
            )
            continue
        seen_hashes.add(content_hash)

        filename = _derive_asset_filename(asset, content_type)
        dest_file = unique_path(out_path / asset.category / filename)
        dest_file.write_bytes(content)

        summary.downloaded_by_category[asset.category] += 1
        summary.total_bytes += len(content)
        summary.records.append(
            AssetDownloadRecord(
                category=asset.category,
                source=asset.url,
                status="downloaded",
                saved_path=str(dest_file),
                size_bytes=len(content),
            )
        )

    return summary


def display_extraction_summary(summary: ExtractionSummary) -> None:
    """Render a Rich table with category breakdown and overall totals."""
    rows = []
    for cat in summary.selected_categories:
        rows.append(
            (
                cat.upper(),
                summary.discovered_by_category.get(cat, 0),
                f"[green]{summary.downloaded_by_category.get(cat, 0)}[/green]",
                f"[yellow]{summary.skipped_by_category.get(cat, 0)}[/yellow]",
                f"[red]{summary.failed_by_category.get(cat, 0)}[/red]",
                str(summary.output_dir / cat),
            )
        )
    rows.append(
        (
            "[bold]TOTAL[/bold]",
            f"[bold]{summary.total_discovered}[/bold]",
            f"[bold green]{summary.total_downloaded}[/bold green]",
            f"[bold yellow]{summary.total_skipped}[/bold yellow]",
            f"[bold red]{summary.total_failed}[/bold red]",
            f"[bold]{format_bytes(summary.total_bytes)}[/bold]",
        )
    )

    table = make_table(
        title=f"WebAssetX Extraction Summary - {summary.target_url}",
        columns=[
            ("Category", "bold cyan"),
            ("Discovered", "white"),
            ("Downloaded", "green"),
            ("Skipped (Dup)", "yellow"),
            ("Failed", "red"),
            ("Output / Size", "dim white"),
        ],
        rows=rows,
    )
    console.print()
    console.print(table)
