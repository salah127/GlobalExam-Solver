# GlobalExamSolver

Autonomous GlobalExam exercise solver — logs in, solves exercises continuously, learns from previous sessions via an answer cache, and targets 20+ hours automatically.

<div id="header" align="center">
  <img src="https://content.globalexam.cloud/vi/media/logos/natural/global-exam-natural.png">
</div>

---

## Features

- **Autonomous agent** — runs continuously without manual interaction
- **Smart login** — JS injection + multi-selector fallback (never blocked by page structure changes)
- **Cookie/GDPR banner dismissal** — handled automatically
- **Correction-peek strategy** — submits dummy answers first, reads corrections, then re-submits correctly
- **Answer cache** — correct answers are saved to `progress.json` after each exercise; on repeat visits the agent skips the dummy pass and submits directly (~2× faster)
- **AI answering with session memory** — DeepSeek (or any OpenAI-compatible model) answers exercises using a GlobalExam-specific system prompt + the last 6 Q&A pairs as context so it adapts to the exercise style over time
- **Progress tracking** — persists completed exercises, failures, elapsed hours and cached answers to `progress.json` across sessions
- **Human-like behavior** — random delays, realistic typing, anti-bot flags disabled
- **Auto-recovery** — retries on failures, pauses after 5 consecutive errors
- **Live log GUI** — dark-theme Tkinter interface with real-time emoji status

---

## Requirements

- Python 3.10+
- Google Chrome installed
- ChromeDriver is downloaded automatically via `webdriver-manager`

---

## Installation

```bash
git clone https://github.com/Nv3l/GlobalExamSolver.git
cd GlobalExamSolver
pip install -r requirements.txt
```

---

## Configuration

Edit **`config.py`** before running:

```python
EMAIL    = "your@email.com"   # your GlobalExam account
PASSWORD = "yourpassword"     # your GlobalExam password

TARGET_HOURS   = 20           # stop after N hours
SUBDOMAIN      = "exam"       # "exam" or "general"

PAGE_LOAD_DELAY   = 3         # seconds to wait after navigation
EXERCISE_DELAY    = 1         # pause before submitting (human-like)

DEEPSEEK_API_KEY  = ""        # optional — enables AI-powered answering
                              # get your key at platform.deepseek.com
DEEPSEEK_MODEL    = "deepseek-chat"
HEADLESS          = False     # True = run Chrome in background
```

> **Security note:** never commit `config.py` with real credentials. Add it to `.gitignore`.

---

## Usage

```bash
python globalexam.py
```

1. The GUI opens — credentials and settings are pre-filled from `config.py`
2. Adjust anything if needed
3. Click **Start Agent**
4. Watch the live log — the agent logs in, solves exercises and reports progress
5. Click **Stop** to interrupt gracefully at any time

Progress is saved automatically. The next session will load the answer cache and resume from where you left off.

---

## Project Structure

```
GlobalExamSolver/
├── globalexam.py        # GUI entry point
├── config.py            # credentials & settings
├── requirements.txt
├── progress.json        # auto-generated — progress + answer cache
└── agent/
    ├── browser.py       # Chrome driver, login (JS injection)
    ├── solver.py        # exercise solving loop + cache logic
    ├── ai_service.py    # DeepSeek integration with session memory
    └── tracker.py       # progress persistence + answer cache
```

---

## How it works

### Login
Navigates to `auth.global-exam.com`, scans all `<input>` elements via JavaScript to reliably find the email and password fields (works regardless of dynamic IDs), fills them via JS injection, dismisses cookie banners, and waits for the redirect confirmation.

### Exercise loop

```
for each exercise:
  1. Navigate to grammar exercise list
  2. Click "Me tester"
  3. Check answer cache
     ├── Cache HIT  → submit correct answers immediately  (fast path)
     └── Cache MISS → submit dummy answers
                    → read corrections shown by the site
                    → save answers to cache (progress.json)
                    → navigate back → submit correct answers
```

### AI mode *(optional)*
If `DEEPSEEK_API_KEY` is set, the page text is sent to DeepSeek before the first submission using a system prompt that describes GlobalExam's exercise types (TOEIC/TOEFL/IELTS grammar, vocabulary, fill-in-the-blank). The last 6 correct Q&A pairs from the current session are included as examples so the AI adapts to the exercise style over time.

### Answer cache
Correct answers are stored in `progress.json` keyed by a hash of the exercise URL + question text. On subsequent sessions, cached exercises skip the dummy-answer pass entirely and submit the correct answers directly — roughly doubling throughput once the cache is populated.

---

## Log output example

```
11:08:00 [INFO] 🌐 Navigating to login page...
11:08:03 [INFO] 🍪 Checking for cookie/GDPR banner...
11:08:03 [INFO] 🔍 Scanning page for login fields...
11:08:03 [INFO]   📧 Email field found
11:08:03 [INFO]   🔑 Password field found
11:08:04 [INFO] 🚀 Submitting login form...
11:08:06 [INFO] ✅ LOGIN SUCCESSFUL  →  https://exam.global-exam.com/...
11:08:10 [INFO] ✏️  Filling exercise inputs...
11:08:12 [INFO] 📝 Corrections: ['has been', 'would']
11:08:12 [INFO] 💾 Cached answers for exercise (total cached: 1)
11:08:15 [INFO] ✅ Exercise solved — ✓ 1 completed  ✗ 0 failed  ⏱ 0.01h  📚 1 cached
...
11:09:00 [INFO] 🎯 Cache hit! Submitting known answers directly...
11:09:02 [INFO] ✅ Exercise solved — ✓ 2 completed  ✗ 0 failed  ⏱ 0.02h  📚 1 cached
```
4. **Recovery** — on 5 consecutive failures the agent pauses 30 s and retries; all errors are logged

---

## Tested on

- Python 3.13 / Windows 11
- Google Chrome 147

## Support

Pour tout report de bug, vous pouvez ouvrir une issue sur le repository.


## Disclaimer

This script is for educational purposes only.
