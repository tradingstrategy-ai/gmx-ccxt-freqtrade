"""
Generate a new FreqTrade config and secrets file with a new Ethereum wallet.
Creates both configs/<name>.json and configs/<name>.secrets.json files.

Usage: python generate_config.py <config_name>
Example: python generate_config.py ichiv2_gmx
Example: python generate_config.py my_new_strategy
"""

import copy
import json
import secrets
import string
import sys
from pathlib import Path

from web3 import Web3


def generate_random_string(length=16):
    """Generate a random string for API server credentials."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def load_template_config():
    """Load the template config file."""
    script_dir = Path(__file__).parent
    template_path = script_dir.parent / "configs" / "sample_config.json"
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template config not found: {template_path}")
    
    with open(template_path, 'r') as f:
        return json.load(f)


def load_template_secrets():
    """Load the template secrets file structure."""
    # Return the template structure directly (matches secrets.empty.json format)
    # This avoids JSON comment parsing issues
    return {
        "exchange": {
            "ccxt_config": {
                "rpcUrl": "https://arb1.arbitrum.io/rpc",
                "privateKey": "0x8888888888888888888888888888888888888888888888888888888888888888"
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


def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_config.py <config_name>", file=sys.stderr)
        print("Example: python generate_config.py ichiv2_gmx", file=sys.stderr)
        print("Example: python generate_config.py my_new_strategy", file=sys.stderr)
        sys.exit(1)

    config_name = sys.argv[1]
    
    # Validate config name (basic validation)
    if not config_name or '/' in config_name or '\\' in config_name:
        print("Error: Invalid config name. Use alphanumeric characters and underscores only.", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).parent
    configs_dir = script_dir.parent / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if files already exist
    config_file = configs_dir / f"{config_name}.json"
    secrets_file = configs_dir / f"{config_name}.secrets.json"
    
    if config_file.exists() or secrets_file.exists():
        print("Error: Config files already exist:", file=sys.stderr)
        if config_file.exists():
            print(f"  - {config_file}", file=sys.stderr)
        if secrets_file.exists():
            print(f"  - {secrets_file}", file=sys.stderr)
        print("  Delete existing files or choose a different config name.", file=sys.stderr)
        sys.exit(1)

    # Generate new wallet
    w3 = Web3()
    account = w3.eth.account.create()
    private_key = f"0x{account.key.hex()}"

    print(f"Generated new wallet:", file=sys.stderr)
    print(f"  Address: {account.address}", file=sys.stderr)
    print(f"  Private Key: {private_key[:10]}...{private_key[-10:]}", file=sys.stderr)
    print("", file=sys.stderr)

    # Load templates
    try:
        config_template = load_template_config()
        secrets_template = load_template_secrets()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Update config file
    config_data = copy.deepcopy(config_template)
    # Update bot_name to match config name
    config_data["bot_name"] = config_name.replace("_", "-")
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=4)
    print(f"✓ Created config file: {config_file}", file=sys.stderr)

    # Update secrets file
    secrets_data = copy.deepcopy(secrets_template)
    # Update private key
    secrets_data["exchange"]["ccxt_config"]["privateKey"] = private_key
    # Generate random credentials for API server
    secrets_data["api_server"]["jwt_secret_key"] = generate_random_string(32)
    secrets_data["api_server"]["username"] = generate_random_string(12)
    secrets_data["api_server"]["password"] = generate_random_string(16)
    
    with open(secrets_file, 'w') as f:
        json.dump(secrets_data, f, indent=4)
    print(f"✓ Created secrets file: {secrets_file}", file=sys.stderr)

    print("", file=sys.stderr)
    print("IMPORTANT:", file=sys.stderr)
    print("  - Keep the private key secure and never share it!", file=sys.stderr)
    print("  - The secrets file contains sensitive information", file=sys.stderr)
    print("  - Make sure secrets files are in .gitignore", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"Next steps:", file=sys.stderr)
    print(f"  1. Review and customize {config_file}", file=sys.stderr)
    print(f"  2. Update RPC URL and other settings in {secrets_file}", file=sys.stderr)
    print(f"  3. Add Telegram credentials if needed", file=sys.stderr)
    print(f"  4. Fund your wallet: {account.address}", file=sys.stderr)


if __name__ == "__main__":
    main()