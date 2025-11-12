"""
Finance calculation module for AutoFinder.

Implements standard loan amortization formulas to calculate monthly payments
and filter vehicles based on finance constraints.
"""

from typing import Optional
from models import FinanceConfig, FinanceInfo, FinanceAssumptions


def calculate_monthly_payment(
    price: float,
    down_payment: float,
    finance_config: FinanceConfig
) -> float:
    """
    Calculate monthly payment using standard amortization formula.

    Formula: M = P * [r(1+r)^n] / [(1+r)^n - 1]
    Where:
        P = financed principal (after down payment, with TTL and fees)
        r = monthly interest rate (APR / 12 / 100)
        n = term in months

    Args:
        price: Vehicle list price
        down_payment: Down payment amount
        finance_config: Finance parameters (APR, term, fees, TTL)

    Returns:
        Monthly payment amount

    Raises:
        ValueError: If inputs are invalid or payment cannot be calculated
    """
    if price <= 0:
        raise ValueError(f"Price must be positive, got {price}")
    if down_payment < 0:
        raise ValueError(f"Down payment cannot be negative, got {down_payment}")
    if down_payment > price:
        raise ValueError(f"Down payment ({down_payment}) cannot exceed price ({price})")

    # Calculate total amount to finance
    # Add taxes/title/license and doc fees to the price
    ttl_amount = price * (finance_config.ttl_percent_of_price / 100.0)
    total_cost = price + ttl_amount + finance_config.doc_fees

    # Subtract down payment to get principal
    principal = total_cost - down_payment

    # If principal is zero or negative, no financing needed
    if principal <= 0:
        return 0.0

    # Handle zero APR case (special financing)
    if finance_config.apr_percent == 0:
        return principal / finance_config.term_months

    # Calculate monthly interest rate
    monthly_rate = finance_config.apr_percent / 12.0 / 100.0

    # Standard amortization formula
    numerator = monthly_rate * ((1 + monthly_rate) ** finance_config.term_months)
    denominator = ((1 + monthly_rate) ** finance_config.term_months) - 1

    if denominator == 0:
        raise ValueError("Cannot calculate payment: invalid term or rate")

    monthly_payment = principal * (numerator / denominator)

    # Round to 2 decimal places (cents)
    return round(monthly_payment, 2)


def create_finance_info(
    price: float,
    down_payment: float,
    finance_config: FinanceConfig
) -> FinanceInfo:
    """
    Create complete finance information for a vehicle.

    Args:
        price: Vehicle list price
        down_payment: Down payment amount
        finance_config: Finance parameters

    Returns:
        FinanceInfo object with calculated monthly payment and assumptions
    """
    monthly = calculate_monthly_payment(price, down_payment, finance_config)

    return FinanceInfo(
        est_down=down_payment,
        est_monthly=monthly,
        assumptions=FinanceAssumptions(
            apr_percent=finance_config.apr_percent,
            term_months=finance_config.term_months,
            ttl_percent_of_price=finance_config.ttl_percent_of_price,
            doc_fees=finance_config.doc_fees
        )
    )


def meets_budget_constraints(
    price: float,
    max_down_payment: float,
    max_monthly_payment: float,
    finance_config: FinanceConfig
) -> tuple[bool, Optional[FinanceInfo]]:
    """
    Check if a vehicle meets budget constraints.

    Attempts to finance the vehicle with the configured down payment,
    and checks if the resulting monthly payment is within budget.

    Args:
        price: Vehicle list price
        max_down_payment: Maximum available down payment
        max_monthly_payment: Maximum acceptable monthly payment
        finance_config: Finance parameters

    Returns:
        Tuple of (meets_constraints, finance_info)
        - meets_constraints: True if vehicle is affordable
        - finance_info: FinanceInfo if affordable, None otherwise
    """
    try:
        # Use the maximum down payment for best monthly rate
        down_payment = min(max_down_payment, price)

        finance_info = create_finance_info(price, down_payment, finance_config)

        # Check if monthly payment is within budget
        if finance_info.est_monthly <= max_monthly_payment:
            return True, finance_info
        else:
            return False, None

    except (ValueError, ZeroDivisionError) as e:
        # Invalid calculation - vehicle doesn't meet constraints
        return False, None


def format_currency(amount: float) -> str:
    """Format amount as USD currency string."""
    return f"${amount:,.2f}"


def format_monthly_payment(monthly: float) -> str:
    """Format monthly payment for display."""
    return f"${monthly:,.2f}/mo"


# ============================================================================
# Example usage and validation
# ============================================================================

if __name__ == "__main__":
    """Test finance calculations with example values from spec."""

    # Example from spec: 2019 Honda Accord at $18,990
    test_config = FinanceConfig(
        apr_percent=6.0,
        term_months=60,
        doc_fees=200,
        ttl_percent_of_price=7.5
    )

    price = 18990
    down = 3000
    max_monthly = 450

    print("Finance Calculator Test")
    print("=" * 50)
    print(f"Vehicle Price: {format_currency(price)}")
    print(f"Down Payment: {format_currency(down)}")
    print(f"APR: {test_config.apr_percent}%")
    print(f"Term: {test_config.term_months} months")
    print(f"Doc Fees: {format_currency(test_config.doc_fees)}")
    print(f"TTL: {test_config.ttl_percent_of_price}%")
    print()

    # Calculate monthly payment
    monthly = calculate_monthly_payment(price, down, test_config)
    print(f"Monthly Payment: {format_monthly_payment(monthly)}")
    print()

    # Check budget constraints
    meets, info = meets_budget_constraints(price, down, max_monthly, test_config)
    print(f"Within Budget (max {format_monthly_payment(max_monthly)}): {meets}")

    if info:
        print(f"Total Down: {format_currency(info.est_down)}")
        print(f"Monthly: {format_monthly_payment(info.est_monthly)}")
