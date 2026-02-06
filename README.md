# 🧠 AI-Powered Intelligence Digest System

> **Your Local, Privacy-First Personal Intelligence Analyst.**

This application aggregates content from top tech sources (Hacker News, Reddit, RSS), uses a local LLM (Llama 3.1) to read and evaluate every single item based on *your* specific interests ("Personas"), and delivers a concise, high-value executive summary directly to you via **Telegram** and **Email**.

Unlike standard aggregators that just filter by keywords, this system *reads* the content to understand if it's actually valuable to you. It uses a **"Best Fit"** algorithm to ensure every news item appears only once, in the category where it belongs most.

---

## 🚀 Key Features

*   **🔒 Privacy-First**: Runs 100% locally. Your data and interests never leave your machine.
*   **🧠 AI Evaluation**: Uses Llama 3.1 to score items based on "Personas".
*   **🎯 Smart Exclusive Assignment**: 
    *   Items are scored against all active personas (GenAI, Product, Finance).
    *   Each item is assigned **exclusively** to the persona where it scores highest.
    *   **Result**: No duplicates across categories. A clean, focused digest.
*   **👥 Support for Custom Recipients**: Send the digest to your team or friends easily via the backend management script.
*   **💬 Interactive Telegram Bot**: Control the entire pipeline, change settings, and get digests on demand from your phone.
*   **🕸️ Smart RAG Pipeline**: Uses Vector Search to avoid duplicates and find the most relevant historical context.

---

## 🛠 Prerequisites

1.  **Python 3.11+** installed.
2.  **Ollama** installed and running. [Download Ollama](https://ollama.com/download).
3.  **(Optional) Telegram Account** for mobile delivery and control.
4.  **(Optional) Gmail Account** for email delivery.

---

## 🌊 Architecture & Workflow

Here is the detailed comprehensive breakdown of how the system processes information:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: INGESTION                                   │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │  HackerNews  │     │    Reddit    │     │  RSS Feeds   │
    │   Adapter    │     │   Adapter    │     │   Adapter    │
    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
           │                    │                    │
           └────────────────────┼────────────────────┘
                                ▼
                    ┌───────────────────────┐
                    │   33 Raw Items        │
                    │   (titles, URLs,      │
                    │    content, scores)   │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  DEDUPLICATION        │
                    │  - URL check          │
                    │  - Title hash check   │
                    │  - Vector store check │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  SEMANTIC PREFILTER   │  ◄── all-MiniLM-L6-v2
                    │  (prefilter.py)       │
                    │                       │
                    │  Compares to anchors: │
                    │  - GENAI anchor       │
                    │  - PRODUCT anchor     │
                    │  - FINANCE anchor     │
                    │                       │
                    │  Threshold: 0.35      │
                    │  (lenient)            │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  SAVE TO DATABASE     │
                    │  (SQLite)             │
                    │                       │
                    │  Result: 18 saved     │
                    │  (15 filtered out)    │
                    └───────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 2: GENERATION                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌───────────────────────┐
                    │  LOAD FROM DATABASE   │
                    │  (last 1000 items)    │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  SOURCE FILTERING     │
                    │                       │
                    │  Check UI preferences:│
                    │  ☑ HackerNews: ON     │
                    │  ☐ Reddit: OFF        │
                    │  ☐ RSS: OFF           │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  SELECT TOP ITEMS     │
                    │                       │
                    │  Per source: Top 30   │
                    │  (sorted by score)    │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  TITLE DEDUPLICATION  │
                    │                       │
                    │  Result: 13 unique    │
                    │  candidates           │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  CHECK ACTIVE         │
                    │  PERSONAS (from UI)   │
                    │                       │
                    │  ☑ GenAI: ON          │
                    │  ☐ Product: OFF       │
                    │  ☐ Finance: OFF       │
                    └───────────┬───────────┘
                                ▼
           ┌────────────────────┴────────────────────┐
           │           BATCH PROCESSING              │
           │                                         │
           │  13 items ÷ 12 batch size = 2 batches  │
           │                                         │
           │  ┌─────────────┐    ┌─────────────┐    │
           │  │  Batch 0    │    │  Batch 1    │    │
           │  │  12 items   │    │  1 item     │    │
           │  └──────┬──────┘    └──────┬──────┘    │
           │         │                  │           │
           │         └────────┬─────────┘           │
           │                  ▼                     │
           │    ┌─────────────────────────┐         │
           │    │  PARALLEL PROCESSING    │         │
           │    │  (max 4 concurrent)     │         │
           │    └─────────────────────────┘         │
           └────────────────────┬────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EVALUATOR (per batch)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   STEP 1: Semantic Pre-filter (FAST - ~50ms)                               │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  all-MiniLM-L6-v2 model                                     │          │
│   │                                                             │          │
│   │  Item: "New GPT-5 release with multimodal..."              │          │
│   │                    ▼                                        │          │
│   │  Encode → [0.12, 0.45, 0.23, ...]  (384 dim)               │          │
│   │                    ▼                                        │          │
│   │  Compare to GENAI anchor embedding                          │          │
│   │                    ▼                                        │          │
│   │  Cosine similarity = 0.42                                   │          │
│   │                    ▼                                        │          │
│   │  0.42 >= 0.15 threshold? ✅ PASS                            │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
│   STEP 2: LLM Evaluation (SLOW - ~20-45s)                                  │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  Ollama (llama3.1)                                          │          │
│   │                                                             │          │
│   │  Prompt:                                                    │          │
│   │  "You are an expert AI Editor. Analyze these items..."     │          │
│   │                                                             │          │
│   │  Response:                                                  │          │
│   │  ID: abc123 | SCORE: 8 | DECISION: KEEP | INSIGHT: This    │          │
│   │  article discusses breakthrough in transformer efficiency...│          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                ▼
                    ┌───────────────────────┐
                    │  COLLECT RESULTS      │
                    │                       │
                    │  Filter: score > 5    │
                    │  AND decision = KEEP  │
                    │                       │
                    │  GenAI: 3 items       │
                    │  Product: 0 items     │
                    │  Finance: 0 items     │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  LIMIT TOP 5          │
                    │  (per category)       │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  GENERATE SUMMARY     │
                    │  (LLM)                │
                    │                       │
                    │  "Summarize findings  │
                    │   into executive      │
                    │   summary..."         │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  FORMAT DIGEST        │
                    │  (Markdown)           │
                    │                       │
                    │  # AI Digest          │
                    │  ## Executive Summary │
                    │  ## 🤖 GenAI News     │
                    │  ### [Title](url)     │
                    │  **Insight:** ...     │
                    └───────────┬───────────┘
                                ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 3: DELIVERY                                    │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌───────────────────────┐
                    │  SAVE TO FILE         │
                    │  data/digest_2026-    │
                    │  02-06.md             │
                    └───────────┬───────────┘
                                ▼
           ┌────────────────────┴────────────────────┐
           │                                         │
           ▼                                         ▼
    ┌─────────────┐                         ┌─────────────┐
    │   EMAIL     │                         │  TELEGRAM   │
    │   (SMTP)    │                         │   (Bot)     │
    │             │                         │             │
    │  ✅ Sent!   │                         │  ✅ Sent!   │
    └─────────────┘                         └─────────────┘
```

---

## 📦 Installation

1.  **Open a terminal** in the project folder.
2.  **Install dependencies**:
    ```powershell
    pip install -r requirements.txt
    ```
3.  **Pull the LLM model** (Run this once):
    ```powershell
    ollama pull llama3.1
    ```

---

## ⚙️ Configuration

1.  Copy the example config:
    ```powershell
    copy .env.example .env
    ```
2.  Open `.env` in any text editor and configure your settings.

### 📱 Telegram Setup
1.  Search for **@BotFather** on Telegram -> `/newbot`.
2.  Get your `TELEGRAM_BOT_TOKEN`.
3.  Search for **@userinfobot** to get your `TELEGRAM_CHAT_ID`.
4.  Add these to `.env`.

### 📧 Email Setup
1.  Use a Gmail App Password (Security > 2-Step Verification > App Passwords).
2.  Add `EMAIL_FROM`, `EMAIL_TO`, and `EMAIL_PASSWORD` to `.env`.

---

## 🚦 How to Run

### Method 1: The "One-Click" Start (Easiest)
Double-click **`start.bat`** in the folder.
*   It launches the **Background API** (for the Telegram Bot, CLI logic).
*   It launches the **Web Interface** (at `http://localhost:5173`).

### Method 2: Manual Start
**Window 1: The App Brain (API & Bot)**
```powershell
python -m src.api
```

**Window 2: The Visuals (Frontend)**
```powershell
cd ui
npm run dev
```

---

## 👥 Managing Email Recipients (Backend)

You can add multiple recipients for the digest directly from the command line.

**1. Add a Recipient:**
```powershell
python scripts/manage_emails.py add friend@example.com
```

**2. List All Recipients:**
```powershell
python scripts/manage_emails.py list
```

**3. Remove a Recipient:**
```powershell
python scripts/manage_emails.py remove friend@example.com
```

The system will automatically send the digest to the primary `EMAIL_TO` **plus** everyone on this list!

---

## 🤖 Using the Telegram Bot

| Command | Description |
| :--- | :--- |
| **/run** | 🚀 **Trigger a fresh Digest cycle.** |
| **/status** | Check if the pipeline is currently running. |
| **/digest** | 📄 Send me the last generated digest. |
| **/prefs** | View your current sources and persona settings. |
| **/set** | Change a setting. Ex: `/set rss off` |

---

## 💻 Tech Stack

*   **Core Logic**: Python 3.11+
*   **LLM Engine**: Ollama (Llama 3.1)
*   **API Framework**: FastAPI
*   **Database**: SQLite (Async)
*   **Frontend**: React + Vite
*   **Notification Services**: Telegram Bot API, SMTP (Email)

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See below for more information.

```text
MIT License

Copyright (c) 2024 AI-DEG

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgments

*   [Ollama](https://ollama.com/) for making local LLMs accessible.
*   [FastAPI](https://fastapi.tiangolo.com/) for the high-performance API.
*   [Hacker News API](https://github.com/HackerNews/API) for the data.
