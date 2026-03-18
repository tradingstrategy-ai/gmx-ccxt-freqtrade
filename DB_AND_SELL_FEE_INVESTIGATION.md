# DB Duplicate Entries & Sell-Fee Loop Investigation

**Date:** 2026-02-16  
**DB:** `db/ichiv2_gmx.sqlite`  
**Log:** `user_data/logs/ichiv2_gmx.log`

---

## 1. Database investigation

### 1.1 Schema (relevant tables)

- **orders:** `id`, `ft_trade_id`, `ft_order_side`, `ft_pair`, `ft_is_open`, `order_id`, `status`, `symbol`, `side`, `price`, `average`, `amount`, `filled`, `remaining`, `cost`, `order_date`, `order_filled_date`, `order_update_date`, `funding_fee`, `ft_fee_base`, `ft_order_tag`
- **trades:** `id`, `pair`, `is_open`, `fee_open`, `fee_close`, `fee_close_cost`, `fee_close_currency`, `open_date`, `close_date`, `exit_reason`, `exit_order_status`, …
- **KeyValueStore**, **pairlocks**, **trade_custom_data**

### 1.2 Duplicate checks

| Check | Result |
|-------|--------|
| **Duplicate `(ft_pair, order_id)` in `orders`** | **None found** – every pair + order_id is unique. |
| **Duplicate `order_id` (same string in multiple rows)** | **None found**. |
| **Total orders** | 15 rows. |

So the DB **does not currently contain** duplicate `(ft_pair, order_id)`. The `UNIQUE constraint failed: orders.ft_pair, orders.order_id` seen in logs (e.g. in `ichiv2_gmx_trading_fee_rate_gui.log.1` during cleanup) likely happened when the **code tried to insert** a row that would duplicate an existing `(ft_pair, order_id)`. The insert failed, so no duplicate was ever committed. The problematic code path (e.g. on shutdown/cleanup) may still be attempting that insert.

### 1.3 Trade 1 (HYPE) and the problematic order

**Trade id=1 (HYPE/USDC:USDC):**

- **is_open:** 0 (closed)  
- **fee_close:** 0.01928622  
- **fee_close_cost:** 1.8650140912e-05 ETH  
- **fee_close_currency:** ETH  
- **close_date:** 2026-02-07 00:10:08.605000  

So the trade is closed and the sell fee is already stored.

**Orders for trade 1:**

| id | ft_trade_id | ft_order_side | ft_pair          | order_id (truncated) | status    |
|----|-------------|---------------|------------------|----------------------|-----------|
| 1  | 1           | buy           | HYPE/USDC:USDC   | 0xa456f4...          | closed    |
| 2  | 1           | sell          | HYPE/USDC:USDC   | 0x4e0daa...          | cancelled |
| 3  | 1           | sell          | HYPE/USDC:USDC   | 0x4694de...          | closed    |

The sell-fee loop in the log is for order **0x4694de065d229f7ee89fa8ad0cc88079fac19db3d38b1f31bd4d68988f3eb9ce** (order row id=3, status=**closed**). So in the DB this order is already closed and the trade has a sell fee; the loop is a **logic/state** issue (freqtrade or GMX still treating it as needing a fee update), not missing DB data.

### 1.4 Other notable rows

- **Orders with `order_id = 'None'`:** 2 rows  
  - id=14: trade_id=4, BCH/USDC:USDC, status=rejected  
  - id=15: trade_id=2, TON/USDC:USDC, status=rejected  
  These can be problematic if any code assumes `order_id` is a valid string (e.g. for `fetch_order(order_id)`).

### 1.5 Summary (DB)

- No duplicate `(ft_pair, order_id)` in the DB.
- UNIQUE constraint errors are likely from an **insert** that would create a duplicate (e.g. during cleanup).
- Trade 1 is closed with sell fee stored; order 0x4694de is closed in `orders`; the sell-fee loop is due to runtime logic still considering this trade/order as needing an update.

---

## 2. Sell-fee loop: when and where

### 2.1 When (from logs)

- **Log file:** `user_data/logs/ichiv2_gmx.log`
- **First occurrence:** 2026-02-10 **06:24:01** (line 3)
- **Last occurrence:** 2026-02-10 **11:35:05** (line 28289) – right before the process received SIGINT and shut down
- **Duration:** ~5 hours 11 minutes
- **Approx count:** 1,238 “Updating sell-fee on trade … open_since=closed” lines for Trade id=1, order 0x4694de...
- **Interval:** ~every **15 seconds**, matching `internals.process_throttle_secs: 15` in `configs/ichiv2_gmx.json`

So the loop runs **once per bot throttle cycle** (every 15s) for the same closed trade/order.

### 2.2 Log pattern (one cycle)

Each cycle looks like:

1. `freqtrade.freqtradebot - INFO - Updating sell-fee on trade Trade(id=1, pair=HYPE/USDC:USDC, ..., open_since=closed) for order 0x4694de...`
2. `freqtrade.freqtradebot - INFO - Found open order for Trade(id=1, ...)`
3. `eth_defi.gmx.ccxt.exchange - INFO - ORDER_TRACE: fetch_order(0x4694de...) - NOT IN CACHE, fetching from blockchain (e.g., after bot restart)`
4. ~10s later: `ORDER_TRACE: fetch_order(0x4694de...) - Order EXECUTED at price=0.00, size_usd=0.00 - RETURNING status=closed`
5. `freqtrade.freqtradebot - INFO - Fee for Trade ... [sell]: 1.8650141e-05 ETH - rate: None`
6. `freqtrade.persistence.trade_model - INFO - Updating trade (id=1) ...`

So: freqtrade decides “this trade needs sell-fee update” → looks up “open order” for the trade → finds the sell order 0x4694de → GMX has no cache → fetches from blockchain → gets status=closed and fee → updates trade. Next cycle the same thing repeats.

### 2.3 Where (code locations)

**Freqtrade (upstream, not in this repo):**

- **Logger:** `freqtrade.freqtradebot`  
  So the “Updating sell-fee” and “Found open order” logic lives in **Freqtrade core**, in the `FreqtradeBot` class in **`freqtrade/freqtradebot.py`** (in the official repo: https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/freqtradebot.py).
- This runs in the main worker loop (throttled by `process_throttle_secs`). The bot:
  - Considers trades that still have an “open” sell order (or missing sell fee).
  - For each such trade it finds the corresponding order (“Found open order”) and updates the sell fee (“Updating sell-fee”).
- The bug: for trade 1, the sell order 0x4694de is **closed** and the fee **is** in the DB, but something (e.g. `fee_close` rate not set, or order still in an “open orders” list in memory) keeps this trade in the “needs sell-fee update” set every cycle.

**GMX CCXT (this repo):**

- **“NOT IN CACHE, fetching from blockchain”** is logged in:
  - **`deps/web3-ethereum-defi/eth_defi/gmx/ccxt/exchange.py`** around **line 6518–6521**.
- **Context:** In `fetch_order(id, symbol=None, params=None)`:
  - If the order is in the exchange’s in-memory order cache (e.g. created this session), it returns from cache.
  - If **not in cache** (e.g. after restart, or order created in a previous run), it goes to the “fetch from blockchain” path: load tx receipt → order_key → Subsquid trade_action → build and return order (status=closed, fee, etc.).
  - The important detail: **the result of this blockchain fetch is not written back into the cache.** So every 15s when freqtrade calls `fetch_order(0x4694de...)`, the GMX exchange does the full chain + Subsquid path again (~10s) and never caches the closed order.

So:

- **When:** Every 15s in the main loop, for the whole run (06:24–11:35 on 2026-02-10).
- **Where (freqtrade):** `freqtrade/freqtradebot.py` – “Updating sell-fee” / “Found open order” and the condition that decides a trade still needs a sell-fee update.
- **Where (GMX):** `eth_defi/gmx/ccxt/exchange.py` – `fetch_order()` “NOT IN CACHE” path (around line 6515+) and the fact that it does not cache the fetched order.

---

## 3. Root cause (concise)

1. **Freqtrade** keeps treating trade 1 as needing a sell-fee update (e.g. because `fee_close` rate stays `None` or the sell order is still considered “open” in its internal state).
2. Each throttle cycle it asks GMX for order 0x4694de.
3. **GMX** doesn’t have that order in cache, so it fetches from the blockchain every time and does **not** cache the closed result.
4. So: repeated “Updating sell-fee” → “Found open order” → “NOT IN CACHE” → ~10s chain fetch → “Updating trade (id=1)” → repeat.

---

## 4. Recommendations

### 4.1 Freqtrade side (upstream or local patch)

- Ensure that once a trade is closed and the sell order has a fee (and optionally a rate), it is **no longer** considered for “update sell-fee” (e.g. by marking the order as fee-updated or by excluding closed trades).
- If the issue is `rate: None`, ensure the GMX adapter returns a fee rate when available so the trade’s fee fields are fully set and the “needs update” condition stops firing.

### 4.2 GMX CCXT (this repo)

- In **`exchange.py`**, in the “NOT IN CACHE” branch of `fetch_order()`, after building the order from the blockchain (including status=closed and fee), **put that order into the in-memory order cache** (same structure used when the order is created in-session). Then subsequent `fetch_order(0x4694de...)` calls will hit the cache and avoid repeated chain/Subsquid calls.
- This reduces load and latency even if freqtrade continues to call `fetch_order` for this order.

### 4.3 DB / UNIQUE constraint

- Track down the code path that runs on cleanup and inserts into `orders` (likely in freqtrade’s persistence/cleanup). Ensure it does not insert a row with the same `(ft_pair, order_id)` that already exists (e.g. use “insert or ignore” or “upsert” or skip if the order is already present).
- Handle `order_id = 'None'` safely everywhere (e.g. avoid calling `fetch_order('None')` or treat rejected orders so they don’t trigger fee-update logic).

---

**End of investigation.**
