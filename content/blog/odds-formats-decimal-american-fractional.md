---
title: Odds Formats — Decimal, American, and Fractional
description: Convert between decimal, American, and fractional odds. Reference table and formulas for Hong Kong, Malaysian, and Indonesian formats.
slug: odds-formats-decimal-american-fractional
date: 2026-02-12
keywords: odds converter, decimal odds, American odds, fractional odds
---

Bookmakers worldwide display prices differently. A disciplined ledger stores one **canonical decimal** internally while letting you enter bets in whatever format you see on screen.

## Decimal (European)

Total return per unit stake including stake. Decimal 2.50 → win £1.50 profit on £1 staked.

**Profit** = stake × (decimal − 1)

## American (moneyline)

Positive (+150): profit on a £100 stake. +150 → decimal 2.50.

Negative (−200): stake needed to win £100. −200 → decimal 1.50.

Conversion:

- If American > 0: decimal = 1 + American/100
- If American < 0: decimal = 1 + 100/|American|

## Fractional (UK)

6/4 means win £6 for every £4 staked. Decimal = 1 + numerator/denominator = 2.50.

Some sites show "6/4" as the win fraction only; always confirm whether stake is included in display.

## Asian formats

| Format | Example | Decimal |
|--------|---------|---------|
| Hong Kong | 0.85 | 1.85 |
| Malaysian + | 0.85 | 1.85 |
| Malaysian − | −0.85 | 1 + 1/0.85 ≈ 2.176 |
| Indonesian + | 1.50 | 2.50 |
| Indonesian − | −1.50 | 1 + 1/1.50 ≈ 1.667 |

## Why normalisation matters

Mixing formats in one spreadsheet causes silent errors — American minus signs, fractional denominators, or treating HK as decimal. Software should convert on input and never lose precision.

## Practical tip

Set a **default entry format** in your tracker matching your primary bookmaker, but verify decimal equivalent on save until the habit sticks.

mybetrecord accepts all listed formats and stores decimal odds for every report and Kelly calculation.
