# ichiv2_gmx Crash & Issues – Full Diagnostics Report

**Generated:** 2026-02-16  
**Scope:** docker-compose `ichiv2_gmx` service, all related log files.

---

## 1. Setup Summary

### 1.1 Docker Compose (`docker-compose.yml`)

- **Service:** `ichiv2_gmx`
- **Container:** `ichiv2_gmx`
- **Strategy:** `IchiV2_LS_Live`
- **Config:** `configs/ichiv2_gmx.json` + `configs/ichiv2_gmx.secrets.json`
- **DB:** `sqlite:////freqtrade/db/ichiv2_gmx.sqlite`
- **Log file (configured):** `--logfile /freqtrade/user_data/logs/ichiv2_gmx_trading_fee_rate_gui.log`
- **Port:** `127.0.0.1:9094:8080`
- **Restart:** `unless-stopped`
- **No memory/CPU limits** are set on the service.

**Important:** The running container writes to **`ichiv2_gmx_trading_fee_rate_gui.log`**, not to `ichiv2_gmx.log`. The file `ichiv2_gmx.log` is from a different run (e.g. manual or older config).

### 1.2 Log Files Found

| File | Purpose |
|------|--------|
| `ichiv2_gmx_trading_fee_rate_gui.log` | **Current** – where the container writes (per docker-compose) |
| `ichiv2_gmx_trading_fee_rate_gui.log.1` … `.10` | Rotated logs (same stream) |
| `ichiv2_gmx_trading_fee_rate.log` | Separate run/config |
| `ichiv2_gmx.log` (+ `.1`–`.7`) | Older/different run (e.g. different `--logfile`) |

---

## 2. Root Causes of Crashes / Issues

### 2.1 **Primary: RPC / Network Unreachability (Fatal Exceptions)**

**What happens:** The bot exits with **“Fatal exception!”** during **startup** when it cannot reach any Arbitrum RPC endpoint.

**Where:**  
- `eth_defi/chain.py` → `install_chain_middleware`  
- Call chain: `web3.eth.chain_id` → HTTP request to RPC → all providers fail → exception propagates from `freqtrade/main.py` → process exits.

**Observed errors (from `ichiv2_gmx_trading_fee_rate_gui.log` and rotated files):**

- **ConnectTimeoutError** (e.g. 30s timeout):
  - `harry.tradingstrategy.ai`
  - `arb-mainnet.g.alchemy.com`
  - `lb.drpc.live`
- **NewConnectionError / Network unreachable (Errno 101):**
  - `arb1.arbitrum.io`
  - `arbitrum-one.public.blastapi.io`
  - `lb.drpc.live`

**RPC config (from `configs/ichiv2_gmx.secrets.json`):**

- Multiple URLs in `rpcUrl` (space-separated):  
  `harry.tradingstrategy.ai`, Alchemy, drpc.live, arb1.arbitrum.io, blastapi.io`
- At startup the stack tries each provider; if **all** fail after retries (e.g. 6 retries with backoff), it raises and the process crashes.

**Evidence:**

- **142** occurrences of “Fatal exception” in current `ichiv2_gmx_trading_fee_rate_gui.log` (and many more in rotated logs).
- Latest log (2026-02-16 08:53–08:58) shows startup, then timeouts and “Network is unreachable” on all providers, ending at “Retrying in 12.207031 seconds, retry #5 / 6”. After retry #6 the process would exit with the same fatal exception.

**Conclusion:**  
Crashes are **network/RPC related**: host or network cannot reach Arbitrum RPCs (firewall, DNS, outbound 443, or provider outages). When every RPC fails, the bot has no way to continue and exits.

#### 2.1.1 Root cause: host firewall (DOCKER-USER) blocks compose network

**Verified 2026-02-16:** The RPC servers are reachable from the **host** (all four URLs respond with HTTP 200 to a JSON-RPC `eth_chainId` POST). From **inside** the `ichiv2_gmx` container, all outbound HTTPS connections fail with connect timeout or "Network is unreachable" (Errno 101).

The host `iptables` chain **DOCKER-USER** has explicit ACCEPT rules only for certain bridges (`br-5d9eeb7fb334`, `br-cba92fa5d2a3`, `docker0`, `tailscale0`) and a final **DROP**. The gmx-ccxt-freqtrade compose network uses bridge **`br-eb93aaf157e7`**, which is **not** in that allow list, so all outbound traffic from `ichiv2_gmx` (and any other service on the same compose network) is dropped.

**Fix (run on host):** Allow outbound from the compose bridge:

```bash
sudo iptables -I DOCKER-USER 1 -i br-eb93aaf157e7 -j ACCEPT
```

To make the rule persistent across reboots (Debian/Ubuntu with iptables-persistent), add the same rule to your iptables rules file or a script that runs after Docker. The bridge name `br-eb93aaf157e7` is tied to the compose project network; if you recreate the project (e.g. `docker compose down` and change networks), the bridge id may change and the rule may need to be updated.

**Quick check after applying:** From the host, run:

```bash
docker exec ichiv2_gmx python3 -c "
import urllib.request, json
req = urllib.request.Request('https://arb1.arbitrum.io/rpc',
  data=json.dumps({'jsonrpc':'2.0','method':'eth_chainId','params':[],'id':1}).encode(),
  headers={'Content-Type':'application/json'}, method='POST')
with urllib.request.urlopen(req, timeout=10) as r: print('RPC OK', r.read().decode()[:60])
"
```

You should see `RPC OK {"jsonrpc":"2.0","id":1,"result":"0xa4b1"}`.

---

### 2.2 **Secondary: SQLite UNIQUE Constraint on Cleanup**

**Where:** `ichiv2_gmx_trading_fee_rate_gui.log.1` (and likely other rotated logs).

**Error:**

```text
sqlite3.IntegrityError: UNIQUE constraint failed: orders.ft_pair, orders.order_id
```

**Context:**  
Occurs during **cleanup** (e.g. on exit):  
`freqtrade/commands/trade_commands.py` → `worker.run()` → worker loop → cleanup.  
So the process is already shutting down when it tries to persist something to the `orders` table and hits a duplicate `(ft_pair, order_id)`.

**Impact:**  
- Can cause “Error during cleanup” and unclean shutdown.  
- May leave the DB in a state where the same order is re-processed or fee-update logic keeps retrying (see next section).

**Possible causes:**  
- Same order (e.g. GMX order id) being inserted more than once (e.g. after restart or fee update path).  
- Exit order **rejected** by the exchange (e.g. low gas) so `order_id` is `'None'`; a previous row with `(ft_pair, order_id)=('PAIR', 'None')` already exists, so a second INSERT fails.

**Recovery (one-time DB fix):**  
- Find the duplicate: e.g. `SELECT id, ft_pair, order_id, status FROM orders WHERE order_id = 'None';`  
- Delete the redundant row so only one `(ft_pair, order_id)` remains:  
  `DELETE FROM orders WHERE id = <id> AND ft_pair = '...' AND order_id = 'None';`  
- Restart the bot. Ensure the wallet has enough native gas so exit orders can be submitted and return a real order id.

---

### 2.3 **Behavioral / Logic: Sell-Fee Update Loop (Not a Crash, but Heavy Load)**

**Where:** `ichiv2_gmx.log` (28k+ lines, 2026-02-10).

**What happens:**  
- **1,238** log lines: “Updating sell-fee on trade … **open_since=closed**” for **Trade id=1** (HYPE/USDC:USDC), order `0x4694de...`.  
- Each time: “Found open order” → “NOT IN CACHE, fetching from blockchain” → ~10s later “Order EXECUTED … status=closed” → “Fee for Trade … [sell]: …” → “Updating trade (id=1)”.  
- So the bot keeps treating the **sell order as open** and re-fetching it from the chain and re-updating the fee, even though the trade is already **closed**.

**Impact:**  
- Does not crash the process but:  
  - One blockchain RPC call every ~10–15 seconds for the same closed order.  
  - Extra DB writes.  
  - Contributes to load and log volume; if RPC is slow or flaky, this can amplify timeouts.

**Likely cause:**  
- Fee or order status for that trade is not being marked “done” in the DB or in memory, so the “update sell-fee” / “open order” path keeps running.  
- Could be related to the same order being stored twice (UNIQUE constraint above) or to GMX/CCXT integration not clearing “open order” state for that trade.

---

### 2.4 **Graceful Shutdown in `ichiv2_gmx.log` (Not a Crash)**

The **end** of `ichiv2_gmx.log` (2026-02-10 11:35) shows:

- “worker found … calling exit”
- “Sending rpc message: {'type': status, 'status': '**process died**'}”
- “SIGINT received, aborting …”
- Clean teardown (API server, Telegram, GMX session).

So that run **did not crash**; it was stopped by signal (e.g. `docker stop`, Telegram `/exit`, or manual Ctrl+C). The “process died” message is the worker reacting to the exit, not the cause.

---

## 3. Summary Table

| Issue | Type | Severity | Log(s) | Cause |
|------|------|----------|--------|--------|
| RPC/network unreachable | **Crash** | **Critical** | `ichiv2_gmx_trading_fee_rate_gui.log` (+ rotated) | No working Arbitrum RPC; host/network or provider failure |
| UNIQUE constraint (orders) | Error on cleanup | High | `ichiv2_gmx_trading_fee_rate_gui.log.1` | Duplicate (ft_pair, order_id) on order insert/update |
| Sell-fee update loop | Logic / load | Medium | `ichiv2_gmx.log` | Closed trade’s sell order still treated as open; repeated fee update + chain fetch |
| “process died” / SIGINT | Normal exit | Info | `ichiv2_gmx.log` | Intentional stop (docker/Telegram/manual) |

---

## 4. Recommendations

### 4.1 Stop Crashes (RPC/Network)

1. **Verify outbound connectivity** from the host/container:
   - From the same network as the container:  
     `curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 https://arb1.arbitrum.io/rpc`  
   - Test at least: `arb1.arbitrum.io`, `arb-mainnet.g.alchemy.com`, `lb.drpc.live`.
2. **Check firewall / security groups** for outbound HTTPS (443) to those hosts.
3. **Add a known-good RPC** in `ichiv2_gmx.secrets.json` (e.g. a dedicated Alchemy/Infura/Ankr Arbitrum URL) and put it first in `rpcUrl` so it’s tried first.
4. **Consider retries / backoff at startup:** The stack already retries (e.g. 6 times); if the host often has short network blips, a wrapper that restarts the container on exit (e.g. with a small delay) could help, but fixing network/RPC is the real fix.

### 4.2 Database / Order Handling

5. **Investigate duplicate orders:**  
   - Check `orders` table for duplicate `(ft_pair, order_id)` for the HYPE trade and the GMX order id `0x4694de...`.  
   - Ensure the code path that inserts/updates orders on fee update or restart does not insert the same order twice (or use “insert or ignore” / “upsert” if that matches business logic).
6. **Sell-fee / “open order” logic:**  
   - After a trade is closed and sell fee is updated, ensure the sell order is marked so it is no longer considered “open” and the “update sell-fee” loop does not run for that order again (freqtrade core or GMX exchange adapter).

### 4.3 Observability

7. **Unify log file name** if you want a single place to look:  
   - Either change docker-compose to `--logfile .../ichiv2_gmx.log`, or always inspect `ichiv2_gmx_trading_fee_rate_gui.log` for the running container.
8. **Alert on “Fatal exception”** in the active log file so you know when the bot is exiting due to RPC/network (or other fatal errors).

---

## 5. Quick Checks You Can Run

```bash
# From host (same network as container)
curl -s -o /dev/null -w "%{http_code}\n" --connect-timeout 10 https://arb1.arbitrum.io/rpc
curl -s -o /dev/null -w "%{http_code}\n" --connect-timeout 10 https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY

# Recent fatal exceptions in current log
grep -n "Fatal exception" user_data/logs/ichiv2_gmx_trading_fee_rate_gui.log | tail -5

# Last 50 lines of current log (see if still in RPC retry or other error)
tail -50 user_data/logs/ichiv2_gmx_trading_fee_rate_gui.log
```

---

**End of report.**
