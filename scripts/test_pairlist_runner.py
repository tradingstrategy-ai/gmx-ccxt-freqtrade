"""
Standalone test runner for the volume pairlist chain.

Patches the freqtrade config schema to allow our custom pairlist handlers,
then runs test-pairlist. This avoids needing to modify the base freqtrade image.

Usage (inside container):
    python -u -B /freqtrade/scripts/test_pairlist_runner.py \
        --config /freqtrade/configs/test_volume_pairlist.json \
        --config /freqtrade/configs/ichiv2_gmx.secrets.json \
        -vvv
"""
import sys


def main():
    # Step 1: Apply GMX monkeypatch (same as patched_entrypoint)
    from eth_defi.gmx.freqtrade.monkeypatch import patch_freqtrade

    result = patch_freqtrade()
    print(f"GMX monkeypatch applied: {result}")

    # Step 2: Patch config schema to accept our custom pairlist handlers
    from freqtrade.config_schema import CONF_SCHEMA

    custom_pairlists = ["HistoricalVolumePairList", "GMXLiquidityFilter"]
    method_schema = (
        CONF_SCHEMA.get("properties", {})
        .get("pairlists", {})
        .get("items", {})
        .get("properties", {})
        .get("method", {})
    )
    if "enum" in method_schema:
        for name in custom_pairlists:
            if name not in method_schema["enum"]:
                method_schema["enum"].append(name)
        print(f"Schema patched: added {custom_pairlists} to allowed pairlists")

    # Step 3: Run freqtrade test-pairlist with remaining CLI args
    from freqtrade.main import main as ft_main

    sys.argv = ["freqtrade", "test-pairlist"] + sys.argv[1:]
    ft_main()


if __name__ == "__main__":
    main()
