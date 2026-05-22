from web3 import Web3
import json, os
from dotenv import load_dotenv

load_dotenv()
w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))

with open("contract_artifacts.json") as f:
    abi = json.load(f)["abi"]

contract = w3.eth.contract(
    address=Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS")),
    abi=abi
)

admin = contract.functions.getAdmin().call()
user  = w3.eth.accounts[1]

print("Admin:", admin)
print("User :", user)

# 🔥 Test 1: Non-admin mint
try:
    contract.functions.mintCoins(user, w3.to_wei(1, "ether")).transact({"from": user})
    print("❌ FAIL: user minted coins!")
except:
    print("✅ PASS: user cannot mint")

# 🔥 Test 2: Pause protection
try:
    contract.functions.pause().transact({"from": admin})
    print("✅ Admin paused contract")

    try:
        contract.functions.purchaseRewardItem(1).transact({"from": user})
        print("❌ FAIL: purchase worked while paused")
    except:
        print("✅ PASS: purchase blocked while paused")

    contract.functions.resume().transact({"from": admin})
    print("✅ Admin resumed contract")

except Exception as e:
    print("❌ Error:", e)