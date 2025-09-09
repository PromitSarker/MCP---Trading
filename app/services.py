import asyncio
import json
from typing import List, Optional, Any
import re
import logging
from app.config import get_settings, get_openai_client

# --------------- SECTION GROUPING ---------------
MAX_TOKENS_PARTIAL = 29000

# More logical grouping - separate text sections from financial sections
SECTION_GROUPS = [
    ["financial_highlights", "cash_flow_analysis", "profit_and_loss_projection"],
    ["balance_sheet", "net_financial_position", "debt_structure", "key_ratios"],
    ["operating_cost_breakdown"],
    ["executive_summary"],
    ["business_overview"],
    ["market_analysis"],
    ["business_model"],
    ["marketing_and_sales_strategy"],
    # Financial sections grouped together for consistency
    
    ["sector_strategy"],
    ["funding_sources"],
    ["operations_plan"]
]

# --------------- SCHEMA DEFINITION ---------------

# Define the schema as a Python dictionary instead of a string
SCHEMA_DEFINITION = {
    "executive_summary": "Summarize the overall business opportunity in 300+ words: include the core product or service, the market need it addresses, key team strengths, business traction (if any), and the long-term vision. Highlight why this business matters now.",
    "business_overview": "Describe the company's mission, vision, and founding story in 1050+ words. Include when and why it was started, what goals it seeks to achieve, where it is currently based, and what motivates the team behind it.",
    "market_analysis": "Provide a 1000+ word analysis of the market: total addressable market (TAM), serviceable available market (SAM), and obtainable market (SOM). Identify competitors, customer segments, market trends, and why the timing is right for this solution.",
    "business_model": "Explain how the business makes money in 1200+ words. Describe primary and secondary revenue streams, customer acquisition strategy, pricing model, cost structure, margins, and how the model scales over time.",
    "marketing_and_sales_strategy": "Describe in 1500+ words how the business plans to go to market. Include positioning, target customers, sales channels (online/offline), customer acquisition cost (CAC) strategies, conversion funnels, and how growth will be driven operationally.",
    "financial_highlights": [
        {"year": "int", "revenue": "float", "net_income": "float", "capex": "float", "debt_repayment": "float"}
    ],
    "cash_flow_analysis": [
        {"year": "int", "operating": "float", "investing": "float", "financing": "float", "net_cash": "float"}
    ],
    "profit_and_loss_projection": [
        {
            "year": "int",
            "revenue": "float",
            "cogs": "float",
            "gross_profit": "float",
            "operating_expenses": "float",
            "ebitda": "float",
            "depreciation_amortization": "float",
            "ebit": "float",
            "interest": "float",
            "taxes": "float",
            "net_income": "float"
        }
    ],
    "balance_sheet": [
        {
            "year": "int",
            "assets": "float",
            "current_assets": "float",
            "non_current_assets": "float",
            "liabilities": "float",
            "current_liabilities": "float",
            "non_current_liabilities": "float",
            "equity": "float"
        }
    ],
    "net_financial_position": [{"year": "int", "net_position": "float"}],
    "debt_structure": [{"year": "int", "repayment": "float", "interest_rate": "float", "outstanding_debt": "float"}],
    "key_ratios": [
        {
            "year": "int",
            "roi": "float",
            "roe": "float",
            "debt_to_equity": "float",
            "gross_margin": "float",
            "ebitda_margin": "float",
            "net_margin": "float",
            "current_ratio": "float",
            "quick_ratio": "float",
            "asset_turnover": "float"
        }
    ],
    "operating_cost_breakdown": [
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
            "tax": "float"
        }
    ],
    "sector_strategy": "Provide a detailed strategy (minimum 1250+ words) outlining how the company will operate within its specific industry sector. This should include analysis of current sector trends, competitive landscape, regulatory environment, key success factors, and how the business will position itself to gain a competitive advantage over time.",
    "funding_sources": "Explain in detail (minimum 1200+ words) all current and future funding sources, including but not limited to equity investment, loans, grants, crowdfunding, or internal cash flow. Specify amounts, stages of funding, potential investors or lenders, and how the funds will be allocated within the business.",
    "operations_plan": "Describe in depth (minimum 1500+ words) the company's operation plan, and any strategic moves. Include what the business will do to execute its strategy, including any strategic partnerships, collaborations, or acquisitions. Explain how the business will manage risks and opportunities, and how it will adapt to changing market conditions."
}

# --------------- SYSTEM PROMPT TEMPLATES ---------------

SYSTEM_PROMPT_HEADER = """
You are a senior financial analyst generating a detailed, investor-grade business plan in valid JSON. Provide everything in JSON MUST.

STRICT RULES:
- Output ONLY valid JSON, no markdown, no comments, no text outside JSON.
- STRICTLY FOLLOW THE STRUCTURE AND DATA TYPES in the schema.
- Language: match user input language.
- Financials: 3 years (year 1 to 3), fully consistent (e.g., net_cash = sum of flows, assets = liabilities + equity).
- Currency: All amounts must be in {currency}.
- Standards: All financial statements MUST follow Italian D.Lgs. 127/91 (CEE layout).

Only generate the following parts of the schema:
"""

# --------------- LOGGING ---------------
logger = logging.getLogger(__name__)


async def enhance_short_sections(client, plan: dict, context: str, model: str, language: str = "English") -> dict:
    """Enhance sections that are too short by making additional API calls"""
    enhanced_plan = plan.copy()
    
    # Define target word counts
    target_word_counts = {
        "executive_summary": 300,
        "business_overview": 1050, 
        "market_analysis": 1000,
        "business_model": 1200,
        "marketing_and_sales_strategy": 1500,
        "sector_strategy": 1250,
        "funding_sources": 1200,
        "operations_plan": 1500
    }
    
    for section, current_content in plan.items():
        if section in target_word_counts and isinstance(current_content, str):
            word_count = len(current_content.split())
            target_count = target_word_counts[section]
            
            if word_count < target_count * 0.8:  # If less than 80% of target
                logger.info(f"Enhancing {section} from {word_count} to {target_count} words")
                
                enhancement_prompt = f"""
The following {section} is too short. Please enhance it to be at least {target_count} words while maintaining the same content style and information.

Current {section}:
{current_content}

Please provide an enhanced version that is more detailed and comprehensive:
"""
                
                try:
                    response = await client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": f"You are enhancing a business plan section to meet word count requirements. Use {language}."},
                            {"role": "user", "content": enhancement_prompt}
                        ],
                        model=model,
                        temperature=0.5,
                        max_tokens=4000,  # Increased tokens for longer responses
                    )
                    
                    enhanced_content = response.choices[0].message.content.strip()
                    enhanced_plan[section] = enhanced_content
                    logger.info(f"Enhanced {section} to {len(enhanced_content.split())} words")
                    
                except Exception as e:
                    logger.error(f"Failed to enhance {section}: {e}")
                    # Keep the original content if enhancement fails
    
    return enhanced_plan

# --------------- HELPER FUNCTIONS ---------------

def build_partial_prompt(section_keys: List[str], language: str = "English", currency: str = "EUR") -> str:

 
    """Build a detailed prompt with explicit word count requirements"""
    if not section_keys:
        raise ValueError("section_keys cannot be empty")

    # Define word count requirements for each section
    word_count_requirements = {
        "executive_summary": "300+ words",
        "business_overview": "1050+ words", 
        "market_analysis": "1000+ words",
        "business_model": "1200+ words",
        "marketing_and_sales_strategy": "1500+ words",
        "sector_strategy": "1250+ words",
        "funding_sources": "1200+ words",
        "operations_plan": "1500+ words"
    }
    
    # Build section-specific instructions
    section_instructions = []
    for key in section_keys:
        if key in word_count_requirements:
            section_instructions.append(f"- {key}: {word_count_requirements[key]}")
        elif key in ["financial_highlights", "cash_flow_analysis", "profit_and_loss_projection", 
                    "balance_sheet", "net_financial_position", "debt_structure", "key_ratios", 
                    "operating_cost_breakdown"]:
            section_instructions.append(f"- {key}: 3 years of financial data (year 1, 2, 3)")
    
    # Build financial consistency instructions for financial sections
    financial_instructions = ""
    if any(key in section_keys for key in ["financial_highlights", "cash_flow_analysis", 
                                         "profit_and_loss_projection", "balance_sheet", 
                                         "net_financial_position", "debt_structure", 
                                         "key_ratios", "operating_cost_breakdown"]):
        financial_instructions = """
FINANCIAL CONSISTENCY REQUIREMENTS:
- All financial statements must cover 3 years (year 1 to 3)
- Numbers must be consistent across all statements
- Revenue in financial_highlights must match profit_and_loss_projection
- Net income must be consistent across statements
- Assets must equal liabilities + equity in balance sheet
- Cash flow components must sum to net_cash
- Ratios must be calculated correctly from the financial data
- All amounts in {currency}
"""

    # Create example JSON for the requested sections
    example_json = {}
    for key in section_keys:
        if key in ["executive_summary", "business_overview", "market_analysis", 
                  "business_model", "marketing_and_sales_strategy", "sector_strategy",
                  "funding_sources", "operations_plan"]:
            example_json[key] = f"This section should contain {word_count_requirements.get(key, 'detailed content')} as specified in the requirements."
        else:
            # For financial sections, create example arrays
            example_json[key] = [{"year": 1, "example_field": "example_value"}]
    
    example_str = json.dumps(example_json, indent=2)

    prompt = f"{SYSTEM_PROMPT_HEADER.format(currency=currency)}{', '.join(section_keys)}\n\n" \
    f"LANGUAGE REQUIREMENT:\n- All output must be written in **{language}**.\n\n" \
             "CRITICAL WORD COUNT REQUIREMENTS:\n" + \
             "\n".join(section_instructions) + "\n\n" \
             "IMPORTANT: You MUST generate content that meets or exceeds the word count requirements. " \
             "If your response is too short, I will need to regenerate it, which is inefficient. " \
             "Please ensure you provide comprehensive, detailed content that fully addresses each section.\n\n" \
             f"{financial_instructions}" \
             f"Example output format:\n{example_str}\n\n" \
             "Return ONLY valid JSON matching this format. Do not include any other text, comments, or markdown formatting."
    
    return prompt


def extract_json_block(text: str) -> str:
    """Return only the first JSON object found in the string."""
    text = text.strip()
    # Remove markdown fences
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```\s*$', '', text, flags=re.IGNORECASE)

    # Find first opening brace
    start = text.find('{')
    if start == -1:
        start = text.find('[')
    if start == -1:
        raise ValueError("No JSON object or array found")

    # Balance braces/brackets
    brace = 0
    in_str = False
    escape = False
    result = []
    
    for char in text[start:]:
        result.append(char)
        
        if not in_str:
            if char in '{[':
                brace += 1
            elif char in '}]':
                brace -= 1
                if brace == 0:
                    break
            elif char == '"':
                in_str = True
        else:
            if char == '"' and not escape:
                in_str = False
            escape = (char == '\\' and not escape)
    
    return ''.join(result)

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
    
    # Fix unquoted keys
    text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', text)
    
    return text.strip()


async def call_partial_openai_with_wordcount_enforcement(client, section_keys, context, model, max_retries=3):
    """Call OpenAI with enforcement of word count requirements"""
    for attempt in range(max_retries):
        try:
            result = await call_partial_openai(client, section_keys, context, model)
            
            # Check if text sections meet word count requirements
            text_sections = [key for key in section_keys if key in [
                "executive_summary", "business_overview", "market_analysis", 
                "business_model", "marketing_and_sales_strategy", "sector_strategy",
                "funding_sources", "operations_plan"
            ]]
            
            needs_regeneration = False
            for key in text_sections:
                if key in result and isinstance(result[key], str):
                    word_count = len(result[key].split())
                    min_word_count = {
                        "executive_summary": 300,
                        "business_overview": 1050, 
                        "market_analysis": 1000,
                        "business_model": 1200,
                        "marketing_and_sales_strategy": 1500,
                        "sector_strategy": 1250,
                        "funding_sources": 1200,
                        "operations_plan": 1500
                    }.get(key, 0)
                    
                    if word_count < min_word_count:
                        logger.warning(f"Section {key} has only {word_count} words, needs regeneration")
                        needs_regeneration = True
                        break
            
            if needs_regeneration and attempt < max_retries - 1:
                logger.info(f"Regenerating sections {section_keys} due to word count issues")
                continue
                
            return result
                
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"All retries failed for {section_keys}: {e}")
                return create_empty_section(section_keys)
            wait_time = (2 ** attempt) + 0.5
            logger.warning(f"Attempt {attempt + 1} failed for {section_keys}, retrying in {wait_time:.2f}s: {e}")
            await asyncio.sleep(wait_time)

def create_empty_section(section_keys: List[str]) -> dict:
    """Create empty structure for failed sections"""
    empty_sections = {}
    for key in section_keys:
        if key in ["financial_highlights", "cash_flow_analysis", "profit_and_loss_projection", 
                  "balance_sheet", "net_financial_position", "debt_structure", "key_ratios", 
                  "operating_cost_breakdown"]:
            # Array types - create empty arrays
            empty_sections[key] = []
        else:
            # String types - create empty strings
            empty_sections[key] = ""
    return empty_sections

def validate_section_result(result: dict, section_keys: List[str]) -> bool:
    """Validate that the result contains the expected sections with proper data"""
    text_sections = ["executive_summary", "business_overview", "market_analysis", 
                    "business_model", "marketing_and_sales_strategy", "sector_strategy",
                    "funding_sources", "operations_plan"]
    
    financial_sections = ["financial_highlights", "cash_flow_analysis", "profit_and_loss_projection", 
                         "balance_sheet", "net_financial_position", "debt_structure", "key_ratios", 
                         "operating_cost_breakdown"]
    
    # Define minimum word counts for text sections (reduced for initial validation)
    min_word_counts = {
        "executive_summary": 200,  # Reduced from 300
        "business_overview": 800,   # Reduced from 1050
        "market_analysis": 800,     # Reduced from 1000
        "business_model": 900,      # Reduced from 1200
        "marketing_and_sales_strategy": 1200,  # Reduced from 1500
        "sector_strategy": 1000,    # Reduced from 1250
        "funding_sources": 1000,    # Reduced from 1200
        "operations_plan": 1200     # Reduced from 1500
    }
    
    for key in section_keys:
        if key not in result:
            logger.error(f"Missing expected key {key} in result")
            return False
            
        # Check if text sections have content
        if key in text_sections:
            if not isinstance(result[key], str):
                logger.error(f"Section {key} is not a string")
                return False
                
            content = result[key].strip()
            if len(content) < 50:
                logger.error(f"Section {key} is too short")
                return False
                
            # Check word count if we have a requirement for this section
            if key in min_word_counts:
                word_count = len(content.split())
                if word_count < min_word_counts[key]:
                    logger.warning(f"Section {key} has only {word_count} words, but ideally should have {min_word_counts[key]}+")
                    # Don't fail validation for word count, just warn
                    # return False
                
        # Check if financial arrays have data
        elif key in financial_sections:
            if not isinstance(result[key], list) or len(result[key]) == 0:
                logger.error(f"Financial section {key} is empty or not a list")
                return False
                
            # Check if we have 3 years of data
            if len(result[key]) < 3:
                logger.error(f"Financial section {key} has only {len(result[key])} years, but requires 3 years")
                return False
                
    return True

# --------------- API CALL FUNCTIONS ---------------

async def call_partial_openai(client, section_keys, context, model, language="English", currency="EUR"):
    partial_prompt = build_partial_prompt(section_keys, language, currency)
    messages = [
        {"role": "system", "content": partial_prompt},
        {"role": "user", "content": context}
    ]
    
    try:
        response = await client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.1,  # Lower temperature for more consistent JSON
            max_tokens=MAX_TOKENS_PARTIAL,
        )

        content = response.choices[0].message.content.strip()
        logger.info(f"Raw API response for {section_keys}: {content[:200]}...")
        
        # Try multiple parsing strategies
        parsing_attempts = [
            # Attempt 1: Direct JSON parse
            lambda: json.loads(content),
            
            # Attempt 2: Clean and parse
            lambda: json.loads(clean_json_response(content)),
            
            # Attempt 3: Extract JSON block and parse
            lambda: json.loads(extract_json_block(content)),
        ]
        
        for i, attempt in enumerate(parsing_attempts):
            try:
                result = attempt()
                logger.info(f"Successfully parsed {section_keys} with attempt {i+1}")
                
                # Validate the result has the expected structure
                if validate_section_result(result, section_keys):
                    return result
                else:
                    raise ValueError("Result doesn't match expected schema")
                    
            except (ValueError, json.JSONDecodeError) as e:
                if i == len(parsing_attempts) - 1:
                    logger.error(f"All parsing attempts failed for {section_keys}: {e}")
                    # Try to extract just the values we need from the malformed JSON
                    return extract_values_from_text(content, section_keys)
                continue
                
    except Exception as e:
        logger.error(f"API call failed for {section_keys}: {e}")
        raise e

def extract_values_from_text(text: str, section_keys: List[str]) -> dict:
    """Try to extract values from malformed JSON response text"""
    result = {}
    
    for key in section_keys:
        # Look for the key in the text
        pattern = f'"{key}"\\s*:\\s*("([^"]*)"|\\[([^\\]]*)\\])'
        match = re.search(pattern, text)
        
        if match:
            if match.group(2):  # String value
                result[key] = match.group(2)
            elif match.group(3):  # Array value
                # Try to parse the array
                try:
                    # Add brackets to make it a valid JSON array
                    array_text = "[" + match.group(3) + "]"
                    result[key] = json.loads(array_text)
                except:
                    result[key] = []
        else:
            # If we can't find the key, use empty value
            if key in ["financial_highlights", "cash_flow_analysis", "profit_and_loss_projection", 
                      "balance_sheet", "net_financial_position", "debt_structure", "key_ratios", 
                      "operating_cost_breakdown"]:
                result[key] = []
            else:
                result[key] = ""
    
    return result

async def call_partial_openai_with_retry(client, section_keys, context, model, language="English", currency="EUR", max_retries=3):
    for attempt in range(max_retries):
        try:
            # Call the actual OpenAI function with the language parameter
            result = await call_partial_openai(client, section_keys, context, model, language, currency)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"All retries failed for {section_keys}: {e}")
                return create_empty_section(section_keys)
            wait_time = (2 ** attempt) + 0.5
            logger.warning(f"Attempt {attempt + 1} failed for {section_keys}, retrying in {wait_time:.2f}s: {e}")
            await asyncio.sleep(wait_time)

# --------------- MAIN BUSINESS PLAN FUNCTION ---------------

async def generate_business_plan(
    uploaded_file: Optional[str] = None,
    user_input: List[Any] = None,
    user_id: str = None,
    language: str = "English",
    currency: str = "EUR"  # New parameter
) -> dict:
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
        
        for group in SECTION_GROUPS:
            try:
                # Use a higher max_tokens for text sections
                max_tokens = MAX_TOKENS_PARTIAL
                if any(key in group for key in ["executive_summary", "business_overview", "market_analysis", 
                                              "business_model", "marketing_and_sales_strategy", "sector_strategy",
                                              "funding_sources", "operations_plan"]):
                    max_tokens = 10000  # Increased tokens for text sections
                
                # Pass the language parameter to the retry function
                result = await call_partial_openai_with_retry(
    client, group, context, settings.model_name, language=language, currency=currency, max_retries=3
)
                if isinstance(result, dict):
                    merged_plan.update(result)
                await asyncio.sleep(1)  # Rate limiting
            except Exception as group_error:
                logger.error(f"Failed to generate group {group}: {group_error}")
                # Create empty sections as fallback
                empty_result = create_empty_section(group)
                merged_plan.update(empty_result)
        
        # Enhance short sections and pass the language
        enhanced_plan = await enhance_short_sections(client, merged_plan, context, settings.model_name, language)

        
        return enhanced_plan
        
    except Exception as e:
        logger.error(f"Critical error during plan generation: {e}")
        # Return at least an empty structure
        return create_empty_section([section for group in SECTION_GROUPS for section in group])
    

# --------------- SUGGESTION FUNCTION ---------------

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