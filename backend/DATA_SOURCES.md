# Data Sources

Every figure the app displays comes from a real, verifiable source. This
document records where each series comes from, how it is validated, and how to
re-check it.

## Background: why this document exists

An earlier version of the seed scripts silently fell back to synthetic data
when their API calls failed:

- `seed_bitcoin.py` requested 1825 days from CoinGecko. The free tier rejects
  ranges beyond 365 days, so the call always failed and the script fell back to
  a `random.uniform(-0.08, 0.08)` daily random walk seeded at EUR 1000. The
  database ended up with a maximum "Bitcoin" price of EUR 9,314 for a period
  when BTC actually traded above EUR 80,000.
- `seed_pprs.py` invented ten plausible-looking fund names with fabricated
  ISINs, and generated their performance from a hardcoded average return plus
  noise.

Both failures were silent: the database looked populated and healthy. The
current scripts have **no synthetic fallback** and exit non-zero if real data
cannot be obtained.

## Bitcoin: BTC/EUR daily closes

- **Source:** Bitstamp public OHLC API (`/api/v2/ohlc/btceur/`), no API key.
- **Coverage:** 2017-01-01 to present, ~3,500 daily closes.
- **Fetcher:** `services/bitcoin_history.py`
- **Seed:** `python data/seeds/seed_bitcoin.py [--refresh]`

Rejected alternatives:

| Source | Why not |
|---|---|
| CoinGecko (free) | Rejects ranges > 365 days (error 10012) |
| Kraken OHLC | Caps at ~720 candles regardless of `since` |

Validation before any write (`validate_prices`): at least 1,000 daily points,
every price within EUR 100–1,000,000, and the newest point no more than 7 days
old.

## PPR funds: daily NAV (valor da unidade de participação)

- **Source:** Optimize Investment Partners' published daily NAV series, read
  from the chart endpoint on their public fund pages.
- **Coverage:** 4 funds, 2008-09-25 to present, 15,196 NAV observations.
- **Fetcher:** `services/ppr_history.py`
- **Seed:** `python data/seeds/seed_pprs.py [--refresh]`

| Fund | ISIN | History from |
|---|---|---|
| Optimize PPR Ativo | PTOPZAHM0003 | 2008-09-25 |
| Optimize PPR Equilibrado | PTOPZBHM0002 | 2008-09-25 |
| Optimize PPR Moderado | PTOPZDHM0000 | 2010-08-19 |
| Optimize PPR Agressivo | PTOPZEHM0017 | 2018-12-31 |

Rejected alternatives:

| Source | Why not |
|---|---|
| Investing.com | HTTP 403 to scripted requests (Cloudflare). A **visible, non-headless** Chrome session does get through, but headless is detected — so it cannot run on a server or in CI. Usable as a periodic manual export only. See "Investing.com fund naming" below before trusting a fund's identity. |
| APFIPP calculator API | Covers 58 PPR funds across all 9 major managers, ~20 years, including inactive funds — but returns only two aggregate numbers (effective + annualised return) per query, not a time series. Cannot populate a chart. |
| IMGA charts API | Real daily series for 13 PPR funds (IMGA + EuroBic), but rebased to 10,000 rather than actual NAV, and history starts 2018–2021. |
| BPI | OutSystems JS app; no reachable JSON endpoint without a browser. |
| CMVM | OutSystems JS app; would need a headless browser. |
| tools.morningstar.pt | Host does not resolve. |

This is a real **observed daily series**, not interpolation between annual
figures. That distinction matters: volatility, Sharpe, Sortino and maximum
drawdown are only meaningful when computed from the real path.

`taxa_gestao` is deliberately left NULL. The published NAV is already net of
management fees, and the fee is not machine-readable from the source; storing
a guessed figure would misstate a real product's costs.

### Investing.com fund naming

Investing.com lists Portuguese PPR funds under **outdated names**. Its page
for ISIN `PTYPJDLM0002` is titled "BPI Reforma Valorização A PPR/OICVM", a
name that appears in neither the CMVM register nor APFIPP — both list only
"BPI Smart" funds. The fund was evidently renamed and Investing.com kept the
old title.

Identity was established by matching returns rather than names. Measured to
2025-12-31, the Investing.com series gives 1y 1.53%, 2y 5.36%, 3y 6.73%.
Against CMVM's four BPI funds:

| CMVM fund | 1y | delta |
|---|---|---|
| **BPI Smart Dinâmico** | **1.53** | **0.00** |
| BPI Smart Obrigações | 2.01 | 0.48 |
| BPI Smart Moderado | 5.03 | 3.50 |
| BPI Smart Ações | −5.40 | 6.93 |

So `PTYPJDLM0002` is **BPI Smart Dinâmico** (CMVM `NUM_FUN` 781). The 2025
calendar-year return computed from the series (+1.53%) independently equals
CMVM's published 1-year figure.

A related trap: APFIPP lists three "BPI Smart Dinâmico" classes with unit
values around 5.00, while this series runs 8.02 → 9.14. That is not a
different fund. CMVM shows five records sharing `NUM_FUN` 781 — one fund,
five share classes — of which only the original carries history; the four
newer classes launched at a base of 5.00 and report no returns yet. The
series itself contains no jump greater than 15%, confirming no rebase.

**Rule: never identify a fund from an Investing.com page title.** Confirm it
by matching returns against the CMVM register, which is keyed by `NUM_FUN`
and is the regulator's own record.

All four BPI PPR funds have been identified by return-matching. Note that the
listing-page titles are outdated but the **historical-data page titles carry
the current names**, which independently corroborate every match:

| Listing title (outdated) | ISIN | CMVM identity | 1y Δ | avg Δ |
|---|---|---|---|---|
| BPI Reforma Valorização | PTYPJDLM0002 | **BPI Smart Dinâmico** | 0.00pp | 0.10pp |
| BPI Reforma Investimento | PTYPIQLM0008 | **BPI Smart Moderado** | 0.01pp | 0.06pp |
| BPI Reforma Obrigações | PTYPIRLM0007 | **BPI Smart Obrigações** | 0.00pp | 0.05pp |
| BPI Reforma Global Equities | PTYPIEHM0024 | **BPI Smart Ações** | 0.01pp | 0.17pp |

Every match is unambiguous: the runner-up candidate is 10–25x worse in each
case. Note how badly a name-based guess would have failed — "Reforma
Investimento" is *Moderado*, and "Reforma Global Equities" is *Ações*, not
the equity-sounding "Investimento".

BPI Smart Obrigações carries **5,000 daily rows back to 2006-05-12**, the
deepest PPR series found from any source.

### Why the BPI series stop on 2026-07-01: the SMART rebrand

All four BPI series stop at **2026-07-01**. This is not an Investing.com
problem and not a fetch artifact -- the listing page quotes Optimize Ativo at
21.633 and Agressivo at 17.159, matching our own 2026-08-27 values exactly,
and both the JSON API and the rendered table agree on the same cut-off for
BPI.

The cause is a **rebrand effective 3 July 2026**. BPI Gestão de Ativos
renamed its "BPI Reforma" PPR range to "BPI SMART", alongside changes to each
fund's investment policy. Participants were notified and given until 30 June
2026 to redeem free of charge if they disagreed.

This is the same mapping the return-matching produced, arrived at
independently:

| Old name (still on Investing.com) | New name from 2026-07-03 |
|---|---|
| BPI Reforma Valorização | BPI SMART Dinâmico |
| BPI Reforma Investimento | BPI SMART Moderado |
| BPI Reforma Obrigações | BPI SMART Obrigações |
| BPI Reforma Global Equities | BPI SMART Ações |

Corroborating details:

- The **ISINs are unchanged** (PTYPJDLM0002 still resolves to the fund now
  called BPI SMART Dinâmico), so these are renames, not new funds.
- Investing.com's own historical-data page titles already show the SMART
  names while its listing page still shows the old ones.
- The Morningstar ticker for BPI SMART Ações, `0P0001ITBQ`, is the same
  ticker Investing.com reports for "BPI Reforma Global Equities".
- The last NAV in the series, 9.143, is quoted elsewhere as the value on
  2026-07-03 -- the changeover date itself.
- BPI's page for BPI SMART Dinâmico gives "Data de Início de Actividade
  03-07-2026" and is open for subscriptions from EUR 1.

**The funds are alive and open.** Investing.com simply stopped updating these
records at the rename and has not carried the series forward under the new
names, so its BPI data is a closed historical archive ending 2026-07-01.

Consequences for seeding:

- The pre-rebrand history is real and usable, and BPI SMART Obrigações
  carries 5,000 rows back to 2006.
- It cannot be kept current from this source. Investing.com's Portugal
  listing carries no BPI SMART records -- the three "Smart" entries on it are
  "Smart Invest", an unrelated manager -- and the post-rebrand ISINs
  (PTBG2OHM0004, PTBG2QHM0002, PTBG2WHM0004) all return 404 there.

### Searching for a live BPI feed: what was tried

No automatable daily source for the BPI SMART funds has been found yet.

| Source | Result |
|---|---|
| bancobpi.pt fund pages | OutSystems app, no NAV endpoint in the HTML |
| bancobpi.pt `/cotacoes` | Has a PPR option in its instrument dropdown, but the native `<select>` sits behind a custom widget that resists scripted selection |
| Investing.com, new ISINs | 404 -- only the pre-rebrand records exist |
| big.pt `/Reports/FundInfoDetails/Index/{ISIN}` | Serves BPI funds by ISIN and offers a "Histórico de Cotações" link, but returns "Fundo não encontrado" for both the old and new PPR ISINs |
| stockevents.app | Carries `PTBG2OHM0004.FUND` (BPI SMART Ações P) live at EUR 5.15 with an interactive chart, but exposes no downloadable series |

Two observations worth carrying forward:

- The new share classes trade around EUR 5.15, consistent with the four
  newly-created classes under CMVM `NUM_FUN` 781 launching at a base of 5.00.
  A post-rebrand series will therefore **not** continue the old 9.14 series
  numerically, even though the ISIN of the original class is unchanged.
- big.pt's ISIN-keyed URL pattern works for other BPI funds (verified with
  PTYPIALM0006, BPI Renda Trimestral), so it is worth re-checking once the
  SMART funds have been trading longer.
- The investment policies changed on the same date, so pre- and post-rebrand
  performance are not strictly the same strategy. Any chart spanning
  2026-07-03 should say so.

## Alves Ribeiro: Investing.com as a last-resort source

Alves Ribeiro PPR (EUR 372m, #4 by AUM) has no usable manager feed:

- `investalvesribeiro.pt` does not resolve.
- Banco Invest (same group) exposes a REST fund API at
  `bancoinvest.pt/restapi/GetFundosGestaoList_ByFilters` that returns the
  fund with a **current** NAV and dated quote, but no historical series and
  no per-fund history endpoint. Useful for a freshness cross-check, useless
  for backtesting.

`services/investing_history.py` therefore pulls it from Investing.com:
**5,000 daily NAV points, 2006-03-13 to present**, in real EUR. Verified
against CMVM at 2025-12-31 across five horizons -- 1y 4.77 vs 4.77 exactly,
10y 4.74 vs 4.67, mean deviation 0.06pp.

The cost is that this fetcher **cannot run headless or on a server**, so it
is a manual periodic refresh rather than part of the scheduler. It is opt-in:

```bash
python data/seeds/seed_pprs.py --refresh --with-investing
```

Cloudflare rate-limits rapid successive requests, so the fetcher re-warms on
the fund page and backs off between attempts. A blocked request raises rather
than seeding a partial series.

### Scope limitation

The catalogue covers three fund managers, roughly 19% of the PPR market by
assets under management. Extending coverage means a separate integration per
manager. The app should not imply it compares the whole Portuguese PPR market.

Remaining gaps, in order of size:

| Manager | Share | Status |
|---|---|---|
| BPI | ~23% | Funds identified, but renamed to "BPI SMART" on 2026-07-03 and no live feed found for the new names |
| Caixa | ~8% | CGD's quotes page is JS-rendered with no reachable JSON endpoint |
| Casa de Investimentos | ~7% | **Reachable**: an open JSON API at `casa-de-investimentos-api.vercel.app/api/get-excel-data?worksheet=grafico_founders` returns 1,527 daily points from 2020-10-01, indexed to 100. Identified by return-matching as the fund CMVM registers as "SAVE & GROW PPR/OICVM" (1y 5.46 vs 5.46). Not yet seeded. |

### Market context and fund ranking

The correct ranking metric is **assets under management (AUM)**, not trading
volume: PPRs are not exchange-traded, so there is no order-book volume. AUM is
what APFIPP itself uses to size the industry.

APFIPP puts the total PPR market at **EUR 5.56bn — 19.6% of all Portuguese
funds, the single largest category**. The 25 PPR funds listed on one page of
Investing.com sum to EUR 3.9bn, ~70% of the market, so a top-10 list is
already broadly representative.

Largest PPR funds by AUM (Investing.com, Aug 2026):

| # | Fund | AUM |
|---|---|---|
| 1 | BPI Reforma Investimento PPR | EUR 650.5m |
| 2 | IMGA Poupanca PPR - A | EUR 404.3m |
| 3 | IMGA Poupanca PPR - R | EUR 404.3m |
| 4 | Alves Ribeiro PPR | EUR 372.6m |
| 5 | Casa Global Value PPR Founders | EUR 371.4m |
| 6 | BPI Reforma Obrigacoes PPR | EUR 355.7m |
| 7 | Caixa Moderado PPR | EUR 309.1m |
| 8 | BPI Reforma Valorizacao PPR | EUR 224.2m |
| 9 | Caixa Arrojado PPR | EUR 141.3m |
| 10 | Optimize Capital Reforma PPR Agressivo | EUR 103.5m |

Note that several entries are share classes of the same product (IMGA A/R),
so a top-10 list should deduplicate by share class.

By manager: BPI EUR 1,281m, IMGA EUR 921m, Caixa EUR 450m. Adding BPI and
IMGA would take coverage from ~3.5% to roughly 40% of the market.

## PPR funds: IMGA and EuroBic performance index

- **Source:** the chart API behind charts.imga.pt (`apicharts.imga.pt`), the
  same one IMGA uses on its own fund pages. No key, no browser required.
- **Coverage:** 6 funds, 2003-05-06 to present, 19,012 observations.
- **Fetcher:** `services/imga_history.py`

| Fund | History from |
|---|---|
| IMGA Poupanca PPR | 2003-05-06 |
| IMGA Investimento PPR Acoes | 2006-01-11 |
| EuroBic PPR Ciclo de Vida -34 | 2018-10-19 |
| EuroBic PPR Ciclo de Vida 35-44 | 2018-10-18 |
| EuroBic PPR Ciclo de Vida 45-54 | 2018-10-16 |
| EuroBic PPR Ciclo de Vida +55 | 2018-10-15 |

**This series is a performance index rebased to 10,000, not a unit value in
EUR.** Returns, volatility, Sharpe, Sortino and drawdown are unaffected
because they depend only on ratios between points, but the stored numbers are
not unit prices. Such funds are marked `(indice)` in `categoria` and carry no
ISIN, and the disclaimer says so.

Fund ids are verified against their expected names on every fetch, so a
renumbering upstream fails loudly instead of attaching one fund's history to
another's name. Two caveats found while integrating: `code` must be sent as a
string (an integer is rejected), and the obvious-looking id for IMGA Poupanca
PPR (48837) returns an empty series -- the populated one is 61601.

The CAT share classes (61602, 61604) duplicate the funds above with a shorter
history starting 2021, and IMGA Crescimento (63100/63101) returns nothing, so
none are seeded.

## CMVM Portal do Investidor (reference, not a series)

`investidor.cmvm.pt` exposes the regulator's PPR comparator through an
OutSystems data action:

    POST /PInvestidor/screenservices/PInvestidor/Comparator/PPRList/DataActionGetPPRs

It returns **all 167 PPR funds** with YTD/1/2/3/5/10-year returns, the TEC
(taxa de encargos correntes), risk class and managing entity, and it is
callable with a plain POST -- no browser needed -- once the OutSystems
`versionInfo` tokens are supplied. `MaxRecords` controls the page size.

It carries **no NAV time series**, so it cannot drive the chart. It is
valuable as an authoritative reference for fund discovery, fee data (the TEC
this project currently leaves NULL) and as a second cross-check on returns.
Not yet integrated.

## Verification

```bash
python scripts/verify_ppr_data.py
```

Cross-checks the annualised returns implied by the stored NAV series against
the figures **APFIPP** publishes for the same funds — an independent source
from the fund manager — and spot-checks Bitcoin against known historical
prices.

Returns are compared on APFIPP's own as-of date, parsed from its table header.
Comparing a return measured today against one published weeks earlier produces
large spurious differences on short horizons.

Last run (APFIPP as of 2026-08-07) — all 30 return checks within 0.1pp,
every 1-year figure exact:

| Fund | 1y implied / published | 3y | 5y |
|---|---|---|---|
| Optimize Ativo | 17.00 / 17.00 | 9.32 / 9.32 | 3.82 / 3.86 |
| Optimize Equilibrado | 10.49 / 10.49 | 7.11 / 7.15 | 2.34 / 2.36 |
| Optimize Moderado | 7.07 / 7.07 | 6.64 / 6.73 | 2.26 / 2.27 |
| Optimize Agressivo | 33.55 / 33.55 | 13.17 / 13.11 | 5.52 / 5.62 |
| IMGA Poupanca | 5.28 / 5.28 | 5.04 / 5.08 | 0.48 / 0.49 |
| IMGA Investimento | 8.70 / 8.70 | 6.87 / 6.94 | 1.97 / 1.98 |
| EuroBic -34 | 11.37 / 11.37 | 8.21 / 8.17 | 3.07 / 3.08 |
| EuroBic 35-44 | 10.42 / 10.42 | 7.83 / 7.81 | 2.91 / 2.92 |
| EuroBic 45-54 | 6.75 / 6.75 | 6.00 / 5.99 | 1.59 / 1.58 |
| EuroBic +55 | 3.28 / 3.28 | 4.05 / 4.07 | 0.13 / 0.11 |

APFIPP lists the EuroBic lifecycle funds under ABANCA, which acquired
EuroBic, so the verifier maps that manager name explicitly.

## Scheduled updates

`services/data_refresh.py` re-fetches a 30-day trailing window daily and
upserts it, reusing the same validated fetchers as the seeds so the live data
cannot drift onto a different source. A failed refresh leaves existing rows
untouched. Wired into `services/scheduler.py`.
