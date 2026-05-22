from web3 import Web3
import json, os
from dotenv import load_dotenv
from collections import Counter

load_dotenv()
w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))

with open("contract_artifacts.json") as f:
    abi = json.load(f)["abi"]

contract = w3.eth.contract(
    address=Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS")),
    abi=abi
)

latest = w3.eth.block_number
tx_counter = Counter()

for b in range(latest - 50, latest + 1):  # 🔥 faster
    block = w3.eth.get_block(b, full_transactions=True)
    for tx in block.transactions:
        if tx.to and tx.to.lower() == os.getenv("CONTRACT_ADDRESS").lower():
            tx_counter[tx["from"]] += 1

print("\n📊 Top Active Users:")
print("====================================")

for addr, cnt in tx_counter.most_common(5):
    try:
        name = contract.functions.getUserName(addr).call()
        display_name = name if name else "Unknown"
    except:
        display_name = "Unknown"

    print(f"{display_name:<10} | {addr} | {cnt} tx")