# Brief: 3 bed 2 bath apartment in Riverton

- Workstream: apartment-search
- Kind: search/decide
- Plan first: yes: the search split, the fields per listing, and how photos get checked, before many agents start
- Goal: find about 10 listings of a 3 bed 2 bath apartment in Riverton
- Decision: unknown: which listing will you tour or apply for, and by when?
- Context: you, your partner and one other tenant; the split is 2600 for the couple and 1700 for the other tenant; no listings or sites named yet
- Must-haves:
  - [m1] 3 bed, 2 bath, in Riverton (proof: the listing page)
  - [m2] little to no carpet; carpet only in the bedrooms is fine, none in the living room (proof: a photo of the living room, not the description)
  - [m3] budget up to 5k if it's really good (hedged, confirm)
  - [m4] if a result is under the max, also peek the next 100 dollars up to see what else is there
  - investigate: does each listing's "updated" claim hold up in its photos?
- Taste (flag, don't filter): modern, not a nineties place; shown by photos of the kitchen and bathrooms, with no dated fixtures or finishes
- Output: a ranked list of about 10 listings; fields unknown
- Verify:
  - m1: `python3 check_listings.py --beds 3 --baths 2 --city Riverton listings.csv` every claim names its listing link or photo, or says guess; descriptions are never proof. A second agent that did not do the search checks the first one's work, like a senior reviewing a junior.
  - m2: `python3 check_photos.py --room living_room --no-carpet listings.csv` The check needs a way to open listing photos
  - m3: `python3 check_listings.py --max-rent "$CAP" listings.csv`
  - m4: `python3 check_listings.py --peek-over 100 listings.csv`
- If stuck: report only, take no action on any listing; never loosen a must-have without asking
- Skills:
  - none run yet
  - how: one agent per source, run in parallel
  - save what worked for next time, with your approval for each rule
- Parking lot: a cousin found a place through a Facebook group, worth a look? (not acted on)
- Unknowns:
  - unknown: is 5k the hard cap for rent, and what is your target below it?
  - unknown: which listing sites or sources should the search use?
  - unknown: which fields do you want for each listing?
  - unknown: what is the move-in date?
  - unknown: which decision is this result for?

## Questions

1. Is 5k the hard cap for rent, and what is your target below it?
2. Which decision is this for (tour, apply), and by what move-in date?
3. Which sites should I search, and which fields do you want per listing?
