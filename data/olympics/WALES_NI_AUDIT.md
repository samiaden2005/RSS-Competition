# Audit: Zero Wales / Zero Northern Ireland Apportionment (2020-2025 GB Athletics)

Date: 2026-07-19
Scope: `data/olympics/gb_apportionment_2020.csv`, `data/world_athletics/gb_apportionment_2022.csv`,
`data/olympics/gb_apportionment_2024.csv`, `data/world_athletics/gb_apportionment_2025.csv`

## Conclusion

**Both (a) and (b).** The zero-Wales/zero-NI picture is overwhelmingly a genuine reflection of
current elite depth — Wales and Northern Ireland simply did not produce any individual GB
Athletics medallist across Tokyo 2020, Eugene 2022, Paris 2024, or Tokyo 2025, and Azu's bronze
is the *only* track-and-field medal a Welsh athlete has won for GB since Iwan Thomas/Jamie Baulch
in the 1996 Atlanta 4x400m relay. That is a real, externally-corroborated scarcity, not a data
error.

However, the methodology's winner-take-all "majority home nation" rule for relays is **not
neutral** with respect to smaller home nations: it structurally rounds any minority contribution
down to zero. In this dataset it masked exactly one genuine Welsh contribution (Azu) and, as a
side effect, also rounded two genuine Scottish relay contributions (Yeargin, twice) down to zero.
No Wales/NI masking was found beyond the already-known Azu case — but the mechanism that produced
it is generic and will keep zeroing out minority nations on any future mixed relay, so it is worth
fixing even though it only changes one row of history so far.

## Methodology cross-check (Task item 1)

Fetched the official GB medal lists from Wikipedia for all four events and compared row-by-row
against the CSVs:

- **Tokyo 2020**: 5 medals (Kerr bronze 1500m, Hodgkinson silver 800m, Muir silver 1500m,
  Bradshaw bronze PV, Women's 4x100m bronze) — matches CSV exactly.
- **Eugene 2022 Worlds**: 7 medals (Wightman gold 1500m, Hodgkinson silver 800m, Muir bronze
  1500m, Asher-Smith bronze 200m, Hudson-Smith bronze 400m, Men's 4x100m bronze, Women's 4x400m
  bronze) — matches CSV exactly.
- **Paris 2024**: 10 medals (Hodgkinson gold 800m, Kerr silver 1500m, Hudson-Smith silver 400m,
  Johnson-Thompson silver heptathlon, Women's 4x100m silver, Mixed 4x400m bronze, Men's 4x100m
  bronze, Men's 4x400m bronze, Women's 4x400m bronze, Hunter Bell bronze 1500m) — matches CSV
  exactly.
- **Tokyo 2025 Worlds**: 5 medals (Wightman silver 1500m, Hunt silver 200m, Hunter Bell silver
  800m, Johnson-Thompson bronze heptathlon, Hodgkinson bronze 800m) — matches CSV exactly (O'Connor
  heptathlon silver correctly excluded/footnoted as an IRL, not GBR, medal).

No missing or extra medal events found in any of the four files.

## Relay roster audit (Task item 2)

Every named athlete on every relay roster (final-race and heats-only) across all four files was
checked individually against Wikipedia, Welsh Athletics, and Athletics Northern Ireland for
Commonwealth Games nation. Full roster list checked (24 distinct relay-roster athletes beyond the
already-flagged cases): Asha Philip, Imani-Lara Lansiquot, Dina Asher-Smith, Daryll Neita, Jona
Efoloko, Zharnel Hughes, Nethaneel Mitchell-Blake, Reece Prescod, Adam Gemili, Victoria Ohuruogu,
Jessie Knight, Laviai Nielsen, Ama Pipi, Amy Hunt, Bianca Williams, Desirèe Henry, Sam Reardon,
Alex Haydock-Wilson, Amber Anning, Louie Hinchliffe, Richard Kilty, Lewis Davey, Charlie Dobson,
Toby Harries, Yemi Mary John, Hannah Kelly, Jodie Williams, Lina Nielsen. Every one of them is
English (explicit "Representing England" / Team England selection, or unambiguous English
birthplace with no contrary Commonwealth Games record), except the two already correctly flagged
as Scottish (Nicole Yeargin) in the CSVs. **No additional Welsh or Northern Irish athlete was found
on any relay roster.** Azu remains the sole case.

### Masked relay contributions (majority rule zeroed a genuine minority nation)

| Games | Event | Medal | Final roster split | Masked nation |
|---|---|---|---|---|
| Paris 2024 | Men's 4 x 100m relay | Bronze | 3 England (Hinchliffe, Mitchell-Blake, Hughes) vs 1 Wales (Azu) | **Wales — 0.25 share zeroed** |
| Eugene 2022 Worlds | Women's 4 x 400m relay | Bronze | 3 England (Ohuruogu, Knight, L. Nielsen) vs 1 Scotland (Yeargin) | Scotland — 0.25 share zeroed |
| Paris 2024 | Mixed 4 x 400m relay | Bronze | 4 England (final roster; Yeargin ran heats only, replaced by Anning) | Scotland — masked only if heats-only credit is desired (final-roster majority is unanimous England, so this is a weaker case than the others) |
| Paris 2024 | Women's 4 x 400m relay | Bronze | 3 England (Ohuruogu, L. Nielsen, Anning) vs 1 Scotland (Yeargin) | Scotland — 0.25 share zeroed |

Only the first row (Azu) is relevant to this audit's Wales/NI question. The Yeargin rows are
included because they demonstrate the majority rule is a general-purpose distortion, not something
that happens to only affect Wales — it will zero out *any* minority nation on a mixed relay,
which matters for methodology going forward even though today it only visibly costs Wales one
event.

## Individual (non-relay) medal check (Task item 3)

- Confirmed via ITV News Wales / Sport Wales / Welsh Athletics that Jeremiah Azu's Paris 2024
  relay bronze was "the first track and field medal for a Welsh athlete since [1996]" — i.e.
  Wales has had **zero individual GB athletics medals** in this entire 2020-2025 window, and the
  only Welsh medal at all (individual or relay) was Azu's relay share.
- No Northern Irish athlete won an individual GB Athletics medal at any of the four Games. Kate
  O'Connor's 2025 Worlds heptathlon silver was won for Ireland (IRL), not Great Britain, and is
  already correctly excluded from the GBR apportionment (footnoted in the 2025 CSV) rather than
  miscounted as a GB medal.
- Sanity-checked other notable current Welsh internationals (e.g. Aled Davies, Hollie Arnold —
  both Paralympic/Para athletics, not applicable here; Cari Hughes — European Cross Country/steeplechase,
  no Olympic/Worlds senior medal in this window). None won a senior GB Olympic/World
  Championships athletics medal 2020-2025.

## Recommendation

Switch mixed-nation relay apportionment from winner-take-all majority to **fractional/weighted
apportionment** proportional to final-race roster composition (heats-only reserves who did not
run the final should not receive a share, consistent with current practice). Concretely:

- Paris 2024 Men's 4x100m relay bronze: currently 1.0 England → should be **0.75 England + 0.25
  Wales**.
- Eugene 2022 Women's 4x400m relay bronze: currently 1.0 England → should be **0.75 England +
  0.25 Scotland**.
- Paris 2024 Women's 4x400m relay bronze: currently 1.0 England → should be **0.75 England +
  0.25 Scotland**.

This is a small change in aggregate medal-count terms (a few tenths of a medal moved per Games)
but it removes a structural bias that will otherwise keep rounding Wales's and Northern Ireland's
true relay contributions to zero any time they place fewer than a majority of runners on a mixed
GB relay team — precisely the scenario that is likeliest to be how a smaller home nation's
athletes show up in GB relay success (contributing one leg, not three or four). Given the stated
purpose of these files is to apportion GB medals for Commonwealth Games home-nation medal
prediction, fractional apportionment is more defensible than winner-take-all and should be adopted
prospectively; whether to restate the four historical files is a judgment call for the modelling
team (this audit does not modify them).

## Note

No CSV files were modified as part of this audit. This document is a standalone recommendation.
