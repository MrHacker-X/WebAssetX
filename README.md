<div align="center">

# ⃤ W E B A S S E T X ⃤

### *Extract every image, video, font, asset from any website - one command.*

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![OS](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Stars](https://img.shields.io/github/stars/MrHacker-X/webassetx?style=flat-square&color=orange)
![Forks](https://img.shields.io/github/forks/MrHacker-X/webassetx?style=flat-square&color=cyan)

</div>

---

## 📋 Table of Contents

- [🎯 Why WebAssetX?](#-why-webassetx)
- [🧭 What It Does](#-what-it-does)
- [🚀 Quick Start](#-quick-start)
- [🖼️ Preview](#-preview)
- [📦 Installation](#-installation)
- [✨ Features](#-features)
- [⌨️ Usage](#%EF%B8%8F-usage)
- [⚙️ Configuration](#%EF%B8%8F-configuration)
- [🧰 Tech Stack](#-tech-stack)
- [⚠️ Disclaimer](#%EF%B8%8F-disclaimer)
- [🤝 Contributing](#-contributing)
- [📜 License](#-license)
- [👨‍💻 Developer](#-developer)

---

## 🎯 Why WebAssetX?

> Saving images from a website shouldn't mean opening DevTools, clicking through the Network tab, and downloading files one by one. **WebAssetX does it in two commands**: point it at a URL and it discovers, categorizes, and downloads every asset the page references - images, favicon, icons, fonts - into organized folders.
>
> **It's built to be a zero-setup, single-purpose tool.** No accounts, no API keys, no configuration needed: clone it, install two dependencies, and extract.

---

## 🧭 What It Does

| # | Task | What it gives you |
|---|------|-------------------|
| 1️⃣ | Extract assets from a URL | Every `<img>`, `<video>`, `srcset`, CSS-referenced asset on the page, classified by type |
| 2️⃣ | Download into organized folders | Assets saved into category folders (`extracted_assets/images`, `/fonts`, …) |
| 3️⃣ | Interactive + direct CLI | Same extraction through a friendly menu or a flag-driven command |

---

## 🚀 Quick Start

```bash
git clone https://github.com/MrHacker-X/webassetx.git
cd webassetx
pip install -r requirements.txt
python webassetx.py                 # interactive menu
```

---

## 🖼️ Preview

<div align="center">

![WebAssetX Preview](https://i.ibb.co/XZpYXZ7s/webassetx.png)

</div>

---

## 📦 Installation

```bash
# 1. clone
git clone https://github.com/MrHacker-X/webassetx.git
cd webassetx

# 2. install dependencies
pip install -r requirements.txt

# 3. run
python webassetx.py
```

### Supported Systems

| OS | Status | Notes |
|----|--------|-------|
| 🐧 Linux | ✅ Fully supported | Any distro with Python 3.8+ |
| 🪟 Windows | ✅ Fully supported | Python from python.org, then the steps above |
| 🍎 macOS | ✅ Fully supported | `brew install python`, then the steps above |
| 📱 Termux (Android) | ✅ Fully supported | `pkg install python`, then the steps above |

> 💡 WebAssetX works entirely locally - pages are fetched, parsed, and their assets saved with no data leaving your machine.

---

## ✨ Features

| | Feature | Description |
|---|---------|-------------|
| 🎨 | **Multi-category extraction** | Images, videos, fonts, favicons & other assets - classified by extension and content type |
| ➕ | **`srcset` + CSS aware** | Picks up responsive `srcset` URLs and background-image/font assets referenced from stylesheets |
| 🗂️ | **Clean folder structure** | Assets land in per-category folders with collision-safe filenames |
| 📊 | **Rich summary tables** | Per-category counts and bytes downloaded, rendered as a colored Rich table |
| 🎛️ | **Two modes** | A guided interactive menu or a fully flag-driven direct CLI |
| 📁 | **Configurable output** | Choose a custom download root; category folders are created on demand |
| 🧱 | **Robust fetching** | Retries, size limits, and graceful skip on failures instead of a half-done folder |
| 🪶 | **Minimal dependencies** | `requests` + `beautifulsoup4` + `rich`, nothing else |

---

## ⌨️ Usage

```bash
python webassetx.py                 # interactive menu
python webassetx.py -h              # help
python webassetx.py -v              # version
```

### Direct CLI

```bash
# extract everything a page references into ./extracted_assets
python webassetx.py https://example.com

# only images and fonts, 8 workers, custom output directory
python webassetx.py https://example.com -c images fonts -w 8 -o ./my_assets
```

| Option | Values / Example | Meaning |
|--------|------------------|---------|
| `url` | a target URL (positional) | Page to scan |
| `-c` / `--categories` | `images` `svgs` `fonts` `css` `js` `all` | Which categories to extract (default `all`) |
| `-o` / `--output` | directory | Where assets land (default `extracted_assets/`) |
| `-w` / `--workers` | number | Concurrent download workers (default 6) |
| `--timeout` | seconds | Per-request timeout (default 15) |

---

## ⚙️ Configuration

Extraction behavior lives in [`core/config.py`](core/config.py):

| Setting | Default | Effect |
|---------|---------|--------|
| Category map | extension / content-type → category | How every asset URL is classified |
| Default fetch limit | capped per category | Stops runaway downloads from one page |
| Request headers | browser-like User-Agent | Serves through basic bot-blocking pages |
| Output root | `extracted_assets/` | Where downloads land (CLI `--out` overrides) |

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.8+ |
| HTTP | `requests` (fetching pages & asset URLs) |
| Parsing | `beautifulsoup4` (HTML walk) + regex (CSS asset references) |
| UI | `rich` (menus, colored tables, prompts) |

---

## ⚠️ Disclaimer

> ### Read this before using WebAssetX.
>
> 1. **Respect site rights.** Assets on the sites you scan are usually copyrighted. Download only for personal, educational, or fair-use purposes - and don't republish or monetize what you extracted.
> 2. **Don't hammer sites.** Each page fetches and downloads assets the site owner pays to serve. Use reasonable `--limit` values and don't run WebAssetX against a site you don't have permission to crawl.
> 3. **Legal compliance.** You are responsible for complying with the target site's terms of service, robots.txt, and applicable law in your jurisdiction.
> 4. **No warranty.** WebAssetX is provided "as is", with no warranty of any kind. The author is **not liable** for misuse, charges, or damage from using this tool.

---

## 🤝 Contributing

Contributions are welcome!

```bash
# 1. fork it
# 2. create your branch
git checkout -b feature/amazing-feature
# 3. commit
git commit -m "Add amazing feature"
# 4. push
git push origin feature/amazing-feature
# 5. open a Pull Request
```

---

## 📜 License

WebAssetX is the original project by MrHacker-X - see the [`LICENSE`](https://github.com/MrHacker-X/webassetx) file in the upstream repository for details.

---

## 👨‍💻 Developer

| | |
|---|---|
| **Dev** | MrHacker-X |
| **GitHub** | [github.com/MrHacker-X](https://github.com/MrHacker-X) |
| **Email** | [contact@vritrasec.com](mailto:contact@vritrasec.com) |
| **Website** | [vritrasec.com](https://vritrasec.com) |
| **Network** | [link.vritrasec.com](https://link.vritrasec.com) |

---

<div align="center">

### ⭐ Star the repo if WebAssetX made asset extraction effortless ⭐

*Built by MrHacker-X - extract responsibly, save ethically.*

</div>
