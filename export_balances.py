from web3 import Web3
import json, os, csv
from dotenv import load_dotenv

load_dotenv()
w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))

with open("contract_artifacts.json") as f:
    abi = json.load(f)["abi"]

contract = w3.eth.contract(
    address=Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS")),
    abi=abi
)

with open("balances.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Address", "RPC Balance", "ETH Balance"])

    for acc in w3.eth.accounts:
        rpc = contract.functions.getCoinBalance(acc).call()
        eth = w3.eth.get_balance(acc)
        writer.writerow([acc, rpc, eth])

print("✅ balances.csv created")