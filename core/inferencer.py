import re
import json
import torch

from transformers import AutoModelForCausalLM, AutoTokenizer
from core.fc import get_tool_response

class Inferencer:
    def __init__(self, model_config=None, tools=None, thinking=False):
        """Initializes the model and tokenizer."""
        self.default_model_name = "Qwen/Qwen3-1.7B"
        self.model_config = model_config if model_config is not None else {}
        self.model_name = self.model_config.get("model_name", self.default_model_name)
        self.torch_dtype = self.model_config.get(
            "torch_dtype",
            torch.bfloat16 if torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8 else torch.float16
        )
        self.thinking = thinking
        self.tools = tools if tools is not None else []
        self._tools = []
        for tool in self.tools:
            tool_copy = tool.copy()
            if "function" in tool_copy:
                del tool_copy["function"]
            self._tools.append(tool_copy)

        print(f"Loading model: {self.model_name} with dtype: {self.torch_dtype}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=self.torch_dtype,
                device_map="auto",
                trust_remote_code=True
            )

            if self.tokenizer.pad_token_id is None:
                 self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
                 print(f"Warning: Tokenizer pad_token_id is None, setting to eos_token_id: {self.tokenizer.pad_token_id}")

        except Exception as e:
            print(f"Error loading model or tokenizer: {e}")
            raise

        print("Model and tokenizer loaded successfully.")
        if not hasattr(self.tokenizer, 'chat_template') or ('<tool_call>' not in str(self.tokenizer.chat_template) and self.tools):
             print(f"Warning: Tokenizer template might not fully support Qwen function calling structured output.")


    def infer(self, messages: list, generation_args: dict = None) -> list:
        """
        Generates model response, executes tools if needed, and continues generation
        until a final natural language response is produced. Returns the full history.
        """
        if not isinstance(messages, list):
             raise TypeError("Input 'messages' must be a list.")

        default_generation_args = {
            "max_new_tokens": 5000,
            "do_sample": True,
            "top_k": 20,
            "top_p": 0.8,
            "temperature": 0.7,
            "repetition_penalty": 1.0,
        }
        gen_args = default_generation_args.copy()
        if generation_args:
            gen_args.update(generation_args)

        if "eos_token_id" not in gen_args:
            gen_args["eos_token_id"] = self.tokenizer.eos_token_id
        if "pad_token_id" not in gen_args:
             gen_args["pad_token_id"] = self.tokenizer.pad_token_id

        current_messages = list(messages)

        while True:
            try:
                # drop callable key "function"

                input_ids = self.tokenizer.apply_chat_template(
                    current_messages,
                    chat_template=self.tokenizer.chat_template,
                    add_generation_prompt=True,
                    return_tensors='pt',
                    tools=self._tools,
                    enable_thinking=self.thinking,
                ).to(self.model.device)
            except Exception as e:
                print(f"Error applying chat template: {e}"); raise

            try:
                output_ids = self.model.generate(input_ids, **gen_args)
            except TypeError as e:
                 if "'tools'" in str(e) or "model_kwargs are not used: ['tools']" in str(e):
                     print(f"\nWarning: generate method does not accept 'tools'. Removing.")
                     temp_gen_args = gen_args.copy()
                     temp_gen_args.pop('tools', None)
                     try: output_ids = self.model.generate(input_ids, **temp_gen_args);
                     except Exception as inner_e: print(f"Error after removing 'tools': {inner_e}"); raise
                 else: print(f"Error during generation (TypeError): {e}"); raise
            except Exception as e:
                 print(f"Error during generation: {e}"); raise

            new_tokens = output_ids[0, input_ids.shape[1]:]
            response_text = self.tokenizer.decode(new_tokens, skip_special_tokens=False)

            assistant_response_message = {"role": "assistant", "content": response_text}
            current_messages.append(assistant_response_message)

            tool_call_pattern = r'<tool_call>(.*?)</tool_call>'
            match = re.search(tool_call_pattern, response_text, re.DOTALL)

            if match:
                tool_call_content = match.group(1).strip()
                print(f"[DEBUG] Tool call found.")
                try:
                    tool_call_data = json.loads(tool_call_content)
                    print(f"[DEBUG] Tool call data: {tool_call_data}")
                    tool_name = tool_call_data.get("name")
                    arguments = tool_call_data.get("arguments")

                    if tool_name and arguments is not None:
                        print(f"[DEBUG] Executing tool: {tool_name} with arguments: {arguments}")
                        tool_response_content = get_tool_response(self.tools, tool_name, arguments)
                        print(f"[DEBUG] Tool response: {tool_response_content}")
                        current_messages.append({
                            "role": "tool",
                            "content": tool_response_content,
                            "name": tool_name
                        })
                        print("[DEBUG] Tool executed. Asking model to continue answering.")

                        # 插入一条提示，引导模型继续
                        current_messages.append({
    "role": "user",
    "content": (
        f"The tool `{tool_name}` has responded with the following data:\n\n"
        f"{tool_response_content}\n\n"
        "Please summarize this result and continue your answer for the user."
    )
})
                    else:
                        print("Warning: Malformed tool call data (missing name/arguments). Ending turn.")
                        break

                except json.JSONDecodeError:
                    print("Warning: Could not decode tool call JSON. Ending turn.")
                    break
                except Exception as e:
                    print(f"Error during tool execution: {e}. Ending turn.")
                    break

            else:
                print("[DEBUG] No tool call found in response. Ending turn.")

                # 检查是否有工具调用历史
                tool_messages = [m for m in current_messages if m["role"] == "tool"]
                last_tool = tool_messages[-1] if tool_messages else None

                # 尝试提取 <think> 内容
                think_match = re.search(r"<think>(.*?)</think>", response_text, re.DOTALL)
                final_answer = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL).strip()

                # 构造 Header
                header = ""
                if last_tool:
                    # 查找对应的参数（根据 tool_name 匹配调用）
                    try:
                        tool_name = last_tool.get("name", "unknown")
                        for m in current_messages:
                            if m.get("role") == "assistant":
                                m_match = re.search(r'"name"\s*:\s*"{}"'.format(re.escape(tool_name)), m["content"])
                                if m_match:
                                    args_match = re.search(r'"arguments"\s*:\s*({.*?})', m["content"])
                                    if args_match:
                                        args_json = json.loads(args_match.group(1))
                                        args_str = json.dumps(args_json, ensure_ascii=False)
                                        break
                                    else:
                                        args_str = "{}"
                                else:
                                    args_str = "{}"
                    except Exception:
                        args_str = "{}"

                    header += f"[This answer used Function Call: {tool_name} Parameter: {args_str}]\n\n"

                if think_match:
                    header += "💡Model thinking：\n" + think_match.group(1).strip() + "\n\n"

                header += "🤖Model answer：\n" + final_answer

                # 替换最终 assistant 消息
                current_messages[-1] = {"role": "assistant", "content": header.strip()}
                break

        return current_messages