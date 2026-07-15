# PCB-BOM

A Claude Code skill for working with Bills of Materials (BOMs) for PCB projects — create, parse, validate, merge, and cross-reference BOMs exported from Altium, KiCad, or Excel.

## What it does

Invoke with `/bom` in Claude Code. The main workflow is:

| Command | Description |
|---|---|
| `/bom source` | Full sourcing workflow: validates MPNs, resolves connector mating/terminal part numbers + obsolescence status from the manufacturer's own site, computes terminal quantities needed, exports a real `.xlsx` (BOM + Supplier Comparison sheets), and compares EUR price/stock across DigiKey and EU distributors (Mouser, Farnell, RS Components, TME, defaulting to Luxembourg-adjacent locales). Multi-supplier pricing defaults to connectors/mating/terminal parts only — use `/bom source full` to sweep every line item |

See [`SKILL.md`](./SKILL.md) for the full set of commands (`validate`, `jlcpcb`, `mouser`, `digikey`, `merge`, `obsolete`) and their detailed behavior.

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
2. Run `/bom` to load and summarize it, or `/bom source` to run the full sourcing workflow.

See [`SKILL.md`](./SKILL.md) for the full skill definition.
