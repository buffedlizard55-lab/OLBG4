# OLBG.com reverse-engineering note

Scope of this note: **structure only** — sport taxonomy, URL grammar and the anatomy of a tips
listing. It is written so that our own coverage can be mapped onto OLBG's categories. No OLBG price,
tip, prediction or community percentage is copied into this repository, and none is used as a model
input.

Evidence captured on **21 October 2026**. Machine-readable copy: `session-4afef1af/data/olbg-taxonomy.json`.

## 1. Compliance boundary

`https://www.olbg.com/robots.txt` disallows, among others:

```
/api/
/sports/
/events.php
/tips/hot
/newbg/
/storage/app/json_data/*
```

and blocks a long list of crawler user agents including `Python-urllib`, `Wget`, `WebZip`,
`Teleport` and `EmailCollector`.

The betting-tips hub pages used for this note are not disallowed for a normal browser user agent.
The project therefore:

* reads a handful of **public hub pages** with a normal single-page fetch,
* never requests the disallowed paths,
* performs no bulk crawl, stores no OLBG content beyond the structural facts quoted here,
* uses OLBG only as a taxonomy reference.

## 2. URL grammar

```
hub:   https://www.olbg.com/betting-tips/<Sport>/<sport_id>
event: https://www.olbg.com/betting-tips/<Sport>/<Region>/<Competition>/<Event_slug>/<sport_id>?event_id=<event_id>
```

Captured examples:

| URL | Notes |
|---|---|
| `https://www.olbg.com/betting-tips/Basketball/4` | sport hub; id 4 = Basketball |
| `https://www.olbg.com/betting-tips/Basketball/NBA/NBA/MIL_Bucks_@_WAS_Wizards/4?event_id=534889` | NBA event; `@` slug form |
| `https://www.olbg.com/betting-tips/Basketball/European/Euroleague/Hapoel_Tel_Aviv_vs_Virtus_Bologna/4?event_id=535919` | EuroLeague; `_vs_` slug form |
| `https://www.olbg.com/betting-tips/Football/UK/England_Premier_League/Chelsea_v_Tottenham/1?event_id=2043412` | Football; id 1 |
| `https://www.olbg.com/betting-tips/Horse_Racing/UK/Newmarket/2:25_Newmarket/2?event_id=1134655` | Horse racing; id 2 |
| `https://www.olbg.com/betting-tips/Gaelic_Football/All_Gaelic_Football/All_Events/St_Finbarrs_v_Nemo_Rangers/25?event_id=3530` | Gaelic football; id 25 |

**The numeric id is mandatory.** `https://www.olbg.com/betting-tips/Basketball` returns HTTP 404;
`https://www.olbg.com/betting-tips/Basketball/4` resolves. This is the single most important
structural finding for any integration: a hub URL built without the sport id silently 404s.

## 3. Page anatomy

A sport hub renders:

* the sport name, a **SPORTS MENU** filter, a **Show Expired Events** toggle and a
  **Customise Tips** control;
* a list of upcoming events. Each row carries the event link (`?event_id=`), the competition label
  (`NBA`, `Euroleague`, `Euro Cup`, `Basketball Champions League`, `Korea KBL`), the day and local
  start time, the featured selection, the market label (`Money Line`, `Full Time Result`,
  `Daily Racing`), `n/m Win Tips` with a percentage, a comment count and, where present, an expert
  count;
* competition hubs one level deeper, e.g. `/Basketball/NBA/4`, `/Basketball/WNBA/4`,
  `/Basketball/European/Euroleague/4`, `/Basketball/Other/Korea_KBL/4`.

The tips hub (`/betting-tips`) mixes every sport and is ordered by community tip volume by default,
not by start time — an important trap when reconstructing a schedule.

## 4. Findings

1. **Sport id is part of the path.** `/betting-tips/<Sport>/<id>`, not `/betting-tips/<Sport>`.
2. **Slugs are inconsistent.** `MIL_Bucks_@_WAS_Wizards`, `Chelsea_v_Tottenham` and
   `Hapoel_Tel_Aviv_vs_Virtus_Bologna` coexist. The slug cannot be parsed for venue or home/away.
3. **Two identifiers.** The path id is the *sport* id (4 for every basketball event); `event_id` is
   the *fixture* id (e.g. 534889). Both are needed to deep-link.
4. **No prices on the listing.** Rows expose tip share, comments and experts, not odds. The Value
   Rating described on the page compares a selection's odds with its tip share, which implies prices
   live on the event/bookmaker layer. OLBG is therefore not usable as a price source, which is
   consistent with the brief's requirement that we originate our own lines.
5. **Breadth exceeds official feeds.** OLBG's basketball hub covers WNBA, EuroLeague, EuroCup,
   Basketball Champions League and Korea KBL alongside the NBA. Our official-feed ingestion covers
   the NBA only. Where the two overlap they agree on date and matchup — for example
   `MIL Bucks @ WAS Wizards` on 21 Oct 2026 appears both in OLBG's listing and in the NBA schedule
   feed at 23:10Z (19:10 ET).
6. **The exclusion list is not an OLBG category.** OLBG groups sports its own way; the owner's
   exclusions (soccer, American football, boxing, UFC/MMA, hurling, Gaelic football, horse racing,
   cycling, specials) had to be applied on top of OLBG's taxonomy.

## 5. What we did with it

* Mapped our three ingested leagues onto OLBG's sport ids: Basketball 4, Ice Hockey (id not captured
  in this session), Baseball (id not captured).
* Published a coverage table on the dashboard's Sources page that marks every sport as *ingested*,
  *not ingested* or *excluded*, using the owner's scope, not OLBG's categories.
* Kept OLBG out of the data path entirely: fixtures, results, records and form come from the NBA,
  NHL and MLB feeds documented in `docs/sources.md`.

## 6. Open questions for review

* Gaelic football is treated as out of scope because the owner excluded both "football" and
  "hurling". If Gaelic football should be included, this is the decision to revisit.
* The Ice Hockey and Baseball OLBG sport ids were not captured in this session; the dashboard marks
  them as not captured rather than guessing.
* OLBG's own competition coverage inside basketball is wider than the NBA. Expanding official-feed
  coverage to EuroLeague/WNBA would need a league-owned feed that can be verified.
