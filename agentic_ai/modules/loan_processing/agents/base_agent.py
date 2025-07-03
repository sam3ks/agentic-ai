import re
from agentic_ai.core.utils.formatting import format_indian_commas, format_indian_currency_without_decimal


class BaseAgent:
    """
    Base class for all loan processing agents. Provides common utilities for formatting and post-processing output.
    """

    def __init__(self, *args, **kwargs):
        pass  # Extend as needed for agent initialization

    def _format_agent_reasoning(self, text: str) -> str:
        # Replace all international formatted numbers with Indian comma style
        def replace_with_indian_commas(match):
            num = int(match.group(0).replace(",", ""))
            return format_indian_commas(num)

        text = re.sub(r"\d{1,3}(?:,\d{3})+|\d{7,}", replace_with_indian_commas, text)
        return text

    def postprocess_output(self, text: str) -> str:
        # Replace all international formatted numbers (with or without rupee symbol) with Indian comma style
        def replace_with_indian_currency(match):
            num = int(match.group(2).replace(",", ""))
            return format_indian_currency_without_decimal(num)

        # Replace patterns like ₹12,345,678 or 12,345,678
        text = re.sub(r"(₹?)(\d{1,3}(?:,\d{3}){2,}|\d{7,})(?!,\d{2},\d{3})", replace_with_indian_currency, text)
        return text

