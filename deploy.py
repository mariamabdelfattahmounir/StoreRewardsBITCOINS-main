import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

try:
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies. Run: pip install web3 python-dotenv")
    sys.exit(1)

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):    print(f"  {GREEN}{RESET}  {msg}")
def warn(msg):  print(f"  {YELLOW}{RESET}  {msg}")
def err(msg):   print(f"  {RED}{RESET}  {msg}"); sys.exit(1)
def info(msg):  print(f"  {CYAN}{RESET}  {msg}")
def title(msg): print(f"\n{BOLD}{CYAN}{msg}{RESET}")

parser = argparse.ArgumentParser(description="Deploy StoreRewardsV2")
parser.add_argument("--rpc",     help="Override RPC URL from .env")
parser.add_argument("--network", help="Named network (for display only)")
args = parser.parse_args()

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

RPC_URL     = args.rpc or os.getenv("RPC_URL", "HTTP://127.0.0.1:7545")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0xa13288972aa5294b4fcf174238db97490f4fcc308a3418f398f890e65f05e084")

print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════╗
║  StoreRewardsV2 — Deployment Script      ║
║  Blockchain Reward System                ║
╚══════════════════════════════════════════╝{RESET}
""")

title("STEP 1 — Loading Configuration")

if not PRIVATE_KEY or PRIVATE_KEY == "0xYOUR_PRIVATE_KEY_HERE":
    err("PRIVATE_KEY not set in .env — cannot sign transactions")

info(f"Network RPC : {RPC_URL}")
info(f"Network     : {args.network or 'custom'}")


title("STEP 2 — Connecting to Node")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    err(f"Cannot connect to {RPC_URL}. Is your node running?")

CHAIN_ID = w3.eth.chain_id

ok(f"Connected   : {RPC_URL}")
ok(f"Block number: #{w3.eth.block_number}")
ok(f"Chain ID    : {CHAIN_ID}")

account = w3.eth.account.from_key(PRIVATE_KEY)
DEPLOYER = account.address
balance  = w3.eth.get_balance(DEPLOYER)
balance_eth = w3.from_wei(balance, "ether")

ok(f"Deployer    : {DEPLOYER}")
ok(f"Balance     : {balance_eth:.4f} ETH")

if balance_eth < 0.01:
    warn("Low balance — deployment may fail.")

title("STEP 3 — Loading Contract Artifacts")

ARTIFACTS_FILE = BASE_DIR / "contract_artifacts.json"
SOL_FILE       = BASE_DIR / "StoreRewardsV2.sol"

if ARTIFACTS_FILE.exists():
    info("Found pre-compiled artifacts → loading …")
    artifacts = json.loads(ARTIFACTS_FILE.read_text())
    ABI      = artifacts["abi"]
    BYTECODE = artifacts["bytecode"]
    ok(f"ABI loaded ({len(ABI)} entries), bytecode ready")
else:
    info("No artifacts found — compiling StoreRewardsV2.sol …")
    try:
        from solcx import compile_files, set_solc_version, install_solc
        install_solc("0.8.20", show_progress=False)
        set_solc_version("0.8.20")
        compiled = compile_files(
            [str(SOL_FILE)],
            output_values=["abi", "bin"],
            solc_version="0.8.20",
        )
        key = list(compiled.keys())[0]
        ABI      = compiled[key]["abi"]
        BYTECODE = compiled[key]["bin"]
        ARTIFACTS_FILE.write_text(json.dumps({"abi": ABI, "bytecode": BYTECODE}, indent=2))
        ok("Compiled and cached to contract_artifacts.json")
    except Exception as e:
        err(f"Compilation failed: {e}")


title("STEP 4 — Deploying Contract")

Contract = w3.eth.contract(abi=ABI, bytecode=BYTECODE)

try:
    gas_estimate = Contract.constructor().estimate_gas({"from": DEPLOYER})
    gas_limit    = int(gas_estimate * 1.2)
    info(f"Gas estimate: {gas_estimate:,}  (using {gas_limit:,} with 20% buffer)")
except Exception as e:
    gas_limit = 5_000_000
    warn(f"Gas estimation failed — using fallback: {gas_limit:,}")

gas_price = w3.eth.gas_price
info(f"Gas price   : {w3.from_wei(gas_price, 'gwei'):.2f} gwei")

nonce = w3.eth.get_transaction_count(DEPLOYER)
deploy_tx = Contract.constructor().build_transaction({
    "from":     DEPLOYER,
    "nonce":    nonce,
    "gas":      gas_limit,
    "gasPrice": gas_price,
    "chainId":  CHAIN_ID,
})

info("Signing transaction …")
signed_tx = w3.eth.account.sign_transaction(deploy_tx, PRIVATE_KEY)

info("Broadcasting transaction …")
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
ok(f"TX Hash     : {tx_hash.hex()}")

info("Waiting for confirmation …")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

if receipt.status != 1:
    err(f"Transaction FAILED. Hash: {tx_hash.hex()}")

CONTRACT_ADDRESS = receipt.contractAddress
ok(f"Contract Address: {CONTRACT_ADDRESS}")
ok(f"Block: #{receipt.blockNumber}")
ok(f"Gas used: {receipt.gasUsed:,}")

title("STEP 5 — Saving Deployment Info")

deploy_info = {
    "contractAddress": CONTRACT_ADDRESS,
    "deployerAddress": DEPLOYER,
    "transactionHash": tx_hash.hex(),
    "blockNumber":     receipt.blockNumber,
    "gasUsed":         receipt.gasUsed,
    "network":         args.network or "custom",
    "rpcUrl":          RPC_URL,
    "chainId":         CHAIN_ID,
    "timestamp":       datetime.now().isoformat(),
}

DEPLOY_FILE = BASE_DIR / "deployment.json"
DEPLOY_FILE.write_text(json.dumps(deploy_info, indent=2))
ok("Saved to deployment.json")

title("STEP 5b — Seeding Fake Reward Items")

SAMPLE_ITEMS = [
    ("Coffee Mug",    w3.to_wei(50,  "ether"), 10),
    ("Gift Card $10", w3.to_wei(100, "ether"),  5),
    ("Tote Bag",      w3.to_wei(75,  "ether"), 20),
]

seeded_contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

for item_name, item_cost, item_qty in SAMPLE_ITEMS:
    try:
        nonce   = w3.eth.get_transaction_count(DEPLOYER)
        gas_est = seeded_contract.functions.addRewardItem(
                      item_name, item_cost, item_qty
                  ).estimate_gas({"from": DEPLOYER})
        seed_tx = seeded_contract.functions.addRewardItem(
                      item_name, item_cost, item_qty
                  ).build_transaction({
                      "from":     DEPLOYER,
                      "nonce":    nonce,
                      "gas":      int(gas_est * 1.2),
                      "gasPrice": w3.eth.gas_price,
                      "chainId":  CHAIN_ID,
                  })
        signed_seed = w3.eth.account.sign_transaction(seed_tx, PRIVATE_KEY)
        tx_hash_s   = w3.eth.send_raw_transaction(signed_seed.raw_transaction)
        receipt_s   = w3.eth.wait_for_transaction_receipt(tx_hash_s, timeout=60)
        if receipt_s.status == 1:
            ok(f"Added item: '{item_name}'  |  cost={w3.from_wei(item_cost,'ether'):.0f} RPC  |  qty={item_qty}")
        else:
            warn(f"Item '{item_name}' tx reverted")
    except Exception as e:
        warn(f"Could not seed '{item_name}': {e}")

total_items = seeded_contract.functions.getTotalRewardItems().call()
ok(f"Total reward items on-chain: {total_items}")

# Update .env
env_path = BASE_DIR / ".env"
if env_path.exists():
    content = env_path.read_text()
    if "CONTRACT_ADDRESS=" in content:
        lines = content.splitlines()
        updated = [f"CONTRACT_ADDRESS={CONTRACT_ADDRESS}" if l.startswith("CONTRACT_ADDRESS=") else l for l in lines]
        env_path.write_text("\n".join(updated) + "\n")
        ok(".env updated with CONTRACT_ADDRESS")

title("STEP 6 — Smoke Test")

deployed = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

try:
    ok(f"Coin Name   : {deployed.functions.coinName().call()}")
    ok(f"Symbol      : {deployed.functions.coinSymbol().call()}")
    ok(f"Admin       : {deployed.functions.getAdmin().call()}")
    ok(f"Paused      : {deployed.functions.getContractPaused().call()}")
    ok(f"Reward Items: {deployed.functions.getTotalRewardItems().call()}")
except Exception as e:
    warn(f"Smoke test error: {e}")

print(f"""
{BOLD}{GREEN}══════════════════════════════════════════════════════{RESET}
{BOLD}{GREEN}    DEPLOYMENT SUCCESSFUL{RESET}
{BOLD}{GREEN}══════════════════════════════════════════════════════{RESET}

  Contract : {BOLD}{CONTRACT_ADDRESS}{RESET}
  TX Hash  : {tx_hash.hex()}
  Block    : #{receipt.blockNumber}

Next step:
  python transaction_sender.py
""")