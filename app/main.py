from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Query
from fastapi.responses import JSONResponse
import json
from .models import BusinessIdeaInput, BusinessPlan, PDFExtraction, SuggestionRequest, SuggestionResponse, DocumentExtraction, FinancialExtraction
from app.services import generate_business_plan, generate_suggestions
from app.pdf_service import extract_text_from_pdf
from typing import List
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Business Plan Generator API",
    version="1.0.0",
    description="Generates a comprehensive JSON business plan"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)


@app.post("/generate", response_model=dict)
async def create_business_plan(payload: BusinessIdeaInput):
    plan_dict = await generate_business_plan(
        uploaded_file=payload.uploaded_file,
        user_input=payload.user_input,
        user_id=payload.user_id
    )
    return plan_dict

@app.post("/extract-pdf", response_model=DocumentExtraction)
async def extract_pdf(
    file: UploadFile = File(...),
    document_type: str = Query(..., description="Type of document: 'balance_sheet' or 'company_extract'")
):
    """
    Extract text and financial data from PDF files
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        contents = await file.read()
        text_content, page_count, metadata, financial_data = extract_text_from_pdf(contents, document_type)
        
        return DocumentExtraction(
            text_content=text_content,
            page_count=page_count,
            metadata=metadata,
            financial_data=FinancialExtraction(**financial_data) if financial_data else None,
            document_type=document_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

# @app.post("/generate-from-pdf", response_model=BusinessPlan)
# async def create_business_plan_from_pdf(file: UploadFile = File(...)):
#     """
#     Extract text from PDF and generate a business plan
#     """
#     if not file.filename.lower().endswith('.pdf'):
#         raise HTTPException(status_code=400, detail="File must be a PDF")
    
#     try:
#         contents = await file.read()
#         text_content, _, _ = extract_text_from_pdf(contents)
        
#         # Generate business plan from extracted text
#         plan_dict = generate_business_plan(text_content)
#         return BusinessPlan(**plan_dict)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/suggestions", response_model=SuggestionResponse)
async def get_suggestions(request: SuggestionRequest):
    """
    Generate multiple answer suggestions for a business plan question
    """
    try:
        suggestions = await generate_suggestions(
            question=request.question
        )
        return SuggestionResponse(
            question=request.question,
            suggestions=suggestions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )
