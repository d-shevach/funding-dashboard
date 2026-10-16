"""Input validation for all transaction types"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class TransactionValidator:
    """Validates all transaction inputs"""

    VALID_BANKS = {"BTG Pactual", "BofA", "Morgan Stanley", "Millenium"}
    VALID_CURRENCIES = {"USD", "BRL", "EUR", "GBP", "JPY"}

    @staticmethod
    def validate_ticker(ticker: str) -> str:
        """Validate and clean ticker symbol"""
        if not ticker or not isinstance(ticker, str):
            raise ValidationError("Ticker must be a non-empty string")

        ticker = ticker.strip().upper()
        if len(ticker) < 1 or len(ticker) > 10:
            raise ValidationError("Ticker must be between 1 and 10 characters")

        if not ticker.replace(".", "").isalnum():
            raise ValidationError("Ticker can only contain letters, numbers, and dots")

        return ticker

    @staticmethod
    def validate_name(name: str) -> str:
        """Validate asset name"""
        if not name or not isinstance(name, str):
            raise ValidationError("Name must be a non-empty string")

        name = name.strip()
        if len(name) < 2 or len(name) > 255:
            raise ValidationError("Name must be between 2 and 255 characters")

        return name

    @staticmethod
    def validate_setor(setor: str) -> str:
        """Validate sector"""
        if not setor or not isinstance(setor, str):
            raise ValidationError("Sector must be a non-empty string")

        setor = setor.strip()
        if len(setor) < 2 or len(setor) > 100:
            raise ValidationError("Sector must be between 2 and 100 characters")

        return setor

    @staticmethod
    def validate_quantity(quantity: Any) -> Decimal:
        """Validate quantity"""
        try:
            qty = Decimal(str(quantity))
        except:
            raise ValidationError("Quantity must be a valid number")

        if qty <= 0:
            raise ValidationError("Quantity must be greater than zero")

        if qty > Decimal("999999999"):
            raise ValidationError("Quantity is too large")

        return qty

    @staticmethod
    def validate_price(price: Any) -> Decimal:
        """Validate price"""
        try:
            p = Decimal(str(price))
        except:
            raise ValidationError("Price must be a valid number")

        if p <= 0:
            raise ValidationError("Price must be greater than zero")

        if p > Decimal("999999999"):
            raise ValidationError("Price is too large")

        # Check decimal places (max 8)
        sign, digits, exponent = p.as_tuple()
        if exponent < -8:
            raise ValidationError("Price can have at most 8 decimal places")

        return p

    @staticmethod
    def validate_currency(currency: str) -> str:
        """Validate currency code"""
        if not currency or not isinstance(currency, str):
            raise ValidationError("Currency must be a non-empty string")

        currency = currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValidationError("Currency must be a 3-letter code (e.g., USD, BRL)")

        return currency

    @staticmethod
    def validate_bank(bank: str) -> str:
        """Validate bank name"""
        if not bank or not isinstance(bank, str):
            raise ValidationError("Bank must be a non-empty string")

        bank = bank.strip()
        if bank not in TransactionValidator.VALID_BANKS:
            raise ValidationError(
                f"Bank must be one of: {', '.join(TransactionValidator.VALID_BANKS)}"
            )

        return bank

    @staticmethod
    def validate_date(date_input: Any) -> date:
        """Validate date"""
        if isinstance(date_input, date):
            d = date_input
        elif isinstance(date_input, datetime):
            d = date_input.date()
        elif isinstance(date_input, str):
            try:
                d = datetime.strptime(date_input, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Date must be in format YYYY-MM-DD")
        else:
            raise ValidationError("Invalid date format")

        if d > date.today():
            raise ValidationError("Date cannot be in the future")

        return d

    @staticmethod
    def validate_stock_transaction(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a complete stock transaction"""
        validated = {}

        validated["nome"] = TransactionValidator.validate_name(data.get("nome"))
        validated["ticker"] = TransactionValidator.validate_ticker(data.get("ticker"))
        validated["setor"] = TransactionValidator.validate_setor(data.get("setor"))
        validated["data"] = TransactionValidator.validate_date(data.get("data"))
        validated["quantidade"] = TransactionValidator.validate_quantity(data.get("quantidade"))
        validated["preco"] = TransactionValidator.validate_price(data.get("preco"))
        validated["moeda"] = TransactionValidator.validate_currency(data.get("moeda"))
        validated["banco"] = TransactionValidator.validate_bank(data.get("banco"))

        # Check for minimum investment
        valor_investido = validated["quantidade"] * validated["preco"]
        if valor_investido < Decimal("0.01"):
            raise ValidationError("Investment value must be at least 0.01")

        return validated

    @staticmethod
    def validate_etf_transaction(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate ETF transaction - same as stock"""
        return TransactionValidator.validate_stock_transaction(data)

    @staticmethod
    def validate_fund_transaction(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate fund transaction"""
        validated = {}

        validated["nome"] = TransactionValidator.validate_name(data.get("nome"))
        validated["ticker"] = TransactionValidator.validate_ticker(data.get("ticker"))
        validated["tipo"] = TransactionValidator.validate_name(data.get("tipo"))
        validated["data"] = TransactionValidator.validate_date(data.get("data"))
        validated["quantidade"] = TransactionValidator.validate_quantity(data.get("quantidade"))
        validated["preco"] = TransactionValidator.validate_price(data.get("preco"))
        validated["moeda"] = TransactionValidator.validate_currency(data.get("moeda"))
        validated["banco"] = TransactionValidator.validate_bank(data.get("banco"))

        # Validate fees (optional, defaults to 0)
        try:
            taxa_admin = Decimal(str(data.get("taxa_administracao", 0)))
            taxa_perf = Decimal(str(data.get("taxa_performance", 0)))

            if taxa_admin < 0 or taxa_admin > 100:
                raise ValidationError("Administration fee must be between 0 and 100")
            if taxa_perf < 0 or taxa_perf > 100:
                raise ValidationError("Performance fee must be between 0 and 100")

            validated["taxa_administracao"] = taxa_admin
            validated["taxa_performance"] = taxa_perf
        except:
            raise ValidationError("Fees must be valid numbers between 0 and 100")

        # Resgate (redemption term)
        validated["resgate"] = TransactionValidator.validate_name(data.get("resgate", "Indeterminado"))

        return validated

    @staticmethod
    def validate_bond_transaction(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate bond transaction"""
        validated = {}

        validated["nome"] = TransactionValidator.validate_name(data.get("nome"))
        validated["ticker"] = TransactionValidator.validate_ticker(data.get("ticker"))
        validated["tipo_titulo"] = TransactionValidator.validate_name(data.get("tipo_titulo"))
        validated["data"] = TransactionValidator.validate_date(data.get("data"))
        validated["data_vencimento"] = TransactionValidator.validate_date(data.get("data_vencimento"))
        validated["quantidade"] = TransactionValidator.validate_quantity(data.get("quantidade"))
        validated["preco"] = TransactionValidator.validate_price(data.get("preco"))
        validated["moeda"] = TransactionValidator.validate_currency(data.get("moeda"))
        validated["banco"] = TransactionValidator.validate_bank(data.get("banco"))

        # Validate maturity date is after purchase date
        if validated["data_vencimento"] <= validated["data"]:
            raise ValidationError("Maturity date must be after purchase date")

        # Validate coupon
        try:
            cupom = Decimal(str(data.get("cupom", 0)))
            if cupom < 0 or cupom > 100:
                raise ValidationError("Coupon must be between 0 and 100")
            validated["cupom"] = cupom
        except:
            raise ValidationError("Coupon must be a valid number")

        return validated

    @staticmethod
    def validate_sale(
        quantidade_disponivel: Decimal,
        quantidade_venda: Decimal,
        preco_venda: Decimal
    ) -> tuple:
        """Validate a sale transaction"""
        quantidade_venda = TransactionValidator.validate_quantity(quantidade_venda)
        preco_venda = TransactionValidator.validate_price(preco_venda)

        if quantidade_venda > quantidade_disponivel:
            raise ValidationError(
                f"Cannot sell {quantidade_venda} units. Only {quantidade_disponivel} available"
            )

        return quantidade_venda, preco_venda
