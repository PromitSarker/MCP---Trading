import asyncio
import json
from typing import List, Optional, Any, Dict
import re
import logging
from app.config import get_settings, get_openai_client

# --------------- LOGGING ---------------
logger = logging.getLogger(__name__)

# --------------- INDIVIDUAL SECTION SCHEMAS ---------------
INDIVIDUAL_SECTION_SCHEMAS = {
    "executive_summary": {
        "type": "string",
        "description": "Summarize the overall business opportunity in 300+ words: include the core product or service, the market need it addresses, key team strengths, business traction (if any), and the long-term vision. Highlight why this business matters now. ",
        "min_words": 300
    },
    "business_overview": {
        "type": "string", 
        "description": "Describe the company's mission, vision, and founding story. Include when and why it was started, what goals it seeks to achieve, where it is currently based, and what motivates the team behind it.",
        "min_words": 500
    },
    "market_analysis": {
        "type": "string",
        "description": "Provide a analysis of the market: total addressable market (TAM), serviceable available market (SAM), and obtainable market (SOM). Identify competitors, customer segments, market trends, and why the timing is right for this solution.",
        "min_words": 700
    },
    "business_model": {
        "type": "string",
        "description": "Explain how the business makes money. Describe primary and secondary revenue streams, customer acquisition strategy, pricing model, cost structure, margins, and how the model scales over time.",
        "min_words": 500
    },
    "marketing_and_sales_strategy": {
        "type": "string",
        "description": "Describe how the business plans to go to market. Include positioning, target customers, sales channels (online/offline), customer acquisition cost (CAC) strategies, conversion funnels, and how growth will be driven operationally.",
        "min_words": 500
    },
    "financial_highlights": {
        "type": "json",
        "description": "5 years of key financial metrics. DO NOT JUST PUT THE NUMBERS AS IN THE EXAMPLE. PROVIDE REALISTIC NUMERICAL DATAS.",
        "schema": [{"year": "int", "revenue": "float", "net_income": "float", "capex": "float", "debt_repayment": "float"}],
        "example": [
            {"year": 1, "revenue": 250000, "net_income": 30, "capex": 50000, "debt_repayment": 10000},
            {"year": 2, "revenue": 400000, "net_income": 60, "capex": 70000, "debt_repayment": 15000},
            {"year": 3, "revenue": 650000, "net_income": 100, "capex": 90000, "debt_repayment": 20000}
        ]
    },
    "cash_flow_analysis": {
        "type": "json",
        "description": "5 years of cash flow statement following standard format. DO NOT JUST PUT THE NUMBERS AS IN THE EXAMPLE. PROVIDE REALISTIC NUMERICAL DATAS.",
        "schema": [{"year": "int", "operating": "float", "investing": "float", "financing": "float", "net_cash": "float"}],
        "example": [
            {"year": 1, "operating": 80000, "investing": -50000, "financing": 10000, "net_cash": 40000},
            {"year": 2, "operating": 120000, "investing": -70000, "financing": 15000, "net_cash": 50000},
            {"year": 3, "operating": 200000, "investing": -90000, "financing": 20000, "net_cash": 110000}
        ]
    },
    "profit_and_loss_projection": {
        "type": "json",
        "description": "5 years of profit & loss statement with detailed breakdown. DO NOT JUST PUT THE NUMBERS AS IN THE EXAMPLE. PROVIDE REALISTIC NUMERICAL DATAS.",
        "schema": [{"year": "int", "revenue": "float", "cogs": "float", "gross_profit": "float", "operating_expenses": "float", "ebitda": "float", "depreciation_amortization": "float", "ebit": "float", "interest": "float", "taxes": "float", "net_income": "float"}],
        "example": [
            {"year": 1, "revenue": 250000, "cogs": 100000, "gross_profit": 150000, "operating_expenses": 120000, "ebitda": 30000, "depreciation_amortization": 5000, "ebit": 25000, "interest": 2000, "taxes": 3000, "net_income": 30000},
            {"year": 2, "revenue": 400000, "cogs": 160000, "gross_profit": 240000, "operating_expenses": 160000, "ebitda": 80000, "depreciation_amortization": 7000, "ebit": 73000, "interest": 4000, "taxes": 9000, "net_income": 60000},
            {"year": 3, "revenue": 650000, "cogs": 260000, "gross_profit": 390000, "operating_expenses": 200000, "ebitda": 190000, "depreciation_amortization": 10000, "ebit": 180000, "interest": 6000, "taxes": 24000, "net_income": 100000}
        ]
    },
    "balance_sheet": {
        "type": "json",
        "description": "5 years of balance sheet with detailed breakdown. DO NOT JUST PUT THE NUMBERS AS IN THE EXAMPLE. PROVIDE REALISTIC NUMERICAL DATAS.",
        "schema": [{"year": "int", "assets": "float", "current_assets": "float", "non_current_assets": "float", "liabilities": "float", "current_liabilities": "float", "non_current_liabilities": "float", "equity": "float"}],
        "example": [
            {"year": 1, "assets": 300000, "current_assets": 150000, "non_current_assets": 150000, "liabilities": 200000, "current_liabilities": 100000, "non_current_liabilities": 100000, "equity": 100000},
            {"year": 2, "assets": 450000, "current_assets": 200000, "non_current_assets": 250000, "liabilities": 280000, "current_liabilities": 130000, "non_current_liabilities": 150000, "equity": 170000},
            {"year": 3, "assets": 650000, "current_assets": 280000, "non_current_assets": 370000, "liabilities": 380000, "current_liabilities": 180000, "non_current_liabilities": 200000, "equity": 270000}
        ]
    },
    "net_financial_position": {
        "type": "json",
        "description": "5 years of net financial position. DO NOT JUST PUT THE NUMBERS AS IN THE EXAMPLE. PROVIDE REALISTIC NUMERICAL DATAS.",
        "schema": [{"year": "int", "net_position": "float"}],
        "example": [
            {"year": 1, "net_position": -50000},
            {"year": 2, "net_position": -30000},
            {"year": 3, "net_position": 10000}
        ]
    },
    "debt_structure": {
        "type": "json",
        "description": "5 years of debt structure and repayment schedule. DO NOT JUST PUT THE NUMBERS AS IN THE EXAMPLE. PROVIDE REALISTIC NUMERICAL DATAS.",
        "schema": [{"year": "int", "repayment": "float", "interest_rate": "float", "outstanding_debt": "float"}],
        "example": [
            {"year": 1, "repayment": 10000, "interest_rate": 4.5, "outstanding_debt": 100000},
            {"year": 2, "repayment": 15000, "interest_rate": 4.2, "outstanding_debt": 85000},
            {"year": 3, "repayment": 20000, "interest_rate": 4.0, "outstanding_debt": 65000}
        ]
    },
    "key_ratios": {
        "type": "json",
        "description": "5 years of key financial ratios. DO NOT JUST PUT THE NUMBERS AS IN THE EXAMPLE. PROVIDE REALISTIC NUMERICAL DATAS.",
        "schema": [{"year": "int", "roi": "float", "roe": "float", "debt_to_equity": "float", "gross_margin": "float", "ebitda_margin": "float", "net_margin": "float", "current_ratio": "float", "quick_ratio": "float", "asset_turnover": "float"}],
        "example": [
            {"year": 1, "roi": 12.5, "roe": 15.2, "debt_to_equity": 2.0, "gross_margin": 60.0, "ebitda_margin": 12.0, "net_margin": 12.0, "current_ratio": 1.5, "quick_ratio": 1.2, "asset_turnover": 0.83},
            {"year": 2, "roi": 15.8, "roe": 18.5, "debt_to_equity": 1.65, "gross_margin": 60.0, "ebitda_margin": 20.0, "net_margin": 15.0, "current_ratio": 1.54, "quick_ratio": 1.25, "asset_turnover": 0.89},
            {"year": 3, "roi": 18.2, "roe": 22.1, "debt_to_equity": 1.41, "gross_margin": 60.0, "ebitda_margin": 29.2, "net_margin": 15.4, "current_ratio": 1.56, "quick_ratio": 1.3, "asset_turnover": 1.0}
        ]
    },
    "operating_cost_breakdown": {
    "type": "json",
    "description": "5 years of comprehensive operating cost breakdown following Italian GAAP (OIC standards) and D.Lgs. 127/91 requirements, with extensive numerical analysis specific to Italian business environment. Include quarterly breakdown reflecting Italian seasonal business patterns, cost growth rates accounting for Italian inflation trends, variance analysis using Italian industry benchmarks, and operational KPIs relevant to Italian market conditions. Provide detailed subcategory metrics with percentage changes based on Italian labor costs (including 13th/14th month salaries, TFR contributions, INPS/INAIL contributions), Italian tax structure (IRES, IRAP), regional business costs variations across Northern/Central/Southern Italy, and compliance with Italian employment regulations. Factor in Italian-specific costs like commercialista fees, camera di commercio fees, regional tax variations, and sector-specific Italian regulations. DO NOT JUST PUT THE NUMBERS AS IN THE EXAMPLE. PROVIDE REALISTIC NUMERICAL DATAS.",

    "schema": [
        {
            "year": "int",
            "revenue": "float",
            "cogs": "float",
            "employee_costs": "float",
            "marketing": "float", 
            "rent": "float",
            "administration": "float",
            "amortization": "float",
            "other_expenses": "float",
            "interest_expenses": "float",
            "tax": "float",
            "quarterly_breakdown": {
                "q1_revenue": "float",
                "q2_revenue": "float", 
                "q3_revenue": "float",
                "q4_revenue": "float",
                "q1_costs": "float",
                "q2_costs": "float",
                "q3_costs": "float", 
                "q4_costs": "float"
            },
            "employee_analytics": {
                "management_costs": "float",
                "operations_staff": "float",
                "sales_team": "float",
                "avg_salary_per_employee": "float",
                "total_headcount": "int",
                "cost_per_employee": "float",
                "productivity_ratio": "float",
                "overtime_costs": "float",
                "benefits_percentage": "float"
            },
            "marketing_analytics": {
                "digital_marketing": "float",
                "traditional_marketing": "float",
                "events_conferences": "float",
                "content_creation": "float",
                "paid_advertising": "float",
                "cost_per_acquisition": "float",
                "marketing_roi": "float",
                "lead_generation_cost": "float",
                "conversion_cost": "float"
            },
            "operational_metrics": {
                "cost_per_unit_sold": "float",
                "variable_cost_ratio": "float",
                "fixed_cost_coverage": "float",
                "operational_leverage": "float",
                "cost_efficiency_index": "float",
                "break_even_units": "int",
                "capacity_utilization": "float"
            },
            "cost_percentages": {
                "cogs_percent": "float",
                "employee_percent": "float", 
                "marketing_percent": "float",
                "rent_percent": "float",
                "admin_percent": "float",
                "other_percent": "float"
            },
            "variance_analysis": {
                "budget_vs_actual_variance": "float",
                "yoy_cost_growth_rate": "float",
                "cost_inflation_impact": "float",
                "efficiency_improvement": "float",
                "cost_per_revenue_ratio": "float"
            },
            "benchmarking_ratios": {
                "industry_avg_cogs": "float",
                "employee_cost_benchmark": "float",
                "marketing_spend_benchmark": "float",
                "admin_cost_benchmark": "float"
            }
        }
    ],
    "example": [
        {
            "year": 1,
            "revenue": 250000,
            "cogs": 100000,
            "employee_costs": 80000,
            "marketing": 20000,
            "rent": 15000,
            "administration": 10000,
            "amortization": 5000,
            "other_expenses": 5000,
            "interest_expenses": 2000,
            "tax": 3000,
            "quarterly_breakdown": {
                "q1_revenue": 50000,
                "q2_revenue": 60000,
                "q3_revenue": 65000,
                "q4_revenue": 75000,
                "q1_costs": 45000,
                "q2_costs": 52000,
                "q3_costs": 58000,
                "q4_costs": 65000
            },
            "employee_analytics": {
                "management_costs": 35000,
                "operations_staff": 30000,
                "sales_team": 15000,
                "avg_salary_per_employee": 53333,
                "total_headcount": 5,
                "cost_per_employee": 16000,
                "productivity_ratio": 50000,
                "overtime_costs": 2500,
                "benefits_percentage": 15.0
            },
            "marketing_analytics": {
                "digital_marketing": 12000,
                "traditional_marketing": 4000,
                "events_conferences": 2000,
                "content_creation": 1500,
                "paid_advertising": 8000,
                "cost_per_acquisition": 125,
                "marketing_roi": 12.5,
                "lead_generation_cost": 45,
                "conversion_cost": 85
            },
            "operational_metrics": {
                "cost_per_unit_sold": 95,
                "variable_cost_ratio": 0.48,
                "fixed_cost_coverage": 1.8,
                "operational_leverage": 2.2,
                "cost_efficiency_index": 0.88,
                "break_even_units": 1750,
                "capacity_utilization": 0.72
            },
            "cost_percentages": {
                "cogs_percent": 40.0,
                "employee_percent": 32.0,
                "marketing_percent": 8.0,
                "rent_percent": 6.0,
                "admin_percent": 4.0,
                "other_percent": 10.0
            },
            "variance_analysis": {
                "budget_vs_actual_variance": -5.2,
                "yoy_cost_growth_rate": 0.0,
                "cost_inflation_impact": 2.1,
                "efficiency_improvement": 0.0,
                "cost_per_revenue_ratio": 0.88
            },
            "benchmarking_ratios": {
                "industry_avg_cogs": 42.0,
                "employee_cost_benchmark": 35.0,
                "marketing_spend_benchmark": 10.0,
                "admin_cost_benchmark": 5.5
            }
        }
    ]
},
    "sector_strategy": {
        "type": "string",
        "description": "Provide a detailed strategy outlining how the company will operate within its specific industry sector. This should include analysis of current sector trends, competitive landscape, regulatory environment, key success factors, and how the business will position itself to gain a competitive advantage over time.",
        "min_words": 300
    },
    "funding_sources": {
        "type": "string",
        "description": "Explain in detail  all current and future funding sources, including but not limited to equity investment, loans, grants, crowdfunding, or internal cash flow. Specify amounts, stages of funding, potential investors or lenders, and how the funds will be allocated within the business.",
        "min_words": 300
    },
    "operations_plan": {
        "type": "string",
        "description": "Describe in depth the company's operation plan, and any strategic moves. Include what the business will do to execute its strategy, including any strategic partnerships, collaborations, or acquisitions. Explain how the business will manage risks and opportunities, and how it will adapt to changing market conditions.",
        "min_words": 300
    },
    # NEW SECTIONS BASED ON WAYNE SRL EXAMPLE
    "financial_analysis": {
        "type": "json",
        "description": "Comprehensive Italian financial analysis following Wayne SRL example structure. Include detailed breakdown of financial position, cash flow analysis, and key Italian financial metrics. Follow Italian GAAP standards and D.Lgs. 127/91 requirements.",
        "schema": [
  {
    "year": 2023,
                "gross_operating_cash_flow": 94739,
                "working_capital_change": 18872,
                "current_management_cash_flow": 113611,
                "operating_cash_flow": -286389,
                "debt_service_cash_flow": -287988,
                "shareholders_cash_flow": 112012,
                "net_cash_flow": 112012,
                "sales_revenue": 1405366,
                "production_value": 1405366,
                "gross_operating_margin": 130774,
                "ebit": 129157,
                "ebt": 127053,
                "net_income": 91523,
                "dividends": 0,
                "net_tangible_assets": 405516,
                "net_intangible_assets": 475,
                "financial_assets": 0,
                "trade_assets": 0,
                "inventory": 0,
                "deferred_liquidity": 102204,
                "immediate_liquidity": 112826,
                "equity": 167638,
                "long_term_debt": 430767,
                "short_term_debt": 22616,
                "net_financial_position": 323674,
                "mortgage_loans": 400000,
                "other_financial_debts": 36500,
                "cash_and_banks": -112826
  }
],
        "example": [
            {
  "year": 2023,
  "gross_operating_cash_flow": 94739,
  "working_capital_change": 18872,
  "current_management_cash_flow": 113611,
  "operating_cash_flow": -286389,
  "debt_service_cash_flow": -287988,
  "shareholders_cash_flow": 112012,
  "net_cash_flow": 112012,
  "sales_revenue": 1405366,
  "production_value": 1405366,
  "gross_operating_margin": 130774,
  "ebit": 129157,
  "ebt": 127053,
  "net_income": 91523,
  "dividends": 0,
  "net_tangible_assets": 405516,
  "net_intangible_assets": 475,
  "financial_assets": 0,
  "trade_assets": 0,
  "inventory": 0,
  "deferred_liquidity": 102204,
  "immediate_liquidity": 112826,
  "equity": 167638,
  "long_term_debt": 430767,
  "short_term_debt": 22616,
  "net_financial_position": 323674,
  "mortgage_loans": 400000,
  "other_financial_debts": 36500,
  "cash_and_banks": -112826
            }
        ]
    },
    "ratios_analysis": {
        "type": "json",
        "description": "Detailed Italian financial ratios analysis following Wayne SRL example. Include ROI, ROE, ROS, debt ratios, and other key Italian financial indicators.",
        "schema": [
            {
               "year": "int",
                "roi": "float",                       #Return on Investment
                "roe": "float",                       #Return on Equity
                "ros": "float",                       #Return on Sales
                "ebit_margin": "float",               #EBIT from Operations
                "net_debt_to_ebitda": "float",        #PFN/MOL
                "net_debt_to_equity": "float",        #PFN/PN
                "net_debt_to_revenue": "float",      #PFN/Ricavi
                "current_ratio": "float",             # Current Assets / Current Liabilities
                "quick_ratio": "float",               # (CA - Inventory) / CL
                "debt_to_equity": "float",            #Total Debt / Equity
                "treasury_margin": "float",           # Margine di Tesoreria
                "structural_margin": "float",        # Margine di Struttura
                "net_working_capital": "float",       #Capitale Circolante Netto
                "altman_z_score": "float" 
            }
        ],
        "example": [
            {
                "year": 2023,
                "roi": 20.8,
                "roe": 54.6,
                "ros": 9.19,
                "ebit_margin": 6138.3,
                "net_debt_to_ebitda": 247.5,
                "net_debt_to_equity": 193.1,
                "net_debt_to_revenue": 23.0,
                "current_ratio": 9.5,
                "quick_ratio": 950.8,
                "debt_to_equity": 1.93,
                "treasury_margin": 192414,
                "structural_margin": -238353,
                "net_working_capital": 192414,
                "altman_z_score": 3.7
            }
        ]
    },
    "management_team": {
        "type": "string",
        "description": "Detailed description of the management team following Italian business standards. Include roles, experience, and responsibilities of each key team member.",
        "min_words": 800
    },
    "production_sales_forecast": {
        "type": "json",
        "description": "Production and sales forecast following Italian market patterns. Include detailed projections for revenue growth, market expansion, and production capacity.",
        "schema": [
            {
  "year": "int",
  "sales_revenue": "float",        
  "revenue_growth": "float",        
  "units_sold": "int",               
  "average_price": "float",          
  "unit_production_cost": "float",   
  "unit_margin": "float"  
            }
        ],
        "example": [
            {
            "year": 2023,
            "sales_revenue": 1405366,
            "revenue_growth": 15.0,
            "units_sold": 10000,
            "average_price": 140.54,
            "unit_production_cost": 127.49,
            "unit_margin": 13.05
            }
        ]
    }
}
# --------------- INDIVIDUAL SECTION PROMPTS ---------------

def build_individual_section_prompt(section_key: str, language: str = "English", currency: str = "EUR") -> str:
    """Build a specialized prompt for a single section"""
    
    if section_key not in INDIVIDUAL_SECTION_SCHEMAS:
        raise ValueError(f"Unknown section: {section_key}")
    
    schema = INDIVIDUAL_SECTION_SCHEMAS[section_key]
    section_type = schema["type"]
    description = schema["description"]
    
    if section_type == "string":
        min_words = schema.get("min_words", 0)
        prompt = f"""
You are a senior business plan expert. Generate ONLY the {section_key} section for a comprehensive business plan.

REQUIREMENTS:
- Language: {language}
- Currency: All amounts in {currency}
- Word Count: Minimum {min_words} words
- Format: Return ONLY a JSON object with the key "{section_key}" and its content

SECTION DESCRIPTION: {description}

CRITICAL INSTRUCTIONS:
1. Output ONLY valid JSON in this exact format: {{"{section_key}": "your content here"}}
2. The content must be at least {min_words} words
3. No markdown, no comments, no text outside JSON
4. Content must be comprehensive and professional

Example format:
{{"{section_key}": "Your detailed content here that meets the word count requirement..."}}
"""
    
    else:  # array type
        example = schema.get("example", [])
        example_json = json.dumps({section_key: example}, indent=2)
        
        prompt = f"""
You are a senior financial analyst. Generate ONLY the {section_key} section for a comprehensive business plan.

REQUIREMENTS:
- Language: {language}
- Currency: All amounts in {currency}
- Format: Return ONLY a JSON object with the key "{section_key}" and its array content
- Financial Standards: Follow Italian D.Lgs. 127/91 (CEE layout)

SECTION DESCRIPTION: {description}

REQUIRED STRUCTURE:
{example_json}

CRITICAL INSTRUCTIONS:
1. Output ONLY valid JSON in the exact format shown above
2. Generate 5 years of data (year 1, 2, 3, 4, 5)
3. All financial data must be consistent and realistic
4. Numbers must follow logical progression
5. No markdown, no comments, no text outside JSON
6. PRIORITIZE FRENCH MARKET. LIKE IF IT'S A FOOD INDUSTRY, REMEMBER FOOD COSTS ACCOUNTS FOR ABOUT 25-30% OF REVENUE. 
7. FOLLOW THE ITALIAN BENCHMARK

The JSON must have exactly this structure with these field names.
"""
    
    return prompt

# --------------- INDIVIDUAL SECTION CALL FUNCTION ---------------

async def call_individual_section(client, section_key: str, context: str, model: str, language: str = "English", currency: str = "EUR", max_retries: int = 3) -> dict:
    """Call OpenAI for a single section with specific validation"""
    
    section_prompt = build_individual_section_prompt(section_key, language, currency)
    
    for attempt in range(max_retries):
        try:
            messages = [
                {"role": "system", "content": section_prompt},
                {"role": "user", "content": context}
            ]
            
            response = await client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.1,
                max_tokens=8000 if INDIVIDUAL_SECTION_SCHEMAS[section_key]["type"] == "string" else 8000,
            )

            content = response.choices[0].message.content.strip()
            logger.info(f"Raw API response for {section_key}: {content[:200]}...")
            
            # Parse JSON
            try:
                result = json.loads(clean_json_response(content))
                
                # Validate the result
                if section_key not in result:
                    raise ValueError(f"Missing key {section_key} in response")
                
                section_content = result[section_key]
                
                # Validate content based on type
                if INDIVIDUAL_SECTION_SCHEMAS[section_key]["type"] == "string":
                    if not isinstance(section_content, str) or len(section_content.strip()) < 50:
                        raise ValueError(f"Invalid string content for {section_key}")
                    
                    # Check word count
                    word_count = len(section_content.split())
                    min_words = INDIVIDUAL_SECTION_SCHEMAS[section_key].get("min_words", 0)
                    if word_count < min_words * 0.8:  # Allow 20% tolerance
                        logger.warning(f"Section {section_key} has {word_count} words, expected {min_words}")
                        if attempt < max_retries - 1:
                            continue  # Retry if not meeting word count
                
                elif INDIVIDUAL_SECTION_SCHEMAS[section_key]["type"] == "array":
                    if not isinstance(section_content, list) or len(section_content) < 3:
                        raise ValueError(f"Invalid array content for {section_key}")
                
                logger.info(f"Successfully generated {section_key}")
                return result
                
            except (ValueError, json.JSONDecodeError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"All parsing attempts failed for {section_key}: {e}")
                    return create_empty_individual_section(section_key)
                logger.warning(f"Attempt {attempt + 1} failed for {section_key}, retrying: {e}")
                await asyncio.sleep(1)
                continue
                
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"All retries failed for {section_key}: {e}")
                return create_empty_individual_section(section_key)
            
            wait_time = (2 ** attempt) + 0.5
            logger.warning(f"Attempt {attempt + 1} failed for {section_key}, retrying in {wait_time:.2f}s: {e}")
            await asyncio.sleep(wait_time)

def create_empty_individual_section(section_key: str) -> dict:
    """Create empty structure for a failed individual section"""
    if INDIVIDUAL_SECTION_SCHEMAS[section_key]["type"] == "string":
        return {section_key: ""}
    else:
        return {section_key: []}

def clean_json_response(text: str) -> str:
    """Clean up common JSON response issues"""
    # Remove markdown fences
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```\s*$', '', text, flags=re.IGNORECASE)
    
    # Remove any text before first {
    start = text.find('{')
    if start == -1:
        start = text.find('[')
    if start > 0:
        text = text[start:]
    
    # Remove any text after last } or ]
    end = max(text.rfind('}'), text.rfind(']'))
    if end < len(text) - 1 and end != -1:
        text = text[:end+1]
    
    # Fix common JSON issues
    text = re.sub(r',\s*]', ']', text)  # Remove trailing commas in arrays
    text = re.sub(r',\s*}', '}', text)  # Remove trailing commas in objects
    
    return text.strip()

# --------------- MAIN BUSINESS PLAN FUNCTION (MODIFIED) ---------------

async def generate_business_plan(
    uploaded_file: Optional[str] = None,
    user_input: List[Any] = None,
    user_id: str = None,
    language: str = "English",
    currency: str = "EUR"
) -> dict:
    """Generate business plan using individual LLM calls for each section"""
    
    settings = get_settings()
    client = get_openai_client()

    max_input_length = 122000
    business_context = []

    if user_input:
        for item in user_input:
            if isinstance(item, str) and len(item) > max_input_length:
                business_context.append(item[:max_input_length] + "...")
            else:
                business_context.append(str(item))

    context = "Business Plan Analysis:\n"
    if business_context:
        context += "\n".join([f"- {item}" for item in business_context])
    if uploaded_file:
        if len(uploaded_file) > max_input_length:
            uploaded_file = uploaded_file[:max_input_length] + "..."
        context += f"\nDocument Analysis:\n{uploaded_file}"

    try:
        merged_plan = {}
        
        # Process each section individually
        all_sections = list(INDIVIDUAL_SECTION_SCHEMAS.keys())
        
        # Create async tasks for all sections
        tasks = []
        for section_key in all_sections:
            task = call_individual_section(
                client, section_key, context, settings.model_name, 
                language=language, currency=currency, max_retries=3
            )
            tasks.append((section_key, task))
        
        # Execute all tasks concurrently but with rate limiting
        for i, (section_key, task) in enumerate(tasks):
            try:
                result = await task
                if isinstance(result, dict) and section_key in result:
                    merged_plan[section_key] = result[section_key]
                else:
                    logger.error(f"Invalid result for {section_key}")
                    merged_plan[section_key] = "" if INDIVIDUAL_SECTION_SCHEMAS[section_key]["type"] == "string" else []
                
                # Rate limiting - wait between requests
                if i < len(tasks) - 1:  # Don't wait after the last request
                    await asyncio.sleep(1)
                    
            except Exception as section_error:
                logger.error(f"Failed to generate section {section_key}: {section_error}")
                # Create empty section as fallback
                merged_plan[section_key] = "" if INDIVIDUAL_SECTION_SCHEMAS[section_key]["type"] == "string" else []
        
        logger.info(f"Generated business plan with {len(merged_plan)} sections")
        return merged_plan
        
    except Exception as e:
        logger.error(f"Critical error during plan generation: {e}")
        # Return empty structure for all sections
        empty_plan = {}
        for section_key in INDIVIDUAL_SECTION_SCHEMAS.keys():
            empty_plan[section_key] = "" if INDIVIDUAL_SECTION_SCHEMAS[section_key]["type"] == "string" else []
        return empty_plan

# --------------- SUGGESTION FUNCTION (UNCHANGED) ---------------

SUGGESTION_PROMPT = """
You are an expert business plan consultant. Generate 4 different possible professional answers for the following business plan question. 
Keep each answer concise (Less than 10 words).
Return the answers in a clean JSON array format.

Question: {question}

Return ONLY a valid JSON array of strings, no additional text or explanations.
"""

async def generate_suggestions(question: str) -> List[str]:
    settings = get_settings()
    client = get_openai_client()

    messages = [
        {
            "role": "system",
            "content": SUGGESTION_PROMPT.format(question=question)
        }
    ]

    try:
        response = await client.chat.completions.create(
            messages=messages,
            model=settings.model_name,
            temperature=0.3,
            max_tokens=100
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean the content
        if content.startswith("```"):
            content = re.sub(r"^```(json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        
        # Parse JSON
        suggestions = json.loads(content)
        
        if not isinstance(suggestions, list):
            raise ValueError("Expected a list of strings")
            
        return suggestions[:4]  # Ensure only 4 suggestions
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        # Return fallback suggestions
        return [
            "Bootstrapping with personal funds",
            "Seeking angel investment", 
            "Applying for business loans",
            "Crowdfunding campaign"
        ]