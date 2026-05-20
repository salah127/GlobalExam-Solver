"""
agent/ai_service.py
Optional AI layer — uses DeepSeek (OpenAI-compatible API) to answer exercises.
Falls back gracefully if no API key is configured.

Context: GlobalExam (global-exam.com) is an online platform for preparing
English language certifications (TOEIC, TOEFL, IELTS, Cambridge, etc.).
Exercises include grammar fill-in-the-blank, vocabulary, reading comprehension,
listening comprehension, and sentence correction. Answers are typically single
words or short phrases (verb conjugations, prepositions, articles, pronouns).
"""

import logging
from collections import deque

import config

logger = logging.getLogger(__name__)

_client = None

# Rolling memory of the last N Q&A pairs — helps AI learn the exercise style
_MEMORY_SIZE = 6
_memory: deque = deque(maxlen=_MEMORY_SIZE)   # each item: {"question": ..., "answer": ...}

# System prompt with full GlobalExam context
_SYSTEM_PROMPT = (
    "You are an expert English language teacher helping a student prepare for "
    "English certification exams on the GlobalExam platform (global-exam.com). "
    "GlobalExam is a French online learning platform specialising in English "
    "certifications such as TOEIC, TOEFL, IELTS, BULATS, and Cambridge exams. "
    "Exercises are typically:\n"
    "  • Fill-in-the-blank grammar (verb tenses, prepositions, articles, pronouns)\n"
    "  • Vocabulary gap-fill (choose the correct word in context)\n"
    "  • Sentence correction (identify the grammatically correct form)\n"
    "  • Short reading/listening comprehension answers\n\n"
    "Key grammar rules to apply carefully:\n"
    "  • 'every' is used with singular countable nouns. NEVER use 'every' before 'of' — use 'all' instead.\n"
    "  • 'all' can precede 'of', plural nouns, or uncountable nouns ('all of them', 'all students').\n"
    "  • 'each' focuses on individuals in a group ('each student has a book').\n"
    "  • 'whole' means entire/complete and precedes a singular noun ('the whole team').\n"
    "  • 'some' vs 'any': use 'some' in affirmatives, 'any' in negatives/questions.\n"
    "  • Always match subject-verb agreement and tense from the surrounding sentence.\n\n"
    "Rules:\n"
    "  1. Return ONLY the answer word or short phrase — nothing else.\n"
    "  2. No punctuation at the end unless required by the answer itself.\n"
    "  3. Match the exact form required (e.g. 'has been' not 'have been').\n"
    "  4. Analyse each blank individually in its sentence context before answering.\n"
    "  5. If unsure, give the most grammatically correct English answer."
)


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not config.DEEPSEEK_API_KEY:
        return None
    try:
        from openai import OpenAI
        _client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
        logger.info("🤖 DeepSeek AI ready (model: %s)", config.DEEPSEEK_MODEL)
        return _client
    except ImportError:
        logger.warning("openai package not installed — AI answering disabled.")
        return None


def record_result(question: str, answer: str) -> None:
    """
    Call this after each exercise with the correct answer so the AI
    can learn the exercise style throughout the session.
    """
    _memory.append({"question": question[:200], "answer": answer})


def answer_question(question: str, options: list[str] | None = None,
                    context: str = "", n_blanks: int = 1) -> str | None:
    """
    Send a question to DeepSeek and return the best answer string.
    Includes session memory (last 6 Q&A pairs) so the AI adapts to the
    exercise style over time.
    Returns None if AI is unavailable or the call fails.
    """
    client = _get_client()
    if client is None:
        return None

    # Build messages: system prompt + memory examples + current question
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

    if _memory:
        examples = "\n".join(
            f"Q: {m['question']}  →  A: {m['answer']}"
            for m in _memory
        )
        messages.append({
            "role": "user",
            "content": f"Here are recent exercises from this session so you understand the style:\n{examples}"
        })
        messages.append({
            "role": "assistant",
            "content": "Understood. I'll match this style for the next answer."
        })

    options_text = ""
    if options:
        options_text = "\nOptions: " + " / ".join(options)

    if n_blanks > 1:
        user_prompt = (
            f"IMPORTANT: The rendered exercise form has EXACTLY {n_blanks} input fields. "
            f"You MUST reply with EXACTLY {n_blanks} answers separated by ' | ' (pipe) — "
            f"no more, no less. Do NOT count blanks yourself from the text; trust the number {n_blanks}. "
            f"Analyse EACH blank separately in its own sentence context — do not repeat the same word "
            f"lazily. Apply grammar rules (e.g. 'every' cannot precede 'of', use 'all' instead). "
            f"Example for {n_blanks} blanks: " + " | ".join(["word"] * n_blanks) + "\n"
            f"Exercise: {question}{options_text}"
        )
    else:
        user_prompt = f"Exercise: {question}{options_text}"
    if context:
        user_prompt = f"Context: {context}\n{user_prompt}"

    messages.append({"role": "user", "content": user_prompt})

    try:
        response = client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=messages,
            max_tokens=max(60, n_blanks * 20),
            temperature=0.1,
        )
        answer = response.choices[0].message.content.strip()
        logger.info("📥 DeepSeek response: %r  (memory size: %d)", answer, len(_memory))
        return answer
    except Exception as e:
        logger.warning("⚠️  DeepSeek call failed: %s", e)
        return None


