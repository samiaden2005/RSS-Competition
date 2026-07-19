# RSS-Competition

Predicting the medal table for the Glasgow 2026 Commonwealth Games, for the RSS prediction
competition ([rules](https://qsay.uk/posts/RSScomp2026/#submission-template)).

## Competition rules (summary)

- Submit a predicted **rank** (not raw medal count) for each of the 74 competing nations.
- The true final ranking is decided by gold medals; silver breaks gold ties, bronze breaks
  silver ties. Submitted ranks may be integers, non-integers, or tied ("clustered").
- Scored by Kendall's tau over all country pairs: correctly-ordered pairs score positive,
  incorrectly-ordered pairs score negative, tied pairs score zero.
- Submission file: `RSS_pred_comp_submission_<NAME>.csv`, same row order as the template,
  only the `Rank` column may change.
- Deadline: 23:59, Wednesday 22 July 2026. Games start 23 July 2026.

## Repository layout

```
data/
  RSS_pred_comp_submission_template.csv   competition-provided template (74 countries)
  RSS_pred_comp_submission_Sami.csv       our current submission (generated)
  predicted_medals_2026.csv               full predicted gold/silver/bronze table (generated)
  glasgow_2026_sports_programme.csv       the 10 sports + medal-event counts at Glasgow 2026

  historical/                             actual past Commonwealth Games results (2010-2022)
    medals_<year>_<host>.csv              overall medal table per Games
    by_sport/medals_<year>_by_sport.csv   medal table broken down by sport, already filtered
                                           to the 10 sports on the Glasgow 2026 programme

  world_athletics/                        World Athletics Championships (2022, 2025)
  world_aquatics/                         World Aquatics Championships, swimming (2022, 2025)
  olympics/                               Olympics, athletics + swimming (2020 Tokyo, 2024 Paris)
    gb_apportionment_<year>[_swimming].csv   how GB's medals split across home nations
    medals_<year>[_swimming].csv             medal table with GB replaced by home-nation rows
    WALES_NI_AUDIT.md                        audit of the relay apportionment methodology

scripts/
  predict_medals.py                       the prediction model (see below)
```

## Data pipeline

**Why home nations, not "Great Britain":** the Commonwealth Games splits Great Britain into
England, Scotland, Wales and Northern Ireland, but every other major athletics/swimming
competition (Olympics, World Championships) has them compete as one GBR team. To use those
results as a predictor, every individual GB medal was traced to the athlete's Commonwealth Games
home nation via Wikipedia (quoted directly as evidence in the `gb_apportionment_*.csv` files),
so `medals_*.csv` in `olympics/` and `world_athletics/` / `world_aquatics/` report England,
Scotland, Wales and Northern Ireland as if they'd competed separately.

**Relay apportionment:** relay medals have athletes from more than one home nation. Each medal
is split into fractional shares proportional to the *final-race* roster composition only
(heats-only substitutes are recorded but don't count) — e.g. a bronze won by a team of 3 English
and 1 Welsh athlete counts as 0.75 England + 0.25 Wales, not winner-take-all to the majority
nation. This replaced an earlier winner-take-all rule after `WALES_NI_AUDIT.md` found it was
systematically rounding minority contributions (Wales, and some Scotland relay legs) down to
zero. Every `gb_apportionment_*.csv` file has a `share` column recording this.

**Verification applied throughout:** every medal-event's shares sum to exactly 1.0 (no medal
fabricated or lost in the apportionment), and every `medals_*.csv` home-nation total reconciles
exactly against its apportionment file.

## Prediction model (`scripts/predict_medals.py`)

For each of the 10 sports on the Glasgow 2026 programme:

1. Compute each country's **share** of that sport's gold/silver/bronze medals in each of the
   2010/2014/2018/2022 Commonwealth Games, restricted to countries that actually compete at the
   CG (so a country's historical strength isn't diluted by non-Commonwealth nations).
2. Average those shares across the four Games with recency weighting
   (2022 → 0.40, 2018 → 0.28, 2014 → 0.20, 2010 → 0.12), renormalized to whichever years a sport
   was actually contested (e.g. Judo and 3x3 Basketball are recent additions).
3. **For Athletics and Swimming only** — the two sports with scraped, home-nation-apportioned
   data from 2020-2025 — a second share is computed the same way from the Olympics/World
   Championships results (2025 → 0.40, 2024 → 0.30, 2022 → 0.20, 2020 → 0.10), and blended
   60% recent-form / 40% Commonwealth-Games-history. This gives those two sports (53% of all
   2026 medal events) a much fresher signal than the now 4-year-old 2022 Birmingham Games.
4. **Athletics/Swimming only:** the 60/40 blend from step 3 is applied only to the *standard*
   portion of each sport's 2026 events (43/59 athletics, 42/56 swimming) — see
   `data/PARA_SPORT_AUDIT.md`. The remaining *para* portion (16/59 athletics, 14/56 swimming)
   uses the historical share unblended (`PARA_SPLIT_2026` in the script), since Commonwealth
   Games history folds para medals into the same total as standard ones but the Olympics/World
   Championships recent-form data is standard-only by construction — blending the two for the
   full event count would understate para-strong countries (and overstate ones with strong
   standard-only recent form but weak para history). All other sports have no recent-form
   component to begin with, so this split doesn't apply to them.
5. Each country's final predicted medal count per sport is summed across all 10 sports.
6. Countries are ranked by predicted gold → silver → bronze, per the competition's own tie-break
   rule. Countries with negligible predicted totals (< 0.05 medals) are clustered into a single
   tied last-place rank rather than given spurious fine-grained ordering.

Sanity check: total predicted golds and silvers across all countries each sum to exactly 215 —
the true number of 2026 medal events — confirming the share math has no leakage.

Run it with `python3 scripts/predict_medals.py`. It regenerates both `predicted_medals_2026.csv`
(full gold/silver/bronze table) and `RSS_pred_comp_submission_Sami.csv` (the actual submission).

## Known limitations / possible improvements

Roughly in order of expected impact:

1. **8 of 10 sports have no recent-form signal.** Gymnastics, Boxing, Judo, Track Cycling,
   Weightlifting, Bowls, Netball and 3x3 Basketball currently rely purely on 2010-2022
   Commonwealth Games history — there's no equivalent of the Olympics/Worlds scrape for them.
   World Championships exist for all of these (e.g. World Judo Championships, UCI Track Cycling
   World Championships, IWF Weightlifting World Championships) and could be scraped and
   apportioned to home nations the same way Athletics/Swimming were. This is the single biggest
   likely accuracy gain, since it currently affects 47% of medal events.

2. **[FIXED, 2026-07-19] Para-sport events were being mishandled.** Confirmed in
   `data/PARA_SPORT_AUDIT.md`: the historical `by_sport` data folds para medals into the same
   undifferentiated total as standard medals (verified exactly for 2018 and 2022; gold-column
   sums match known combined totals precisely), while the Olympics/World Championships scrapes
   are structurally standard-only (Paralympics/World Para Championships are separate
   competitions, never scraped). Blending a standard-only recent-form share against an
   undifferentiated standard+para historical share for the *entire* event count was distorting
   predictions — worked example in the audit: Wales's 2022 Athletics row is half explained by a
   single Paralympic discus result invisible to the recent-form data. **Fix applied**: the 60/40
   recent-form blend now only applies to the standard-event portion of Athletics/Swimming's 2026
   allocation; the para portion uses the historical share unblended (see step 4 above).
   **Remaining follow-up, not yet done:** this still assumes a country's medal share is identical
   in the standard and para portions of a sport (it isn't, per the Wales example) — scraping
   World Para Athletics/World Para Swimming Championships results and apportioning them to home
   nations the same way the standard results were would give the para portion its own genuine
   recent-form signal instead of this approximation.

3. **No home-Games effect.** Glasgow 2026 is hosted in Scotland; host nations (and to a lesser
   extent the rest of the host country's home nations) typically over-perform their historical
   trend at a home Games — this is a well-documented Olympic/Commonwealth effect. The model
   currently has no adjustment for England/Scotland/Wales/Northern Ireland hosting.

4. **No account of actual team selection.** The model is purely historical-trend-based; it
   doesn't know who's actually been selected for Glasgow 2026, who's injured, retired, or in
   career-best form right now. Cross-referencing announced 2026 squads (as they're released)
   against past medallists would be a meaningful signal, especially close to the Games.

5. **Weighting choices are hand-picked, not fitted.** The recency-decay weights (0.40/0.28/0.20/
   0.12 etc.) and the 60/40 recent-vs-historical blend for Athletics/Swimming were chosen by
   intuition. A proper backtest — hold out 2022 Birmingham, train the model on 2010-2018 (+
   whatever pre-2022 global results are available), and tune the weights to maximize Kendall's
   tau against the real 2022 result — would let the weights be justified empirically instead of
   guessed, and would give an honest estimate of how good the model actually is before the real
   Games happen.

6. **Share-based heuristic instead of a real statistical model.** Right now each country/sport/
   colour gets a point-estimate share with no uncertainty. A Poisson or negative-binomial model
   per country per sport (or a Bayesian model with shrinkage toward the sport-wide mean for
   small-sample countries) would handle small countries more gracefully — right now a country
   that won one bronze in Judo by chance in 2010 gets a nonzero predicted 2026 share purely from
   that one data point, with no shrinkage toward "probably zero." This is likely inflating noise
   in the middle and bottom of the predicted table.

7. **Tie-break sensitivity untested.** The ZERO_MEDAL_THRESHOLD clustering cutoff (0.05) and the
   general approach of using exact predicted-value ties are both unvalidated choices — worth
   checking how sensitive the Kendall's tau score is to where that cutoff is drawn.

8. **No validation against 2022 results at all yet.** Item 5 mentions backtesting for weight
   tuning, but even just running the current model's logic on 2010-2018 data and checking how it
   would have ranked the 2022 Birmingham Games (which we have ground truth for) would be a cheap
   sanity check on whether the whole approach is sound before trusting it for 2026.
