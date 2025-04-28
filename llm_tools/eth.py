import os
import requests

ETHERSCAN_API_URL = "https://api.etherscan.io/api"
API_KEY = os.getenv("API_KEY")

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
]
