"""
Backtest: train the model's logic on 2010/2014/2018 Commonwealth Games history (+ Tokyo 2020
Olympics recent-form for Athletics/Swimming, the only pre-2022 recent-form source in the repo)
and see how well it would have ranked the actual Birmingham 2022 Games, scored by the
competition's own Kendall's tau.

Ground truth is built from data/historical/by_sport/medals_2022_by_sport.csv (already filtered to
the same 10 sports as the Glasgow 2026 programme), aggregated per country and ranked by the
competition's gold->silver->bronze tie-break. Per-sport 2022 event counts (needed to convert
predicted shares into predicted medal counts) are derived the same way, from that file's own gold
column sums, rather than reusing the 2026 programme file -- 2022 Birmingham had different event
counts per sport.

Scoring is restricted to the ~44 countries that won at least one medal in these 10 sports at
Birmingham 2022, since that's the full set of countries this repo has verified ground truth for
(no full non-medallist participant list for 2022 exists in the repo). Countries outside that set
would be tied-last in both predicted and actual rankings anyway and contribute zero to tau.

This is a pure diagnostic script: it prints tau for a given configuration and, run standalone,
grid-searches CG_WEIGHTS decay / RECENT_BLEND / ZERO_MEDAL_THRESHOLD / host-boost to report the
configuration that maximizes backtest tau. It does not write any files.
"""
import csv
import itertools
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
MEDAL_COLORS = ["gold", "silver", "bronze"]
SPORT_NAME_MAP = {"Cycling (Track)": "Track Cycling"}
PARA_SPLIT_2026 = {
    "Athletics": {"standard": 43, "para": 16},
    "Swimming": {"standard": 42, "para": 14},
}
# 2022 Birmingham CG standard/para athletics+swimming event split (see data/PARA_SPORT_AUDIT.md)
PARA_SPLIT_2022 = {
    "Athletics": {"standard": 48, "para": 10},
    "Swimming": {"standard": 40, "para": 12},
}
HOST_NATION_2022 = "England"  # Birmingham 2022 host, for backtest host-boost validation


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_historical_by_sport(years):
    files = {2010: "medals_2010_by_sport.csv", 2014: "medals_2014_by_sport.csv",
             2018: "medals_2018_by_sport.csv", 2022: "medals_2022_by_sport.csv"}
    data = {}
    for year in years:
        by_sport = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        for r in load_csv(DATA / "historical" / "by_sport" / files[year]):
            for color in MEDAL_COLORS:
                by_sport[r["sport"]][r["country"]][color] += float(r[color])
        data[year] = by_sport
    return data


def load_recent_global_pre2022(sport, cg_countries):
    # Only Tokyo 2020 Olympics predates Birmingham 2022 in this repo's data.
    sources = {"Athletics": [(2020, "olympics/medals_2020.csv")],
               "Swimming": [(2020, "olympics/medals_2020_swimming.csv")]}
    data = {}
    for year, relpath in sources[sport]:
        by_country = defaultdict(lambda: defaultdict(float))
        for r in load_csv(DATA / relpath):
            if r["country"] not in cg_countries:
                continue
            for color in MEDAL_COLORS:
                by_country[r["country"]][color] += float(r[color])
        data[year] = by_country
    return data


def weighted_shares(year_country_color, weights):
    available_years = [y for y in weights if y in year_country_color and year_country_color[y]
                        and weights[y] > 0]
    total_w = sum(weights[y] for y in available_years)
    shares = {color: defaultdict(float) for color in MEDAL_COLORS}
    if not available_years or total_w == 0:
        return shares
    for color in MEDAL_COLORS:
        for year in available_years:
            w = weights[year] / total_w
            year_data = year_country_color[year]
            year_total = sum(counts[color] for counts in year_data.values())
            if year_total == 0:
                continue
            for country, counts in year_data.items():
                shares[color][country] += w * (counts[color] / year_total)
    return shares


def raw_medal_counts(year_country_color, available_years):
    """Unweighted total medal count per country per colour, summed across the given years --
    used as a sample-size proxy for shrinkage (a country with one lucky medal across 3 Games of
    history is less trustworthy than one with a steady double-digit haul)."""
    counts = {color: defaultdict(float) for color in MEDAL_COLORS}
    for year in available_years:
        year_data = year_country_color.get(year, {})
        for country, c in year_data.items():
            for color in MEDAL_COLORS:
                counts[color][country] += c.get(color, 0.0)
    return counts


def shrink_shares(shares, raw_counts, k):
    """James-Stein-style shrinkage: pull each country's share toward zero in proportion to how
    thin its evidence is (k tunes shrinkage strength; k=0 disables it), then renormalize so each
    colour's shares still sum to what they did before shrinkage."""
    if k == 0:
        return shares
    shrunk = {color: defaultdict(float) for color in MEDAL_COLORS}
    for color in MEDAL_COLORS:
        original_total = sum(shares[color].values())
        for country, share in shares[color].items():
            n = raw_counts[color].get(country, 0.0)
            shrunk[color][country] = share * (n / (n + k))
        shrunk_total = sum(shrunk[color].values())
        if shrunk_total > 0:
            rescale = original_total / shrunk_total
            for country in shrunk[color]:
                shrunk[color][country] *= rescale
    return shrunk


def blend(cg_shares, recent_shares, recent_blend):
    blended = {color: defaultdict(float) for color in MEDAL_COLORS}
    for color in MEDAL_COLORS:
        countries = set(cg_shares[color]) | set(recent_shares[color])
        for country in countries:
            cg_s = cg_shares[color].get(country, 0.0)
            rec_s = recent_shares[color].get(country, 0.0)
            blended[color][country] = recent_blend * rec_s + (1 - recent_blend) * cg_s
    return blended


def true_2022(cg_countries):
    """Ground truth: aggregate the 10-sport-filtered 2022 by_sport file per country."""
    rows = load_csv(DATA / "historical" / "by_sport" / "medals_2022_by_sport.csv")
    totals = defaultdict(lambda: [0.0, 0.0, 0.0])
    events_per_sport = defaultdict(float)
    for r in rows:
        c = r["country"]
        g, s, b = float(r["gold"]), float(r["silver"]), float(r["bronze"])
        totals[c][0] += g
        totals[c][1] += s
        totals[c][2] += b
        events_per_sport[r["sport"]] += g
    return totals, events_per_sport


def kendall_tau(pred_ranks, true_ranks, countries):
    """Competition definition: (concordant - discordant) / total pairs, ties (in either
    ranking) contribute zero to the numerator but count in the denominator."""
    countries = list(countries)
    c = d = t = 0
    for i in range(len(countries)):
        for j in range(i + 1, len(countries)):
            a, b = countries[i], countries[j]
            pa, pb = pred_ranks[a], pred_ranks[b]
            ta, tb = true_ranks[a], true_ranks[b]
            if pa == pb or ta == tb:
                t += 1
                continue
            pred_order = pa < pb  # lower rank number = better
            true_order = ta < tb
            if pred_order == true_order:
                c += 1
            else:
                d += 1
    total = c + d + t
    return (c - d) / total if total else 0.0


def rank_from_gsb(country_gsb, threshold):
    scored = [(country, g, s, b) for country, (g, s, b) in country_gsb.items()]
    nonzero = [row for row in scored if (row[1] + row[2] + row[3]) >= threshold]
    zero = [row for row in scored if (row[1] + row[2] + row[3]) < threshold]
    nonzero.sort(key=lambda row: (-row[1], -row[2], -row[3]))
    ranks = {}
    position = 1
    prev_key = None
    for i, row in enumerate(nonzero):
        key = (row[1], row[2], row[3])
        if key != prev_key:
            position = i + 1
        ranks[row[0]] = position
        prev_key = key
    zero_rank = len(nonzero) + 1
    for row in zero:
        ranks[row[0]] = zero_rank
    return ranks


def run_backtest(cg_weights, recent_blend, zero_threshold, host_boost=0.0, host_nation=HOST_NATION_2022,
                  shrink_k=0.0):
    template = load_csv(DATA / "RSS_pred_comp_submission_template.csv")
    cg_countries = {r["CGA"] for r in template}

    historical = load_historical_by_sport([2010, 2014, 2018])
    true_totals, events_per_sport = true_2022(cg_countries)
    scored_countries = set(true_totals)  # countries with >=1 real medal in these 10 sports, 2022

    totals = defaultdict(lambda: defaultdict(float))
    for sport, n_events in events_per_sport.items():
        hist_name = SPORT_NAME_MAP.get(sport, sport)
        year_data = {year: historical[year].get(hist_name, {}) for year in historical}
        cg_shares = weighted_shares(year_data, cg_weights)
        if shrink_k:
            raw_counts = raw_medal_counts(year_data, list(cg_weights))
            cg_shares = shrink_shares(cg_shares, raw_counts, shrink_k)

        if sport in PARA_SPLIT_2026:
            recent_data = load_recent_global_pre2022(sport, cg_countries)
            recent_shares = weighted_shares(recent_data, {2020: 1.0})
            blended_shares = blend(cg_shares, recent_shares, recent_blend)
            n_standard = PARA_SPLIT_2022[sport]["standard"]
            n_para = PARA_SPLIT_2022[sport]["para"]
            for color in MEDAL_COLORS:
                countries = set(blended_shares[color]) | set(cg_shares[color])
                for country in countries:
                    predicted = (blended_shares[color].get(country, 0.0) * n_standard
                                 + cg_shares[color].get(country, 0.0) * n_para)
                    totals[country][color] += predicted
        else:
            for color in MEDAL_COLORS:
                for country, share in cg_shares[color].items():
                    totals[country][color] += share * n_events

    if host_boost:
        for color in MEDAL_COLORS:
            totals[host_nation][color] *= (1 + host_boost)

    pred_gsb = {c: (t.get("gold", 0.0), t.get("silver", 0.0), t.get("bronze", 0.0))
                for c, t in totals.items()}
    for c in scored_countries:
        pred_gsb.setdefault(c, (0.0, 0.0, 0.0))
    pred_ranks = rank_from_gsb(pred_gsb, zero_threshold)

    true_gsb = {c: tuple(v) for c, v in true_totals.items()}
    true_ranks = rank_from_gsb(true_gsb, threshold=0.0)  # every scored country has >=1 real medal

    tau = kendall_tau(pred_ranks, true_ranks, scored_countries)
    return tau


if __name__ == "__main__":
    baseline = run_backtest(
        cg_weights={2018: 0.28 / 0.60, 2014: 0.20 / 0.60, 2010: 0.12 / 0.60},
        recent_blend=0.6, zero_threshold=0.05,
    )
    print(f"Baseline (current predict_medals.py constants, minus 2022): tau = {baseline:.4f}")
    print()

    print("Grid search over CG_WEIGHTS decay, RECENT_BLEND, ZERO_MEDAL_THRESHOLD, host-boost:")
    results = []
    decay_options = {
        "steep (0.5/0.3/0.2)": {2018: 0.5, 2014: 0.3, 2010: 0.2},
        "current (0.467/0.333/0.2)": {2018: 0.28 / 0.60, 2014: 0.20 / 0.60, 2010: 0.12 / 0.60},
        "flat (0.4/0.35/0.25)": {2018: 0.4, 2014: 0.35, 2010: 0.25},
        "2018-only": {2018: 1.0, 2014: 0.0, 2010: 0.0},
        "equal (1/3 each)": {2018: 1 / 3, 2014: 1 / 3, 2010: 1 / 3},
    }
    for decay_name, cg_w in decay_options.items():
        for recent_blend in (0.0, 0.15, 0.3, 0.5, 0.6, 0.7, 0.85, 1.0):
            for zero_thr in (0.05, 0.15, 0.3, 0.5):
                for host_boost in (0.0, 0.1, 0.15, 0.2, 0.25, 0.35, 0.5):
                    tau = run_backtest(cg_w, recent_blend, zero_thr, host_boost)
                    results.append(((decay_name, recent_blend, zero_thr, host_boost), tau))
    results.sort(key=lambda r: -r[1])
    print("\nTop 15 configs:")
    for key, tau in results[:15]:
        print(f"  decay={key[0]:<28} recent_blend={key[1]:<5} zero_thr={key[2]:<5} "
              f"host_boost={key[3]:<5} -> tau = {tau:.4f}")
    best = results[0]
    print(f"\nBest config: decay={best[0][0]}, recent_blend={best[0][1]}, "
          f"zero_threshold={best[0][2]}, host_boost={best[0][3]} -> tau = {best[1]:.4f}")
