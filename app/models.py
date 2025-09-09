from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any    
from pydantic import BaseModel, Field
from typing import List

class BusinessIdeaInput(BaseModel):
    uploaded_file: Optional[List[Any]] = Field(
        [],
        description="Base64-encoded PDF or plain-text document (≤ 10 MB)"
    )
    user_input: List[Any] = Field(
        [],
        description="List of strings / objects describing the business idea or requirements"
    )
    language: str = "English" 
    currency: str = "Euro"
    user_id: str 

class Section(BaseModel):
    title: str
    content: str
    

class SubSection(BaseModel):
    title: str
    sections: List[Section]

class FinancialHighlight(BaseModel):
    year: int
    revenue: float
    net_income: float
    capex: float
    debt_repayment: float

class CashFlow(BaseModel):
    year: int
    operating: float
    investing: float
    financing: float
    net_cash: float

class ProfitLoss(BaseModel):
    year: int
    revenue: float
    cogs: float
    gross_profit: float
    operating_expenses: float
    net_income: float

class BalanceSheet(BaseModel):
    year: int
    assets: float
    liabilities: float
    equity: float

class NetPosition(BaseModel):
    year: int
    net_position: float

class DebtRepayment(BaseModel):
    year: int
    repayment: float

class KeyRatio(BaseModel):
    year: int
    roi: float
    roe: float
    debt_to_equity: float

class OperatingCostBreakdown(BaseModel):
    year: int
    revenue: float
    cogs: float
    employee_costs: float
    marketing: float
    rent: float
    administration: float
    amortization: float
    other_expenses: float
    interest_expenses: float
    tax: float


class BusinessPlan(BaseModel):
    executive_summary: str
    business_overview: str
    market_analysis: str
    business_model: str
    marketing_and_sales_strategy: Optional[str] = []
    financial_highlights: List[FinancialHighlight] = []
    cash_flow_analysis: List[CashFlow] = []
    profit_and_loss_projection: List[ProfitLoss] = []
    balance_sheet: List[BalanceSheet] = []
    net_financial_position: List[NetPosition] = []
    debt_structure: List[DebtRepayment] = []
    key_ratios: List[KeyRatio] = []
    sector_strategy: str = []
    operations_plan:str=[]
    funding_sources:str= []


class PDFExtraction(BaseModel):
    text_content: str
    page_count: int
    metadata: Dict

class SuggestionRequest(BaseModel):
    question: str = Field(..., description="The business plan question to generate suggestions for")

class SuggestionResponse(BaseModel):
    question: str
    suggestions: List[str]

class FinancialExtraction(BaseModel):
    total_assets: Optional[float] = None
    total_revenue: Optional[float] = None
    net_income: Optional[float] = None
    total_liabilities: Optional[float] = None
    equity: Optional[float] = None
    year: Optional[int] = None
    currency: Optional[str] = "EUR"

class DocumentExtraction(PDFExtraction):
    financial_data: Optional[FinancialExtraction] = None
    document_type: str
