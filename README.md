# RSS-Competition

Predicting the medal table for the Glasgow 2026 Commonwealth Games, for the RSS prediction
competition ([rules](https://qsay.uk/posts/RSScomp2026/#submission-template)).

## Methodology

For each of the 10 sports on the Glasgow 2026 programme, a country's predicted gold/silver/bronze
share is an equal-weighted average of its historical share of that sport's medals across the
2010-2022 Commonwealth Games, restricted to nations that actually compete at the CG. For Athletics
and Swimming — 53% of all 2026 medal events — this is blended 35% with a fresher signal from recent
Olympics/World Championships results (2020-2025), applied only to the standard-event portion of
each sport; the para portion uses CG history unblended, since Commonwealth Games history combines
para and standard medals into one total while global championships are standard-only, and blending
the two undifferentiated would misattribute a country's para-only strength to a "recent form"
signal that structurally cannot see it. Because the Commonwealth Games splits Great Britain into
England, Scotland, Wales and Northern Ireland while every other competition fields one GBR team,
every individual GB Olympic/World Championships medal since 2020 was traced to the athlete's
Commonwealth Games home nation via Wikipedia, with mixed-nation relay medals apportioned
fractionally by final-race roster composition rather than winner-take-all (which was found to
systematically round minority home nations' contributions down to zero). Scotland, as Glasgow
2026's host, also receives a 20% boost to its predicted total, redistributed proportionally from
the rest of the field rather than invented, sized from the home-Games effect actually observed in
all three of the last four Games' hosts.

Since collecting more data is expensive relative to extracting more signal from what's already
gathered, the model's free parameters — the weighting across Games years, the recent-form blend
weight, and the zero-medal clustering threshold — were tuned empirically rather than by hand: a
backtest holds out Birmingham 2022, trains the model on 2010-2018 data only, and scores the
resulting prediction against Birmingham's real result using the competition's own Kendall's tau
definition. This raised backtest tau from 0.599 to 0.620 (+3.5%) over the original hand-picked
constants, and was also used to reject candidate changes — such as shrinking small-sample
countries' shares toward zero — that looked plausible but didn't hold up under the same test.
