import json
import os
import sys
import argparse
from pathlib import Path

try:
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies. Run: python setup.py")
    sys.exit(1)

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def ok(msg):    print(f"  {GREEN}{msg}{RESET}")
def warn(msg):  print(f"  {YELLOW}{msg}{RESET}")
def err(msg):   print(f"  {RED}{msg}{RESET}")
def info(msg):  print(f"  {CYAN}{msg}{RESET}")
def sep():      print(f"  {DIM}{'─'*52}{RESET}")

parser = argparse.ArgumentParser(description="Interact with StoreRewardsV2")
parser.add_argument("--address", help="Override contract address")
parser.add_argument("--rpc",     help="Override RPC URL")
parser.add_argument("--key",     help="Override private key")
args = parser.parse_args()


BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

RPC_URL          = args.rpc     or os.getenv("RPC_URL", "HTTP://127.0.0.1:7545")
PRIVATE_KEY      = args.key     or os.getenv("PRIVATE_KEY", "0xa13288972aa5294b4fcf174238db97490f4fcc308a3418f398f890e65f05e084")
CONTRACT_ADDRESS = args.address or os.getenv("CONTRACT_ADDRESS", "0x057b5642307Edb5fF24408594c80814137DDad07")

if not CONTRACT_ADDRESS:
    deploy_file = BASE_DIR / "deployment.json"
    if deploy_file.exists():
        d = json.loads(deploy_file.read_text())
        CONTRACT_ADDRESS = d.get("contractAddress", "0x057b5642307Edb5fF24408594c80814137DDad07")


w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    print(f"{RED}Cannot connect to {RPC_URL}{RESET}")
    sys.exit(1)

CHAIN_ID = w3.eth.chain_id

account = w3.eth.account.from_key(PRIVATE_KEY) if PRIVATE_KEY and PRIVATE_KEY != "0xYOUR_PRIVATE_KEY_HERE" else None
SENDER = account.address if account else None

artifacts_file = BASE_DIR / "contract_artifacts.json"
if not artifacts_file.exists():
    print(f"{RED}contract_artifacts.json not found. Run setup.py then deploy.py first.{RESET}")
    sys.exit(1)

ABI = json.loads(artifacts_file.read_text())["abi"]

if not CONTRACT_ADDRESS:
    print(f"{RED}CONTRACT_ADDRESS not set. Run deploy.py first.{RESET}")
    sys.exit(1)

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=ABI
)
admin = contract.functions.getAdmin().call()
is_admin = (SENDER and SENDER.lower() == admin.lower())

def send_tx(func_call, description=""):
    if not account:
        err("PRIVATE_KEY not configured — cannot send transactions")
        return None
    try:
        nonce   = w3.eth.get_transaction_count(SENDER)
        gas_est = func_call.estimate_gas({"from": SENDER})
        latest = w3.eth.get_block("latest")
        base_fee = latest["baseFeePerGas"]
        tx = func_call.build_transaction({
            "from":                 SENDER,
            "nonce":                nonce,
            "gas":                  int(gas_est * 1.2),
            "maxFeePerGas":         base_fee * 2,
            "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
            "chainId":              CHAIN_ID,
        })
        signed  = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        info(f"TX sent: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        if receipt.status == 1:
            ok(f"{description or 'Transaction'} confirmed (block #{receipt.blockNumber}, gas: {receipt.gasUsed:,})")
        else:
            err(f"Transaction REVERTED — hash: {tx_hash.hex()}")
        return  tx_hash
    except Exception as e:
        err(f"Transaction failed: {e}")
        return None

def prompt(msg, default=None):
    suffix = f" [{default}]" if default is not None else ""
    try:
        val = input(f"    {CYAN}{msg}{suffix}: {RESET}").strip()
        return val if val else str(default)
    except (KeyboardInterrupt, EOFError):
        print()
        return None

def show_status():
    sep()
    print(f"  {BOLD}CONTRACT STATUS{RESET}")
    sep()
    try:
        info(f"Address     : {CONTRACT_ADDRESS}")
        info(f"Coin Name   : {contract.functions.coinName().call()}")
        info(f"Symbol      : {contract.functions.coinSymbol().call()}")
        info(f"Admin       : {contract.functions.getAdmin().call()}")
        info(f"Paused      : {contract.functions.getContractPaused().call()}")
        info(f"Total Supply: {w3.from_wei(contract.functions.getTotalMintedCoins().call(), 'ether'):.4f} RPC")
        info(f"Total Items : {contract.functions.getTotalRewardItems().call()}")
        info(f"Total TXs   : {contract.functions.getTotalTransactions().call()}")
        info(f"Block #     : {w3.eth.block_number}")
        if SENDER:
            bal = contract.functions.getCoinBalance(SENDER).call()
            info(f"Your Balance: {w3.from_wei(bal, 'ether'):.4f} RPC")
    except Exception as e:
        err(f"Failed to read contract: {e}")

def check_balance():
    addr = prompt("Address to check (leave blank for your address)", SENDER)
    if not addr:
        return

    try:
        addr = Web3.to_checksum_address(addr)

        # RPC Balance
        rpc_balance = contract.functions.getCoinBalance(addr).call()
        rpc_balance_eth = w3.from_wei(rpc_balance, "ether")

        # ETH Balance 🔥
        eth_balance = w3.eth.get_balance(addr)
        eth_balance_eth = w3.from_wei(eth_balance, "ether")

        # Name
        name = contract.functions.getUserName(addr).call()

        sep()
        ok(f"Address : {addr}")
        ok(f"Name    : {name or '(not registered)'}")

        print("\n💰 Balances:")
        print("====================================")
        ok(f"RPC : {rpc_balance_eth:.4f}")
        ok(f"ETH : {eth_balance_eth:.4f}")

    except Exception as e:
        err(str(e))

def mint_coins():
    to_addr = prompt("Recipient address")
    amount  = prompt("Amount of RPC tokens to mint (e.g. 100)")
    if not to_addr or not amount:
        return
    try:
        to_addr    = Web3.to_checksum_address(to_addr)
        amount_wei = w3.to_wei(float(amount), "ether")
        send_tx(contract.functions.mintCoins(to_addr, amount_wei), f"Mint {amount} RPC to {to_addr}")
    except Exception as e:
        err(str(e))

def transfer_coins():
    to_addr = prompt("Recipient address")
    amount  = prompt("Amount of RPC tokens to transfer")
    if not to_addr or not amount:
        return
    try:
        to_addr    = Web3.to_checksum_address(to_addr)
        amount_wei = w3.to_wei(float(amount), "ether")
        send_tx(contract.functions.transferCoins(to_addr, amount_wei), f"Transfer {amount} RPC to {to_addr}")
    except Exception as e:
        err(str(e))

def approve_spender():
    spender = prompt("Spender address")
    amount  = prompt("Amount to approve")
    if not spender or not amount:
        return
    try:
        spender    = Web3.to_checksum_address(spender)
        amount_wei = w3.to_wei(float(amount), "ether")
        send_tx(contract.functions.approveCoinSpender(spender, amount_wei), "Approve spender")
    except Exception as e:
        err(str(e))

def register_user():
    name = prompt("Your name to register")
    if not name:
        return
    send_tx(contract.functions.registerUser(name), f"Register user '{name}'")

def add_reward_item():
    name     = prompt("Item name")
    cost     = prompt("Points cost (in RPC tokens, e.g. 50)")
    qty      = prompt("Quantity available")
    if not all([name, cost, qty]):
        return
    try:
        cost_wei = w3.to_wei(float(cost), "ether")
        send_tx(
            contract.functions.addRewardItem(name, cost_wei, int(qty)),
            f"Add item '{name}'"
        )
    except Exception as e:
        err(str(e))

def list_reward_items():
    total = contract.functions.getTotalRewardItems().call()
    sep()
    print(f"  {BOLD}REWARD ITEMS ({total} total){RESET}")
    sep()
    if total == 0:
        warn("No reward items added yet.")
        return
    for i in range(1, total + 1):
        try:
            item_id, name, cost, qty, active = contract.functions.getRewardItem(i).call()
            status = f"{GREEN}Active{RESET}" if active else f"{RED}Inactive{RESET}"
            print(f"  [{item_id}] {BOLD}{name}{RESET}  |  Cost: {w3.from_wei(cost,'ether'):.0f} RPC  |  Qty: {qty}  |  {status}")
        except Exception as e:
            warn(f"Item {i}: {e}")

def purchase_item():
    list_reward_items()
    item_id = prompt("Item ID to purchase")
    if not item_id:
        return
    try:
        send_tx(contract.functions.purchaseRewardItem(int(item_id)), f"Purchase item #{item_id}")
    except Exception as e:
        err(str(e))

def pause_contract():
    confirm = prompt("Pause the contract? (yes/no)", "no")
    if confirm.lower() == "yes":
        send_tx(contract.functions.pause(), "Pause contract")

def resume_contract():
    confirm = prompt("Resume the contract? (yes/no)", "no")
    if confirm.lower() == "yes":
        send_tx(contract.functions.resume(), "Resume contract")

def transfer_ownership():
    new_admin = prompt("New admin address")
    if not new_admin:
        return
    confirm = prompt(f"Transfer ownership to {new_admin}? (yes/no)", "no")
    if confirm.lower() == "yes":
        try:
            new_admin = Web3.to_checksum_address(new_admin)
            send_tx(contract.functions.transferOwnership(new_admin), "Transfer ownership")
        except Exception as e:
            err(str(e))
def show_activity_history():
    try:
        sep()
        print(f"{BOLD}📊 Activity History{RESET}")
        print("====================================")

        latest_block = w3.eth.block_number
        found = False  

        for block_num in range(0, latest_block + 1):
            block = w3.eth.get_block(block_num, full_transactions=True)

            for tx in block.transactions:
                if tx.to and tx.to.lower() == CONTRACT_ADDRESS.lower():
                    
                    found = True  

                    print(f"Block #{block_num}")
                    print(f"From : {tx['from']}")
                    if tx.input != "0x":
                        print("Action: Contract Interaction")
                    print(f"Tx   : {tx.hash.hex()}")
                    print("-" * 40)
        if not found:
            warn("No activity found yet.")

    except Exception as e:
        err(str(e))

def is_registered():
    try:
        name = contract.functions.getUserName(SENDER).call()
        return name != ""
    except:
        return False
def get_menu():
    menu = [
        ("Contract Status", show_status),
        ("Check Coin Balance", check_balance),
        ("─── USER ACTIONS ───", None),
    ]

    if not is_registered():
        menu.append(("Register User", register_user))

    menu += [
        ("Transfer Coins", transfer_coins),
        ("View Reward Items", list_reward_items),
        ("Purchase Reward Item", purchase_item),
        ("Activity History", show_activity_history),
    ]

    if is_admin:
        menu += [
            ("─── ADMIN ONLY ───", None),
            ("Mint Coins", mint_coins),
            ("Add Reward Item", add_reward_item),
            ("Pause Contract", pause_contract),
            ("Resume Contract", resume_contract),
            ("Transfer Ownership", transfer_ownership),
        ]

    return menu

def main():
    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════╗
║        🎁 Store Rewards System           ║
╚══════════════════════════════════════════╝{RESET}
  Network : {RPC_URL}
  Chain ID: {CHAIN_ID}
  Contract: {CONTRACT_ADDRESS or f'{RED}(NOT SET){RESET}'}
  Wallet  : {SENDER or f'{YELLOW}(READ-ONLY, no private key){RESET}'}
""")
    if SENDER:
        name = contract.functions.getUserName(SENDER).call()
        if name == "":
            print("⚠️ You must register first")
            register_user()
        else:
            print(f"👋 Welcome {name}")
    while True:
        print(f"\n{BOLD}── MENU ────────────────────────────────{RESET}")
        if is_registered():
            print(f"{GREEN}✔ Registered{RESET}", end="  |  ")
        print(f"{CYAN}{'👑 Admin Mode' if is_admin else '👤 User Mode'}{RESET}")
        print(f"{DIM}────────────────────────────────────────{RESET}")
        menu = get_menu()
        for i, (label, fn) in enumerate(menu):
            if fn is None:
                print(f"     {DIM}{label}{RESET}")
            else:
                print(f"    {CYAN}[{i+1:2d}]{RESET}  {label}")
        print(f"    {CYAN}[ 0]{RESET}  Exit")
        print()

        choice = prompt("Choose an option")
        if choice is None or choice == "0":
            print(f"\n{GREEN}Goodbye!{RESET}\n")
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(menu) and menu[idx][1] is not None:
                print()
                menu[idx][1]()
            else:
                warn("Invalid choice — try again")
        except ValueError:
            warn("Please enter a number")
        except KeyboardInterrupt:
            print(f"\n{GREEN}Goodbye!{RESET}\n")
            break

if __name__ == "__main__":
    main()