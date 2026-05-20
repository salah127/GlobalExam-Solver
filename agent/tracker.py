"""
agent/tracker.py
Persists and reports exercise progress to a local JSON file.
Includes an answer cache so repeated exercises are solved instantly.

Cache format in progress.json:
  "answer_cache": {
    "1": { "question": "...", "answers": ["word1", "word2", ...] },
    "2": { "question": "...", "answers": ["word1"] },
    ...
  }
"""

import hashlib
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

PROGRESS_FILE = Path(__file__).parent.parent / "progress.json"


def _load() -> dict:
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            data.setdefault("exercises_completed", 0)
            data.setdefault("exercises_failed", 0)
            data.setdefault("total_seconds", 0)
            data.setdefault("session_start", None)
            data.setdefault("last_update", None)
            data.setdefault("answer_cache", {})
            return data
        except Exception:
            pass
    return {
        "exercises_completed": 0,
        "exercises_failed": 0,
        "total_seconds": 0,
        "session_start": None,
        "last_update": None,
        "answer_cache": {},
    }


def _save(data: dict) -> None:
    PROGRESS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _make_title_key(question_text: str) -> str:
    """Extract the exercise title (first non-empty, non-digit line) as the JSON key."""
    for line in question_text.splitlines():
        line = line.strip()
        if line and len(line) > 4 and not line.replace('/', '').replace(' ', '').replace('.', '').isdigit():
            return line[:80]
    return hashlib.md5(question_text[:100].encode()).hexdigest()[:16]


class Tracker:
    def __init__(self) -> None:
        self._data = _load()
        self._session_start = time.time()
        self._data["session_start"] = self._session_start

        # Migrate old formats to title-keyed sentence-pair format
        cache = self._data["answer_cache"]
        migrated: dict = {}

        for key, entry in cache.items():
            if isinstance(entry, dict) and "sentences" in entry:
                # Already new format — keep as-is
                migrated[key] = entry
            elif isinstance(entry, dict) and "answers" in entry:
                # Old {"question": ..., "answers": [...]} format
                q = entry.get("question", "")
                title = _make_title_key(q) if q else key
                migrated[title] = {
                    "sentences": [{"blank": "", "answer": a} for a in entry.get("answers", [])]
                }
            elif isinstance(entry, list):
                # Very old list-only format
                migrated[key] = {
                    "sentences": [{"blank": "", "answer": a} for a in entry]
                }

        self._data["answer_cache"] = migrated
        cached_count = len(migrated)
        if cached_count:
            logger.info("📚 Answer cache loaded: %d exercise(s) remembered", cached_count)

    # ------------------------------------------------------------------
    def record_success(self) -> None:
        self._data["exercises_completed"] += 1
        self._flush()

    def record_failure(self) -> None:
        self._data["exercises_failed"] += 1
        self._flush()

    def elapsed_hours(self) -> float:
        session_seconds = time.time() - self._session_start
        return (self._data["total_seconds"] + session_seconds) / 3600

    # ------------------------------------------------------------------
    # Answer cache
    # ------------------------------------------------------------------

    def get_cached_answers(self, exercise_url: str, question_text: str) -> list | None:
        """Return cached answers (in order) for this question, or None if not in cache."""
        title = _make_title_key(question_text)
        entry = self._data["answer_cache"].get(title)
        if not entry:
            return None
        sentences = entry.get("sentences", [])
        answers = [s.get("answer", "") for s in sentences]
        return answers if any(a for a in answers if a) else None

    def cache_answers(self, exercise_url: str, question_text: str, sentence_pairs: list) -> None:
        """Save sentence-answer pairs for this question (only if non-empty)."""
        if not sentence_pairs:
            logger.warning("⚠️  Skipping cache — no pairs to save.")
            return

        # Normalize: if list of plain strings (legacy), wrap them
        if isinstance(sentence_pairs[0], str):
            sentence_pairs = [{"blank": "", "answer": a} for a in sentence_pairs]

        real = [p for p in sentence_pairs if p.get("answer", "").strip()]
        if not real:
            logger.warning("⚠️  Skipping cache — all answers are empty.")
            return

        title = _make_title_key(question_text)
        self._data["answer_cache"][title] = {"sentences": sentence_pairs}

        logger.info("💾 Saved '%s' — %d answer(s) cached (total: %d)",
                    title, len(real), len(self._data["answer_cache"]))
        self._flush()

    def cache_size(self) -> int:
        return len(self._data["answer_cache"])

    # ------------------------------------------------------------------

    def _flush(self) -> None:
        self._data["total_seconds"] += time.time() - self._session_start
        self._session_start = time.time()
        self._data["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _save(self._data)

    def summary(self) -> str:
        d = self._data
        return (
            f"✓ {d['exercises_completed']} completed  "
            f"✗ {d['exercises_failed']} failed  "
            f"⏱ {self.elapsed_hours():.2f}h elapsed  "
            f"📚 {self.cache_size()} cached"
        )
