import csv
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
MEDAL_COLORS = ["gold", "silver", "bronze"]

# Historical Commonwealth Games sport name -> 2026 programme sport name differs only here.
SPORT_NAME_MAP = {"Cycling (Track)": "Track Cycling"}

# Recency weights for the four past Commonwealth Games (renormalized per sport to whichever
# years that sport was actually contested, e.g. Judo/3x3 Basketball are newer additions).
CG_WEIGHTS = {2022: 0.40, 2018: 0.28, 2014: 0.20, 2010: 0.12}

# Recency weights for the recent global competitions (Olympics/World Championships), used only
# for Athletics and Swimming where we have scraped, home-nation-apportioned data. These are a
# fresher form signal than the 2022 Commonwealth Games (4 years stale by 2026).
RECENT_WEIGHTS = {2025: 0.40, 2024: 0.30, 2022: 0.20, 2020: 0.10}

# Weight given to the recent-global-form signal vs. the Commonwealth-Games-history signal,
# for Athletics and Swimming only.
RECENT_BLEND = 0.6

# Commonwealth Games athletics/swimming medal tables have always folded para-sport events into
# the same headline total as standard events (confirmed for 2018/2022 in data/PARA_SPORT_AUDIT.md:
# summed historical gold counts match combined standard+para totals exactly). The Olympics/World
# Championships data behind RECENT_BLEND is standard-only by construction (Paralympics and World
# Para Championships are separate competitions, never scraped here), so blending it against an
# undifferentiated standard+para historical share overstates recent-form countries' para strength
# and understates para-strong countries whose standard results don't show it (see the Wales/Aled
# Davies case in the audit). Fix: only apply RECENT_BLEND to the standard-event portion of each
# sport's 2026 allocation; the para-event portion uses the historical share unblended, since there
# is no recent-form signal for it yet.
PARA_SPLIT_2026 = {
    "Athletics": {"standard": 43, "para": 16},
    "Swimming": {"standard": 42, "para": 14},
}

# Below this total predicted medal count, a country is treated as a genuine zero and clustered
# into a single tied last-place rank rather than given spurious fine-grained ordering.
ZERO_MEDAL_THRESHOLD = 0.05

RECENT_SOURCES = {
    "Athletics": [
        (2020, "olympics/medals_2020.csv"),
        (2022, "world_athletics/medals_2022.csv"),
        (2024, "olympics/medals_2024.csv"),
        (2025, "world_athletics/medals_2025.csv"),
    ],
    "Swimming": [
        (2020, "olympics/medals_2020_swimming.csv"),
        (2022, "world_aquatics/medals_2022.csv"),
        (2024, "olympics/medals_2024_swimming.csv"),
        (2025, "world_aquatics/medals_2025.csv"),
    ],
}


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_template():
    rows = load_csv(DATA / "RSS_pred_comp_submission_template.csv")
    return rows, {r["CGA"] for r in rows}


def load_programme():
    rows = load_csv(DATA / "glasgow_2026_sports_programme.csv")
    return {r["sport"]: int(r["medal_events"]) for r in rows}


def load_historical_by_sport():
    files = {
        2010: "medals_2010_by_sport.csv",
        2014: "medals_2014_by_sport.csv",
        2018: "medals_2018_by_sport.csv",
        2022: "medals_2022_by_sport.csv",
    }
    data = {}
    for year, fname in files.items():
        by_sport = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        for r in load_csv(DATA / "historical" / "by_sport" / fname):
            for color in MEDAL_COLORS:
                by_sport[r["sport"]][r["country"]][color] += float(r[color])
        data[year] = by_sport
    return data


def load_recent_global(sport, cg_countries):
    data = {}
    for year, relpath in RECENT_SOURCES[sport]:
        by_country = defaultdict(lambda: defaultdict(float))
        for r in load_csv(DATA / relpath):
            if r["country"] not in cg_countries:
                continue
            for color in MEDAL_COLORS:
                by_country[r["country"]][color] += float(r[color])
        data[year] = by_country
    return data


def weighted_shares(year_country_color, weights):
    available_years = [y for y in weights if y in year_country_color and year_country_color[y]]
    total_w = sum(weights[y] for y in available_years)
    shares = {color: defaultdict(float) for color in MEDAL_COLORS}
    if not available_years:
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


def blend(cg_shares, recent_shares):
    blended = {color: defaultdict(float) for color in MEDAL_COLORS}
    for color in MEDAL_COLORS:
        countries = set(cg_shares[color]) | set(recent_shares[color])
        for country in countries:
            cg_s = cg_shares[color].get(country, 0.0)
            rec_s = recent_shares[color].get(country, 0.0)
            blended[color][country] = RECENT_BLEND * rec_s + (1 - RECENT_BLEND) * cg_s
    return blended


def predict():
    _, cg_countries = load_template()
    programme = load_programme()
    historical = load_historical_by_sport()

    totals = defaultdict(lambda: defaultdict(float))
    sport_breakdown = defaultdict(dict)

    for sport, n_events in programme.items():
        hist_name = SPORT_NAME_MAP.get(sport, sport)
        year_data = {year: historical[year].get(hist_name, {}) for year in historical}
        cg_shares = weighted_shares(year_data, CG_WEIGHTS)

        if sport in PARA_SPLIT_2026:
            recent_data = load_recent_global(sport, cg_countries)
            recent_shares = weighted_shares(recent_data, RECENT_WEIGHTS)
            blended_shares = blend(cg_shares, recent_shares)
            n_standard = PARA_SPLIT_2026[sport]["standard"]
            n_para = PARA_SPLIT_2026[sport]["para"]

            for color in MEDAL_COLORS:
                countries = set(blended_shares[color]) | set(cg_shares[color])
                for country in countries:
                    predicted = (blended_shares[color].get(country, 0.0) * n_standard
                                 + cg_shares[color].get(country, 0.0) * n_para)
                    totals[country][color] += predicted
                    sport_breakdown[sport][country] = sport_breakdown[sport].get(country, 0.0) + predicted
        else:
            for color in MEDAL_COLORS:
                for country, share in cg_shares[color].items():
                    predicted = share * n_events
                    totals[country][color] += predicted
                    sport_breakdown[sport][country] = sport_breakdown[sport].get(country, 0.0) + predicted

    return totals, sport_breakdown


def rank_countries(totals, all_countries):
    scored = []
    for country in all_countries:
        t = totals.get(country, {})
        g, s, b = t.get("gold", 0.0), t.get("silver", 0.0), t.get("bronze", 0.0)
        scored.append((country, g, s, b))

    nonzero = [row for row in scored if (row[1] + row[2] + row[3]) >= ZERO_MEDAL_THRESHOLD]
    zero = [row for row in scored if (row[1] + row[2] + row[3]) < ZERO_MEDAL_THRESHOLD]

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

    return ranks, {row[0]: row for row in scored}


def main():
    template_rows, cg_countries = load_template()
    totals, sport_breakdown = predict()
    ranks, by_country = rank_countries(totals, cg_countries)

    predictions_path = DATA / "predicted_medals_2026.csv"
    with open(predictions_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["country", "gold", "silver", "bronze", "total", "rank"])
        for country, g, s, b in sorted(by_country.values(), key=lambda r: ranks[r[0]]):
            total = g + s + b
            w.writerow([country, f"{g:.2f}", f"{s:.2f}", f"{b:.2f}", f"{total:.2f}", ranks[country]])

    submission_path = DATA / "RSS_pred_comp_submission_Sami.csv"
    with open(submission_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Code", "CGA", "Rank"])
        for row in template_rows:
            w.writerow([row["Code"], row["CGA"], ranks[row["CGA"]]])

    print(f"Wrote {predictions_path}")
    print(f"Wrote {submission_path}")
    print()
    print("Top 20 predicted:")
    print(f"{'rank':>4}  {'country':<22}{'gold':>7}{'silver':>8}{'bronze':>8}{'total':>8}")
    for country, g, s, b in sorted(by_country.values(), key=lambda r: ranks[r[0]])[:20]:
        print(f"{ranks[country]:>4}  {country:<22}{g:>7.2f}{s:>8.2f}{b:>8.2f}{g+s+b:>8.2f}")

    n_zero = sum(1 for c in cg_countries if (by_country[c][1] + by_country[c][2] + by_country[c][3]) < ZERO_MEDAL_THRESHOLD)
    print(f"\n{n_zero} of {len(cg_countries)} countries clustered at zero-predicted-medals (tied last).")


if __name__ == "__main__":
    main()

