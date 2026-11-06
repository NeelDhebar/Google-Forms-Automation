"""
Google Forms Automation — Frido Consumer Survey
================================================
Form: "Analysing Consumer Awareness, Preference and Perception
       Towards Frido's Ergonomic Lifestyle Products" (Ahmedabad University)
URL : https://forms.gle/iVpffvxRmVHuLL2cA

Question map
------------
Q0  (index 0)  — Are you aware of the brand "Frido"?           [radio, 3 opts]
Q1  (index 1)  — Do you know about Ergonomic Lifestyle Products?[radio, 3 opts]
Q2  (index 2)  — Where did you first hear about Frido?         [radio, 15 opts]
Q3  (index 3)  — Which Frido product categories are you aware? [checkbox, 6 opts]
Q4  (index 4)  — Aware of specific health benefits?            [radio, 3 opts]
Q5  (index 5)  — Which product category prefer purchasing?     [radio, 5 opts]
Q6  (index 6)  — What primary purpose drives interest?         [radio, 5 opts]
Q7  (index 7)  — Preferred budget per ergonomic product?       [radio, 4 opts]
Q8  (index 8)  — Rank product attributes (Q9 in form)          [grid 5×5]
Q9  (index 9)  — Rank product offerings  (Q10 in form)         [grid 5×5]
Q10 (index 10) — Perception Likert scale (30 statements×5)    [likert grid]
Q11 (index 11) — Age                                           [radio, 4 opts]
Q12 (index 12) — Gender                                        [radio, 4 opts]
Q13 (index 13) — Annual income bracket                         [radio, 4 opts]
Q14 (index 14) — Highest education level                       [radio, 4 opts]
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

# ── Form-specific answer pools ────────────────────────────────────────────────

ANSWER_POOLS = {
    # Q0 — Aware of Frido?
    0: ["Yes", "No", "Don't Know"],
    # Q1 — Know Ergonomic products?
    1: ["Yes", "No", "Don't Know"],
    # Q2 — Where first heard
    2: [
        "Instagram", "Facebook", "YouTube Video Ads", "Google Search Results",
        "Amazon Product Listings", "Flipkart Store Pages", "Friend Recommendation",
        "Family Recommendation", "Workplace Colleague", "Doctor Recommendation",
        "Physiotherapist Advice", "Online Health Blogs", "Influencer Reviews",
        "Newspaper Feature", "Retail Store Display",
    ],
    # Q3 — Product categories aware of (checkboxes)
    3: [
        "Seat Cushions & Lumbar Back Supports",
        "Orthotic Insoles & Footwear",
        "Ergonomic Office Chairs",
        "Neck & Sleep Contoured Pillows",
        "Joint Support Braces",
        "None of the above",
    ],
    # Q4 — Aware of health benefits?
    4: ["Yes", "No", "Don't Know"],
    # Q5 — Preferred product category
    5: [
        "Ergonomic Seat & Back Cushions",
        "Orthotic Footwear & Insoles",
        "Neck & Spinal Support Pillows",
        "Ergonomic Office Chairs",
        "Posture Correction Support Accessories",
    ],
    # Q6 — Primary purpose
    6: [
        "Relieving existing physical discomfort",
        "Posture correction long-term spinal care",
        "Enhancing routine working sitting comfort",
        "Medical professional advice recommendation",
        "Everyday personal physical wellness",
    ],
    # Q7 — Budget
    7: [
        "Below ₹1,000",
        "₹1,000 – ₹2,500",
        "₹2,500 – ₹5,000",
        "Above ₹5,000",
    ],
    # Q8 — Rank product attributes (grid 5 rows × cols 1-5)
    # Stored as list of [row_label, column_value] — randomized per row
    8: {
        "type": "ranking_grid",
        "rows": [
            "Ergonomic Design & Body Alignment Contour",
            "Material Quality & Product Durability",
            "Pricing Affordability & Value Ratio",
            "Medical Credibility & Orthopedic Testing",
            "Brand Reputation & Verified Reviews",
        ],
        "cols": ["1", "2", "3", "4", "5"],
    },
    # Q9 — Rank product offerings (grid 5 rows × cols 1-5)
    9: {
        "type": "ranking_grid",
        "rows": [
            "Desk Seating Memory Foam Support Cushions",
            "Customizable Arch Support Orthotic Foot Insoles",
            "Contoured Spinal Cervical Sleep Pillows",
            "Adjustable Lumbar Workstation Office Chairs",
            "Portable Travel Posture Support Cushions",
        ],
        "cols": ["1", "2", "3", "4", "5"],
    },
    # Q10 — Likert scale (30 statements × 5 options SD-SA)
    10: {
        "type": "likert_grid",
        "cols": ["SD", "D", "N", "A", "SA"],
        "num_rows": 30,
    },
    # Q11 — Age
    11: ["18–25 years", "26–35 years", "36–50 years", "Above 50 years"],
    # Q12 — Gender
    12: ["Male", "Female", "Prefer not to say", "Other"],
    # Q13 — Annual income
    13: [
        "Below ₹3,00,000",
        "₹3,00,000 – ₹9,00,000",
        "₹9,00,001 – ₹15,00,000",
        "Above ₹15,00,000",
    ],
    # Q14 — Education
    14: [
        "High School",
        "Bachelor's Degree",
        "Master's Degree",
        "Doctorate / Professional",
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_defaults() -> dict:
    if DEFAULTS_FILE.exists():
        with DEFAULTS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("questions", {})
    return {}


def pick_radio_option(page: Page, options: Locator, want: str | None) -> None:
    """Click a radio option — by label match if want is given, else random."""
    count = options.count()
    if count == 0:
        return
    if want:
        for i in range(count):
            try:
                # The label text lives in the parent container
                parent = options.nth(i).locator("xpath=..")
                label = parent.inner_text(timeout=2000).strip()
            except Exception:
                label = ""
            if want.lower() in label.lower():
                options.nth(i).click()
                return
        print(f"    ⚠  '{want}' not found; randomizing.")
    options.nth(random.randint(0, count - 1)).click()


def fill_ranking_grid(page: Page, grid_el: Locator, default_rows: dict | None) -> None:
    """
    Fill a 5×5 ranking grid.
    Each row gets a unique rank from 1-5 (a random permutation).
    default_rows: optional dict mapping row-index (str) → column value (str "1"–"5")
    """
    rows = grid_el.locator('[role="row"]')
    row_count = rows.count()
    if row_count == 0:
        # Fallback: try to find radio buttons inside the grid
        radios = grid_el.locator('[role="radio"]')
        total  = radios.count()
        # Assume 5 cols
        cols   = 5
        for r in range(total // cols):
            choice = random.randint(0, cols - 1)
            radios.nth(r * cols + choice).click()
            page.wait_for_timeout(100)
        return

    perm = list(range(5))
    random.shuffle(perm)      # unique rank assignment per row

    for r in range(row_count):
        row_el = rows.nth(r)
        # Skip header row
        if row_el.locator('[role="columnheader"]').count() > 0:
            continue
        cells = row_el.locator('[role="gridcell"]')
        cell_count = cells.count()
        if cell_count == 0:
            continue

        # Determine which column to pick
        col_idx = perm[r % len(perm)]
        col_idx = min(col_idx, cell_count - 1)

        # Check default for this row
        if default_rows and str(r) in default_rows:
            try:
                col_idx = int(default_rows[str(r)]) - 1
            except (ValueError, TypeError):
                pass

        radio = cells.nth(col_idx).locator('[role="radio"]')
        if radio.count() > 0:
            radio.first.click()
        else:
            cells.nth(col_idx).click()
        page.wait_for_timeout(80)


def fill_likert_grid(page: Page, grid_el: Locator, default_col: str | None) -> None:
    """
    Fill a Likert-scale grid (30 rows × 5 cols).
    Each row gets a random column unless default_col is given (SD/D/N/A/SA).
    """
    rows = grid_el.locator('[role="row"]')
    row_count = rows.count()

    # Map text → index
    likert_map = {"SD": 0, "D": 1, "N": 2, "A": 3, "SA": 4}
    default_idx = likert_map.get((default_col or "").upper())

    for r in range(row_count):
        row_el = rows.nth(r)
        if row_el.locator('[role="columnheader"]').count() > 0:
            continue
        cells = row_el.locator('[role="gridcell"]')
        cell_count = cells.count()
        if cell_count == 0:
            continue

        col_idx = default_idx if default_idx is not None else random.randint(0, cell_count - 1)
        col_idx = min(col_idx, cell_count - 1)

        radio = cells.nth(col_idx).locator('[role="radio"]')
        if radio.count() > 0:
            radio.first.click()
        else:
            cells.nth(col_idx).click()
        page.wait_for_timeout(60)


# ── Form Filler ───────────────────────────────────────────────────────────────

def fill_all_questions(page: Page, defaults: dict) -> None:
    """Fill the entire form (all sections) using the known question map."""

    page.wait_for_load_state("networkidle", timeout=20_000)
    page.wait_for_timeout(1000)

    # ── SECTION A ─────────────────────────────────────────────────────────────
    print("\n  ── Section A: Awareness ──")

    _answer_radio(page, 0, defaults)   # Q0
    _answer_radio(page, 1, defaults)   # Q1
    _answer_radio(page, 2, defaults)   # Q2
    _answer_checkbox(page, 3, defaults)# Q3
    _answer_radio(page, 4, defaults)   # Q4

    _click_next(page)

    # ── SECTION B ─────────────────────────────────────────────────────────────
    print("\n  ── Section B: Preference ──")

    _answer_radio(page, 5, defaults)   # Q5
    _answer_radio(page, 6, defaults)   # Q6
    _answer_radio(page, 7, defaults)   # Q7
    _answer_grid(page, 8, defaults)    # Q8  — ranking grid
    _answer_grid(page, 9, defaults)    # Q9  — ranking grid

    _click_next(page)

    # ── SECTION C ─────────────────────────────────────────────────────────────
    print("\n  ── Section C: Perception Likert ──")

    _answer_likert(page, 10, defaults) # Q10

    _click_next(page)

    # ── SECTION D ─────────────────────────────────────────────────────────────
    print("\n  ── Section D: Demographics ──")

    _answer_radio(page, 11, defaults)  # Q11
    _answer_radio(page, 12, defaults)  # Q12
    _answer_radio(page, 13, defaults)  # Q13
    _answer_radio(page, 14, defaults)  # Q14

    _click_submit(page)


# ── Per-question helpers ──────────────────────────────────────────────────────

def _resolve(q_idx: int, defaults: dict):
    """Return (answer, force_random) from defaults, or (None, False)."""
    entry = defaults.get(str(q_idx), {})
    if not isinstance(entry, dict):
        return entry, False
    force_random = entry.get("randomize", False)
    answer = None if force_random else entry.get("answer")
    return answer, force_random


def _answer_radio(page: Page, q_idx: int, defaults: dict) -> None:
    answer, _ = _resolve(q_idx, defaults)
    pool = ANSWER_POOLS.get(q_idx, [])
    want = answer if answer else (random.choice(pool) if pool else None)
    print(f"    Q{q_idx} [radio]: {want}")

    # Locate all radio buttons on the page and find the right group
    # Google Forms groups each question's radios by jsname or data-answer-value
    # We identify the question by its index among visible question blocks.
    q_block = _get_question_block(page, q_idx)
    if q_block is None:
        print(f"    ⚠  Could not locate Q{q_idx} block.")
        return

    radios = q_block.locator('[role="radio"]')
    pick_radio_option(page, radios, want)
    page.wait_for_timeout(150)


def _answer_checkbox(page: Page, q_idx: int, defaults: dict) -> None:
    answer, _ = _resolve(q_idx, defaults)
    pool = ANSWER_POOLS.get(q_idx, [])

    # Determine which options to tick
    if answer:
        chosen = answer if isinstance(answer, list) else [answer]
    else:
        # Avoid picking "None of the above" together with real options
        real_opts = [o for o in pool if "none" not in o.lower()]
        num = random.randint(1, min(3, len(real_opts)))
        chosen = random.sample(real_opts, num)

    print(f"    Q{q_idx} [checkbox]: {chosen}")

    q_block = _get_question_block(page, q_idx)
    if q_block is None:
        print(f"    ⚠  Could not locate Q{q_idx} block.")
        return

    checkboxes = q_block.locator('[role="checkbox"]')
    count = checkboxes.count()
    for i in range(count):
        try:
            parent = checkboxes.nth(i).locator("xpath=..")
            label = parent.inner_text(timeout=2000).strip()
        except Exception:
            label = ""
        if any(c.lower() in label.lower() for c in chosen):
            checkboxes.nth(i).click()
            page.wait_for_timeout(100)


def _answer_grid(page: Page, q_idx: int, defaults: dict) -> None:
    """Fill a ranking grid question."""
    answer, _ = _resolve(q_idx, defaults)
    print(f"    Q{q_idx} [ranking grid]: randomized per row")

    q_block = _get_question_block(page, q_idx)
    if q_block is None:
        print(f"    ⚠  Could not locate Q{q_idx} block.")
        return

    default_rows = answer if isinstance(answer, dict) else None
    fill_ranking_grid(page, q_block, default_rows)


def _answer_likert(page: Page, q_idx: int, defaults: dict) -> None:
    """Fill the 30-statement Likert grid."""
    answer, _ = _resolve(q_idx, defaults)
    default_col = answer if isinstance(answer, str) else None
    print(f"    Q{q_idx} [likert grid 30 rows]: "
          f"{'all ' + default_col if default_col else 'randomized'}")

    q_block = _get_question_block(page, q_idx)
    if q_block is None:
        # Fallback: search the whole page for the grid
        grid = page.locator('[role="grid"]').first
        if grid.count() > 0:
            fill_likert_grid(page, grid, default_col)
        else:
            print(f"    ⚠  Could not locate Q{q_idx} Likert grid.")
        return

    fill_likert_grid(page, q_block, default_col)


# ── Navigation helpers ────────────────────────────────────────────────────────

def _get_question_block(page: Page, q_idx: int) -> Locator | None:
    """
    Return the Locator for the q_idx-th question block on the current page.
    Google Forms wraps each question in a [role="listitem"] or a freebirdForm… div.
    """
    # Primary selector used by modern Google Forms
    selectors = [
        '.freebirdFormviewerViewItemsItemItem',
        '.freebirdFormviewerComponentsQuestionBaseRoot',
        '[role="listitem"]',
    ]
    for sel in selectors:
        blocks = page.locator(sel)
        if blocks.count() > q_idx:
            return blocks.nth(q_idx)
    return None


def _click_next(page: Page) -> None:
    """Click the Next button and wait for the next section to load."""
    next_btn = page.locator(
        'div[role="button"]:has-text("Next"), '
        '[jsname="OCpkoe"], '
        'button:has-text("Next")'
    ).first
    if next_btn.is_visible(timeout=5000):
        next_btn.click()
        page.wait_for_load_state("networkidle", timeout=15_000)
        page.wait_for_timeout(1000)
    else:
        print("    ⚠  Next button not found!")


def _click_submit(page: Page) -> bool:
    """Click Submit and verify confirmation."""
    submit_btn = page.locator(
        'div[role="button"]:has-text("Submit"), '
        '[jsname="M2UYVd"], '
        'button:has-text("Submit")'
    ).first
    if submit_btn.is_visible(timeout=5000):
        submit_btn.click()
        page.wait_for_timeout(2500)
        # Check for confirmation
        if ("formResponse" in page.url or
                page.locator(':has-text("Your response has been recorded")').count() > 0 or
                page.locator(':has-text("response was recorded")').count() > 0):
            print("  ✅ Submitted successfully!")
            return True
        print("  ⚠  Submission may not have been confirmed.")
        return False
    print("    ⚠  Submit button not found!")
    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def submit_response(page: Page, submission_num: int, total: int, defaults: dict) -> bool:
    """Open the form, fill it out, and submit one response."""
    print(f"\n{'─'*55}")
    print(f"[{submission_num}/{total}] Opening form …")
    page.goto(FORM_URL, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(1500)

    try:
        fill_all_questions(page, defaults)
        return True
    except Exception as exc:
        print(f"  ❌ Error: {exc}")
        return False


def main() -> None:
    print("=" * 55)
    print("  Google Forms Automation — Frido Survey")
    print("=" * 55)
    print(f"  Form URL : {FORM_URL}")
    print(f"  Defaults : {DEFAULTS_FILE.name}")
    print(f"  Headless : {HEADLESS}")
    print("=" * 55)

    # Prompt for number of responses
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

            # Pause between submissions
            if i < num_responses:
                delay = random.uniform(2.0, 4.5)
                print(f"  ⏳ Waiting {delay:.1f}s before next submission …")
                time.sleep(delay)

        browser.close()

    print("\n" + "=" * 55)
    print(f"  Done!  ✅ {successes} successful   ❌ {failures} failed")
    print("=" * 55)


if __name__ == "__main__":
    main()
