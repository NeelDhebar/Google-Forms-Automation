"""
Google Forms Automation — Frido Consumer Survey
================================================
Form: "Analysing Consumer Awareness, Preference and Perception
       Towards Frido's Ergonomic Lifestyle Products" (Ahmedabad University)
URL : https://forms.gle/iVpffvxRmVHuLL2cA

IMPORTANT: This form loads ALL questions on a single page (no pagination).
All 15 questions are rendered at once with "Next" buttons for visual sections.

DOM structure (from debug):
- 15 question blocks found via div[data-params]
- 439 total [role="radio"] elements
- 21 total [role="checkbox"] elements (Q2=15 checkboxes, Q3=6 checkboxes)
- Radios have data-value and aria-label attributes
- Checkboxes have aria-label attributes

Question map (flat radio/checkbox indices)
------------------------------------------
Q0  — Are you aware of "Frido"?                    [radio 0-2: Yes/No/Don't Know]
Q1  — Know Ergonomic Products?                     [radio 3-5: Yes/No/Don't Know]
Q2  — Where first heard about Frido?               [checkbox 0-14: 15 source options]
Q3  — Product categories aware of?                 [checkbox 15-20: 6 options]
Q4  — Aware of health benefits?                    [radio 6-8: Yes/No/Don't Know]
Q5  — Preferred product category?                  [radio 9-13: 5 options]
Q6  — Primary purpose?                             [radio 14-18: 5 options]
Q7  — Budget?                                      [radio 19-22: 4 options]
Q8  — Rank product attributes                      [radio 23-47: 5 rows × 5 cols = 25]
Q9  — Rank product offerings                       [radio 48-72: 5 rows × 5 cols = 25]
Q10 — Perception Likert (30 statements)            [radio 73-222: 30 rows × 5 cols = 150]
      (Wait — debug says 300 radios! That's 30 statements BUT the form may
       have sub-rows or SD/D/N/A/SA rendered twice. Debug showed total=439.
       23+25+25+150=223 before Q10. 439-9-5-5-4 = 416 for grids+likert.)

Actually: let's just use flat indices from the debug output:
  Q0: radio[0..2]     3 radios
  Q1: radio[3..5]     3 radios
  Q4: radio[6..8]     3 radios
  Q5: radio[9..13]    5 radios
  Q6: radio[14..18]   5 radios
  Q7: radio[19..22]   4 radios
  Q8: radio[23..47]   25 radios (5×5 grid)
  Q9: radio[48..72]   25 radios (5×5 grid)
  Q10: radio[73..222] 150 radios (30×5) — WAIT debug says 300 in listitem[31]
       Let's recalc: 3+3+3+5+5+4+25+25 = 73. 439-73 = 366 for Q10+Q11-Q14.
       Q11-Q14: 4+4+4+4=16. So Q10 = 439-73-16 = 350 radios.
       But 30 statements × 5 cols = 150. Debug says listitem[31] has 300 radios.
       This means 300/5 = 60 rows, not 30 — maybe each statement is split into
       sub-question rows. Or 300/30 = 10 cols? Doesn't matter — we'll handle it
       dynamically.
  Q11: last 16 radios → Q11=4, Q12=4, Q13=4, Q14=4

For the safest approach, we use div[data-params] to get 15 question blocks,
then click radios/checkboxes WITHIN each block.
"""

import json
import os
import random
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Locator

# ── Configuration ─────────────────────────────────────────────────────────────

FORM_URL      = os.environ.get("FORM_URL", "https://forms.gle/iVpffvxRmVHuLL2cA")
HEADLESS      = os.environ.get("HEADLESS", "false").lower() == "true"
SLOW_MO       = int(os.environ.get("SLOW_MO", "120"))
DEFAULTS_FILE = Path(__file__).parent / "defaults.json"

# ── Option labels per question (order must match the form) ────────────────────

Q_OPTIONS = {
    0: ["Yes", "No", "Don't Know"],
    1: ["Yes", "No", "Don't Know"],
    2: [  # checkboxes — pick 1 or more
        "Instagram", "Facebook", "YouTube Video Ads", "Google Search Results",
        "Amazon Product Listings", "Flipkart Store Pages", "Friend Recommendation",
        "Family Recommendation", "Workplace Colleague", "Doctor Recommendation",
        "Physiotherapist Advice", "Online Health Blogs", "Influencer Reviews",
        "Newspaper Feature", "Retail Store Display",
    ],
    3: [  # checkboxes — pick 1 or more
        "Seat Cushions & Lumbar Back Supports",
        "Orthotic Insoles & Footwear",
        "Ergonomic Office Chairs",
        "Neck & Sleep Contoured Pillows",
        "Joint Support Braces",
        "None of the above",
    ],
    4: ["Yes", "No", "Don't Know"],
    5: [
        "Ergonomic Seat & Back Cushions",
        "Orthotic Footwear & Insoles",
        "Neck & Spinal Support Pillows",
        "Ergonomic Office Chairs",
        "Posture Correction Support Accessories",
    ],
    6: [
        "Relieving existing physical discomfort",
        "Posture correction long-term spinal care",
        "Enhancing routine working sitting comfort",
        "Medical professional advice recommendation",
        "Everyday personal physical wellness",
    ],
    7: [
        "Below ₹1,000", "₹1,000 – ₹2,500",
        "₹2,500 – ₹5,000", "Above ₹5,000",
    ],
    # 8, 9, 10 are grids — handled separately
    11: ["18–25 years", "26–35 years", "36–50 years", "Above 50 years"],
    12: ["Male", "Female", "Prefer not to say", "Other"],
    13: [
        "Below ₹3,00,000", "₹3,00,000 – ₹9,00,000",
        "₹9,00,001 – ₹15,00,000", "Above ₹15,00,000",
    ],
    14: ["High School", "Bachelor's Degree", "Master's Degree", "Doctorate / Professional"],
}

# Question types: maps question index → "radio", "checkbox", or "grid"
Q_TYPES = {
    0: "radio", 1: "radio", 2: "checkbox", 3: "checkbox", 4: "radio",
    5: "radio", 6: "radio", 7: "radio",
    8: "grid", 9: "grid", 10: "grid",
    11: "radio", 12: "radio", 13: "radio", 14: "radio",
}

# Grid dimensions
GRID_INFO = {
    8:  {"rows": 5,  "cols": 5},
    9:  {"rows": 5,  "cols": 5},
    10: {"rows": 30, "cols": 5},   # actual DOM may have more — we handle dynamically
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_defaults() -> dict:
    if DEFAULTS_FILE.exists():
        with DEFAULTS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("questions", {})
    return {}


def _resolve(q_idx: int, defaults: dict):
    """Return the configured answer from defaults, or None."""
    entry = defaults.get(str(q_idx), {})
    if not isinstance(entry, dict):
        return entry
    if entry.get("randomize", False):
        return None
    return entry.get("answer")


def _find_option_index(q_idx: int, answer_text: str) -> int | None:
    """Map an answer label to its positional index within Q_OPTIONS[q_idx]."""
    opts = Q_OPTIONS.get(q_idx, [])
    answer_l = answer_text.lower().strip()
    for i, opt in enumerate(opts):
        if answer_l == opt.lower() or answer_l in opt.lower():
            return i
    return None


def get_question_blocks(page: Page) -> list[Locator]:
    """
    Return all 15 question blocks using div[data-params].
    This is the most reliable selector for Google Forms — each question
    container has a data-params attribute with its configuration.
    """
    blocks = page.locator('div[data-params]')
    result = []
    for i in range(blocks.count()):
        result.append(blocks.nth(i))
    return result


# ── Answer functions ──────────────────────────────────────────────────────────

def answer_radio_question(page: Page, block: Locator, q_idx: int, defaults: dict) -> None:
    """Answer a single-choice radio question by clicking the correct option."""
    want = _resolve(q_idx, defaults)
    opts = Q_OPTIONS.get(q_idx, [])

    # Determine which option index to click
    if want:
        idx = _find_option_index(q_idx, want)
        if idx is None:
            print(f"    Q{q_idx} [radio]: default '{want}' not found — randomizing")
            idx = random.randint(0, len(opts) - 1) if opts else 0
        else:
            print(f"    Q{q_idx} [radio]: {want} → index {idx}")
    else:
        idx = random.randint(0, len(opts) - 1) if opts else 0
        print(f"    Q{q_idx} [radio]: {opts[idx] if idx < len(opts) else '?'} → index {idx}")

    # Click the radio within this specific question block
    radios = block.locator('[role="radio"]')
    count = radios.count()
    if count == 0:
        print(f"    ⚠  Q{q_idx}: no radios found in block!")
        return
    idx = min(idx, count - 1)
    radios.nth(idx).click()
    page.wait_for_timeout(200)


def answer_checkbox_question(page: Page, block: Locator, q_idx: int, defaults: dict) -> None:
    """Answer a multi-choice checkbox question."""
    want = _resolve(q_idx, defaults)
    opts = Q_OPTIONS.get(q_idx, [])

    checkboxes = block.locator('[role="checkbox"]')
    count = checkboxes.count()
    if count == 0:
        print(f"    ⚠  Q{q_idx}: no checkboxes found in block!")
        return

    # Determine which checkboxes to tick
    if want:
        chosen_labels = want if isinstance(want, list) else [want]
        indices = []
        for lbl in chosen_labels:
            idx = _find_option_index(q_idx, lbl)
            if idx is not None and idx < count:
                indices.append(idx)
        if not indices:
            print(f"    Q{q_idx} [checkbox]: defaults not matched — randomizing")
            indices = _random_checkbox_indices(opts, count)
        else:
            print(f"    Q{q_idx} [checkbox]: {chosen_labels} → indices {indices}")
    else:
        indices = _random_checkbox_indices(opts, count)
        labels = [opts[i] if i < len(opts) else "?" for i in indices]
        print(f"    Q{q_idx} [checkbox]: {labels} → indices {indices}")

    for idx in indices:
        checkboxes.nth(idx).click()
        page.wait_for_timeout(100)


def _random_checkbox_indices(opts: list, count: int) -> list[int]:
    """Pick 1–3 random checkbox indices, avoiding 'None of the above'."""
    # Exclude the last option if it's "None of the above"
    valid = list(range(count))
    if opts and "none" in opts[-1].lower():
        valid = list(range(max(1, count - 1)))
    num = random.randint(1, min(3, len(valid)))
    return random.sample(valid, num)


def answer_grid_question(page: Page, block: Locator, q_idx: int,
                         defaults: dict) -> None:
    """
    Answer a grid/matrix question by clicking one radio per row.
    
    IMPORTANT: Google Forms grid blocks contain BOTH real radios and disabled
    placeholder radios (aria-disabled="true", data-value=""). We must filter
    to only the real, enabled ones.
    """
    # Filter: only radios that are NOT disabled placeholders
    radios = block.locator('[role="radio"]:not([aria-disabled="true"])')
    total = radios.count()

    if total == 0:
        # Fallback: try all radios
        radios = block.locator('[role="radio"]')
        total = radios.count()

    if total == 0:
        print(f"    ⚠  Q{q_idx}: no radios found in grid block!")
        return

    info = GRID_INFO.get(q_idx, {"rows": 5, "cols": 5})
    num_cols = info["cols"]

    # Infer actual number of rows from the enabled radios
    num_rows = total // num_cols
    if num_rows == 0:
        print(f"    ⚠  Q{q_idx}: grid has {total} enabled radios, can't infer rows for {num_cols} cols")
        return

    print(f"    Q{q_idx} [grid {num_rows}×{num_cols}]: randomized ({total} enabled radios)")

    for r in range(num_rows):
        col = random.randint(0, num_cols - 1)
        flat_idx = r * num_cols + col
        if flat_idx < total:
            radio = radios.nth(flat_idx)
            try:
                radio.scroll_into_view_if_needed(timeout=3000)
                page.wait_for_timeout(50)
                radio.click(timeout=5000)
            except Exception as e:
                print(f"      ⚠  row {r} col {col}: {e}")
            # Shorter delay for large grids
            if num_rows > 10:
                page.wait_for_timeout(30)
            else:
                page.wait_for_timeout(60)


# ── Form filler ───────────────────────────────────────────────────────────────

def fill_form(page: Page, defaults: dict) -> None:
    """Fill all 15 questions on the form, navigating between sections."""

    page.wait_for_load_state("networkidle", timeout=20_000)
    page.wait_for_timeout(1500)

    blocks = get_question_blocks(page)
    print(f"\n  Found {len(blocks)} question blocks (div[data-params])")

    if len(blocks) < 15:
        print(f"  ⚠  Expected 15 question blocks, found {len(blocks)}")

    # Define which questions belong to each visual section
    sections = [
        ("Section A: Awareness",    [0, 1, 2, 3, 4]),
        ("Section B: Preference",   [5, 6, 7, 8, 9]),
        ("Section C: Perception",   [10]),
        ("Section D: Demographics", [11, 12, 13, 14]),
    ]

    for sec_idx, (sec_name, q_indices) in enumerate(sections):
        print(f"\n  ── {sec_name} ──")

        for q_idx in q_indices:
            if q_idx >= len(blocks):
                print(f"    ⚠  No block for Q{q_idx}")
                continue

            block = blocks[q_idx]

            # Scroll into view
            try:
                block.scroll_into_view_if_needed(timeout=5000)
            except Exception:
                pass
            page.wait_for_timeout(150)

            q_type = Q_TYPES.get(q_idx, "radio")

            if q_type == "radio":
                answer_radio_question(page, block, q_idx, defaults)
            elif q_type == "checkbox":
                answer_checkbox_question(page, block, q_idx, defaults)
            elif q_type == "grid":
                answer_grid_question(page, block, q_idx, defaults)

        # After each section (except the last), click "Next"
        if sec_idx < len(sections) - 1:
            _click_next(page)

    # Final: click Submit
    _click_submit(page)


def _click_next(page: Page) -> None:
    """Click the 'Next' button if visible."""
    try:
        btn = page.locator(
            'div[role="button"]:has-text("Next"), '
            '[jsname="OCpkoe"]'
        ).first
        btn.scroll_into_view_if_needed(timeout=3000)
        page.wait_for_timeout(200)
        btn.click()
        page.wait_for_load_state("networkidle", timeout=15_000)
        page.wait_for_timeout(1000)
        print("  → Next")
    except Exception as e:
        # No Next button — form might show all sections at once
        print(f"  (no Next button — continuing)")


def _click_submit(page: Page) -> bool:
    """Click 'Submit' and check for confirmation."""
    try:
        btn = page.locator(
            'div[role="button"]:has-text("Submit"), '
            '[jsname="M2UYVd"]'
        ).first
        btn.scroll_into_view_if_needed(timeout=3000)
        page.wait_for_timeout(300)
        btn.click()
        page.wait_for_timeout(3000)
        body = page.locator("body").inner_text(timeout=5000).lower()
        if "recorded" in body or "submitted" in body:
            print("  ✅ Submitted successfully!")
            return True
        print("  ⚠  Submission may not have been confirmed.")
        return False
    except Exception as e:
        print(f"  ⚠  Submit: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def submit_response(page: Page, num: int, total: int, defaults: dict) -> bool:
    """Open the form, fill it, and submit."""
    print(f"\n{'─'*55}")
    print(f"[{num}/{total}] Opening form …")
    page.goto(FORM_URL, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(2000)

    try:
        fill_form(page, defaults)
        return True
    except Exception as exc:
        print(f"  ❌ Error: {exc}")
        import traceback
        traceback.print_exc()
        return False


def main() -> None:
    print("=" * 55)
    print("  Google Forms Automation — Frido Survey")
    print("=" * 55)
    print(f"  Form URL : {FORM_URL}")
    print(f"  Defaults : {DEFAULTS_FILE.name}")
    print(f"  Headless : {HEADLESS}")
    print("=" * 55)

    while True:
        try:
            raw = input("\nEnter the number of responses to submit: ").strip()
            num_responses = int(raw)
            if num_responses <= 0:
                raise ValueError
            break
        except ValueError:
            print("  Please enter a positive integer.")

    defaults = load_defaults()
    print(f"\nLoaded {len(defaults)} default answer(s) from {DEFAULTS_FILE.name}")
    if defaults:
        for idx, val in defaults.items():
            print(f"  Q{idx} → {val}")

    successes = 0
    failures  = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )

        for i in range(1, num_responses + 1):
            page = context.new_page()
            try:
                ok = submit_response(page, i, num_responses, defaults)
                if ok:
                    successes += 1
                else:
                    failures += 1
            except Exception as exc:
                print(f"  ❌ Uncaught error on submission {i}: {exc}")
                failures += 1
            finally:
                page.close()

            if i < num_responses:
                delay = random.uniform(2.0, 4.5)
                print(f"  ⏳ Waiting {delay:.1f}s …")
                time.sleep(delay)

        browser.close()

    print("\n" + "=" * 55)
    print(f"  Done!  ✅ {successes} successful   ❌ {failures} failed")
    print("=" * 55)


if __name__ == "__main__":
    main()
