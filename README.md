<div align="center">

# 🌳 gettree

<img src="https://raw.githubusercontent.com/ash-kernel/gettree/main/assets/logo.png" width="170"/>

### A smarter `tree` CLI for developers

Generate clean folder structures with `.gitignore` support, colors, icons, and more.

<br/>

<img src="https://img.shields.io/badge/Python-CLI-blue?logo=python" />
<img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey" />
<img src="https://img.shields.io/badge/Status-Stable-success" />
<img src="https://img.shields.io/badge/License-MIT-green" />
<a href="https://pypi.org/project/gettree/">
  <img src="https://img.shields.io/pypi/v/gettree?color=blue&label=PyPI" />
</a>
</div>

---

## ⚡ Features

- 📂 Clean tree output  
- 🧠 Respects `.gitignore`  
- 🚫 Auto ignores `.git`, `node_modules`, etc.  
- 🎨 Color support  
- 🧩 Icons (VS Code style)  
- 📦 File size display  
- 🔢 Depth control  
- 🔄 Live watch mode  
- 🖥️ Interactive TUI view  
- 📝 Markdown export (for README)

---

## 🚀 Install

### 📦 From PyPI (recommended)
```bash
pip install gettree
```

### 🛠️ From GitHub (latest version)
```bash
pip install git+https://github.com/ash-kernel/gettree.git
```
---

## 🧪 Usage

```bash
gettree                    # current folder
gettree myproject         # specific path

gettree . --depth 2
gettree . --size
gettree . --icons
gettree . --color

gettree . --markdown
gettree . --output tree.txt

gettree . --tui
gettree . --watch
```

---

## 🧠 Example

```bash
gettree . --depth 2 --icons --color
```

```
📁 src
├── 🐍 main.py
└── 📄 README.md
```

---

## 🔥 More from Me

### 🌶️ SpiceDeck  
A modern lightweight game launcher  
👉 https://github.com/ash-kernel/spicedeck

### 🎮 FitGirl API  
Fast & open API for repack scraping  
👉 https://github.com/ash-kernel/fitgirl-api

---

## ⭐ Support

If you like this project, drop a ⭐ on GitHub — it helps a lot!