# Architecture: Integrated Bot + Dashboard

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                 Unified Crypto Bot Runtime (2025 Q4)                │
│                                                                     │
│  ┌─────────────────────────┐      ┌─────────────────────────────┐   │
│  │ backend/api/run.py      │◄────►│ main.py (Trading Engine)    │   │
│  │ Flask Dashboard         │      │ Async trading loop          │   │
│  │ Port 5001               │      │ Scans + executes signals    │   │
│  │ REST & WebSocket API    │      │ Uses Alpaca via services    │   │
│  └─────────────────────────┘      └─────────────────────────────┘   │
│             ▲                                 ▲                     │
│             │       SERVICE REGISTRY +        │                     │
│             └───── CONFIG/STATE SHARING ──────┘                     │
│                           │                                           │
│                    ┌──────▼────────┐                                  │
│                    │ core/ &       │                                  │
│                    │ backend/api/  │                                  │
│                    │ services      │                                  │
│                    │ (Signals, P&L,│                                  │
│                    │  Execution)   │                                  │
│                    └───────────────┘                                  │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   Alpaca API     │
                    │                  │
                    │  • Market data   │
                    │  • Order execution│
                    │  • Account info  │
                    └──────────────────┘
```

## Data Flow: User Clicks "DOUBLE DOWN!"

```
┌──────────────┐
│   Browser    │
│ (Dashboard)  │
└──────┬───────┘
       │ 1. User clicks "🚀 DOUBLE DOWN! 🚀"
       │
       ▼
┌──────────────────────────────────────┐
│  Frontend JS (crypto-dashboard.html) │
│                                      │
│  multiplier *= 2                     │
│  fetch('/api/v1/trading/set-         │
│        multiplier', {multiplier})    │
└──────┬────────────────────────────────┘
       │ 2. POST /api/v1/trading/set-multiplier
       ▼
┌──────────────────────────────────────┐
│  backend/api/run.py (Trading BP)     │
│                                      │
│  trading_service.set_multiplier(     │
│      multiplier=2.0)                 │
│  trading_state.position_multiplier = │
│      2.0                             │
└──────┬────────────────────────────────┘
       │ 3. State persisted via service registry
       ▼
┌──────────────────────────────────────┐
│  TradingService / TradingExecutor    │
│                                      │
│  On next signal:                     │
│    base_size = config.position_size  │
│    order_size = base_size * 2.0      │
│    submit_order(order_size)          │
└──────┬────────────────────────────────┘
       │ 4. Order sent to Alpaca
       ▼
┌──────────────────────────────────────┐
│  Alpaca API                          │
│                                      │
│  BUY crypto @ scaled notional        │
└──────┬────────────────────────────────┘
       │ 5. Fill broadcast
       ▼
┌──────────────────────────────────────┐
│  TradingService log + SocketIO       │
│                                      │
│  emit('trade_update', {...})         │
└──────┬────────────────────────────────┘
       │ 6. Dashboard updates
       ▼
┌──────────────────────────────────────┐
│  Browser                             │
│                                      │
│  Recent Activity shows filled trade  │
└──────────────────────────────────────┘
```

## Component Responsibilities

### backend/api/run.py (Flask Dashboard)
- Serves the dashboard UI from `frontend/`
- Exposes REST + WebSocket endpoints under `/api/v1`
- Delegates business logic to `backend/api/services/`
- Persists runtime state (multipliers, trade logs) through the shared service registry

### core/service_registry & backend/api/services
- Provide dependency injection for trading components and Alpaca clients
- Maintain the active `TradingConfig` and runtime metrics
- Bridge dashboard requests to the trading engine via `TradingService`, `PnLService`, etc.

### main.py (Trading Engine)
- Loads configuration via `config.unified_config.get_config()`
- Runs signal scanning and order execution loops
- Reads multiplier and runtime state from the service registry
- Emits trade/account updates consumed by the dashboard

## Runtime Model

```
┌──────────────┐      SocketIO/REST       ┌────────────────┐
│  Browser UI  │ ◄──────────────────────► │ backend/api/   │
└──────────────┘                          │ app.py         │
                                          └──────┬─────────┘
                                                 │ Service calls
                                                 ▼
                                          ┌──────────────┐
                                          │ TradingService│
                                          │ PnLService    │
                                          └──────┬───────┘
                                                 │ Shared state
                                                 ▼
                                          ┌──────────────┐
                                          │ main.py       │
                                          │ Trading loop  │
                                          └──────────────┘
```

## Configuration Flow

```
config/unified_config.yml
    │
    └─► get_config() → TradingConfig (shared)
            │
            ├─► main.py consumes config for strategy + risk
└─► backend/api/run.py injects config into services
```

## Security & State Management

- Multiplier updates are stored via `TradingService.set_multiplier()` rather than ad-hoc globals.
- Flask and trading engine can run in separate processes; service registry/state adapters keep them synchronized.
- Alpaca credentials load through `utils.alpaca.load_alpaca_credentials`, keeping secrets outside source control.

---

**Summary**: The production deployment pairs `main.py` (execution) with `backend/api/run.py` (dashboard + API). They coordinate through shared services, ensuring multiplier changes, trade events, and account snapshots remain consistent without relying on the archived single-process runner.
