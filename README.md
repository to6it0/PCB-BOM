# PCB-BOM

A Claude Code skill for working with Bills of Materials (BOMs) for PCB projects — create, parse, validate, merge, and cross-reference BOMs exported from Altium, KiCad, or Excel.

## What it does

Invoke with `/bom` in Claude Code. Supports:

| Command | Description |
|---|---|
| `/bom` (no args) | Finds the most recent BOM file in the directory and summarizes it (line items, component count, missing MPNs) |
| `/bom validate` | Flags missing MPN/manufacturer, missing or duplicate reference designators, zero-quantity rows, generic values without footprints, and mixed voltage/tolerance specs |
| `/bom jlcpcb` | Reformats the BOM for JLCPCB SMT assembly upload (`Comment`, `Designator`, `Footprint`, `LCSC Part #`), flags parts missing LCSC numbers and parts outside the basic library |
| `/bom mouser` | Formats MPN + quantity as a Mouser cart import CSV |
| `/bom digikey` | Formats MPN + quantity as a DigiKey BOM manager import CSV |
| `/bom merge <file1> <file2>` | Merges two BOMs, summing quantities on matching MPNs and flagging designator conflicts |
| `/bom obsolete` | Checks parts for NRND/discontinued status and long lead times |
| `/bom source` | Full sourcing workflow: validates MPNs, resolves connector mating/terminal part numbers + obsolescence status from the manufacturer's own site, computes terminal quantities needed, exports a real `.xlsx` (BOM + Supplier Comparison sheets), and compares EUR-normalized price/stock across Mouser, DigiKey, and EU distributors (Farnell, RS Components, TME, optionally Rutronik/Avnet Abacus/Conrad/LCSC). Multi-supplier pricing defaults to connectors/mating/terminal parts only — use `/bom source full` to sweep every line item |

## Supported input formats

- Altium BOM exports (`.xlsx` / `.csv`) — typical columns: `Comment`, `Description`, `Designator`, `Footprint`, `LibRef`, `Quantity`, `Manufacturer`, `Manufacturer Part Number`
- KiCad BOM exports
- Generic Excel/CSV component lists

## Part number formats recognized

- **LCSC**: `C` + digits (e.g. `C14663`)
- **DigiKey**: contains dashes, typically ends in `-ND`
- **Mouser**: numeric string like `581-LMR14020XSDX`

## Usage

1. Drop a BOM export (`.xlsx`/`.csv`) into this directory.
2. Run `/bom` to load and summarize it, or jump straight to a specific command (e.g. `/bom validate`, `/bom jlcpcb`).

See [`SKILL.md`](./SKILL.md) for the full skill definition.
