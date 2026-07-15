r"""
Reusable generator for the /bom source interactive sourcing dashboard.

Usage (from a per-board driver script, same pattern as the .xlsx builder):

    import sys
    sys.path.insert(0, r"C:\Users\RafaelRodrigues\.claude\skills\bom\scripts")
    from generate_dashboard import generate_dashboard

    generate_dashboard(
        board_name="My Board",
        sourced_bom=[...],
        supplier_rows=[...],
        output_path=r"path\to\My Board_Dashboard.html",
        fx_rate=0.875506, fx_date="2026-07-15", fx_source="xe.com",
    )

Data shapes
-----------
sourced_bom: list of dicts, one per unique connector/component:
    designator     str   e.g. "J2"
    manufacturer   str
    mpn            str
    footprint      str
    qty            int
    mating         str   MPN if resolved, or a short label like "No fixed mating PN"
    matingDetail   str   shown under the chip when matingStatus != "good" (cable spec, reasoning, etc.)
    matingStatus   "good" | "info"   -- "good" = real mating PN found, "info" = mates with something
                                          but no fixed catalog PN exists (e.g. custom FFC/FPC cable)
    terminal       str   terminal MPN, or "N/A"
    termQty        str   plain terminal count, or "N/A"
    awg            str   wire gauge range, or "N/A (...)" note

supplier_rows: list of dicts, one per sourced part (base component + its mating + its terminal):
    group          str   the designator this row belongs to, e.g. "J2" -- consecutive rows sharing
                         the same group are visually bracketed together in the table
    mpn            str
    role           str   e.g. "Base component", "Mating housing", "Crimp terminal"
    manufacturer   str
    price          float EUR, already converted
    stock          int
    stockNote      str | None   optional extra stock detail, e.g. "+7,800 factory stock"
    links          dict  {supplier_name: url, ...} -- e.g. {"DigiKey": "...", "Mouser": "...", ...}

Only DigiKey has reliably returned real price/stock data in practice (see SKILL.md's site-reliability
notes) -- other suppliers' `links` are search-result URLs, not confirmed product pages. Pass
`verified_suppliers=["DigiKey"]` (the default) to reflect that; update it if that changes.
"""

import json
import os
from urllib.parse import quote

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_FONT_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "assets", "fonts")


def _read_font_b64(name):
    with open(os.path.join(_FONT_DIR, f"{name}.b64")) as f:
        return f.read().strip()


def _storage_key(board_name):
    slug = "".join(c.lower() if c.isalnum() else "-" for c in board_name).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return f"bomDashboard.{slug}.overridesV1"


# Supplier link URL helpers (Luxembourg-adjacent EUR locales -- see SKILL.md implementation notes)
def mouser_link(mpn):
    return "https://www.mouser.com/c/?q=" + quote(mpn)


def tme_link(mpn):
    return "https://www.tme.eu/nl/katalog/?search=" + quote(mpn)


def farnell_link(mpn):
    return "https://be.farnell.com/fr-BE/search?st=" + quote(mpn)


def rs_link(mpn):
    return "https://befr.rs-online.com/web/c/?searchTerm=" + quote(mpn)


_HTML_TEMPLATE = r"""<title>__BOARD_NAME__ — Sourcing Dashboard</title>
<style>
@font-face {
  font-family: 'Archivo';
  font-weight: 700;
  font-style: normal;
  src: url(data:font/woff2;base64,__ARCHIVO_BOLD__) format('woff2');
  font-display: swap;
}
@font-face {
  font-family: 'Source Sans 3';
  font-weight: 400;
  font-style: normal;
  src: url(data:font/woff2;base64,__SOURCESANS_REGULAR__) format('woff2');
  font-display: swap;
}
@font-face {
  font-family: 'JetBrains Mono';
  font-weight: 400;
  font-style: normal;
  src: url(data:font/woff2;base64,__JBMONO_REGULAR__) format('woff2');
  font-display: swap;
}

:root {
  --bg: #eef2f1;
  --surface: #ffffff;
  --surface-2: #f4f8f7;
  --border: #d7dfdd;
  --ink: #16232b;
  --ink-muted: #57686f;
  --accent: #8a6d1e;
  --accent-ink: #ffffff;
  --accent-soft: #f1e9d3;
  --good-bg: #e3f2ea;
  --good-fg: #1f6b45;
  --info-bg: #e7eef5;
  --info-fg: #2c5a82;
  --warn-bg: #fceedd;
  --warn-fg: #9a4e0d;
  --shadow: 0 1px 2px rgba(22, 35, 43, 0.06), 0 8px 24px -12px rgba(22, 35, 43, 0.18);
}
:root[data-theme="dark"] {
  --bg: #10171b;
  --surface: #182126;
  --surface-2: #1e282d;
  --border: #2b363b;
  --ink: #e7edee;
  --ink-muted: #93a3a8;
  --accent: #d9b65f;
  --accent-ink: #1b1404;
  --accent-soft: #2a2413;
  --good-bg: #123425;
  --good-fg: #7ad4a4;
  --info-bg: #16283a;
  --info-fg: #8fbde3;
  --warn-bg: #3a2a12;
  --warn-fg: #e3a85b;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 12px 32px -16px rgba(0, 0, 0, 0.55);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #10171b;
    --surface: #182126;
    --surface-2: #1e282d;
    --border: #2b363b;
    --ink: #e7edee;
    --ink-muted: #93a3a8;
    --accent: #d9b65f;
    --accent-ink: #1b1404;
    --accent-soft: #2a2413;
    --good-bg: #123425;
    --good-fg: #7ad4a4;
    --info-bg: #16283a;
    --info-fg: #8fbde3;
    --warn-bg: #3a2a12;
    --warn-fg: #e3a85b;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 12px 32px -16px rgba(0, 0, 0, 0.55);
  }
}

* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: 'Source Sans 3', system-ui, sans-serif;
  font-size: 15px;
  line-height: 1.5;
}
body {
  padding: 40px clamp(16px, 4vw, 56px) 72px;
}
a { color: inherit; }
.wrap { max-width: 1180px; margin: 0 auto; display: flex; flex-direction: column; gap: 36px; }

header.page { display: flex; flex-direction: column; gap: 6px; }
.eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--accent);
}
h1 {
  font-family: 'Archivo', sans-serif;
  font-weight: 700;
  font-size: clamp(26px, 3.4vw, 34px);
  margin: 0;
  text-wrap: balance;
  letter-spacing: -0.01em;
}
.sub { color: var(--ink-muted); font-size: 15px; max-width: 62ch; }

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.stat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px 18px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat .label {
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-muted);
  font-weight: 600;
}
.stat .value {
  font-family: 'JetBrains Mono', monospace;
  font-variant-numeric: tabular-nums;
  font-size: 24px;
  font-weight: 400;
}
.stat .value small { font-size: 13px; color: var(--ink-muted); font-family: 'Source Sans 3', sans-serif; }

section.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  overflow: hidden;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px;
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}
.panel-head h2 {
  font-family: 'Archivo', sans-serif;
  font-size: 17px;
  margin: 0;
  font-weight: 700;
}
.panel-head p { margin: 2px 0 0; color: var(--ink-muted); font-size: 13.5px; }
.panel-head .titles { display: flex; flex-direction: column; max-width: 46ch; }
.panel-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.reset-btn {
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-muted);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 7px 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color 120ms ease, color 120ms ease;
}
.reset-btn:hover { border-color: var(--accent); color: var(--accent); }
.reset-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.filter {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 7px 12px;
  min-width: 220px;
}
.filter svg { flex: none; opacity: 0.55; }
.filter input {
  border: none;
  background: transparent;
  outline: none;
  font: inherit;
  color: var(--ink);
  width: 100%;
}
.filter input::placeholder { color: var(--ink-muted); }

.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; min-width: 720px; }
thead th {
  position: sticky;
  top: 0;
  background: var(--surface-2);
  text-align: left;
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-muted);
  font-weight: 600;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
}
thead th:hover { color: var(--ink); }
thead th.sorted-asc::after { content: " \2191"; color: var(--accent); }
thead th.sorted-desc::after { content: " \2193"; color: var(--accent); }
tbody td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: var(--surface-2); }
tbody tr.group-start td { border-top: 2px solid var(--border); }
tbody tr.group-start:first-child td { border-top: none; }

.mono { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
.designator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 22px;
  padding: 0 6px;
  border-radius: 6px;
  background: var(--accent-soft);
  color: var(--accent);
  font-family: 'JetBrains Mono', monospace;
  font-size: 12.5px;
  font-weight: 400;
}
.muted { color: var(--ink-muted); font-size: 13px; }
.detail { color: var(--ink-muted); font-size: 12.5px; margin-top: 4px; max-width: 34ch; }

.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.chip.good { background: var(--good-bg); color: var(--good-fg); }
.chip.info { background: var(--info-bg); color: var(--info-fg); }
.chip.warn { background: var(--warn-bg); color: var(--warn-fg); }

.linkgroup { display: flex; flex-wrap: wrap; gap: 6px; }
.linkchip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 7px;
  font-size: 12.5px;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid var(--border);
  transition: border-color 120ms ease, background 120ms ease;
}
.linkchip:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.linkchip.verified {
  background: var(--good-bg);
  color: var(--good-fg);
  border-color: transparent;
}
.linkchip.verified:hover { filter: brightness(1.06); }
.linkchip.search {
  background: transparent;
  color: var(--ink-muted);
}
.linkchip.search:hover { border-color: var(--accent); color: var(--accent); }
.linkchip .dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor;
}

.price { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; font-weight: 400; }

.edit-cell { display: flex; align-items: center; gap: 6px; }
.edit-cell .cur { color: var(--ink-muted); font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.edit-cell input {
  font-family: 'JetBrains Mono', monospace;
  font-variant-numeric: tabular-nums;
  font-size: 14px;
  color: var(--ink);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 8px;
  width: 100%;
  min-width: 0;
}
.price-cell input { max-width: 84px; }
.stock-cell input { max-width: 150px; }
.edit-cell input:hover { border-color: var(--ink-muted); }
.edit-cell input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
.edit-cell input.edited { border-color: var(--accent); background: var(--accent-soft); }
.edited-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  flex: none;
  display: none;
}
.edit-cell input.edited ~ .edited-dot,
.edit-cell.is-edited .edited-dot { display: inline-block; }

.best-price-cell { display: flex; flex-direction: column; gap: 6px; min-width: 168px; }
.best-price-cell .row { display: flex; align-items: center; gap: 6px; }
.best-price-cell label {
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-muted);
  width: 38px;
  flex: none;
}
.best-price-cell select,
.best-price-cell input {
  font: inherit;
  font-size: 13.5px;
  color: var(--ink);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 8px;
  width: 100%;
  min-width: 0;
}
.best-price-cell input { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
.best-price-cell select.edited,
.best-price-cell input.edited { border-color: var(--accent); background: var(--accent-soft); }
.best-price-cell select:focus,
.best-price-cell input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

footer.note {
  color: var(--ink-muted);
  font-size: 12.5px;
  border-top: 1px solid var(--border);
  padding-top: 18px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
footer.note .legend { display: flex; gap: 14px; flex-wrap: wrap; }
footer.note .legend span { display: inline-flex; align-items: center; gap: 6px; }
footer.note .legend .dot { width: 8px; height: 8px; border-radius: 50%; }

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; }
}
</style>

<div class="wrap">
  <header class="page">
    <div class="eyebrow">Sourcing Dashboard</div>
    <h1>__BOARD_NAME__</h1>
    <p class="sub">__SUBTITLE__</p>
  </header>

  <div class="stats" id="stats"></div>

  <section class="panel">
    <div class="panel-head">
      <div class="titles">
        <h2>Sourced BOM</h2>
        <p id="bomSubhead"></p>
      </div>
      <div class="filter">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
        <input type="text" id="bomFilter" placeholder="Filter by designator, MPN, manufacturer…" />
      </div>
    </div>
    <div class="table-scroll">
      <table id="bomTable">
        <thead>
          <tr>
            <th data-key="designator">Ref</th>
            <th data-key="manufacturer">Manufacturer</th>
            <th data-key="mpn">MPN</th>
            <th data-key="footprint">Footprint</th>
            <th data-key="qty" class="mono">Qty</th>
            <th data-key="mating">Mating</th>
            <th data-key="terminal">Terminal</th>
            <th data-key="termQty">Term. Qty</th>
            <th data-key="awg">Wire Gauge</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head">
      <div class="titles">
        <h2>Supplier Comparison</h2>
        <p>Grouped by connector — base component, then mating housing, then terminal. Price and stock are editable.</p>
      </div>
      <div class="panel-actions">
        <div class="filter">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
          <input type="text" id="supFilter" placeholder="Filter by MPN, role…" />
        </div>
        <button class="reset-btn" id="resetPrices" type="button">Reset to sourced values</button>
      </div>
    </div>
    <div class="table-scroll">
      <table id="supTable">
        <thead>
          <tr>
            <th data-key="group">Group</th>
            <th data-key="mpn">MPN</th>
            <th data-key="role">Role</th>
            <th data-key="price" class="mono">Price (EUR)</th>
            <th data-key="stockDisplay" class="mono">Stock</th>
            <th>Suppliers</th>
            <th>Best Price</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </section>

  <footer class="note">
    <div class="legend" id="legend"></div>
    <div id="fxNote"></div>
  </footer>
</div>

<script>
const DATA = __DATA_JSON__;
const SUPPLIER_NAMES = __SUPPLIER_NAMES_JSON__;
const VERIFIED_SUPPLIERS = __VERIFIED_SUPPLIERS_JSON__;
const FX_NOTE = __FX_NOTE_JSON__;
const STORAGE_KEY = __STORAGE_KEY_JSON__;

function euro(n) {
  if (n === null || n === undefined) return "—";
  return "€" + n.toFixed(3);
}

function renderStats() {
  const bom = DATA.sourcedBom;
  const totalConnectors = bom.length;
  const resolved = bom.filter(r => r.matingStatus === "good").length;
  const customCable = bom.filter(r => r.matingStatus === "info").length;
  const stats = [
    { label: "Connectors", value: totalConnectors },
    { label: "Mating resolved (PN)", value: resolved + " / " + totalConnectors },
    { label: "Custom-cable mates", value: customCable + " / " + totalConnectors },
    { label: "Suppliers with verified data", value: VERIFIED_SUPPLIERS.length + " / " + SUPPLIER_NAMES.length,
      small: VERIFIED_SUPPLIERS.length ? VERIFIED_SUPPLIERS.join(", ") + " only" : "none" },
  ];
  document.getElementById("stats").innerHTML = stats.map(s => `
    <div class="stat">
      <div class="label">${s.label}</div>
      <div class="value">${s.value}${s.small ? ` <small>${s.small}</small>` : ""}</div>
    </div>`).join("");
  document.getElementById("bomSubhead").textContent =
    `${totalConnectors} connector${totalConnectors === 1 ? "" : "s"} — mating and terminal data resolved where a fixed part number exists`;
  document.getElementById("legend").innerHTML = `
    <span><span class="dot" style="background:var(--good-fg)"></span>Verified data (${VERIFIED_SUPPLIERS.join(", ") || "none"})</span>
    <span><span class="dot" style="background:var(--ink-muted)"></span>Search link only — site blocked automated access</span>
    <span><span class="dot" style="background:var(--info-fg)"></span>No fixed mating PN (custom cable)</span>`;
  document.getElementById("fxNote").textContent = FX_NOTE;
}

function matingChip(row) {
  if (row.matingStatus === "good") {
    return `<div><span class="chip good">${row.mating}</span></div>`;
  }
  return `<div><span class="chip info">${row.mating}</span><div class="detail">${row.matingDetail || ""}</div></div>`;
}

function renderBom(rows) {
  const tbody = document.querySelector("#bomTable tbody");
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td><span class="designator">${r.designator}</span></td>
      <td>${r.manufacturer}</td>
      <td class="mono">${r.mpn}</td>
      <td class="mono muted">${r.footprint}</td>
      <td class="mono">${r.qty}</td>
      <td>${matingChip(r)}</td>
      <td class="mono">${r.terminal}</td>
      <td class="muted">${r.termQty}</td>
      <td class="muted">${r.awg}</td>
    </tr>`).join("");
}

function linkChip(label, url) {
  if (!url) return "";
  const verified = VERIFIED_SUPPLIERS.includes(label);
  return `<a class="linkchip ${verified ? "verified" : "search"}" href="${url}" target="_blank" rel="noopener">
    <span class="dot"></span>${label}</a>`;
}

function loadOverrides() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); } catch (e) { return {}; }
}
function saveOverrides(ov) { localStorage.setItem(STORAGE_KEY, JSON.stringify(ov)); }

let lastSupRows = null;

function supplierOptions(selected) {
  const blank = `<option value="" ${!selected ? "selected" : ""}>Select…</option>`;
  const opts = SUPPLIER_NAMES.map(name =>
    `<option value="${name}" ${name === selected ? "selected" : ""}>${name}</option>`).join("");
  return blank + opts;
}

function renderSup(rows) {
  lastSupRows = rows;
  const tbody = document.querySelector("#supTable tbody");
  let lastGroup = null;
  tbody.innerHTML = rows.map(r => {
    const isGroupStart = r.group !== lastGroup;
    lastGroup = r.group;
    const priceEdited = r.price !== r.origPrice;
    const stockEdited = r.stockDisplay !== r.origStockDisplay;
    const supplierEdited = !!r.bestSupplier;
    const moqEdited = r.bestMoq !== "" && r.bestMoq !== undefined && r.bestMoq !== null;
    const links = SUPPLIER_NAMES.map(name => linkChip(name, r.links ? r.links[name] : null)).join("");
    return `
    <tr class="${isGroupStart ? "group-start" : ""}">
      <td>${isGroupStart ? `<span class="designator">${r.group}</span>` : ""}</td>
      <td class="mono">${r.mpn}</td>
      <td>${r.role}<div class="muted">${r.manufacturer}</div></td>
      <td>
        <div class="edit-cell price-cell">
          <span class="cur">EUR</span>
          <input type="text" inputmode="decimal" class="${priceEdited ? "edited" : ""}"
            data-rowkey="${r.rowKey}" data-field="price" value="${r.price.toFixed(3)}"
            aria-label="Price for ${r.mpn}">
          <span class="edited-dot" title="Manually edited"></span>
        </div>
      </td>
      <td>
        <div class="edit-cell stock-cell">
          <input type="text" class="${stockEdited ? "edited" : ""}"
            data-rowkey="${r.rowKey}" data-field="stock" value="${r.stockDisplay}"
            aria-label="Stock for ${r.mpn}">
          <span class="edited-dot" title="Manually edited"></span>
        </div>
      </td>
      <td><div class="linkgroup">${links}</div></td>
      <td>
        <div class="best-price-cell">
          <div class="row">
            <label for="sup-${r.rowKey}">Vendor</label>
            <select id="sup-${r.rowKey}" class="${supplierEdited ? "edited" : ""}"
              data-rowkey="${r.rowKey}" data-field="bestSupplier" aria-label="Best-price supplier for ${r.mpn}">
              ${supplierOptions(r.bestSupplier)}
            </select>
          </div>
          <div class="row">
            <label for="moq-${r.rowKey}">MOQ</label>
            <input id="moq-${r.rowKey}" type="number" min="1" step="1" placeholder="e.g. 10"
              class="${moqEdited ? "edited" : ""}"
              data-rowkey="${r.rowKey}" data-field="bestMoq" value="${r.bestMoq || ""}"
              aria-label="Minimum order quantity for ${r.mpn}">
          </div>
        </div>
      </td>
    </tr>`;
  }).join("");
}

document.addEventListener("change", (e) => {
  const el = e.target;
  if (!el.matches("[data-rowkey]")) return;
  const rowKey = el.dataset.rowkey, field = el.dataset.field;
  const row = DATA.supplierRows.find(r => r.rowKey === rowKey);
  if (!row) return;
  const ov = loadOverrides();
  ov[rowKey] = ov[rowKey] || {};
  if (field === "price") {
    const parsed = parseFloat(el.value.replace(",", "."));
    row.price = isNaN(parsed) ? row.price : Math.round(parsed * 1000) / 1000;
    ov[rowKey].price = row.price;
  } else if (field === "stock") {
    row.stockDisplay = el.value;
    ov[rowKey].stockDisplay = row.stockDisplay;
  } else if (field === "bestSupplier") {
    row.bestSupplier = el.value;
    ov[rowKey].bestSupplier = row.bestSupplier;
  } else if (field === "bestMoq") {
    row.bestMoq = el.value;
    ov[rowKey].bestMoq = row.bestMoq;
  }
  saveOverrides(ov);
  renderSup(lastSupRows);
});

document.getElementById("resetPrices").addEventListener("click", () => {
  localStorage.removeItem(STORAGE_KEY);
  DATA.supplierRows.forEach(r => {
    r.price = r.origPrice;
    r.stockDisplay = r.origStockDisplay;
    r.bestSupplier = "";
    r.bestMoq = "";
  });
  renderSup(lastSupRows || DATA.supplierRows);
});

function attachSort(tableId, data, renderFn) {
  const table = document.getElementById(tableId);
  let sortKey = null, sortDir = 1;
  table.querySelectorAll("th[data-key]").forEach(th => {
    th.addEventListener("click", () => {
      const key = th.dataset.key;
      sortDir = (sortKey === key) ? -sortDir : 1;
      sortKey = key;
      table.querySelectorAll("th").forEach(h => h.classList.remove("sorted-asc", "sorted-desc"));
      th.classList.add(sortDir === 1 ? "sorted-asc" : "sorted-desc");
      const sorted = [...data].sort((a, b) => {
        let av = a[key], bv = b[key];
        if (typeof av === "string") av = av.toLowerCase();
        if (typeof bv === "string") bv = bv.toLowerCase();
        if (av < bv) return -1 * sortDir;
        if (av > bv) return 1 * sortDir;
        return 0;
      });
      renderFn(sorted);
    });
  });
}

function attachFilter(inputId, data, renderFn) {
  const input = document.getElementById(inputId);
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { renderFn(data); return; }
    const filtered = data.filter(row => JSON.stringify(row).toLowerCase().includes(q));
    renderFn(filtered);
  });
}

// Stable identity per row + baseline values, so edits can be detected, persisted, and reset.
DATA.supplierRows.forEach(r => {
  r.rowKey = `${r.group}::${r.mpn}::${r.role}`;
  r.origPrice = r.price;
  r.stockDisplay = r.stockNote ? `${r.stock.toLocaleString()} (${r.stockNote})` : r.stock.toLocaleString();
  r.origStockDisplay = r.stockDisplay;
  r.bestSupplier = "";
  r.bestMoq = "";
});
(function applyStoredOverrides() {
  const ov = loadOverrides();
  DATA.supplierRows.forEach(r => {
    const o = ov[r.rowKey];
    if (!o) return;
    if (o.price !== undefined) r.price = o.price;
    if (o.stockDisplay !== undefined) r.stockDisplay = o.stockDisplay;
    if (o.bestSupplier !== undefined) r.bestSupplier = o.bestSupplier;
    if (o.bestMoq !== undefined) r.bestMoq = o.bestMoq;
  });
})();

renderStats();
renderBom(DATA.sourcedBom);
renderSup(DATA.supplierRows);
attachSort("bomTable", DATA.sourcedBom, renderBom);
attachSort("supTable", DATA.supplierRows, renderSup);
attachFilter("bomFilter", DATA.sourcedBom, renderBom);
attachFilter("supFilter", DATA.supplierRows, renderSup);
</script>
"""


def generate_dashboard(
    board_name,
    sourced_bom,
    supplier_rows,
    output_path,
    fx_rate=None,
    fx_date=None,
    fx_source=None,
    fx_from_currency="USD",
    supplier_names=None,
    verified_suppliers=None,
    subtitle=None,
):
    if supplier_names is None:
        seen = []
        for row in supplier_rows:
            for name in (row.get("links") or {}):
                if name not in seen:
                    seen.append(name)
        supplier_names = seen

    if verified_suppliers is None:
        verified_suppliers = ["DigiKey"] if "DigiKey" in supplier_names else []

    if subtitle is None:
        subtitle = ("Connector BOM, mating/terminal resolution, and multi-supplier pricing. "
                    "Generated from a live /bom source run.")

    if fx_rate is not None:
        fx_note = f"FX: 1 {fx_from_currency} = {fx_rate} EUR"
        if fx_source:
            fx_note += f" · {fx_source}"
        if fx_date:
            fx_note += f", {fx_date}"
    else:
        fx_note = "No currency conversion applied — all prices already in EUR"

    data_json = json.dumps({"sourcedBom": sourced_bom, "supplierRows": supplier_rows}, ensure_ascii=False)

    html = _HTML_TEMPLATE
    html = html.replace("__BOARD_NAME__", board_name)
    html = html.replace("__SUBTITLE__", subtitle)
    html = html.replace("__DATA_JSON__", data_json)
    html = html.replace("__SUPPLIER_NAMES_JSON__", json.dumps(supplier_names, ensure_ascii=False))
    html = html.replace("__VERIFIED_SUPPLIERS_JSON__", json.dumps(verified_suppliers, ensure_ascii=False))
    html = html.replace("__FX_NOTE_JSON__", json.dumps(fx_note, ensure_ascii=False))
    html = html.replace("__STORAGE_KEY_JSON__", json.dumps(_storage_key(board_name), ensure_ascii=False))
    html = html.replace("__ARCHIVO_BOLD__", _read_font_b64("archivo_bold"))
    html = html.replace("__SOURCESANS_REGULAR__", _read_font_b64("sourcesans_regular"))
    html = html.replace("__JBMONO_REGULAR__", _read_font_b64("jetbrainsmono_regular"))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python generate_dashboard.py <input.json> <output.html>")
        print("  input.json must contain: board_name, sourced_bom, supplier_rows,")
        print("  and optionally: output_path (ignored, use CLI arg), fx_rate, fx_date,")
        print("  fx_source, fx_from_currency, supplier_names, verified_suppliers, subtitle")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        payload = json.load(f)
    payload.pop("output_path", None)
    out = generate_dashboard(output_path=sys.argv[2], **payload)
    print("Written:", out)
