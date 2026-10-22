# Board T — fresh verified desk, 22–28 Oct 2026 (session `arena/4ec1fc72-olbg4`)

Live (after merge): https://buffedlizard55-lab.github.io/OLBG4/session-4ec1fc72/

## What this is
A fresh, session-scoped desk built only from official sources read on **2026-10-22**:
49 NHL fixtures, 29 NBA fixtures and MLB World Series Games 1–3 are priced with our
own match-winner, handicap and match-total lines; 16 PDC European Championship
Round One ties are fixture-verified but deliberately unpriced (no verified
quantitative input for both players — see Flagged page).

- **97 rows** (81 priced, 16 flagged fixtures), **2 High-confidence picks**, 24 flagged items.
- High = model probability ≥0.66 **and** originated price inside **−250…+10,000**
  American. Two picks above that band priced shorter than −250 (NY Rangers −253 on
  26 Oct; Edmonton −397 on 28 Oct at model 0.689/0.768) were capped at Medium and
  flagged — no heavy-chalk Highs were promoted.
- High predictions: Edmonton Oilers moneyline vs Detroit (26 Oct, model 0.670, our
  price 1.436 / −229, 118 words) and Minnesota Wild moneyline at Vancouver
  (25 Oct, model 0.664, 1.449 / −223, 111 words). Each names a player with his
  official NHL leader line, current form and recent history, and the exact selection.

## Reproduce / verify
```bash
python3 session-4ec1fc72/build.py    # regenerates data/session-4ec1fc72/data.json + this site
python3 session-4ec1fc72/verify.py   # official-source, odds-window, prediction and link gates
python3 scripts/audit_publication.py --check
```

## Sources (official only; exact URL stored per row)
NHL.com schedule/standings + api-web.nhle.com score feeds · NBA.com schedule/standings ·
MLB Stats API schedule/standings (statsapi.mlb.com) · PDC pdc.tv European Championship
schedule article · WST wst.tv (coverage attempt). OLBG was taxonomy reference only —
no OLBG price or tip is used anywhere (its hub rows publish no prices).

Excluded per brief: soccer, boxing, UFC/MMA, American football, hurling, horse
racing, cycling, specials. All other in-scope sports are accounted for on the
Coverage page; those not refreshed are flagged, not silently omitted.
