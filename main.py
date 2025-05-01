import json
import datetime

from core.inferencer import Inferencer

import llm_tools.math
import llm_tools.eth

try:
    print("Initializing Inferencer...")
    tools = []
    tools.extend(llm_tools.math.math_tools)
    tools.extend(llm_tools.eth.eth_tools)

    inferencer = Inferencer(
        model_config={"model_name": "Qwen/Qwen3-1.7B"}, tools=tools, thinking=True
    )
    print("Inferencer initialized.")

    messages = [
        {
            "role": "system",
            "content": f"You are a helpful assistant with access to tools. Use the available tools when needed. Respond concisely. Current date and time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    ]

    print("\n--- Start Conversation (type 'exit' to quit) ---")

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            print("Exiting conversation.")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response_messages = inferencer.infer(messages)

            messages = response_messages

            print("\n--- Full Conversation History After Turn ---")
            print(json.dumps(messages, indent=2, ensure_ascii=False))
            print("\n--- Model Response ---")
            print(messages[-1]["content"].replace("<|im_end|>", " "))
            print("-" * 20) 

        except Exception as e:
            print(f"\nAn error occurred during inference: {e}")
            if messages and messages[-1]["role"] == "user":
                messages.pop()

except Exception as e:
    print(f"\nAn error occurred during initialization: {e}")
    import traceback

    traceback.print_exc()
