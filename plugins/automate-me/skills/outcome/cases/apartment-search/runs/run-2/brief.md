# Brief: 3 bed apartment in Riverton

- Kind: search/decide
- Plan first: yes: show the sources and filters before the search starts.
- Goal: Find about 10 listings for a 3 bed 2 bath apartment in Riverton and rank them.
- Decision: Pick the top 3 to tour this weekend.
- Context: Three people. The couple pays 2600 and the other tenant pays 1700. The speaker said "we can go up to 5k if it's really good."
- Must-haves:
  - [m1] 3 bed and 2 bath, in Riverton. Proof is the listing page.
  - [m2] Budget cap of 4300 a month. Proof is the listing price.
  - [m3] Move-in by March 1, in Northgate or Elm Park.
- Taste:
  - Modern, flag don't filter. Visible signal in the photos: updated kitchen and bath, no dated fixtures.
  - Little to no carpet; carpet only in the bedrooms is fine. Flag, don't filter. Visible signal is the floor in the living room photos.
- Output: 10 listings, ranked. Fields: link, price, beds, baths, carpet seen, modern seen, photo used as proof, flags.
- Verify:
  - m1: `python3 check_listings.py --beds 3 --baths 2 --city Riverton listings.csv` Check the photos, not the descriptions; the speaker said the descriptions lie. A second reviewer checks the list like a senior reviewing a junior, before it comes back.
  - m2: `python3 check_listings.py --max-rent 4300 listings.csv` Every claim names the listing link or the photo behind it, or says guess.
  - m3: `python3 check_listings.py --move-in 2026-03-01 --areas "Northgate,Elm Park" listings.csv`
- If stuck: if fewer than 10 listings fit under the cap, peek the next 100 dollars up and mark those as over. Stop after one peek. Never loosen a must-have without asking. Report only; contact no landlord.
- Skills:
  - how: search the sources in parallel, not one at a time, one agent per source.
  - No plugin skill fits the search. The run needs a browser tool that can open listing photos; check it works first.
  - After the run, if something great turns up, offer once to save what worked, using the learn-from-run playbook.
- Parking lot:
  - A Facebook group the speaker's cousin used. Not searched unless asked.
- Unknowns:
  - unknown: Do any of you have pets the place must allow?

## Questions

1. Do any of you have pets the place must allow?
