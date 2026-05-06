# CoverBot — AI Health Insurance Plan Assistant

CoverBot is a web-based AI assistant that helps users understand and compare ACA health insurance plans using CMS Marketplace API data and Claude AI.

Users can enter their basic profile, search available plans, compare plan costs, check drug coverage, and ask follow-up questions in simple English.

---

## Features

- Guided plan intake form
- ACA plan search using CMS Marketplace API
- Plan comparison cards
- Drug coverage checker
- Claude-powered insurance explanation
- Context-aware chat using selected plan and user profile
- Official benefits, network, and formulary links
- Safe handling for missing CMS drug coverage data

---

## Architecture

```text
User Input
   ↓
React Frontend
   ↓
FastAPI Backend
   ↓
Claude AI + CMS Marketplace API
   ↓
Plan Search / Drug Coverage / AI Explanation
   ↓
Response shown in UI
```

---

## Folder Structure

```text
wiki-agent/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
│
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── public/
    │   └── index.html
    └── src/
        ├── App.js
        ├── App.css
        └── index.js
```

---

## Tech Stack

```text
Backend:
- Python
- FastAPI
- Uvicorn
- httpx
- Pydantic
- python-dotenv
- Anthropic Claude API
- CMS Marketplace API

Frontend:
- React
- JavaScript
- CSS
- Fetch API
```

---

## Backend Setup

```bash
cd wiki-agent/backend
```

Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

For Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env`:

```bash
cp .env.example .env
```

Add your API keys:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CMS_API_KEY=your_cms_marketplace_api_key_here
ANTHROPIC_MODEL=claude-sonnet-4-6
```

Run backend:

```bash
python -m uvicorn main:app --reload --port 8000
```

Backend runs at:

```text
http://127.0.0.1:8000
```

Swagger docs:

```text
http://127.0.0.1:8000/docs
```

---

## Frontend Setup

Open a second terminal:

```bash
cd wiki-agent/frontend
```

Install dependencies:

```bash
npm install
```

Run frontend:

```bash
npm start
```

Frontend runs at:

```text
http://localhost:3000
```

Make sure `frontend/package.json` has:

```json
"proxy": "http://127.0.0.1:8000"
```

---

## API Endpoints

### Health Check

```http
GET /health
```

Used to confirm backend is running.

---

### AI Chat

```http
POST /ask
```

Request:

```json
{
  "question": "Which plan is best for me if I want the lowest monthly premium?",
  "history": []
}
```

Response:

```json
{
  "answer": "Based on the plans shown, the lowest monthly premium option is...",
  "sources": ["CMS Marketplace — Plan Search"],
  "steps": ["get_plans(...)"]
}
```

---

### Plan Search

```http
POST /plans/search-ui
```

Request:

```json
{
  "zip_code": "60647",
  "state": "IL",
  "age": 25,
  "income": 50000,
  "gender": "Female",
  "uses_tobacco": false,
  "utilization_level": "Medium",
  "year": 2024
}
```

Response:

```json
{
  "plans": [
    {
      "id": "example-plan-id",
      "name": "Example Plan",
      "issuer": "Example Issuer",
      "type": "HMO",
      "metal_level": "Bronze",
      "premium": 300.25,
      "premium_w_credit": 228.2,
      "deductible": 7400,
      "out_of_pocket_max": 9450,
      "quality_rating": 4,
      "hsa_eligible": false,
      "benefits_url": "https://example.com",
      "network_url": "https://example.com",
      "formulary_url": "https://example.com"
    }
  ],
  "total": 5,
  "county_fips": "17031",
  "source": "CMS Marketplace API"
}
```

---

### Drug Coverage Check

```http
POST /drugs/check-ui
```

Request:

```json
{
  "drug_name": "ibuprofen",
  "plan_id": "11512NC0100031",
  "year": 2019
}
```

Response:

```json
{
  "drug": "Ibuprofen",
  "rxcui": "1049589",
  "plan_id": "11512NC0100031",
  "covered": false,
  "coverage_status": "DataNotProvided"
}
```

---

## Sample Inputs

Use this plan search input:

```text
ZIP code: 60647
State: IL
Age: 25
Income: 50000
Gender: Female
Usage: Medium
Tobacco use: unchecked
```

Another working example:

```text
ZIP code: 27360
State: NC
Age: 25
Income: 50000
Gender: Female
Usage: Medium
Tobacco use: unchecked
```

---

## Sample Chat Questions

```text
Which plan is best for me if I want the lowest monthly premium?
```

```text
Explain my selected plan in simple words.
```

```text
What does deductible mean?
```

```text
What does out-of-pocket maximum mean?
```

```text
Should I choose Bronze or Silver if I visit doctors often?
```

```text
What is the difference between HMO and PPO?
```

```text
How do premium tax credits work?
```

---

## Sample Drugs to Test

```text
ibuprofen
metformin
atorvastatin
albuterol
lisinopril
amoxicillin
```

---

## Important CMS API Notes

Some states are not valid for `/plans/search` because they use their own state marketplace.

Examples:

```text
CA — Covered California
NY — NY State of Health
```

Use federal marketplace states for testing, such as:

```text
IL
NC
TX
FL
GA
OH
AZ
```

---

## Drug Coverage Handling

CMS may return:

```text
DataNotProvided
```

This means CMS does not have formulary data for that exact drug-plan combination.

It does not mean the drug is not covered.

CoverBot handles this safely by showing the status as unknown and directing users to the official formulary link when available.

---

## Troubleshooting

### Backend not running

Check:

```text
http://127.0.0.1:8000/health
```

Restart backend:

```bash
python -m uvicorn main:app --reload --port 8000
```

---

### Proxy error

If frontend shows:

```text
Could not proxy request /ask
```

Make sure backend is running on port 8000 and `package.json` has:

```json
"proxy": "http://127.0.0.1:8000"
```

Then restart frontend:

```bash
npm start
```

---

### Invalid Anthropic API key

Check `.env`:

```env
ANTHROPIC_API_KEY=your_key_here
```

Restart backend after editing `.env`.

---

### CMS 403 Forbidden

This usually means the public CMS test key is blocked or rate-limited.

Use a private CMS key:

```env
CMS_API_KEY=your_private_key_here
```

---

### State is not a valid marketplace state

This means the state is not supported by the federal marketplace API.

Try:

```text
IL + 60647
NC + 27360
```

---

## Demo Flow

```text
1. Enter ZIP, state, age, income, gender, and usage level
2. Click Search Plans
3. Compare plan cards
4. Select a plan
5. Check a medication
6. Ask follow-up questions in chat
7. Review official Benefits, Network, or Formulary links
```

---

## Product Safety Behavior

CoverBot avoids giving false insurance answers.

If CMS returns incomplete drug coverage data, the app does not say the drug is not covered. Instead, it shows:

```text
Coverage data unavailable
```

and recommends checking the official formulary or insurer website.

---

## Future Improvements

```text
Provider search
Doctor and hospital in-network checker
Plan ranking by user priority
Tax credit explanation
Medicaid or CHIP estimate
Saved user profile
PDF export for plan comparison
Cloud Run deployment
Login and saved searches
```

---

## Summary

CoverBot is an AI-powered health insurance assistant that combines CMS Marketplace data with Claude AI. It helps users compare ACA plans, understand insurance terms, and safely check drug coverage availability.

CMS Marketplace API gives the real data, like:

Plans
Premiums
Deductibles
Out-of-pocket max
Issuer
Plan type
Metal level
Drug coverage status
Benefits / network / formulary links

Claude explains and summarizes that data, like:

Which plan looks cheaper
What deductible means
Whether Bronze/Silver may be better
How to understand the selected plan
Plain-English recommendations# coverbot
