"""PDF Bank Statement Parser - Extract transactions from bank statements"""

import pdfplumber
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional
from src.logger import get_logger

logger = get_logger("parsers.pdf")


class BankPDFParser:
    """Extract investment transactions from bank PDF statements"""

    @staticmethod
    def parse_merrill_lynch(pdf_path: str) -> List[Dict]:
        """Parse Merrill Lynch / BofA statement PDF"""
        transactions = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"Parsing Merrill Lynch statement: {pdf_path}")

                # Look for holdings table (typically page 6-7)
                for page_num in range(len(pdf.pages)):
                    page = pdf.pages[page_num]
                    text = page.extract_text()

                    # Check if this page has holdings data
                    if text and ('Date acquired' in text or 'Quantity' in text):
                        tables = page.extract_tables()

                        if tables:
                            for table in tables:
                                # Parse holdings table
                                for row in table[1:]:  # Skip header
                                    if len(row) >= 6 and row[0] and row[1]:  # Has date and quantity
                                        try:
                                            # Extract data from row
                                            date_str = row[0].strip()
                                            security_name = row[0] if len(row[0]) > 10 else (row[1] if row[1] else "Unknown")

                                            # This is simplified - full parsing would need better handling
                                            # For now, extract from text analysis instead

                                        except Exception as e:
                                            logger.debug(f"Error parsing row: {e}")
                                            continue

                return transactions

        except Exception as e:
            logger.error(f"Error parsing Merrill Lynch statement: {e}")
            return transactions

    @staticmethod
    def parse_utmost(pdf_path: str) -> List[Dict]:
        """Parse UTMOST offshore statement PDF"""
        transactions = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"Parsing UTMOST statement: {pdf_path}")

                # UTMOST statement structure is different
                # Would need custom parsing based on their format

                return transactions

        except Exception as e:
            logger.error(f"Error parsing UTMOST statement: {e}")
            return transactions

    @staticmethod
    def extract_holdings_from_text(text: str) -> List[Dict]:
        """Extract holdings from parsed text"""
        holdings = []

        lines = text.split('\n')

        for i, line in enumerate(lines):
            # Look for lines with ticker/security names and quantities
            if any(marker in line for marker in ['ISHARES', 'VANGUARD', 'FIDELITY', 'ETF', 'Fund']):
                try:
                    # Try to extract date, quantity, price
                    if i > 0 and i < len(lines) - 1:
                        # Parse the security line and surrounding lines
                        # This is a simplified extraction

                        holding = {
                            'security': line.strip(),
                            'date': None,
                            'quantity': None,
                            'price': None,
                            'type': 'ETF' if 'ETF' in line else 'Fund'
                        }

                        if all([holding['security']]):
                            holdings.append(holding)

                except Exception as e:
                    logger.debug(f"Error extracting holding: {e}")
                    continue

        return holdings


class PDFParserFactory:
    """Factory to detect bank type and create appropriate parser"""

    @staticmethod
    def detect_bank(pdf_path: str) -> Optional[str]:
        """Detect which bank the PDF is from"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Check first few pages for bank identifier
                text = ""
                for page_num in range(min(2, len(pdf.pages))):
                    text += pdf.pages[page_num].extract_text()

                # Detect bank from content
                if 'Merrill Lynch' in text or 'BofA' in text:
                    return "merrill_lynch"
                elif 'UTMOST' in text:
                    return "utmost"
                elif 'BTG' in text or 'BTG Pactual' in text:
                    return "btg_pactual"
                elif 'Morgan Stanley' in text:
                    return "morgan_stanley"
                else:
                    return None

        except Exception as e:
            logger.error(f"Error detecting bank: {e}")
            return None

    @staticmethod
    def parse(pdf_path: str) -> List[Dict]:
        """Auto-detect bank and parse PDF"""
        bank = PDFParserFactory.detect_bank(pdf_path)

        if bank == "merrill_lynch":
            return BankPDFParser.parse_merrill_lynch(pdf_path)
        elif bank == "utmost":
            return BankPDFParser.parse_utmost(pdf_path)
        else:
            logger.warning(f"Unknown bank format for: {pdf_path}")
            return []
