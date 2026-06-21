---
title: Kelly Criterion Explained for Bettors
description: The Kelly criterion sizes stakes from edge and odds. Learn the formula, fractional Kelly, and a numeric example you can verify.
slug: kelly-criterion-explained
date: 2026-01-29
keywords: Kelly criterion calculator, Kelly stake, optimal bet sizing
---

The **Kelly criterion** answers one question: given your estimated edge, what fraction of bankroll should you stake to maximise long-term growth — without risking ruin from one bad run?

## The formula (decimal odds)

For decimal odds *O* and win probability *p*:

**Kelly fraction** = (*O* × *p* − 1) / (*O* − 1)

Stake = Kelly fraction × bankroll (often multiplied by a safety factor).

## Numeric example

You believe a team has a 55% chance to win at decimal odds 2.00 (even money).

- *p* = 0.55, *O* = 2.0
- Kelly = (2.0 × 0.55 − 1) / (2.0 − 1) = 0.10 / 1.0 = **10% of bankroll**

On a £1,000 bankroll, full Kelly suggests £100. Most bettors use **half Kelly** (5%, £50) or **quarter Kelly** to reduce variance.

## Edge from implied odds

If your "fair" price is decimal 1.91 (implied 52.4%) and you get 2.00 (implied 50%), you have positive edge. Kelly converts that edge plus offered odds into a stake size.

## Why not always full Kelly?

Full Kelly maximises geometric growth in theory. In practice:

- Your *p* estimate is wrong more often than you think
- Simultaneous bets correlate (same league, same day)
- Psychological drawdowns cause abandoning the system

Fractional Kelly (0.25–0.5×) is standard among professional bettors.

## Common mistakes

- Using Kelly when you have no genuine edge estimate
- Applying Kelly to correlated parlays as independent events
- Ignoring bankroll that is not truly "risk capital"

## Track Kelly in mybetrecord

Set bankroll and Kelly multiplier in settings. Enter personal implied odds on each bet to see a recommended stake alongside your actual stake — a sanity check, not a command.
