import os
import json
import requests
from datetime import datetime, timezone
import re

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
    """提取并格式化合约源码，支持 Remix JSON 和普通合约字符串"""
    source_code = source_code.strip()

    if not source_code:
        return "该地址未公开合约源码或未验证。"

    # Remix 多文件 JSON 格式（字符串包裹的 JSON）
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
            return f"JSON 解析失败，返回原始源码：\n\n{source_code}"

    # 普通单文件 Solidity 合约
    return source_code

def analyze_contract_by_address(address: str) -> str:
    """识别是否为合约地址，并返回源码"""

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
            return "❌ API 响应格式错误。"

        result = data.get("result")
        if (
            not result
            or not isinstance(result, list)
            or not isinstance(result[0], dict)
            or not result[0].get("SourceCode")
        ):
            return f"✅ 地址 {address} 是合约地址，但未验证或无源码可用。"

        raw_code = result[0]["SourceCode"]
        source_code = extract_source_code(raw_code)

        return f"✅ 地址 {address} 是合约地址：\n\n{source_code[:3000]}..."  # 限制输出长度

    except Exception as e:
        return f"⚠️ 获取合约源码失败：{str(e)}"


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

def clean_user_input(text: str) -> str:
    """清理无意义词，如 '代币'、'币' 等，但保留英文主体"""
    return re.sub(r"(币|coin|代币|加密货币)", "", text, flags=re.IGNORECASE).strip()

def search_coin_id(query: str) -> str:
    """调用 CoinGecko /search 接口获取 coin_id"""
    try:
        response = requests.get("https://api.coingecko.com/api/v3/search", params={"query": query}, timeout=10)
        coins = response.json().get("coins", [])
        if coins:
            return coins[0]["id"]
    except Exception:
        pass
    return None

def get_crypto_price_and_history(user_input: str, vs_currency: str = "usd") -> dict:
    try:
        # 1. 用户输入清理
        cleaned = clean_user_input(user_input)

        # 2. 查找 Coin ID
        coin_id = search_coin_id(cleaned)
        if not coin_id:
            return {"error": f"❌ 未找到币种：{user_input}"}

        # 3. 查询价格
        price_resp = requests.get("https://api.coingecko.com/api/v3/simple/price", params={
            "ids": coin_id,
            "vs_currencies": vs_currency
        }, timeout=10).json()
        current_price = price_resp.get(coin_id, {}).get(vs_currency)

        # 4. 查询历史价格
        hist_resp = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart", params={
            "vs_currency": vs_currency,
            "days": 7,
        }, timeout=10).json()

        history = [
            {"time": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat(), "price": round(p, 6)}
            for ts, p in hist_resp.get("prices", [])
        ]

        return {
            "cleaned_input": cleaned,
            "coin_id": coin_id,
            "vs_currency": vs_currency,
            "current_price": current_price,
            "history": history,
            "has_history": bool(history)
        }

    except Exception as e:
        return {"error": f"请求失败：{str(e)}"}


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
},
    {
    "name": "get_crypto_price_and_history",
    "description": (
        "本工具能获取加密货币的当前价格和过去7天的价格趋势（基于 CoinGecko）。"
        "查询某个加密货币的实时价格与历史趋势，支持中英文币种名模糊匹配（如 '比特币', 'btc', '狗狗币', 'trump coin', 'Official Pepe'），"
        "会自动匹配 CoinGecko 支持的加密货币 ID，并返回结构化数据供回答或绘图。"
        "使用场景：当用户询问某个加密货币的价格、趋势、是否上涨、是否值得投资等问题时，调用此函数。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "user_input": {
                "type": "string",
                "description": "用户输入的币种名或关键词（中英文或拼音，如 btc、eth、狗狗币、official pepe 等）"
            },
            "vs_currency": {
                "type": "string",
                "description": "用于计价的法币（如 usd、cny、eur 等），默认 usd",
                "default": "usd"
            }
        },
        "required": ["user_input"]
    },
    "function": get_crypto_price_and_history
}

]
