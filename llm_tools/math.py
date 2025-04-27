import numpy as np


def calculate(expression: str) -> float:
    """
    Calculate a mathematical expression.

    Args:
        expression (str): The mathematical expression to calculate.

    Returns:
        float: The result of the calculation.
    """
    try:
        # Evaluate the expression safely
        result = eval(expression, {"__builtins__": None}, {})
        return result
    except Exception as e:
        return f"Error in calculation: {str(e)}"


def average(numbers: list) -> float:
    """
    Calculate the average of a list of numbers.

    Args:
        numbers (list): A list of numbers to average.

    Returns:
        float: The average of the numbers.
    """
    try:
        return np.mean(numbers)
    except Exception as e:
        return f"Error in averaging: {str(e)}"


math_tools = [
    {
        "name": "calculate",
        "description": "Calculate a mathematical expression.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to calculate, e.g., '3*10.4+2'.",
                }
            },
            "required": ["expression"],
        },
        "function": calculate,
    },
    {
        "name": "average",
        "description": "Calculate the average of a list of numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "A list of numbers to average.",
                }
            },
            "required": ["numbers"],
        },
        "function": average,
    },
]
