import re
from typing import Optional, Dict
import pytesseract
from decimal import Decimal

class FinancialDataExtractor:
    def __init__(self):
        # Common Italian financial terms and their variations
        self.financial_patterns = {
            'total_assets': r'(?i)(totale attivo|totale dell[\ '']attivo|attività totali)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
            'total_revenue': r'(?i)(ricavi|fatturato|ricavi delle vendite)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
            'net_income': r'(?i)(utile netto|risultato netto|risultato d[\ '']esercizio)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
            'total_liabilities': r'(?i)(totale passivo|totale delle passività)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
            'equity': r'(?i)(patrimonio netto|capitale proprio)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
            'year': r'(?i)(bilancio|esercizio)[\s:]*(20\d{2})'
        }

    def get_scale_multiplier(self, scale: Optional[str]) -> float:
        """Determine the multiplier based on the scale indicator"""
        if not scale:
            return 1000  # Convert to thousands by default
        
        scale = scale.lower()
        if scale in ['k']:
            return 1  # Already in thousands
        elif scale in ['m', 'mln']:
            return 1000  # Convert millions to thousands
        elif scale in ['b', 'mrd']:
            return 1000000  # Convert billions to thousands
        return 0.001  # Default: convert to thousands

    def clean_number(self, value: str, scale: Optional[str] = None) -> float:
        """Clean and convert string numbers to float in thousands"""
        try:
            # Remove any non-numeric characters except . and ,
            cleaned = re.sub(r'[^\d.,]', '', value)
            # Convert Italian number format (1.234,56) to standard float
            cleaned = cleaned.replace('.', '').replace(',', '.')
            number = float(cleaned)
            
            # Apply scale multiplier
            multiplier = self.get_scale_multiplier(scale)
            return number * multiplier
            
        except:
            return 0.0

    def extract_financial_data(self, text: str) -> Dict:
        """Extract financial data from text using regex patterns"""
        financial_data = {}
        
        for key, pattern in self.financial_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                if key == 'year':
                    financial_data[key] = int(matches[0][1])
                else:
                    value, scale = matches[0][1], matches[0][2] if len(matches[0]) > 2 else None
                    financial_data[key] = self.clean_number(value, scale)
        
        return financial_data