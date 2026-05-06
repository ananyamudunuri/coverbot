"""
Healthcare Insurance Agent — FastAPI Backend
Uses Claude + CMS Marketplace API to explain coverage, compare plans,
and check drug coverage in plain English.
"""

import os
import json
import httpx
import anthropic

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Healthcare Insurance Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CMS_API_KEY = os.getenv("CMS_API_KEY", "yourkey")

# Keep model configurable so you can change it in .env if needed
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

CMS_BASE = "https://marketplace.api.healthcare.gov/api/v1"

HTTP_TIMEOUT = httpx.Timeout(
    timeout=20.0,
    connect=8.0,
    read=20.0,
    write=8.0,
)

HEADERS = {
    "User-Agent": "CoverBot/1.0",
    "Accept": "application/json",
}


# ── CMS Marketplace API helpers ───────────────────────────────────────────────

def handle_cms_error(exc: Exception):
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code

        if status == 403:
            raise HTTPException(
                status_code=403,
                detail=(
                    "CMS Marketplace API returned 403 Forbidden. "
                    "The public test key is likely blocked/rate-limited. "
                    "Please use your private CMS_API_KEY in .env."
                ),
            )

        if status == 404:
            raise HTTPException(
                status_code=404,
                detail="CMS could not find data for this request. Check ZIP, state, year, or plan ID.",
            )

        raise HTTPException(
            status_code=status,
            detail=f"CMS API error: {exc.response.text[:500]}",
        )

    if isinstance(exc, httpx.TimeoutException):
        raise HTTPException(
            status_code=504,
            detail="CMS API timed out. Please try again later.",
        )

    if isinstance(exc, httpx.RequestError):
        raise HTTPException(
            status_code=502,
            detail=f"Could not connect to CMS API: {str(exc)}",
        )

    raise HTTPException(status_code=500, detail=str(exc))


async def cms_get(path: str, params: dict | None = None) -> dict:
    query_params = dict(params or {})
    query_params["apikey"] = CMS_API_KEY

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers=HEADERS) as http:
            response = await http.get(f"{CMS_BASE}{path}", params=query_params)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        handle_cms_error(exc)


async def cms_post(path: str, body: dict, params: dict | None = None) -> dict:
    query_params = dict(params or {})
    query_params["apikey"] = CMS_API_KEY

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers=HEADERS) as http:
            response = await http.post(
                f"{CMS_BASE}{path}",
                params=query_params,
                json=body,
            )
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        handle_cms_error(exc)


# ── Tool implementations for Claude ───────────────────────────────────────────

async def get_plans(
    zip_code: str,
    state: str,
    age: int,
    income: int,
    year: int = 2024,
) -> str:
    county_data = await cms_get(f"/counties/by/zip/{zip_code}", {"year": year})
    counties = county_data.get("counties", [])

    if not counties:
        return json.dumps({"error": f"No county found for ZIP {zip_code}"})

    fips = counties[0]["fips"]

    body = {
        "household": {
            "income": income,
            "people": [
                {
                    "age": age,
                    "aptc_eligible": True,
                    "gender": "Female",
                    "uses_tobacco": False,
                    "utilization_level": "Medium",
                }
            ],
            "has_married_couple": False,
        },
        "market": "Individual",
        "place": {
            "countyfips": fips,
            "state": state.upper(),
            "zipcode": zip_code,
        },
        "year": year,
        "limit": 5,
        "offset": 0,
        "sort": "premium",
        "order": "asc",
    }

    data = await cms_post("/plans/search", body)

    simplified = []
    for plan in data.get("plans", [])[:5]:
        simplified.append(simplify_plan(plan))

    return json.dumps(
        {
            "plans": simplified,
            "total": data.get("total", 0),
            "county_fips": fips,
        },
        ensure_ascii=False,
    )


async def get_plan_details(plan_id: str, year: int = 2024) -> str:
    data = await cms_get(f"/plans/{plan_id}", {"year": year})
    plan = data.get("plan", data)

    details = {
        "id": plan.get("id"),
        "name": plan.get("name"),
        "issuer": plan.get("issuer", {}).get("name"),
        "type": plan.get("type"),
        "metal_level": plan.get("metal_level"),
        "premium": plan.get("premium"),
        "premium_w_credit": plan.get("premium_w_credit"),
        "deductibles": plan.get("deductibles"),
        "moops": plan.get("moops"),
        "benefits": plan.get("benefits", [])[:10],
        "quality_rating": plan.get("quality_rating", {}).get("global_rating"),
        "hsa_eligible": plan.get("hsa_eligible"),
        "benefits_url": plan.get("benefits_url"),
        "network_url": plan.get("network_url"),
    }

    return json.dumps(details, ensure_ascii=False)


async def check_drug_coverage(
    drug_name: str,
    plan_id: str,
    year: int = 2024,
) -> str:
    autocomplete = await cms_get(
        "/drugs/autocomplete",
        {
            "q": drug_name,
            "year": year,
        },
    )

    drugs = autocomplete.get("drugs", []) if isinstance(autocomplete, dict) else autocomplete

    if not drugs:
        return json.dumps({
            "drug": drug_name,
            "covered": False,
            "coverage_status": "DrugNotFound",
            "message": f"Drug '{drug_name}' was not found in CMS drug database.",
        })

    # Prefer exact/simple match instead of first random combo drug
    selected_drug = None
    drug_lower = drug_name.lower()

    for d in drugs:
        name = (d.get("name") or d.get("full_name") or "").lower()
        if name == drug_lower:
            selected_drug = d
            break

    if not selected_drug:
        for d in drugs:
            name = (d.get("name") or d.get("full_name") or "").lower()
            if drug_lower in name and "/" not in name:
                selected_drug = d
                break

    if not selected_drug:
        selected_drug = drugs[0]

    rxcui = selected_drug.get("rxcui") or selected_drug.get("id")
    drug_display_name = (
        selected_drug.get("name")
        or selected_drug.get("full_name")
        or drug_name
    )

    coverage = await cms_get(
        "/drugs/covered",
        {
            "year": year,
            "drugs": rxcui,
            "planids": plan_id,
        },
    )

    coverage_list = []

    if isinstance(coverage, dict):
        coverage_list = (
            coverage.get("Provider & Drug Coverage")
            or coverage.get("drugs")
            or coverage.get("coverage")
            or coverage.get("results")
            or []
        )
    elif isinstance(coverage, list):
        coverage_list = coverage

    coverage_status = "DataNotProvided"
    is_covered = False

    if coverage_list:
        item = coverage_list[0]

        if isinstance(item, dict):
            coverage_status = (
                item.get("coverage")
                or item.get("status")
                or item.get("covered")
                or "DataNotProvided"
            )

            is_covered = str(coverage_status).lower() in [
                "covered",
                "genericcovered",
                "true",
            ]
        else:
            coverage_status = str(item)
            is_covered = coverage_status.lower() in ["covered", "genericcovered"]

    return json.dumps(
        {
            "drug": drug_display_name,
            "rxcui": rxcui,
            "plan_id": plan_id,
            "covered": is_covered,
            "coverage_status": coverage_status,
            "raw_coverage": coverage,
            "matched_drug_options": [
                {
                    "name": d.get("name") or d.get("full_name"),
                    "rxcui": d.get("rxcui") or d.get("id"),
                }
                for d in drugs[:5]
            ],
        },
        ensure_ascii=False,
    )


async def get_states() -> str:
    data = await cms_get("/states")
    return json.dumps(data, ensure_ascii=False)


# ── Plan formatting helper ────────────────────────────────────────────────────

def simplify_plan(plan: dict) -> dict:
    deductible = None
    out_of_pocket_max = None

    deductibles = plan.get("deductibles") or []
    if deductibles:
        deductible = deductibles[0].get("amount")

    moops = plan.get("moops") or []
    if moops:
        out_of_pocket_max = moops[0].get("amount")

    return {
        "id": plan.get("id"),
        "name": plan.get("name"),
        "issuer": plan.get("issuer", {}).get("name"),
        "type": plan.get("type"),
        "metal_level": plan.get("metal_level"),
        "premium": plan.get("premium"),
        "premium_w_credit": plan.get("premium_w_credit"),
        "deductible": deductible,
        "out_of_pocket_max": out_of_pocket_max,
        "quality_rating": plan.get("quality_rating", {}).get("global_rating"),
        "hsa_eligible": plan.get("hsa_eligible"),
        "benefits_url": plan.get("benefits_url"),
        "network_url": plan.get("network_url"),
        "formulary_url": plan.get("formulary_url"),
    }

# ── Claude tool definitions ───────────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_plans",
        "description": (
            "Search for ACA health insurance plans by ZIP, state, age, income, and year. "
            "Returns premiums, deductible, metal level, and plan type."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "zip_code": {"type": "string"},
                "state": {"type": "string"},
                "age": {"type": "integer"},
                "income": {"type": "integer"},
                "year": {"type": "integer", "default": 2024},
            },
            "required": ["zip_code", "state", "age", "income"],
        },
    },
    {
        "name": "get_plan_details",
        "description": "Get detailed information for a specific insurance plan by plan ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "year": {"type": "integer", "default": 2024},
            },
            "required": ["plan_id"],
        },
    },
    {
        "name": "check_drug_coverage",
        "description": "Check whether a medication is covered under a specific plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_name": {"type": "string"},
                "plan_id": {"type": "string"},
                "year": {"type": "integer", "default": 2024},
            },
            "required": ["drug_name", "plan_id"],
        },
    },
    {
        "name": "get_states",
        "description": "Return available US states on the ACA marketplace.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


TOOL_FN_MAP = {
    "get_plans": lambda i: get_plans(
        i["zip_code"],
        i["state"],
        i["age"],
        i["income"],
        i.get("year", 2024),
    ),
    "get_plan_details": lambda i: get_plan_details(
        i["plan_id"],
        i.get("year", 2024),
    ),
    "check_drug_coverage": lambda i: check_drug_coverage(
        i["drug_name"],
        i["plan_id"],
        i.get("year", 2024),
    ),
    "get_states": lambda i: get_states(),
}


# ── Agent loop ────────────────────────────────────────────────────────────────

async def run_agent(user_question: str, history: list | None = None) -> dict:
    history = history or []

    messages = []

    for item in history:
        role = item.get("role")
        content = item.get("content")

        if role in ["user", "assistant"] and content:
            messages.append(
                {
                    "role": role,
                    "content": str(content),
                }
            )

    messages.append({"role": "user", "content": user_question})

    sources: list[str] = []
    steps: list[str] = []

    system = (
        "You are a friendly, expert health insurance advisor called CoverBot. "
        "Explain health insurance in plain, simple English. "
        "Use CMS Marketplace tools when users ask about real plans, premiums, drug coverage, or plan details.\n\n"
        "FORMATTING RULES:\n"
        "- Use **bold** for key terms, costs, and important numbers.\n"
        "- Use ### section headings for multi-part answers.\n"
        "- Use short bullet points when helpful.\n"
        "- Keep responses concise and scannable.\n"
        "- If CMS tools fail, clearly say live data is unavailable instead of pretending exact plan data exists.\n"
        "- End with one short helpful follow-up question."
    )

    for _ in range(8):
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final_text = " ".join(
                block.text
                for block in response.content
                if hasattr(block, "text")
            )

            return {
                "answer": final_text,
                "sources": sources,
                "steps": steps,
            }

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input

                steps.append(f"🔧 {tool_name}({json.dumps(tool_input)})")

                label = {
                    "get_plans": "CMS Marketplace — Plan Search",
                    "get_plan_details": "CMS Marketplace — Plan Details",
                    "check_drug_coverage": "CMS Marketplace — Drug Coverage",
                    "get_states": "CMS Marketplace — States",
                }.get(tool_name, tool_name)

                if label not in sources:
                    sources.append(label)

                try:
                    fn = TOOL_FN_MAP.get(tool_name)
                    if not fn:
                        result = json.dumps({"error": "Unknown tool"})
                    else:
                        result = await fn(tool_input)

                except HTTPException as exc:
                    result = json.dumps({"error": exc.detail})

                except Exception as exc:
                    result = json.dumps({"error": str(exc)})

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

            messages.append({"role": "user", "content": tool_results})

    return {
        "answer": "I wasn’t able to find a complete answer. Please try rephrasing your question.",
        "sources": sources,
        "steps": steps,
    }


# ── Request / Response models ─────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str
    history: list = []


class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]
    steps: list[str]


class PlanSearchUIRequest(BaseModel):
    zip_code: str
    state: str
    age: int
    income: int
    gender: str = "Female"
    uses_tobacco: bool = False
    utilization_level: str = "Medium"
    year: int = 2024


class DrugCoverageUIRequest(BaseModel):
    drug_name: str
    plan_id: str
    year: int = 2024


# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "CoverBot API is running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "anthropic_key_loaded": bool(ANTHROPIC_API_KEY),
        "cms_key_loaded": bool(CMS_API_KEY),
        "model": ANTHROPIC_MODEL,
    }


@app.post("/ask", response_model=AnswerResponse)
async def ask(req: QuestionRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        return await run_agent(req.question, req.history)

    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key.")

    except anthropic.NotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Anthropic model not found. Check ANTHROPIC_MODEL. Full error: {str(exc)}",
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/plans/search-ui")
async def search_plans_ui(req: PlanSearchUIRequest):
    if not req.zip_code.strip():
        raise HTTPException(status_code=400, detail="ZIP code is required.")

    if not req.state.strip():
        raise HTTPException(status_code=400, detail="State is required.")

    try:
        county_data = await cms_get(
            f"/counties/by/zip/{req.zip_code}",
            {"year": req.year},
        )

        counties = county_data.get("counties", [])

        if not counties:
            raise HTTPException(
                status_code=404,
                detail="No county found for this ZIP code.",
            )

        fips = counties[0]["fips"]

        body = {
            "household": {
                "income": req.income,
                "people": [
                    {
                        "age": req.age,
                        "aptc_eligible": True,
                        "gender": req.gender,
                        "uses_tobacco": req.uses_tobacco,
                        "utilization_level": req.utilization_level,
                    }
                ],
                "has_married_couple": False,
            },
            "market": "Individual",
            "place": {
                "countyfips": fips,
                "state": req.state.upper(),
                "zipcode": req.zip_code,
            },
            "year": req.year,
            "limit": 5,
            "offset": 0,
            "sort": "premium",
            "order": "asc",
        }

        data = await cms_post("/plans/search", body)

        plans = [simplify_plan(plan) for plan in data.get("plans", [])[:5]]

        return {
            "plans": plans,
            "total": data.get("total", 0),
            "county_fips": fips,
            "source": "CMS Marketplace API",
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/drugs/check-ui")
async def check_drug_ui(req: DrugCoverageUIRequest):
    if not req.drug_name.strip():
        raise HTTPException(status_code=400, detail="Drug name is required.")

    if not req.plan_id.strip():
        raise HTTPException(status_code=400, detail="Plan ID is required.")

    try:
        result = await check_drug_coverage(
            drug_name=req.drug_name,
            plan_id=req.plan_id,
            year=req.year,
        )

        return json.loads(result)

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))