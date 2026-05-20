"""
agent/solver.py
Core autonomous exercise-solving loop.

Strategy (no AI required):
  1. Submit dummy answers ('a') to intentionally fail
  2. Read the corrections shown by the site
  3. Navigate back to the same exercise
  4. Submit the correct answers
  5. Repeat for the next exercise

If OPENAI_API_KEY is set, AI answers are used on the first pass
instead of dummy values, so we win on the first try.
"""

import logging
import random
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)

import config
from agent.tracker import Tracker
from agent import ai_service

logger = logging.getLogger(__name__)

GRAMMAR_URL = "https://{subdomain}.global-exam.com/library/study-sheets/categories/grammar"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait(driver, timeout=None):
    return WebDriverWait(driver, timeout or config.WAIT_TIMEOUT)


def _human_delay(lo=0.3, hi=0.9):
    time.sleep(random.uniform(lo, hi))


def _safe_click(driver, element):
    """Click via JS as fallback when normal click is intercepted."""
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def _fill_input(driver, element, text: str):
    """Fill an input field with full Vue.js reactive event chain."""
    driver.execute_script(
        """
        var el = arguments[0], val = arguments[1];
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(el, val);
        el.dispatchEvent(new Event('input',  {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
        """,
        element,
        text,
    )
    _human_delay(0.1, 0.3)


def _wait_for_page_stability(driver, timeout=10):
    """Wait until jQuery/document is ready."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Exercise interaction
# ---------------------------------------------------------------------------

_JS_FIND_INPUTS = """
var sel = 'input[type="text"], input:not([type]), input[type=""], [contenteditable="true"]';
var EXCLUDE = ['NAV', 'HEADER', 'ASIDE', 'FOOTER'];
function visible(el) {
    if (!el.offsetParent) return false;
    var s = window.getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity) > 0;
}
function notInChrome(el) {
    var p = el.parentElement;
    while (p) {
        if (p.tagName && EXCLUDE.includes(p.tagName.toUpperCase())) return false;
        p = p.parentElement;
    }
    return true;
}
// 1. Inputs inside <main> (most reliable scope for exercise content)
var main = document.querySelector('main');
if (main) {
    var r = Array.from(main.querySelectorAll(sel)).filter(visible);
    if (r.length) return r;
}
// 2. Inputs inside any element whose class contains 'activity' or 'exercise'
var containers = document.querySelectorAll('[class*="activity"],[class*="exercise"],[class*="content-part"]');
for (var i = 0; i < containers.length; i++) {
    var r2 = Array.from(containers[i].querySelectorAll(sel)).filter(visible);
    if (r2.length) return r2;
}
// 3. All visible inputs not in nav/header/aside/footer
return Array.from(document.querySelectorAll(sel)).filter(function(el) {
    return visible(el) && notInChrome(el);
});
"""

_CSS_FALLBACKS = [
    "input[type='text']",
    "input:not([type='hidden']):not([type='submit']):not([type='button'])"
    ":not([type='checkbox']):not([type='radio'])",
    "main input",
    "[contenteditable='true']",
]


def _get_all_inputs(driver, subdomain: str, _waited: bool = False) -> list:
    """Return ALL visible text inputs in the exercise area."""
    if not _waited:
        time.sleep(2)  # Wait for Vue/SPA to finish rendering

    # Pass 1: JS scan
    try:
        inputs = driver.execute_script(_JS_FIND_INPUTS)
        if inputs:
            logger.debug("JS scan found %d input(s)", len(inputs))
            return inputs
    except Exception as e:
        logger.debug("JS scan error: %s", e)

    # Pass 2: CSS fallbacks (5 s each)
    for sel in _CSS_FALLBACKS:
        try:
            elems = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, sel))
            )
            visible = [el for el in elems if el.is_displayed()]
            if visible:
                logger.debug("CSS '%s' found %d input(s)", sel, len(visible))
                return visible
        except (TimeoutException, Exception):
            continue
    return []


def _get_first_input(driver, subdomain: str):
    """Return the first visible input, with a debug dump when none found."""
    inputs = _get_all_inputs(driver, subdomain)
    if inputs:
        return inputs[0]
    # Debug: log what IS on the page
    try:
        info = driver.execute_script("""
            return Array.from(document.querySelectorAll(
                'input, textarea, select, [contenteditable], button'
            )).slice(0, 15).map(function(el) {
                return el.tagName + '[type=' + (el.type || '') + ']'
                    + ' class=' + el.className.substring(0, 50)
                    + ' visible=' + (el.offsetParent !== null);
            });
        """)
        logger.error("❌ No exercise input found — elements on page: %s", info)
    except Exception:
        logger.error("❌ No exercise input found with any selector")
    return None


def _fill_all_inputs(driver, answers: list[str]):
    """Fill first input then TAB through the rest using ActionChains."""
    first_input = driver.switch_to.active_element
    actions = ActionChains(driver)
    for i, answer in enumerate(answers):
        if i > 0:
            actions.send_keys(Keys.TAB)
        actions.send_keys(answer)
    actions.perform()
    _human_delay()


def _submit_exercise(driver, subdomain: str):
    """Find and click the exercise submit button."""
    # Give Vue.js a moment to enable the button after input
    time.sleep(1.5)

    keywords = ['terminer', 'valider', 'suivant', 'next', 'submit',
                'confirmer', 'vérifier', 'verifier', 'check', 'envoyer']
    xpath = (
        "//button["
        + " or ".join(
            f"contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZÉÈÀÙÂÊÎÔÛÇ',"
            f"'abcdefghijklmnopqrstuvwxyzéèàùâêîôûç'),'{kw}')"
            for kw in keywords
        )
        + " or @type='submit']"
    )

    for attempt in range(3):
        # Try text-based buttons (including disabled — JS click bypasses disabled)
        try:
            btns = driver.find_elements(By.XPATH, xpath)
            visible = [b for b in btns if b.is_displayed()]
            if visible:
                driver.execute_script("arguments[0].click();", visible[-1])
                return True
        except Exception:
            pass

        # Try any submit-type button
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
            visible = [b for b in btns if b.is_displayed()]
            if visible:
                driver.execute_script("arguments[0].click();", visible[0])
                return True
        except Exception:
            pass

        time.sleep(1)

    # Debug: show what buttons are actually on the page
    try:
        info = driver.execute_script("""
            return Array.from(document.querySelectorAll('button'))
                .slice(0, 12).map(function(b) {
                    return b.textContent.trim().substring(0, 30)
                        + ' disabled=' + b.disabled
                        + ' visible=' + (b.offsetParent !== null);
                });
        """)
        logger.error("❌ Could not find submit button — buttons on page: %s", info)
    except Exception:
        logger.error("❌ Could not find submit button")
    return False


def _read_corrections(driver) -> list[str]:
    """
    After submitting, try two strategies to read correct answers:
    1. Inline success-styled elements (no button clicking needed)
    2. Click numbered buttons and read revealed text (fallback)
    Returns list of answer strings (may be empty if extraction fails).
    """
    time.sleep(1.5)  # let Vue re-render the correction state

    # --- Strategy 1: inline success elements already visible after submit ---
    try:
        inline = driver.execute_script("""
            return Array.from(document.querySelectorAll(
                'main [class*="success"], main [class*="correct"], main [class*="green"]'
            )).filter(function(el) {
                if (el.closest('button')) return false;
                var t = el.textContent.trim();
                return t && t.length > 0 && t.length < 50 && !/^\\d+$/.test(t);
            }).map(function(el) { return el.textContent.trim(); });
        """)
        if inline and len(inline) >= 1:
            logger.info("📝 Inline corrections found: %s", inline)
            return inline
    except Exception as exc:
        logger.warning("Inline correction read failed: %s", exc)

    # --- Strategy 2: click numbered answer buttons, read revealed tooltip/text ---
    correct_answers = []
    try:
        answer_buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//button[contains(@class,'lg:w-10')]")
            )
        )
        for btn in answer_buttons[:10]:
            try:
                _safe_click(driver, btn)
                _human_delay(0.3, 0.5)
                # Search page-wide for newly-appeared success text (exclude buttons)
                found = driver.execute_script("""
                    var els = Array.from(document.querySelectorAll(
                        '[class*="success"],[class*="correct"],[class*="green"]'
                    ));
                    for (var i=0; i<els.length; i++) {
                        if (els[i].closest('button')) continue;
                        var t = els[i].textContent.trim();
                        if (t && t.length > 0 && t.length < 50 && !/^\\d+$/.test(t))
                            return t;
                    }
                    return null;
                """)
                if found:
                    correct_answers.append(found)
                else:
                    nearby = driver.execute_script(
                        "return arguments[0].closest('li,section,div[class]')"
                        "?.innerText?.substring(0,150) || '';", btn)
                    logger.warning("⚠️  Button %s: no correction found. Nearby: %r",
                                   btn.text, nearby)
                    correct_answers.append("")
            except Exception as e:
                logger.warning("Correction button error: %s", e)
                correct_answers.append("")
    except TimeoutException:
        logger.error("❌ Correction buttons not found after submit.")
    return correct_answers


def _count_me_tester_step(all_texts: list[str]) -> int:
    """
    Count 'Relancer' entries between first and last 'Me tester'
    (used to navigate back to the same exercise).
    """
    first = last = None
    for i, t in enumerate(all_texts):
        if t == "Me tester":
            if first is None:
                first = i
            last = i
    if first is None:
        return 0
    return sum(1 for i in range(first, last + 1) if all_texts[i] == "Relancer")


# ---------------------------------------------------------------------------
# Main solving functions
# ---------------------------------------------------------------------------

def solve_one_exercise(driver: webdriver.Chrome, subdomain: str,
                       tracker: Tracker) -> bool:
    """
    Perform one full exercise cycle.
    Uses the answer cache if the exercise was seen before (skips dummy pass).
    Returns True on success.
    """
    url = GRAMMAR_URL.format(subdomain=subdomain)
    driver.get(url)
    time.sleep(config.PAGE_LOAD_DELAY)
    _wait_for_page_stability(driver)

    # --- Discover buttons ---
    all_buttons = driver.find_elements(
        By.XPATH, "//button[contains(@class,'button-solid-default-small')]"
    )
    all_texts = [b.text for b in all_buttons]
    step = _count_me_tester_step(all_texts)

    me_tester_buttons = driver.find_elements(By.XPATH, "//button[contains(.,'Me tester')]")
    if not me_tester_buttons:
        logger.warning("⚠️  No 'Me tester' buttons found — skipping")
        return False

    _safe_click(driver, me_tester_buttons[0])
    time.sleep(config.PAGE_LOAD_DELAY)
    _wait_for_page_stability(driver)

# --- Build question text (plain innerText for AI context) ---
    try:
        question_text = driver.execute_script(
            "var m=document.querySelector('main');"
            "return m?m.innerText.replace(/[ \\t]+/g,' ').replace(/\\n{3,}/g,'\\n\\n').trim()"
            ":document.body.innerText;"
        ) or url
    except Exception as exc:
        logger.warning("⚠️  Question text extraction failed: %s — using URL", exc)
        question_text = url
    logger.info("📋 Question text (%d chars):\n%s", len(question_text), question_text[:600])

    # --- Extract per-input sentence context (for cache storage) ---
    _JS_GET_BLANK_SENTENCES = (
        "(function(){"
        "var main=document.querySelector('main')||document.body;"
        "var SKIP=['hidden','submit','button','checkbox','radio','file'];"
        "var inputs=Array.from(main.querySelectorAll('input')).filter(function(inp){"
        "  if(SKIP.indexOf((inp.type||'').toLowerCase())>-1)return false;"
        "  var s=window.getComputedStyle(inp);"
        "  return s.display!=='none'&&s.visibility!=='hidden';"
        "});"
        "function getSentence(inp){"
        "  var el=inp.parentElement,d=0;"
        "  while(el&&d<6){"
        "    var t=el.tagName.toUpperCase();"
        "    if(t==='LI'||t==='P')break;"
        "    if(t==='DIV'&&el.querySelectorAll('input').length<=2)break;"
        "    el=el.parentElement;d++;"
        "  }"
        "  if(!el)return '..............';"
        "  var parts=[];"
        "  function walk(n){"
        "    if(n.nodeType===3){if(n.textContent.trim())parts.push(n.textContent);return;}"
        "    if(n.nodeType!==1)return;"
        "    var tag=n.tagName.toUpperCase();"
        "    if(['SCRIPT','STYLE','BUTTON'].indexOf(tag)>-1)return;"
        "    if(tag==='INPUT'||tag==='TEXTAREA'){parts.push('..............');return;}"
        "    for(var i=0;i<n.childNodes.length;i++)walk(n.childNodes[i]);"
        "  }"
        "  walk(el);"
        "  return parts.join('').replace(/\\s+/g,' ').trim();"
        "}"
        "return inputs.map(getSentence);"
        "})()"
    )
    try:
        blank_sentences = driver.execute_script(_JS_GET_BLANK_SENTENCES) or []
        logger.info("📝 Blank sentences: %s", blank_sentences)
    except Exception as exc:
        logger.warning("⚠️  Blank sentence extraction failed: %s", exc)
        blank_sentences = []

    # --- Check answer cache ---
    cached = tracker.get_cached_answers(url, question_text)
    if cached:
        logger.info("🎯 Cache hit! Filling %d known answer(s)...", len(cached))
        cache_inputs = _get_all_inputs(driver, subdomain)
        if not cache_inputs:
            logger.error("❌ Exercise inputs not found (cache path)")
            return False
        for i, inp in enumerate(cache_inputs[:len(cached)]):
            if cached[i]:
                _safe_click(driver, inp)
                _fill_input(driver, inp, cached[i])
                _human_delay(0.2, 0.4)
        time.sleep(config.EXERCISE_DELAY)
        if config.PAUSE_BEFORE_SUBMIT > 0:
            logger.info("⏸️  Pausing %ds (cache) — check the browser...", config.PAUSE_BEFORE_SUBMIT)
            time.sleep(config.PAUSE_BEFORE_SUBMIT)
        if not _submit_exercise(driver, subdomain):
            return False
        time.sleep(config.BETWEEN_EXERCISES)
        return True

    # --- Find all inputs & get per-blank AI answers ---
    logger.info("✏️  Filling exercise inputs...")
    all_inputs = _get_all_inputs(driver, subdomain)
    if not all_inputs:
        logger.error("❌ Exercise inputs not found after page load")
        return False

    n_blanks = len(all_inputs)
    logger.info("📋 Found %d blank(s)", n_blanks)

    dummy_answers = [""] * n_blanks
    char_limit = max(1500, n_blanks * 200)
    ai_input = question_text[:char_limit]
    logger.info("📤 Sending to DeepSeek (%d chars):\n%s", len(ai_input), ai_input)
    try:
        ai_raw = ai_service.answer_question(ai_input, n_blanks=n_blanks)
        if ai_raw:
            parsed = [a.strip() for a in ai_raw.split("|")]
            if len(parsed) < n_blanks:
                logger.info("⚠️  AI gave %d answer(s) for %d blank(s) — padding remainder with ''",
                            len(parsed), n_blanks)
            # Pad with empty string if AI gave fewer answers; trim if more
            dummy_answers = (parsed + [""] * n_blanks)[:n_blanks]
            logger.info("🤖 AI answers: %s", dummy_answers)
    except Exception as exc:
        logger.error("❌ AI call failed: %s", exc)

    for i, inp in enumerate(all_inputs):
        _safe_click(driver, inp)
        _fill_input(driver, inp, dummy_answers[i])
        _human_delay(0.2, 0.4)

    # --- Cache AI answers NOW (before submit) so we always have real words ---
    real_ai = [a for a in dummy_answers if a and a.strip()]
    if real_ai:
        ai_pairs = [
            {"blank": blank_sentences[i] if i < len(blank_sentences) else "", "answer": a}
            for i, a in enumerate(dummy_answers)
        ]
        logger.info("💾 Pre-caching AI answers: %s", dummy_answers)
        tracker.cache_answers(url, question_text, ai_pairs)

    time.sleep(config.EXERCISE_DELAY)
    if config.PAUSE_BEFORE_SUBMIT > 0:
        logger.info("⏸️  Pausing %ds — check the browser before submit...",
                    config.PAUSE_BEFORE_SUBMIT)
        time.sleep(config.PAUSE_BEFORE_SUBMIT)
    if not _submit_exercise(driver, subdomain):
        return False

    time.sleep(config.PAGE_LOAD_DELAY)

    # --- Try to read real corrections and upgrade the cache ---
    correct_answers = _read_corrections(driver)
    valid = [a for a in correct_answers if a and not a.strip().isdigit() and len(a.strip()) < 50]
    if len(valid) == len(correct_answers) and valid:
        logger.info("📝 Corrections (valid): %s", correct_answers)
        corr_pairs = [
            {"blank": blank_sentences[i] if i < len(blank_sentences) else "", "answer": a}
            for i, a in enumerate(correct_answers)
        ]
        tracker.cache_answers(url, question_text, corr_pairs)
        ai_service.record_result(question_text[:200], " | ".join(correct_answers))
    else:
        logger.warning("⚠️  Corrections invalid/partial: %s — keeping AI answers in cache", correct_answers)

    # --- Navigate back ---
    driver.get(url)
    time.sleep(config.PAGE_LOAD_DELAY + 1)
    _wait_for_page_stability(driver)

    relancer_buttons = driver.find_elements(By.XPATH, "//button[contains(.,'Relancer')]")
    target_index = max(-1 + (-step), -len(relancer_buttons))
    try:
        _safe_click(driver, relancer_buttons[target_index])
    except IndexError:
        logger.error("Relancer button index out of range.")
        return False

    time.sleep(config.PAGE_LOAD_DELAY)
    _wait_for_page_stability(driver)

    # --- Fill correct answers ---
    all_inputs2 = _get_all_inputs(driver, subdomain)
    if not all_inputs2:
        logger.error("Inputs not found on second pass.")
        return False

    for i, inp in enumerate(all_inputs2):
        ans = correct_answers[i] if i < len(correct_answers) else ""
        _safe_click(driver, inp)
        _fill_input(driver, inp, ans)
        _human_delay(0.2, 0.4)

    time.sleep(config.EXERCISE_DELAY)
    if not _submit_exercise(driver, subdomain):
        return False

    time.sleep(config.BETWEEN_EXERCISES)
    return True


def run_loop(driver: webdriver.Chrome, subdomain: str,
             tracker: Tracker, log_callback=None) -> None:
    """
    Continuous loop: solve exercises until target hours reached or no more left.
    log_callback(message) is called with status updates (used by the GUI).
    """
    def log(msg):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    consecutive_failures = 0

    while tracker.elapsed_hours() < config.TARGET_HOURS:
        log("📊 " + tracker.summary())
        try:
            success = solve_one_exercise(driver, subdomain, tracker)
            if success:
                tracker.record_success()
                consecutive_failures = 0
                log("✅ Exercise solved — " + tracker.summary())
            else:
                tracker.record_failure()
                consecutive_failures += 1
                log(f"❌ Exercise failed (consecutive: {consecutive_failures})")
                if consecutive_failures >= 5:
                    log("⏸️  5 consecutive failures — pausing 30s and retrying...")
                    time.sleep(30)
                    consecutive_failures = 0
        except Exception as e:
            tracker.record_failure()
            consecutive_failures += 1
            log(f"⚠️  Unexpected error: {e}")
            time.sleep(5)

    log("🏁 Target reached! Final: " + tracker.summary())
