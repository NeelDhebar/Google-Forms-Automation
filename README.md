# Google Forms Automation 🤖

Automate Google Forms submissions using **Python + Playwright**.  
Tailored for the *"Analysing Consumer Awareness, Preference and Perception Towards Frido's Ergonomic Lifestyle Products"* survey (Ahmedabad University).

Supports **default answers** (from `defaults.json`) and **randomized answers** for all other questions.

---

## Form Question Map

| Index | Question | Type |
|-------|----------|------|
| **0** | Are you aware of the brand "Frido"? | Multiple Choice |
| **1** | Do you know about Ergonomic Lifestyle Products? | Multiple Choice |
| **2** | Where did you first hear about Frido? | Multiple Choice (15 options) |
| **3** | Which Frido product categories are you aware of? | Checkboxes (6 options) |
| **4** | Are you aware of specific health benefits? | Multiple Choice |
| **5** | Which product category would you prefer purchasing? | Multiple Choice |
| **6** | What primary purpose drives your interest in Frido? | Multiple Choice |
| **7** | Preferred budget per ergonomic product? | Multiple Choice |
| **8** | Rank product attributes (Q9 in form) | Ranking Grid 5×5 |
| **9** | Rank product offerings (Q10 in form) | Ranking Grid 5×5 |
| **10** | Perception Likert scale (30 statements) | Likert Grid 30×5 |
| **11** | Age | Multiple Choice |
| **12** | Gender | Multiple Choice |
| **13** | Annual income bracket | Multiple Choice |
| **14** | Highest education level | Multiple Choice |

---

## Features

- 🔁 Submit any number of responses with a single prompt
- ✅ **Question 0 (Q1) always answered "Yes"** by default (configurable in `defaults.json`)
- 🎲 All other questions randomized unless a default is specified
- ⚙️ Configure default answers via `defaults.json`
- 🗂️ Handles all question types: radio, checkbox, ranking grids, Likert scale
- 🤖 Uses Playwright for reliable browser automation with realistic user-agent

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/neeldhebar2/Google-Forms-Automation.git
cd Google-Forms-Automation
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure default answers (optional)

Edit `defaults.json` to fix specific question answers.  
Questions **not listed** in the file will be **fully randomized**.

```json
{
  "questions": {
    "0": {
      "answer": "Yes",
      "randomize": false
    },
    "12": {
      "answer": "Male",
      "randomize": false
    }
  }
}
```

---

## Usage

```bash
python automate.py
```

You'll see a prompt:

```
Enter the number of responses to submit: 10
```

The script opens a browser window (Chromium), navigates through all 4 form sections, and submits each response.

---

## Configuration via `defaults.json`

### Multiple Choice / Radio (most questions)

```json
"0": { "answer": "Yes" }
```

Valid answers for each question:

| Index | Valid Answer Values |
|-------|---------------------|
| 0, 1, 4 | `"Yes"`, `"No"`, `"Don't Know"` |
| 2 | Any of the 15 source options (e.g. `"Instagram"`, `"Doctor Recommendation"`) |
| 3 | *(see Checkboxes below)* |
| 5 | `"Ergonomic Seat & Back Cushions"`, `"Orthotic Footwear & Insoles"`, etc. |
| 6 | `"Relieving existing physical discomfort"`, `"Posture correction long-term spinal care"`, etc. |
| 7 | `"Below ₹1,000"`, `"₹1,000 – ₹2,500"`, `"₹2,500 – ₹5,000"`, `"Above ₹5,000"` |
| 11 | `"18–25 years"`, `"26–35 years"`, `"36–50 years"`, `"Above 50 years"` |
| 12 | `"Male"`, `"Female"`, `"Prefer not to say"`, `"Other"` |
| 13 | `"Below ₹3,00,000"`, `"₹3,00,000 – ₹9,00,000"`, `"₹9,00,001 – ₹15,00,000"`, `"Above ₹15,00,000"` |
| 14 | `"High School"`, `"Bachelor's Degree"`, `"Master's Degree"`, `"Doctorate / Professional"` |

### Checkboxes (Q3 — index 3)

Provide `"answer"` as a **list**:

```json
"3": {
  "answer": ["Seat Cushions & Lumbar Back Supports", "Ergonomic Office Chairs"]
}
```

### Likert Scale (Q10 — index 10)

Provide `"answer"` as `SD`, `D`, `N`, `A`, or `SA` to fix **all 30 rows** to the same response:

```json
"10": { "answer": "A" }
```

Leave it out to randomize each row individually.

### Ranking Grids (Q8/Q9 — indices 8/9)

Provide `"answer"` as a dict mapping **row index → rank (1–5)**:

```json
"8": {
  "answer": { "0": "1", "1": "2", "2": "3", "3": "4", "4": "5" }
}
```

### Force Randomization

Add `"randomize": true` to override any default and always randomize that question:

```json
"0": { "answer": "Yes", "randomize": true }
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FORM_URL` | *(Frido form URL)* | Google Form URL to target |
| `HEADLESS` | `false` | Set `true` to hide the browser window |
| `SLOW_MO` | `120` | Milliseconds between Playwright actions |

```bash
# Example: run headlessly with slower actions
set HEADLESS=true
set SLOW_MO=200
python automate.py
```

---

## Notes

- Playwright must have Chromium installed — run `playwright install chromium` once after setup.
- The form must be **publicly accessible** (no Google login required).
- The script navigates through all 4 form sections automatically.
- A random delay of 2–4.5 seconds is added between submissions to avoid rate limiting.

---

## License

MIT
