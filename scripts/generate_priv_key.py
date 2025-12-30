"""
Generate a new Ethereum wallet with private key and output in JSON format.
Uses web3.py to create a cryptographically secure private key.

This script only generates a wallet - use generate_config.py to create full config files.

Usage: python generate_priv_key.py <output_file>
Example: python generate_priv_key.py configs/hyperliquid/wallet.secrets.json
"""

import json
import sys
from pathlib import Path

from web3 import Web3


def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_priv_key.py <output_file>", file=sys.stderr)
        print("Example: python generate_priv_key.py configs/hyperliquid/wallet.secrets.json", file=sys.stderr)
        sys.exit(1)

    output_file = sys.argv[1]
    output_path = Path(output_file)
    
    # Check if file already exists
    if output_path.exists():
        print(f"Error: File already exists: {output_path}", file=sys.stderr)
        print("  Delete the existing file or choose a different filename.", file=sys.stderr)
        sys.exit(1)

    # Generate new wallet
    w3 = Web3()
    account = w3.eth.account.create()
    private_key = f"0x{account.key.hex()}"

    # Create output in FreqTrade secrets format
    config = {
        "exchange": {
            "ccxt_config": {
                "rpcUrl": "https://arb1.arbitrum.io/rpc",
                "privateKey": private_key
            }
        },
        "api_server": {
            "jwt_secret_key": "x",
            "username": "x",
            "password": "x"
        },
        "telegram": {
            "token": "x",
            "chat_id": "x"
        }
    }

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the file
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=4)

    print(f"Generated new wallet and saved to: {output_file}", file=sys.stderr)
    print(f"Wallet Address: {account.address}", file=sys.stderr)
    print(f"Private Key: {private_key[:10]}...{private_key[-10:]}", file=sys.stderr)
    print("", file=sys.stderr)
    print("IMPORTANT: Keep this private key secure and never share it!", file=sys.stderr)
    print("", file=sys.stderr)
    print("Note: This creates a minimal secrets file. For full config generation, use:", file=sys.stderr)
    print("  python scripts/generate_config.py <config_name>", file=sys.stderr)


if __name__ == "__main__":
    main()

