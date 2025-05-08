import os
import json
import requests

ETHERSCAN_API_URL = "https://api.etherscan.io/api"
API_KEY = "W2GBRSZRC7V7P37W6EA289GH8ES1WFVMHX"

def get_eth_balance(address: str) -> float:
    """Get the ETH balance of an address"""
    params = {
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
        "apikey": API_KEY
    }
    response = requests.get(ETHERSCAN_API_URL, params=params).json()
    if response["status"] != "1":
        raise Exception(f"Error: {response['message']}")
    return int(response["result"]) / 1e18


def wei_to_eth(wei_value: str) -> float:
    """Convert Wei to ETH"""
    return int(wei_value) / 1e18

def eth_to_wei(eth_value: float) -> str:
    """Convert ETH to Wei"""
    return str(int(eth_value * 1e18))

def get_bytecode_from_etherscan(address: str) -> str:
    """Check if an address is a contract by getting its bytecode."""
    params = {
        "module": "proxy",
        "action": "eth_getCode",
        "address": address,
        "tag": "latest",
        "apikey": API_KEY
    }
    response = requests.get(ETHERSCAN_API_URL, params=params).json()
    if "result" not in response:
        raise Exception("Failed to retrieve bytecode.")
    return response["result"]  # '0x' means it's not a contract


def extract_source_code(source_code: str) -> str:
    """Extract and format the contract source code, supporting Remix JSON and ordinary contract strings"""
    source_code = source_code.strip()

    if not source_code:
        return "This address does not disclose the contract source code or has not been verified."

    # Remix multi-file JSON format (JSON wrapped in strings)
    if source_code.startswith("{") and source_code.endswith("}"):
        try:
            parsed = json.loads(source_code)
            if isinstance(parsed, dict) and "sources" in parsed:
                code_blocks = []
                for filename, fileinfo in parsed["sources"].items():
                    code = fileinfo.get("content", "")
                    code_blocks.append(f"// File: {filename}\n{code}")
                return "\n\n".join(code_blocks)
        except json.JSONDecodeError as e:
            return f"JSON parsing failed. Return the original source code:\n\n{source_code}"

    # 普通单文件 Solidity 合约
    return source_code

def analyze_contract_by_address(address: str) -> str:
    """Identify whether it is a contract address and return the source code"""

    try:
        # 1. 先判断该地址是否为合约（非 EOA）
        bytecode = get_bytecode_from_etherscan(address)
        if not bytecode or bytecode == "0x":
            return f"❌ 地址 {address} 不是合约地址。"

        # 2. 再尝试获取合约源码
        url = "https://api.etherscan.io/api"
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": API_KEY,
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if not isinstance(data, dict):
            return "❌ The API response format is incorrect."

        result = data.get("result")
        if (
            not result
            or not isinstance(result, list)
            or not isinstance(result[0], dict)
            or not result[0].get("SourceCode")
        ):
            return f"✅ Addresses {address} It is a contract address, but it has not been verified or there is no source code available."

        raw_code = result[0]["SourceCode"]
        source_code = extract_source_code(raw_code)

        return f"✅ Addresses {address} isc ontract address：\n\n{source_code[:3000]}..."  # 限制输出长度

    except Exception as e:
        return f"⚠️ Failed to obtain the contract source code:{str(e)}"


def get_latest_transactions(address: str, limit: int = 10):
    """Get the latest transactions of an address"""
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": API_KEY
    }
    response = requests.get(ETHERSCAN_API_URL, params=params).json()
    if response["status"] != "1":
        raise Exception(f"Error: {response['message']}")
    
    transactions = response["result"][:limit]
    for tx in transactions:
        tx['value'] = wei_to_eth(tx['value'])
    
    return transactions


def get_transaction_status(tx_hash: str) -> str:
    """Get the status of a transaction by its hash"""
    params = {
        "module": "transaction",
        "action": "gettxreceiptstatus",
        "txhash": tx_hash,
        "apikey": API_KEY
    }
    response = requests.get(ETHERSCAN_API_URL, params=params).json()
    if response["status"] != "1":
        raise Exception(f"Error: {response['message']}")
    return "Success" if response["result"]["status"] == "1" else "Fail"


def get_eth_gas_price() -> float:
    """Get the current ETH gas price (in Gwei)"""
    params = {
        "module": "gastracker",
        "action": "gasoracle",
        "apikey": API_KEY
    }
    response = requests.get(ETHERSCAN_API_URL, params=params).json()
    if response["status"] != "1":
        raise Exception(f"Error: {response['message']}")
    return float(response["result"]["ProposeGasPrice"])

# def search_online_blockchain_info(query: str) -> str:
#     """Use search engines or third-party apis to retrieve answers to blockchain questions"""
#     """Problems such as newly established blockchain companies or technologies（background knowledge）"""
#     from serpapi import GoogleSearch  # 或其他搜索 API
#     params = {
#         "q": query,
#         "api_key": "你的SerpAPI Key",  # 或者用 Bing/Web search API
#         "num": 1
#     }
#     search = GoogleSearch(params)
#     results = search.get_dict()
#     snippet = results.get("organic_results", [{}])[0].get("snippet", "未找到结果")
#     return snippet


eth_tools = [
    {
        "name": "get_eth_balance",
        "description": "Get the ETH balance of an address. This tool allows you to check the current ETH balance of a specified Ethereum address. The balance is returned in ETH.",
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Ethereum address to check the balance of.  Must be a valid Ethereum address.",
                }
            },
            "required": ["address"],
        },
        "function": get_eth_balance,
    },
    {
        "name": "wei_to_eth",
        "description": "Convert Wei to ETH. This tool converts a given amount in Wei to its equivalent in ETH.",
        "parameters": {
            "type": "object",
            "properties": {
                "wei_value": {
                    "type": "string",
                    "description": "Amount in Wei to convert. Must be a valid Wei value.",
                }
            },
            "required": ["wei_value"],
        },
    },
    {
        "name": "eth_to_wei",
        "description": "Convert ETH to Wei. This tool converts a given amount in ETH to its equivalent in Wei.",
        "parameters": {
            "type": "object",
            "properties": {
                "eth_value": {
                    "type": "number",
                    "description": "Amount in ETH to convert. Must be a valid ETH value.",
                }
            },
            "required": ["eth_value"],
        },
        "function": eth_to_wei,
    },
    {
          "name": "get_latest_transactions",
          "description": "Get the latest transactions of an address.  This tool retrieves a list of the most recent transactions associated with a given Ethereum address. You can specify the maximum number of transactions to return. Please carefully check the unit.",
          "parameters": {
                "type": "object",
                "properties": {
                     "address": {
                          "type": "string",
                          "description": "Ethereum address to check the transactions of. Must be a valid Ethereum address.",
                     },
                     "limit": {
                          "type": "integer",
                          "description": "Maximum number of transactions to return.  Defaults to 10 if not specified.",
                     }
                },
                "required": ["address"],
          },
          "function": get_latest_transactions,
     },
     {
          "name": "get_transaction_status",
          "description": "Get the status of a transaction. This tool checks the status of a specific Ethereum transaction based on its transaction hash. It returns whether the transaction was successful or failed.",
          "parameters": {
                "type": "object",
                "properties": {
                     "tx_hash": {
                          "type": "string",
                          "description": "Transaction hash to check the status of. Must be a valid Ethereum transaction hash.",
                     }
                },
                "required": ["tx_hash"],
          },
          "function": get_transaction_status,
     },
     {
          "name": "get_eth_gas_price",
          "description": "Get the current ETH gas price. This tool fetches the current recommended gas price for Ethereum transactions. The gas price is returned in Gwei.",
          "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
          },
          "function": get_eth_gas_price,
     },
     {
    "name": "analyze_contract_by_address",
    "description": (
        "Analyze whether a given Ethereum address is a smart contract address and retrieve its source code if verified. "
        "Use this tool when the user asks whether an address is a contract, whether it's a proxy contract, what functions it has, "
        "or if it is secure. If the address is not a contract, the tool will return a message indicating so. "
        "If it is a contract, it will return the Solidity source code."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "address": {
                "type": "string",
                "description": "The Ethereum address to analyze. Must be a valid Ethereum address.",
            }
        },
        "required": ["address"],
    },
    "function": analyze_contract_by_address,
}

]
