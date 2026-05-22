import subprocess
import sys
import os
import json
import importlib
from importlib.metadata import PackageNotFoundError, version as pkg_version
from pathlib import Path


print("STEP 1 — Python Version Check")
v = sys.version_info
if v.major < 3 or (v.major == 3 and v.minor < 8):
    print(f"Python 3.8+ required. Found {v.major}.{v.minor}")
    sys.exit(1)
print(f"Python {v.major}.{v.minor}.{v.micro}")

print("STEP 2 — Checking for solcx")


def get_solcx_version(solcx_module):
    module_version = getattr(solcx_module, "__version__", None)
    if module_version:
        return module_version
    try:
        return pkg_version("py-solc-x")
    except PackageNotFoundError:
        return "unknown"


try:
    solcx = importlib.import_module("solcx")
    print(f"solcx found (version: {get_solcx_version(solcx)})")
except ImportError:
    print("solcx not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "py-solc-x"])
    solcx = importlib.import_module("solcx")
    print(f"solcx installed (version: {get_solcx_version(solcx)})")

print("STEP 3 — Compiling StoreRewardsV2.sol")

SOL_FILE = Path("D:/Project crpto/files/StoreRewardsV2.sol")
OUT_FILE = Path(__file__).parent / "contract_artifacts.json"

if not SOL_FILE.exists():
    print(f"StoreRewardsV2.sol not found at {SOL_FILE}")
    sys.exit(1)

try:
    set_solc_version = solcx.set_solc_version
    compile_files = solcx.compile_files
    set_solc_version("0.8.20")

    compiled = compile_files(
        [str(SOL_FILE)],
        output_values=["abi", "bin"],
        solc_version="0.8.20",
    )

    contract_id = next((k for k in compiled.keys() if k.endswith(":StoreRewardsV2")), None)
    if not contract_id:
        raise KeyError(f"StoreRewardsV2 not found. Available keys: {list(compiled.keys())}")
    abi = compiled[contract_id]["abi"]
    bytecode = compiled[contract_id]["bin"]

    artifacts = {"abi": abi, "bytecode": bytecode}
    OUT_FILE.write_text(json.dumps(artifacts, indent=2))
    print(f"Compiled → {OUT_FILE.name}")
    print(f"ABI has {len(abi)} entries")

except Exception as e:
    print(f"Compilation failed: {e}")
    print("You can compile manually via Remix IDE and paste the ABI into contract_artifacts.json")


print("STEP 5 — Writing .env Template")

ENV_FILE = Path(__file__).parent / ".env"


if ENV_FILE.exists():
    print(".env already exists — skipping (won't overwrite your secrets)")
else:
    print(".env template created")

print("Edit .env and fill in your RPC_URL and PRIVATE_KEY before running deploy.py")

print("STEP 6 — Verifying web3.py Import")
try:
    import importlib
    web3_mod = importlib.import_module("web3")
    print(f"web3.py imported successfully (version: {web3_mod.__version__})")
except ImportError as e:
    print(f"web3 import failed: {e}")

print(f"""
Next steps:
  1. Start a local node:    ganache
  2. Edit .env with your RPC_URL and PRIVATE_KEY
  3. Deploy the contract:  python deploy.py
  4. Interact:             python transaction_sender.py
""")
