# Event lists for the extended event cap (frozen 2026-11-04, BEFORE any test; compiled from public sources, not from returns)

Rule for turning an event into an "event day" for the cap: the day the market REACTS. If the event happens during or before an Indian session on a trading day, that day; if it falls on a weekend/holiday or after the Indian close (US events), the NEXT Indian trading day. The cap (<= 1.0x notional) runs from the previous close through the close of the event day, as for the existing cap (E2: 3 election results + 17 Union Budgets, `V2FE_SPEC.md`).

## Tier A - Indian state election results
Inclusion rule fixed first: a counting day counts if (a) a state with >= 20 Lok Sabha seats counts that day, or (b) three or more states/UTs count that day. General-election days are already in E2. Excluded by the rule: Delhi 2020-02-11 and 2025-02-08 (7 seats, single state), Haryana + J&K 2024-10-08 (two small states), and results before the sample starts (UP etc. 2017-03-11).
Counting days (sources: news reports of ECI counting schedules and Dataful ECI master data; Wikipedia table of state assembly elections):
2017-12-18 (Gujarat, Himachal) | 2018-05-15 (Karnataka) | 2018-12-11 (Rajasthan, MP, Chhattisgarh, Telangana, Mizoram) | 2019-10-24 (Maharashtra, Haryana) | 2020-11-10 (Bihar) | 2021-05-02 Sunday -> 2021-05-03 (West Bengal, Tamil Nadu, Kerala, Assam, Puducherry) | 2022-03-10 (UP, Punjab, Uttarakhand, Goa, Manipur) | 2022-12-08 (Gujarat, Himachal) | 2023-03-02 (Tripura, Meghalaya, Nagaland) | 2023-05-13 Saturday -> 2023-05-15 (Karnataka) | 2023-12-03 Sunday -> 2023-12-04 (MP, Rajasthan, Chhattisgarh, Telangana) | 2024-11-23 Saturday -> 2024-11-25 (Maharashtra, Jharkhand) | 2025-11-14 (Bihar) | 2026-05-04 (West Bengal, Tamil Nadu, Kerala, Assam, Puducherry).
Event days in TRAIN (2017-04..2023-12): 11. In TEST (2024-26): 3.

## Tier B - US presidential results and major foreign votes
US election-night results -> the next Indian session: 2012-11-07 (US election 2012-11-06), 2016-11-09 (2016-11-08), 2020-11-04 (2020-11-03), 2024-11-06 (2024-11-05). Major foreign referendums (Brexit-type): 2016-06-24 (Brexit, same Indian session), 2016-12-05 (Italian constitutional referendum). Official dates: US Federal Election Commission / state calendars; UK Electoral Commission; Italian Interior Ministry.
Event days in TRAIN: 1 (2020-11-04). In TEST: 1 (2024-11-06). In the 2012-16 holdout: 2012-11-07, 2016-06-24, 2016-11-09, 2016-12-05.
Pre-declared minimum for a TRAIN test: >= 6 event days. Tier B has 1, so it is NOT TESTED on TRAIN; it stays for the holdout, if the owner releases it.

## Tier C - US FOMC scheduled decision days (reaction session = next Indian trading day after the US announcement date)
Source: federalreserve.gov FOMC meeting calendars (2017 tentative-then-held schedule, 2018-2026 historical and current calendar pages). Scheduled meetings only; the unscheduled meetings of 2020-03-03 and 2020-03-15 and the cancelled 2020-03-18 meeting are not in the list. Announcement dates inside the data (2017-04-03 .. 2026-10-30):
2017: May 3, Jun 14, Jul 26, Sep 20, Nov 1, Dec 13 | 2018: Jan 31, Mar 21, May 2, Jun 13, Aug 1, Sep 26, Nov 8, Dec 19 | 2019: Jan 30, Mar 20, May 1, Jun 19, Jul 31, Sep 18, Oct 30, Dec 11 | 2020: Jan 29, Apr 29, Jun 10, Jul 29, Sep 16, Nov 5, Dec 16 | 2021: Jan 27, Mar 17, Apr 28, Jun 16, Jul 28, Sep 22, Nov 3, Dec 15 | 2022: Jan 26, Mar 16, May 4, Jun 15, Jul 27, Sep 21, Nov 2, Dec 14 | 2023: Feb 1, Mar 22, May 3, Jun 14, Jul 26, Sep 20, Nov 1, Dec 13 | 2024: Jan 31, Mar 20, May 1, Jun 12, Jul 31, Sep 18, Nov 7, Dec 18 | 2025: Jan 29, Mar 19, May 7, Jun 18, Jul 30, Sep 17, Oct 29, Dec 10 | 2026: Jan 28, Mar 18, Apr 29, Jun 17, Jul 29, Sep 16, Oct 28 (Dec 9 is after the data).
Event days in TRAIN: 53. In TEST: 23.

## How dates get added later
Append new dates to this file with the announcement source and date BEFORE the event day. Next known items: Union Budget 2027 (date to be announced), FOMC 2026-12-09 and the 2027 calendar, state elections due in 2027 (to be listed when the ECI announces counting days).
