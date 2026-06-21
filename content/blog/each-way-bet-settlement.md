---
title: Each-Way Bet Settlement Explained
description: How each-way bets pay on the win and place parts. Worked examples with place fractions and dead-heat rules.
slug: each-way-bet-settlement
date: 2026-02-19
keywords: each way bet calculator, each way settlement, place terms
---

An **each-way** bet is two bets in one: half the stake on the selection to win, half on it to place (finish in the places per book terms). Settlement math trips up many spreadsheets.

## Structure

Total stake *S* splits:

- Win part: *S*/2 at win odds
- Place part: *S*/2 at place odds

Place odds = 1 + (win odds − 1) × **place fraction**

Common place fraction: **1/4** or **1/5** of win odds.

## Example — winner

£20 each-way (£10 win + £10 place) at 10.00 win odds, 1/4 place terms.

- Win part pays: 10 × £10 = £100 return (£90 profit)
- Place odds: 1 + (10 − 1) × 0.25 = 3.25 → 3.25 × £10 = £32.50 return (£22.50 profit)
- **Total profit** = £90 + £22.50 = **£112.50**

## Example — placed only

Same bet, horse finishes second (places paid, no win):

- Win part loses: −£10
- Place part wins: £22.50 profit as above
- **Net profit** = **£12.50**

## Example — unplaced

Both parts lose: **−£20** (full stake).

## Exchange and special cases

Exchanges often separate win and place markets — not a single each-way ticket. Dead heats reduce place returns. Rule 4 deductions apply on racing win parts.

Always record **each_way=true** and **place_fraction** in your ledger so software applies the same formula every time.

## Track each-way in mybetrecord

Toggle each-way on bet entry, set place fraction, and let settlement recompute profit when you mark win/loss/placed outcomes.
