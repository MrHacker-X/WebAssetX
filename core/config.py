#!/usr/bin/env python3
"""WebAssetX configuration constants (built-in, self-contained)."""
from __future__ import annotations

_CONFIGS: dict = {
    "asset_types.json": {
        "image_extensions": [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
            ".avif",
            ".bmp",
            ".ico",
            ".tiff",
            ".tif"
        ],
        "svg_extensions": [
            ".svg"
        ],
        "font_extensions": [
            ".woff",
            ".woff2",
            ".ttf",
            ".otf",
            ".eot"
        ],
        "css_extensions": [
            ".css"
        ],
        "js_extensions": [
            ".js",
            ".mjs"
        ],
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 WebAssetX/1.0",
        "max_css_fetch": 15,
        "default_output_dir": "extracted_assets",
        "default_workers": 6,
        "default_timeout": 15
    },
    "defaults.json": {
        "tool": "webassetx",
        "name": "WebAssetX",
        "subtitle": "Website Asset Extractor",
        "version": "1.0.0",
        "description": "Target public website URL",
        "homepage": "https://github.com/MrHacker-X/webassetx",
        "author": "MrHacker-X",
        "email": "contact@vritrasec.com",
        "website": "https://vritrasec.com",
        "network": "https://link.vritrasec.com",
        "about_overview": (
            "WebAssetX is a fast, standalone website asset extractor: point it at any public URL and it discovers every image, SVG, font, CSS and JavaScript file the page references, then downloads them into clean, categorized folders. The entire pipeline runs locally with configurable concurrency and timeouts - no accounts, no API keys, no telemetry."
        ),
        "about_features": [
            "Asset discovery from HTML, srcset and CSS references",
            "Category-aware downloads: images, SVGs, fonts, CSS, JS",
            "Concurrent fetching with configurable workers & timeout",
            "Collision-safe file naming and organized output folders",
            "Dual interface: interactive menu or direct CLI flags",
            "Rich console tables summarizing every extraction run",
        ]
    }
}


def load_tool_data(filename: str) -> dict:
    """Return the built-in configuration table stored under `filename`."""
    return dict(_CONFIGS.get(filename, {}))


def load_defaults() -> dict:
    """Return the tool identity / defaults configuration."""
    return dict(_CONFIGS.get("defaults.json", {}))
