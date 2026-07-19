# Audit: Para-Sport Events in Athletics/Swimming Historical vs Recent-Form Data

Date: 2026-07-19
Scope: `data/historical/by_sport/medals_2018_by_sport.csv`, `data/historical/by_sport/medals_2022_by_sport.csv`,
`data/olympics/medals_2020.csv`, `data/olympics/medals_2020_swimming.csv`,
`data/olympics/medals_2024.csv`, `data/olympics/medals_2024_swimming.csv`,
`data/world_athletics/medals_2022.csv`, `data/world_athletics/medals_2025.csv`,
`data/world_aquatics/medals_2022.csv`, `data/world_aquatics/medals_2025.csv`

## Conclusion

**Confirmed bug — the model's Athletics/Swimming blend mixes two data sources that measure
different things.** The 40%-weighted "Commonwealth Games history" component includes para-sport
medals combined with standard medals as a single undifferentiated total. The 60%-weighted "recent
form" component (Olympics/World Championships) is standard-only by construction — Paralympic and
World Para Athletics/Swimming Championships are structurally separate competitions (different
host cities, different dates, never scraped for this project) and cannot appear in it. Because
16/59 (27%) of Glasgow 2026 athletics events and 14/56 (25%) of swimming events are para events,
this is not a marginal contamination — it is large enough to materially distort predicted shares
for any country whose para-sport strength diverges from its standard-sport strength, and the model
currently has no way to know the two halves of its 60/40 blend disagree about what "Athletics" even
means.

## Ground truth: standard vs para event split (Task item 1)

Fetched Wikipedia's "Athletics/Swimming at the 20XX Commonwealth Games" pages directly.

| Games | Sport | Total gold events | Standard | Para | Source quote |
|---|---|---|---|---|---|
| Birmingham 2022 | Athletics | 58 | 48 | 10 | "spread across 58 events (including 10 para athletics events)" |
| Birmingham 2022 | Swimming | 52 | 40 | 12 | "spread across fifty-two events (including twelve parasport events)" |
| Gold Coast 2018 | Athletics | 58 | ~44-46 | 12 | "58 medal events including additional para-sport disciplines"; "six men's and six women's [para] events" |
| Gold Coast 2018 | Swimming | 50 | 38 | 12 | "Of the 50, 38 were for able-bodied athletes... the remaining 12 were for para sport athletes" |

Para events are explicitly identified with T/F classification codes (track/field impairment
classes, e.g. T54, T38, F44/F64) and S/SB/SM codes for swimming (freestyle/breaststroke/medley
impairment classes, e.g. S9, SB6, SM10). Every one of the four Wikipedia articles states the
combined total (58, 52, 58, 50) *and* explicitly flags that this total includes para events — the
"headline" event count for each Games' athletics/swimming competition has always included para
since at least 2018, consistent with the README's framing that CG has integrated para into the
main medal table since Manchester 2002.

## Historical `by_sport` files: cross-check against ground truth (Task item 2)

Summed the `gold` column for Athletics and Swimming in both historical files:

| File | Sport | Gold column sum | Matches |
|---|---|---|---|
| `medals_2022_by_sport.csv` | Athletics | **58** | Birmingham 2022 combined total (48 standard + 10 para) exactly |
| `medals_2022_by_sport.csv` | Swimming | **52** | Birmingham 2022 combined total (40 standard + 12 para) exactly |
| `medals_2018_by_sport.csv` | Athletics | **58** | Gold Coast 2018 combined total exactly |
| `medals_2018_by_sport.csv` | Swimming | **50** | Gold Coast 2018 combined total (38 standard + 12 para) exactly |

All four sums match the **combined standard+para total**, not the standard-only subtotal, and the
match is exact (not off by a handful, which would suggest partial/accidental para inclusion — it's
a clean, complete combination). This confirms unambiguously: **the historical `by_sport` data
includes para medals, undifferentiated from standard medals, in every year checked.**

A concrete illustration of the resulting distortion: `medals_2022_by_sport.csv` records
`Athletics,Wales,2,0,1,3` (2 gold, 1 bronze). Cross-checking the actual 2022 para-athletics
results, the Discus F44/F64 event alone was won gold by Aled Davies (Wales) with bronze to
Harrison Walsh (Wales) — a single para event supplies half of Wales's golds and 100% of its
bronze in the "Athletics" row. Davies is a multiple Paralympic champion who does not compete in
standard World Athletics Championships or Olympic athletics, so this contribution is entirely
invisible to the 60%-weighted recent-form component of the blend — Wales's historical share looks
stronger in "Athletics" than its standard-athletics recent form would ever indicate, and the model
has no mechanism to separate the two.

## Olympics/World Championships scrapes: confirmed standard-only (Task item 3)

Summed gold-medal columns and compared to known standard-only totals:

| File | Gold sum | Known standard-only total | Match |
|---|---|---|---|
| `olympics/medals_2024.csv` (Athletics) | 48.0 | 48 events, Paris 2024 Olympic athletics | Exact |
| `olympics/medals_2024_swimming.csv` | 37.0 | 37 events (35 pool + 2 marathon), Paris 2024 Olympic swimming | Exact |
| `olympics/medals_2020.csv` (Athletics) | 49.0 | 48 events; the extra 1.0 is the Barshim/Tamberi high-jump tie (two golds awarded, one event) — not para | Explained, not para |
| `olympics/medals_2020_swimming.csv` | 35.0 | 35 pool events (open-water marathon swimming appears not to have been scraped into this file) | Explained, not para; a separate, smaller scope gap unrelated to this audit |

No fractional or extra counts trace to para events in any file — the two minor discrepancies
(2020 high-jump tie, apparent exclusion of 2020 marathon swimming) are both fully accounted for by
non-para causes.

Also independently confirmed structurally: the 2025 World Athletics Championships (Tokyo, 13–21
September 2025) and the 2025 World Para Athletics Championships (New Delhi, 27 September–5 October
2025) are separate competitions in different cities on non-overlapping dates — the same pattern
holds for World Aquatics vs. World Para Swimming Championships and for the Olympics vs.
Paralympics. It is not possible for `world_athletics/medals_2025.csv`, `world_aquatics/medals_2025.csv`,
or either `olympics/medals_2024*.csv` file to contain para results; they were sourced from
standard-competition Wikipedia pages that structurally cannot include them.

(Note: `world_athletics/medals_*.csv` files are pre-filtered to Commonwealth-eligible countries
only, per the model's stated methodology, so their gold sums are much smaller than the full World
Championships event count and were not usable for this exact-total check — the Olympics files,
which are not pre-filtered, provided the clean confirmation instead.)

## Is this a real bug? (Task item 4)

Yes. The model blends:
- 60% recent form: Olympics/Worlds, **standard-only**, 2020-2025
- 40% historical: Commonwealth Games, **standard+para combined**, 2010-2022

as if both were measuring the same underlying "Athletics" or "Swimming" strength. They are not:
one measures ~100% standard-event strength, the other measures a ~73-75%-standard/~25-27%-para
blend that varies by country (a country strong in para relative to its standard performance — as
Wales is, via Aled Davies — will show an inflated historical share relative to what its recent
standard-only form predicts). The 2026 event count the blended share gets multiplied by (59
athletics, 56 swimming) is itself the combined standard+para total, so the *output* granularity is
correct — the problem is specifically that the two *inputs* to the 60/40 blend disagree about what
fraction of "Athletics" they each represent, and the model has no term correcting for that
mismatch.

## Recommendation (Task item 5)

**Option (a), event-count-weighted decomposition, is the right fix and is directly actionable with
existing data** — no new scraping is strictly required, though (b) would improve it further:

1. Split each historical `by_sport` Athletics/Swimming row into a standard-weighted and
   para-weighted share, by the standard/para event-count ratio for that Games year (e.g. Birmingham
   2022 Athletics: 48/58 of a country's historical share treated as "standard-like", 10/58 as
   "para-like"). This is an approximation (it assumes even split across events, which is not
   exactly true — see Wales/Davies above) but is far better than the current fully-undifferentiated
   blend, and is a one-line adjustment to the recency-weighted averaging step already in
   `predict_medals.py`.
2. For the 2026 prediction: apply the existing 60/40 recent-form/historical blend **only to the
   standard-weighted portion** (43/59 athletics, 42/56 swimming events), since that's the only
   portion where a recent-form signal exists. Apply the historical-only para-weighted share
   (unblended, since there is no recent-form para signal) to the remaining para portion (16/59
   athletics, 14/56 swimming events).
3. **Recommended follow-up, not required for the immediate fix:** scrape World Para Athletics
   Championships and World Para Swimming Championships results (2022/2023 and 2024/2025 editions
   exist) the same way the standard Olympics/Worlds data was scraped and apportioned to home
   nations, to give the para portion its own recent-form signal instead of relying on 2018-2022
   history alone. This closes the gap properly rather than working around it, but is more effort
   (a new scrape + apportionment) than (1)-(2), which can be done today from data already in the
   repo.
4. **Explicitly do not** attempt to retroactively strip para medals out of the existing
   `by_sport` historical files to make them "standard-only" — that would throw away real signal
   (para medals are Commonwealth Games medals that count toward 2026's real medal table) rather
   than using it correctly. The fix is to weight the two portions correctly, not to delete one of
   them.

## Note

No CSV files or `scripts/predict_medals.py` were modified as part of this audit. This document is
a standalone recommendation, in the same spirit as `data/olympics/WALES_NI_AUDIT.md`.
