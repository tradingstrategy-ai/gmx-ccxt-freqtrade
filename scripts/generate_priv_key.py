"""
Generate a new Ethereum wallet with private key and output in JSON format.
Uses web3.py to create a cryptographically secure private key.

Usage: python generate_wallet.py <output_file>
Example: python generate_wallet.py configs/hyperliquid/new_wallet.secrets.json
"""

import json
import sys
from pathlib import Path

from web3 import Web3


def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_wallet.py <output_file>", file=sys.stderr)
        print("Example: python generate_wallet.py configs/hyperliquid/wallet.secrets.json", file=sys.stderr)
        sys.exit(1)

    output_file = sys.argv[1]

    w3 = Web3()
    account = w3.eth.account.create()

    config = {
        "exchange": {
            "walletAddress": account.address,
            "privateKey": f"0x{account.key.hex()}",
        }
    }

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(json.dumps(config, indent=4).encode("utf-8"))

    print(f"Generated new wallet and saved to: {output_file}", file=sys.stderr)
    print(f"Wallet Address: {account.address}", file=sys.stderr)
    print("IMPORTANT: Keep this private key secure and never share it!", file=sys.stderr)


if __name__ == "__main__":
    main()