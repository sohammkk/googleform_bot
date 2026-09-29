# Google Form Bot

Fills out a Google Form many times with Selenium, picking answers so the results match the percentages you choose for each question.

Only use it on forms you own, for example to generate test data for your results sheet or charts.

## Requirements

- Python 3.9 or newer
- Google Chrome (ChromeDriver is downloaded automatically by `webdriver-manager`)
- A Google Form that contains **only single-choice (radio button) questions** and does not require sign-in

## Installation

```powershell
git clone <repo-url>
cd googleform_bot

python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows (PowerShell)
# source .venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
```

If PowerShell blocks the activation script, run this first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## Setup

Copy the example config and edit it:

```powershell
Copy-Item config.example.json config.json   # Windows
# cp config.example.json config.json        # macOS / Linux
```

`config.json` is in `.gitignore`, so your form link is never committed.

```json
{
  "link": "https://forms.gle/your-form-id",
  "responses": 100,
  "percents": [
    [25, 75, 0],
    [2, 18, 42, 22, 12, 3, 1],
    [45, 25, 15, 12, 3]
  ]
}
```

| Key | Description |
|---|---|
| `link` | The form's share link (`forms.gle/...` or `docs.google.com/forms/...`). |
| `responses` | How many times the form is submitted. |
| `percents` | One list per question, in the order the questions appear on the form. Each list has one number per option, in the order the options appear, and must add up to 100. |

For example, `[25, 75, 0]` means about 25% of responses pick the first option, 75% the second, and none the third.

## Usage

```powershell
python main.py
```

Chrome windows open (up to 4 at a time), fill in the form and submit it. Each submission prints `Form #N submitted successfully` only after Google shows its confirmation page. Failures are printed as `ERROR`.

## Notes

- The percentages are approximate: counts are rounded down and the leftover slots are filled randomly. With few responses (under ~30) the results will not match the percentages closely.
- `percents` must have exactly one list per question. If the form has more questions than lists, every submission fails.
- If a list has more entries than the question has options, answers that point to a missing option are skipped. If that question is required, the submission fails.
- The script finds the submit button through Google's internal page structure, which Google can change at any time. If submissions start failing, that is the most likely cause.
