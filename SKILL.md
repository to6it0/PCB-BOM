---
name: bom
description: Create, parse, validate, merge, and cross-reference Bills of Materials from Altium, KiCad, or Excel exports. Identify missing MPNs, flag substitutions, check for obsolete parts, find mating connectors/terminals, compare multi-supplier pricing, and format BOMs for JLCPCB, PCBWay, or Mouser/DigiKey ordering. Use when the user mentions BOM, bill of materials, component list, or part numbers.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - Bash
---

# /bom — Bill of Materials Assistant

Arguments passed: `$ARGUMENTS`

---

## Dispatch on arguments

Parse `$ARGUMENTS`. If empty, search the current directory for BOM files and load the most recent one.

### No args — load and summarize

1. Search for BOM files: `*.xlsx`, `*.csv`, `*.xls`, `*BOM*`, `*bom*`.
2. Read the most recent file. For `.csv`, parse directly. For `.xlsx`, ask the user to export as CSV or describe the columns.
3. Report: total line items, total component count, unique values, any rows missing MPN/manufacturer.

### `validate` — BOM completeness check

Review the loaded BOM and flag:
- Missing Manufacturer Part Number (MPN)
- Missing manufacturer name
- Missing reference designators
- Duplicate reference designators
- Components with quantity = 0
- Generic values without footprint (e.g. "10k" with no package)
- Mixed voltage/tolerance specs that may indicate substitution risk

### `jlcpcb` — Format for JLCPCB assembly

Reformat the BOM for JLCPCB SMT assembly upload:

Required columns: `Comment`, `Designator`, `Footprint`, `LCSC Part #`

1. Map existing BOM columns to JLCPCB format.
2. Flag any parts missing LCSC part numbers — these must be either sourced by user or hand-assembled.
3. Warn about parts not in JLCPCB's basic library (extended parts add setup fee per unique part).
4. Output a CSV ready for upload.

### `mouser` — Format for Mouser cart

1. Extract MPN and quantity columns.
2. Format as Mouser BOM import: `Mouser Part Number` or `Manufacturer Part Number` + `Quantity`.
3. Output CSV compatible with Mouser's multi-line order entry.

### `digikey` — Format for DigiKey cart

1. Extract MPN and quantity columns.
2. Format as DigiKey BOM import CSV: `Digi-Key Part Number` or `Manufacturer Part Number` + `Customer Reference` + `Quantity`.
3. Output CSV ready for DigiKey's BOM manager upload.

### `merge <file1> <file2>` — Merge BOMs

Merge two BOM files (e.g. from two boards being ordered together):
1. Combine line items with matching MPN — sum quantities.
2. Flag conflicts (same reference designator, different MPN).
3. Output merged BOM with board-of-origin column added.

### `obsolete` — Check for obsolete/NRND parts

For each part with an MPN, search for obsolescence signals:
- "NRND" (Not Recommended for New Designs)
- "Discontinued" / "Obsolete"
- Long lead times (>16 weeks typically signals supply risk)
Use WebSearch to check distributor availability if needed.

### `source` / `source full` — Full sourcing workflow (MPN → mating/terminals → multi-supplier pricing)

End-to-end workflow: extract every part number on the board, validate it, resolve connector mating/terminal part numbers (and obsolescence status) from the original manufacturer, then compare price and stock across distributors.

- `source` (default scope): the multi-supplier price/stock sweep in step 5 runs only on connectors, their mating parts, and terminals — this is the expensive, WebFetch-heavy part and it scales with connector count, not total line-item count.
- `source full`: extends the step 5 price/stock sweep to every unique MPN in the BOM (passives, ICs, everything). Warn the user before running this on a large BOM — cost scales as (unique MPNs) × (suppliers).

1. **Extract & validate.** Run the same checks as `validate` (missing MPN, missing manufacturer, duplicate reference designators, qty=0) plus: flag MPNs reused across conflicting designators/values as possible entry errors. Line items with no MPN (e.g. generic "10k" with no footprint) cannot be sourced — mark them clearly in `Validation Flags` and exclude them from steps 3 and 5 rather than silently dropping them.
2. **Identify connector/mating candidates, and split into two sub-types** — they need different lookups:
   - **Housing+terminal type** (wire-to-board headers, terminal blocks, board-to-board headers): mates with a separate receptacle housing that itself takes loose crimp terminals.
   - **FFC/FPC ZIF type** (flat-flex/flat-ribbon-cable connectors — e.g. Molex Easy-On, Hirose FH-series): this is a **"no mating connector" category — it does NOT have a separate mating housing or loose terminals.** It clamps directly onto a flex cable. This still requires a lookup, just a different one: find the **mating cable spec** (conductor/position count, pitch, cable thickness, contact side — top/bottom — and single/double-ended), not a mating part number. Don't skip the lookup just because there's no "Mating MPN" to find.
   - Flag every connector's sub-type as part of `type: connector (housing+terminal)` or `type: connector (FFC/FPC ZIF)`, and record pin/position count if derivable from footprint/description (needed for terminal or cable-conductor-count math).
3. **Mating/cable lookup, plus obsolescence — manufacturer site is the source of truth, not distributors, when reachable.**
   - For each connector MPN, WebFetch the manufacturer's own product page, catalog, or datasheet for that exact part number/series.
   - If the direct product URL isn't known, WebSearch `"<MPN>" datasheet site:<manufacturer domain>` first, then WebFetch the top manufacturer-domain result.
   - **Housing+terminal type**: extract the official mating receptacle housing part number and compatible crimp terminal/contact part number(s).
   - **FFC/FPC ZIF type**: extract the mating cable spec (conductor count, pitch, thickness, contact side/orientation) from the connector's own datasheet/catalog — there is no housing/terminal PN to find, and that's expected, not a lookup failure.
   - While on the manufacturer page, also check for NRND/discontinued/obsolete status (this replaces a separate `obsolete` pass for these parts — reuse the fetch instead of hitting the same page twice).
   - **Known reliability issue, and the fix for it.** WebFetch alone gets blocked (403/connection-reset) on molex.com, Mouser, TME, Farnell, RS, Jameco, Octopart, componentsearchengine, and Arrow. These fall into two different categories, and only one is fixable without extra credentials:
     - **TLS-fingerprint blocking (fixable)**: molex.com's block is purely based on the HTTP client's TLS handshake fingerprint, not JS execution. Fix: run a short Python script via Bash using `curl_cffi` (`pip install curl_cffi` if not already present) with `impersonate="chrome"`, e.g. `creq.get(url, impersonate="chrome", timeout=30)`. This has reliably returned real page content from molex.com. Use `BeautifulSoup`/regex on the response, and check for JSON-LD `<script type="application/ld+json">` blocks — Molex embeds structured `PropertyValue` data there, which is more reliable to parse than the visible HTML text.
     - **JS-executing bot-challenge blocking (not fixable with HTTP tools)**: Mouser and RS run a PerimeterX/HUMAN-style challenge ("Powered and protected by Privacy..." interstitial, HTTP 200 with no real content), TME runs a Cloudflare JS challenge ("Just a moment..."), and Farnell returns a hard WAF 403 regardless of headers or TLS fingerprint. None of these can be solved by `curl`/`requests`/`curl_cffi` — they require executing real JavaScript (canvas fingerprinting, challenge-token solving), which needs an actual browser runtime. If no headless-browser tool is available in the environment, don't keep retrying these domains — switch to DigiKey (reliably reachable) or note the gap and recommend the user's own account/an official API (Mouser Search API, TME API, Element14/Farnell Product Search API, or the Octopart/Nexar API which aggregates most distributors including these — all require a free developer API key the user must register for). Scraping is also against most of these sites' terms of service, so an official API is the correct fix, not just a workaround.
   - Even when molex.com IS reachable, don't assume it has the answer: some parts return "This part is not formally published to our online part catalog. Limited information is available to display on molex.com." — meaning Molex's own site genuinely lacks a mating cross-reference or lifecycle field for that specific part number. That's a real absence, not a fetch failure — fall back to a DigiKey product page's own "You may also be interested in" / "Accessories" cross-reference section, and label it as manufacturer-sourced-via-DigiKey rather than independently molex.com-confirmed.
   - A terminal PN confirmed for one position-count member of a series (e.g. the 4-position header) can reasonably be inferred for other members of the same series (e.g. the 12-position header), since crimp terminals are usually shared across an entire series regardless of housing size — but label it explicitly as "inferred by series consistency, not independently confirmed" rather than presenting it as directly confirmed.
   - If no confident mating/terminal/cable-spec match is found after trying the manufacturer site and the DigiKey cross-reference fallback, leave the field blank and note it as unresolved in the final summary — do not guess a mating part number, cable spec, or terminal quantity.
   - **Terminal quantity** (housing+terminal type only): compute `Terminal Qty Needed` = (contacts per connector, from pin/position count) × (board instances of that designator, from `Quantity`). This is the number of loose terminals to buy, separate from the housing quantity.
4. **Export baseline workbook.** Write a real `.xlsx` (not CSV) via a short Python script (`openpyxl`) run through Bash — do not hand-construct xlsx binary content. One row per unique component, columns: `Designator(s)`, `Manufacturer`, `MPN`, `Description/Value`, `Footprint`, `Quantity`, `Type` (connector sub-type/passive/etc.), `Validation Flags`, `Obsolescence Status`, `Mating MPN` (housing+terminal type) or `Mating Cable Spec` (FFC/FPC ZIF type), `Terminal MPN(s)`, `Terminal Qty Needed`.
   - **One file per board, always.** Use a single, stable output filename (e.g. `<board name>_Sourcing.xlsx`) and overwrite it in place on every run — never create `_v2`/`_v3`-suffixed copies. If the save fails with a permission/lock error, that means the file is open elsewhere (commonly Excel) — say so and ask the user to close it, rather than silently saving under a new filename that then leaves duplicate files to clean up later.
5. **Multi-supplier price & availability**, scoped per the `source`/`source full` mode above. For each in-scope MPN (plus resolved mating/terminal MPNs), check price and stock at the confirmed supplier set:
   - Global: Mouser, DigiKey
   - EU (prioritized for Luxembourg-area shipping): Farnell/element14, RS Components, TME, and — if requested — Rutronik, Avnet Abacus, Conrad
   - LCSC, when the board is also going through the `jlcpcb` flow or the user asks for it — LCSC pricing is what actually matters for JLCPCB assembly cost, not the EU distributors.
   - Rutronik, Avnet Abacus, and Conrad are B2B distributors that commonly gate pricing behind a login — treat these as manual-check suppliers to mention, not ones to automatically WebFetch, unless the user specifically asks for a live check.
   - Pull the price at the quantity break matching the BOM's actual required quantity (or terminal qty, for terminals) — not just the qty-1 unit price, since distributor pricing is tiered.
   - If a supplier's page can't be reliably fetched (blocked, JS-rendered, no data returned), leave that cell blank and label it (e.g. "Blocked — 403/connection reset, not retrieved") rather than guessing — apply the same no-fabrication rule as step 3. Don't retry the same blocked domain more than once or twice per run.
   - Do not filter by "authorized distributor" status — check whichever of the selected suppliers list the part, authorized or not.
   - **EUR is the only reference currency.** WebSearch for the current exchange rate (e.g. "USD to EUR exchange rate today") and convert every price to EUR before it goes in the workbook — don't show the original currency alongside it in the sheet. Cite the rate and its source/date once in the chat summary (not as a spreadsheet column), never fabricate a rate. If no live rate can be found, say so in the chat and hold that supplier's price out of the sheet rather than presenting an unconverted number as if it were EUR.
   - For a supplier whose page can't be fetched (blocked, JS-rendered, no data returned), put a link to a live search on that distributor's site for the exact MPN in that cell instead of leaving it blank or writing "blocked" — that gives the user something clickable to check manually. Construct the link as a generic site search, not a guessed deep product-page URL, since the deep link's ID can't be verified without fetching it. **Default to the Luxembourg-adjacent locale for each distributor** (confirmed working domains, not guesses): Mouser `https://www.mouser.com/c/?q=<MPN>`, TME `https://www.tme.eu/nl/katalog/?search=<MPN>` (Eindhoven, NL — TME's Benelux warehouse), Farnell `https://be.farnell.com/fr-BE/search?st=<MPN>` (Liège, BE logistics hub, French locale), RS Components `https://befr.rs-online.com/web/c/?searchTerm=<MPN>` (Belgium French locale). URL-encode the MPN (e.g. via `urllib.parse.quote`) since part numbers often contain `()`/`.` characters.
   - Add one price/stock column per reachable supplier (EUR only), plus a plain link column for suppliers whose data couldn't be extracted.
6. **Output.** Single `.xlsx` workbook with at least two sheets:
   - `BOM` — full component list, validation flags, obsolescence status, mating/terminal/cable-spec columns and quantities (from steps 1–4)
   - `Supplier Comparison` — one row per sourced MPN (component + mating + terminal), EUR price/stock per reachable supplier, a search-link column per unreachable supplier, plus a `Best Price (EUR)` helper column. No per-row notes column — caveats (FX rate/date, unresolved items, blocked suppliers) go in the chat summary, not the sheet.
7. In the chat response, summarize: total components, scope used (`source` vs `source full`), how many connectors had mating/terminal/cable-spec data resolved vs. unresolved (and via which source — manufacturer site or DigiKey cross-reference fallback), any parts flagged obsolete/NRND or with conflicting lifecycle signals, and any suppliers that returned no data — don't let those get silently dropped from the sheet.

---

## Implementation notes

- Altium exports BOMs as `.xlsx` or `.csv`. Common column names: `Comment`, `Description`, `Designator`, `Footprint`, `LibRef`, `Quantity`, `Manufacturer`, `Manufacturer Part Number`.
- LCSC part numbers follow format `C` + digits (e.g. `C14663`).
- DigiKey part numbers typically contain dashes and end in `-ND`.
- Mouser part numbers are numeric strings like `581-LMR14020XSDX`.
- When grouping designators, sort them naturally: R1, R2, R10 not R1, R10, R2.
- For `.xlsx` output, generate the file with a Python `openpyxl` script via Bash rather than writing raw file bytes.
- Manufacturer sites are authoritative for MPN details, mating connectors, terminal/contact part numbers, and obsolescence status. Distributor pages are for price/stock — except that a distributor's own "accessories / mates with / you may also be interested in" cross-reference field is manufacturer-sourced data surfaced through the distributor's catalog, and is an acceptable fallback for mating/terminal PNs when the manufacturer's own site is unreachable (label it as such).
- FFC/FPC ZIF connectors (Molex Easy-On, Hirose FH-series, etc.) are a **"no mating connector" category** — they mate directly with a flex cable, not a separate housing+terminal pair. Still look up and report the mating cable spec (conductor count, pitch, thickness, contact side) rather than treating them the same as a wire-to-board header, and don't leave the field blank just because there's no PN to find.
- Site reliability observed in practice: **molex.com, Mouser, TME, Farnell, RS, Jameco, Octopart, componentsearchengine, and Arrow have all blocked WebFetch (403 or connection reset)** at various points — this is common enough to expect, not a one-off. **DigiKey has been the one consistently fetchable source via WebFetch.** molex.com is separately fixable via a `curl_cffi` (Chrome TLS-fingerprint impersonation) Bash script — see step 3 above. Mouser/RS/TME/Farnell run JS-executing bot challenges (PerimeterX/HUMAN, Cloudflare, Akamai) that no HTTP-level tool can solve; don't burn retries on them — use DigiKey, or recommend the user register for the relevant official API (Mouser, TME, Element14/Farnell, or Octopart/Nexar).
- Default ordering country is Luxembourg, EUR only. Use each distributor's Luxembourg-adjacent locale, not their UK/US default: TME → `tme.eu/nl/` (Eindhoven, NL — TME's Benelux warehouse), Farnell → `be.farnell.com/fr-BE/` (Liège, BE logistics hub), RS Components → `befr.rs-online.com` (Belgium French locale). Add LCSC when JLCPCB assembly is in play. Rutronik, Avnet Abacus, and Conrad are typically login-gated for pricing — mention them as manual-check options rather than automating a fetch by default.
- **EUR only.** Every price in a `source` workbook is EUR, converted using a live-searched exchange rate (WebSearch "X to Y exchange rate today") — never show original currency alongside it in the sheet, and never fabricate a rate. Cite the rate/source/date in the chat summary, not as a spreadsheet column. If no live rate is available, say so in chat and omit that supplier's price from the sheet rather than mislabeling an unconverted number as EUR.
- Distributor price/stock data is often JS-rendered or blocked outright and may not be reliably extractable via WebFetch — treat an empty/unclear/blocked result as "unavailable," not zero stock or zero price.
