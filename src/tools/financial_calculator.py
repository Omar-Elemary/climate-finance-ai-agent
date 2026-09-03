import logging

from .base import Tool, ToolResult

logger = logging.getLogger(__name__)


class FinancialCalculatorTool(Tool):
    """
    Computes basic financial metrics (NPV, ROI) for climate finance
    scenarios, e.g. evaluating a climate adaptation or mitigation project.
    """

    name = "financial_calculator"
    description = (
        "Calculate financial metrics for a climate finance scenario. "
        "Supports: 'npv' (Net Present Value) and 'roi' (Return on Investment). "
        "For NPV, provide: initial_investment, cash_flows (list of yearly returns), "
        "discount_rate (e.g. 0.05 for 5%). "
        "For ROI, provide: initial_investment, final_value."
    )

    def run(self, calculation: str = "", **kwargs) -> ToolResult:
        calculation = calculation.lower().strip()

        if calculation == "npv":
            return self._calculate_npv(**kwargs)
        elif calculation == "roi":
            return self._calculate_roi(**kwargs)
        else:
            return ToolResult(
                success=False,
                error=f"Unknown calculation type: '{calculation}'. Use 'npv' or 'roi'.",
            )

    def _calculate_npv(self, **kwargs) -> ToolResult:
        try:
            initial_investment = float(kwargs.get("initial_investment", 0))
            cash_flows = kwargs.get("cash_flows", [])
            discount_rate = float(kwargs.get("discount_rate", 0.0))

            if not cash_flows:
                return ToolResult(success=False, error="No cash_flows provided.")

            npv = -initial_investment
            for year, cash_flow in enumerate(cash_flows, start=1):
                npv += float(cash_flow) / ((1 + discount_rate) ** year)

            logger.info("Calculated NPV: %.2f", npv)
            return ToolResult(
                success=True,
                data={
                    "metric": "NPV",
                    "value": round(npv, 2),
                    "initial_investment": initial_investment,
                    "discount_rate": discount_rate,
                    "years": len(cash_flows),
                },
            )
        except (ValueError, TypeError) as e:
            logger.error("NPV calculation failed: %s", e)
            return ToolResult(success=False, error=f"Invalid input for NPV calculation: {e}")

    def _calculate_roi(self, **kwargs) -> ToolResult:
        try:
            initial_investment = float(kwargs.get("initial_investment", 0))
            final_value = float(kwargs.get("final_value", 0))

            if initial_investment == 0:
                return ToolResult(success=False, error="initial_investment cannot be zero.")

            roi = (final_value - initial_investment) / initial_investment * 100

            logger.info("Calculated ROI: %.2f%%", roi)
            return ToolResult(
                success=True,
                data={
                    "metric": "ROI",
                    "value": round(roi, 2),
                    "unit": "percent",
                    "initial_investment": initial_investment,
                    "final_value": final_value,
                },
            )
        except (ValueError, TypeError) as e:
            logger.error("ROI calculation failed: %s", e)
            return ToolResult(success=False, error=f"Invalid input for ROI calculation: {e}")