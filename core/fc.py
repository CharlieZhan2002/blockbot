def get_tool_response(
    tools: list[dict],
    tool_name: str,
    arguments
) -> str:
    """
    Simulate the execution of a tool.
    Args:
        tools (list): List of available tools.
        tool_name (str): Name of the tool to simulate.
        arguments (dict): Arguments for the tool.
    Returns:
        str: Result of the tool execution.
    """

    print(f"Simulating tool: {tool_name}, args: {arguments}")

    for tool in tools:
        if tool["name"] == tool_name:
            func = tool["function"]
            try:
                result = func(**arguments)
                return result
            except Exception as e:
                return f"Error executing tool {tool_name}: {str(e)}"
