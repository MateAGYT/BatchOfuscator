<div align="center">

# BatchOfuscator
# [Download Releases](https://github.com/MateAGYT/CliToApp/releases)

**A modular, Python-powered Windows Batch and PowerShell obfuscation and deobfuscation laboratory featuring automated signature detection, multi-layered wrapping, and a dark animated CustomTkinter interface.**

<img src="https://files.catbox.moe/vuhaid.png" width="500" />

![Language](https://img.shields.io/badge/language-Python-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)
![GUI](https://img.shields.io/badge/gui-CustomTkinter-41CD52?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-brightgreen)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)

> **`MateAGYT` is the exclusive official repository creator.** Avoid running unverified builds from external sources.

</div>

---

# 📑 Table of contents

- [1. About](#-about)
- [2. Disclaimer & License](#-disclaimer--license)
- [3. Features](#️-features)
  - [Obfuscation Methods](#-obfuscation-methods)
  - [Deobfuscation & Analysis](#-deobfuscation--analysis)
- [4. Why BatchOfuscator?](#-why-batchofuscator)
- [5. Comparison](#-comparison)
- [6. Requirements](#-requirements)
- [7. Installation](#️-installation)
- [8. Troubleshooting & FAQ](#-troubleshooting--faq)
- [9. Roadmap](#-roadmap)
- [10. Credits](#-credits)
- [11. Contributing](#-contributing)

---

# 🧭 About

**BatchOfuscator** is a desktop laboratory built for security researchers, developers, and administrators who need to protect or analyze Windows command scripts (`.bat`, `.cmd`, `.ps1`). Rather than relying on simple string substitutions, it bundles multiple real-world wrapping schemes—ranging from AES-256-CBC self-reading loader stubs to variable indirection, path shards, and certutil certificate blocks.

The application features a dark-themed interface built on top of CustomTkinter, complete with a live animated background canvas, signature scanning engine, asynchronous worker threads to prevent UI freezing, and an automated deobfuscation chaining engine capable of peeling back multiple layers of protection automatically.

---

# ❗ Disclaimer & License

**a) Disclaimer.** This tool is provided strictly for educational purposes, defensive analysis, and authorized security auditing. The author assumes no responsibility for any misuse or illegal activities conducted with scripts generated or processed by this software.

**b) License.** MIT License. See [`LICENSE`](LICENSE) for complete terms.

---

# ⚙️ Features

> 8 dedicated obfuscation techniques and automated multi-layer deobfuscation.

## 🔒 Obfuscation Methods

| Method | Description | Target Formats |
|---|---|---|
| **AES-256-CBC Self-Read** | Encrypts payload with AES-256-CBC/PKCS7, stores it as a comment block separated by `++++` from a PowerShell loader stub that derives keys at runtime. | `.bat`, `.ps1` |
| **Path Shard Reassembly** | Splits base64 strings into fake directory path components inside random environment variables, concatenating and stripping backslashes before execution. | `.bat` |
| **Variable Indirection** | Breaks scripts into random variables, rebuilding commands via `%a%%b%` percent concatenation, case-mangling, and random comment/echo noise. | `.bat` |
| **Certutil Polyglot** | Embeds payload base64 inside a fake certificate block, extracting and decoding it at runtime via `certutil -decode`. | `.bat`, `.ps1` |
| **PowerShell -EncodedCommand** | Converts script blocks into UTF-16LE base64 strings passed directly to PowerShell execution arguments. | `.ps1` |
| **Character Code Array** | Translates every payload byte into a decimal array rebuilt using `[char]` casting and immediate execution. | `.ps1` |
| **Single Byte XOR** | Encodes payload bytes using a random single-byte XOR key combined with base64 wrapper storage. | `.bat`, `.ps1` |
| **Plain Base64 Blob** | Wraps single base64 blocks written out to temporary files and launched silently. | `.bat`, `.ps1` |

## 🔍 Deobfuscation & Analysis

- **Automated Signature Detection:** Scans script headers and content structures to assign heuristic confidence scores for known obfuscation patterns.
- **Multi-Layer Chain Mode:** Automatically detects a wrapping layer, reverses it, and feeds the resulting text back into the signature scanner up to a user-defined depth (1 to 5 layers).
- **Live Terminal Output:** Real-time logging console with error tracking, byte counters, and automatic path autofilling.

---

# 🏆 Why BatchOfuscator?

- **Dual-Mode Laboratory:** Combines robust protection methods with intelligent signature reversing under one roof.
- **Robust Cryptography Support:** Leverages the `cryptography` library for military-grade AES-CBC wrappers when available.
- **Non-Blocking UI Execution:** Heavy processing runs safely on background worker threads with responsive cancellation handling.
- **Clean Artifact Management:** Automatically manages output file paths and directory structures cleanly.

---

# 📊 Comparison

| Feature | BatchOfuscator | Basic Script Wrappers | Manual Obfuscation | Raw CLI Scripts |
|---|---|---|---|---|
| Offline Capable | **✅** | ✅ | ✅ | ✅ |
| Multiple Obfuscation Engines | **✅ (8)** | ❌ (1) | ❌ | ❌ |
| Automated Deobfuscation Chaining | **✅** | ❌ | ❌ | ❌ |
| Signature Heuristic Scanning | **✅** | ❌ | ❌ | ❌ |
| Animated Modern Interface | **✅** | ❌ | ❌ | ❌ |
| Threaded Non-Blocking UI | **✅** | ❌ | n/a | ❌ |

---

# 📋 Requirements

- **Operating System:** Windows 10/11 (x64)
- **Runtime:** Python 3.10+ (with Python added to system PATH)
- **Dependencies:** `customtkinter`, `cryptography` (optional, enables AES methods)

---

# 🛠️ Installation

1. Ensure Python 3.10+ is installed with the PATH option enabled.
2. Clone or download the repository files.
3. Install required runtime libraries via command prompt:
   ```cmd
   py -m pip install customtkinter cryptographyç
   ```
4. Launch the application:
   ```cmd
   py main.py
   ```



---

# 🔧 Troubleshooting & FAQ

* **Missing AES Support:** If the `cryptography` package is missing, AES-based obfuscation methods will be automatically disabled while other methods remain operational.
* **Antivirus False Positives:** Highly obfuscated batch and PowerShell files frequently trigger heuristic flags on Windows Defender. Use exclusions or test strictly in isolated environments.
* **Empty Deobfuscation Results:** Ensure the correct method or **AUTO** mode is selected with an appropriate chain depth for heavily nested scripts.

---

# 🗺️ Roadmap

* [ ] Exportable custom noise profile dictionaries.
* [ ] Drag-and-drop file support directly onto the workspace canvas.
* [ ] Additional PowerShell tokenization wrappers.
* [ ] Linux-compatible shell script obfuscation modules.

---

# 🙏 Credits

* **CustomTkinter** — Modern Python UI widget framework.
* **PyCryptodome / Cryptography** — Secure cryptographic backend primitives.

---

# 🤝 Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/new-obfuscation`).
3. Commit your modifications.
4. Open a Pull Request detailing your changes.