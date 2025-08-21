from typing import List, Dict, Optional, Any
import json
from app.config import get_settings,  get_groq_client
from app.models import BusinessPlan

SYSTEM_PROMPT = """
You are a senior financial analyst generating a full investor-grade business plan in valid JSON format.

Requirements:
- Output must be fully machine-readable, with no comments or markdown.
- Provide the whole output in the same language that the document or user input is given.     
- The business plan MUST BE DETAILED.
- All financial numbers must be plain raw integers or floats (no symbols or strings).
- Text fields must be UTF-8 strings.
- Include all required fields exactly as per schema.
- Each financial section must cover 3 years (year 1 to year 3).
- Ensure all numeric data is logically consistent (e.g., net_cash = sum of flows, assets = liabilities + equity).

Schema:
{
  "executive_summary": "Summarize the overall business opportunity in 200+ words: include the core product or service, the market need it addresses, key team strengths, business traction (if any), and the long-term vision. Highlight why this business matters now.",

  "business_overview": "Describe the company’s mission, vision, and founding story in 250+ words. Include when and why it was started, what goals it seeks to achieve, where it is currently based, and what motivates the team behind it.",

  "market_analysis": "Provide a 500+  word analysis of the market: total addressable market (TAM), serviceable available market (SAM), and obtainable market (SOM). Identify competitors, customer segments, market trends, and why the timing is right for this solution.",

  "business_model": "Explain how the business makes money in 500+  words. Describe primary and secondary revenue streams, customer acquisition strategy, pricing model, cost structure, margins, and how the model scales over time.",

  "marketing_and_sales_strategy": "Describe in 500+  words how the business plans to go to market. Include positioning, target customers, sales channels (online/offline), customer acquisition cost (CAC) strategies, conversion funnels, and how growth will be driven operationally.",

  "financial_highlights": [ { "year": int, "revenue": float, "net_income": float, "capex": float, "debt_repayment": float }, ... ],

  "cash_flow_analysis": [ { "year": int, "operating": float, "investing": float, "financing": float, "net_cash": float }, ... ],

  "profit_and_loss_projection": [
    { 
      "year": int,
      "revenue": float,
      "cogs": float,
      "gross_profit": float,
      "operating_expenses": float,
      "ebitda": float,
      "depreciation_amortization": float,
      "ebit": float,
      "interest": float,
      "taxes": float,
      "net_income": float
    }, ...
  ],

  "balance_sheet": [
    {
      "year": int,
      "assets": float,
      "current_assets": float,
      "non_current_assets": float,
      "liabilities": float,
      "current_liabilities": float,
      "non_current_liabilities": float,
      "equity": float
    }, ...
  ],

  "net_financial_position": [ { "year": int, "net_position": float }, ... ],

  "debt_structure": [ { "year": int, "repayment": float, "interest_rate": float, "outstanding_debt": float }, ... ],

  "key_ratios": [
    {
      "year": int,
      "roi": float,
      "roe": float,
      "debt_to_equity": float,
      "gross_margin": float,
      "ebitda_margin": float,
      "net_margin": float,
      "current_ratio": float,
      "quick_ratio": float,
      "asset_turnover": float
    }, ...
  ],

  "operating_cost_breakdown": [
    {
      "year": int,
      "revenue": float,
      "cogs": float,
      "employee_costs": float,
      "marketing": float,
      "rent": float,
      "administration": float,
      "amortization": float,
      "other_expenses": float,
      "interest_expenses": float,
      "tax": float
    }, ...
  ],

{
  "sector_strategy": "Provide a detailed strategy (minimum 500+  words) outlining how the company will operate within its specific industry sector. This should include analysis of current sector trends, competitive landscape, regulatory environment, key success factors, and how the business will position itself to gain a competitive advantage over time.",
  
  "funding_sources": "Explain in detail (minimum 500+  words) all current and future funding sources, including but not limited to equity investment, loans, grants, crowdfunding, or internal cash flow. Specify amounts, stages of funding, potential investors or lenders, and how the funds will be allocated within the business.",

  "operations_plan": "Describe in depth (minimum 500+ words) the company's operation plan, and any strategic moves. Include what the business will do to execute its strategy, including any strategic partnerships, collaborations, or acquisitions. Explain how the business will manage risks and opportunities, and how it will adapt to changing market conditions."
}
}

Only output clean, valid JSON matching the schema above. Do not skip fields. No markdown, no extra commentary.
"""


async def generate_business_plan(
    uploaded_file: Optional[str] = None,
    user_input: List[Any] = None,
    user_id: str = None   # <-- NEW arg
) -> dict:
    settings = get_settings()
    client = get_groq_client()

    # Limit input sizes
    max_input_length = 100_000
    
    # Build context from user inputs
    business_context = []
    
    context = "Business Plan Analysis:\n"
    for item in business_context:
        if len(item) > max_input_length:
            item = item[:max_input_length] + "..."
        context += f"- {item}\n"
    
    if uploaded_file:
        if len(uploaded_file) > max_input_length:
            uploaded_file = uploaded_file[:max_input_length] + "..."
        context += f"\nDocument Analysis:\n{uploaded_file}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context}
    ]

    try:
        response = await client.create_chat_completion(
            messages=messages,
            model=settings.model_name,
            temperature=0.6,
            max_tokens=8000  # Reduced from 8000
        )

        raw_content = response['choices'][0]['message']['content'].strip()

        if not raw_content:
            raise ValueError("Empty response from AI model.")

# Attempt direct parse
        try:
            plan_data = json.loads(raw_content)
        except json.JSONDecodeError:
            # Try extracting JSON object from response if extra text present
            start = raw_content.find("{")
            end = raw_content.rfind("}")
            if start != -1 and end != -1:
                json_str = raw_content[start:end+1]
                try:
                    plan_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse JSON: {str(e)}. Raw content: {raw_content[:200]}")
            else:
                raise ValueError(f"Invalid JSON response with no braces found. Raw content: {raw_content[:200]}")
            
        return plan_data
    
    except ValueError as e:
        raise ValueError(f"API Error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {str(e)}")
    

SUGGESTION_PROMPT = """
You are an expert business plan consultant. Generate 4 different possible professional answers for the following business plan question. 
Keep each answer concise  (Less than 10 words).
Try to provide shorter answers
Return the answers in a clean JSON array format.

Question: {question}

Return ONLY a valid JSON array of strings, no additional text or explanations.
"""

import re

async def generate_suggestions(question: str) -> List[str]:
    settings = get_settings()
    client = get_groq_client()

    messages = [
        {
            "role": "system",
            "content": SUGGESTION_PROMPT.format(question=question)
        }
    ]

    response = await client.create_chat_completion(
        messages=messages,
        model=settings.model_name,
        temperature=0.4,
        max_tokens=200
    )
    print("🔍 FULL RESPONSE:", response)

    
    try:
        content = response['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError, TypeError) as err:
        raise ValueError(f"Invalid Groq response format: {response} | Error: {err}")

    print("🔍 Raw content:", repr(content))

    # Remove Markdown fences
    if content.startswith("```"):
        content = re.sub(r"^```(json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    try:
        # Try parsing directly
        suggestions = json.loads(content)
        if not isinstance(suggestions, list):
            raise ValueError("Expected a list of strings.")
        return suggestions
    except json.JSONDecodeError:
        # Try to extract JSON array from the content
        try:
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                array_text = match.group(0)
                suggestions = json.loads(array_text)
                return suggestions
        except Exception as e:
            raise ValueError(f"Could not parse suggestions array from model output: {content[:200]}... | Error: {e}")
    
    raise ValueError(f"Invalid JSON returned by model: {content[:200]}...")


