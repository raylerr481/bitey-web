# Bitey IA — Live Market Workspace Integration

Bitey IA now exposes **Mercados en vivo** as a first-class workspace capability.

## What it does

The web workspace adds a sidebar entry that opens the existing Bitey System Bots Trading web environment inside a controlled market panel, with a direct full-terminal fallback.

Target:

`https://bitey-system-bots-trading.raylerr481.workers.dev/`

## Architecture

```text
Bitey IA Web
   │
   ├── Cognitive Core decides when trading/market capability is relevant
   │
   └── Mercados en vivo
          │
          └── Bitey SBT web workspace
                 ├── Market Intelligence
                 ├── Research Lab
                 ├── Bot Lab
                 ├── Validation
                 └── Risk Gate
```

The integration does **not** copy or replace the SBT trading engine. It gives Bitey IA a native workspace entry point into the specialized SBT capability.

## Safety boundary

- Market visualization is informational.
- Bitey IA does not receive broker credentials through this panel.
- The SBT Risk Gate remains authoritative for trading actions.
- The current SBT implementation remains read-only/demo oriented for market data.
- No real-money order is enabled by this integration.
- If browser framing is blocked by deployment headers, the user can open the SBT terminal directly.

## Free-first rule

The integration adds no paid market-data dependency. It reuses the already deployed Bitey SBT web environment and its existing connector contracts.

## Future evolution

The next stage can expose normalized live quotes and market snapshots through a versioned SBT/Bitey API contract, allowing Bitey Brain to reason over current market state without coupling the general workspace to a vendor-specific UI.
