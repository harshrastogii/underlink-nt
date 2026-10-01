# Ethics and data rules

Underlink uses public data about telecommunications infrastructure in places
where most residents are Aboriginal people. The data are public. How we combine
and publish them is our choice, and these are the rules we set for ourselves.
The code enforces some of them; the tests named below check those.

No community, land council or Aboriginal organisation has reviewed any output
of this project. We built it in a few days from published data only. We did no
fieldwork, interviews or surveys, so there were no human participants. Any next
step that involves communities needs their agreement first, and would need
ethics approval (for example through the CDU Human Research Ethics Committee)
and a land council research permit.

## 1. The network is the object of study

We describe radio relays, fibre towns, power backup and repair access. We do
not describe people or communities as weak, vulnerable or disadvantaged. The
finding is about a network design: 18 of 23 larger radio-chain places depend on
at least one relay with no alternative licensed path. That is a statement about
Telstra's licensed links, not about the people who live there.

Words such as "vulnerable" and "disadvantaged" are banned from the community
card, and `tests/test_card_strings.py` checks for them.

## 2. Nothing is published to a community without consent

Every output moves through a publication state machine in
`src/underlink/governance.py`:

```
DRAFT -> COMPUTED -> COMMUNITY_REVIEW -> CUSTODIAN_APPROVED -> PUBLISHED
                          any state  -> WITHHELD
```

- Code, including any AI tool, can only take an output from DRAFT to COMPUTED.
- Only the team can put an output in front of a community for review.
- Only the custodian can approve it. PUBLISHED can only follow CUSTODIAN_APPROVED.
- Only the custodian can withhold an output, from any state, including after it
  was published.

`tests/test_governance.py` checks each of these rules. Today every Underlink
output is at COMPUTED. Nothing has reached COMMUNITY_REVIEW.

## 3. The community chooses the custodian

We do not decide who speaks for a community. The custodian might be a land
council, an Aboriginal community controlled organisation, a local authority or
someone else the community names. Land councils cover the region, but a
community may prefer its own organisation.

## 4. Public numbers are aggregated and small counts are hidden

- Public counts are given for two land council groups only (Central; and the
  Northern, Tiwi and Anindilyakwa councils together), never ranked by community.
  With four separate regions, the two island councils had counts of 1 or 2 that
  anyone could recover by subtracting from the published totals. A test now
  fails if any hidden cell can be recovered that way.
- A count of places from 1 to 2 is shown as `<3`. A count of people below 10 is
  suppressed. Zero stays zero, because an empty cell reveals nothing about a
  community. `tests/test_suppression.py` checks the public region table and
  `numbers.json`.
- Shipped coordinates are rounded to 0.01 degrees (about 1 km).
- Five places are named in the report and slides, and in numbers.json: Ampilatwatja,
  Galiwin'ku, Milingimbi, Wadeye and Borroloola. Each had an outage that was
  reported in the news. We quote their chain class only, so the reader can check the
  method against a known event. The public web app names no community (tested).
- Any output about a real community is written only after its custodian releases it.
  `governance.require_release` is that gate: automated steps cannot reach PUBLISHED,
  and the card builder refuses a real community without a custodian's release
  (`test_card_for_a_real_community_needs_a_custodian_release`).
- Community language text, recordings, symbols and local knowledge added to a card
  belong to that community. The MIT licence covers the code, not them.

## 5. Relay details stay in a restricted tier

A list of the relays that many communities depend on, with their locations,
could help someone who wants to cause an outage. So:

- Relay site ids are replaced by salted hashes before anything is written.
- Relay keys, relay coordinates and per-place chains sit in
  `outputs/restricted/`, which git ignores and the submission does not ship.
- `tests/test_public_outputs.py` scans every public file and every file under
  `docs/` for relay keys and for site or coordinate columns.

The ACMA register is itself public and updated daily. The restricted tier does
not make the underlying facts secret. It means our processed files are not a
ready-made list of weak points. The restricted material is meant for
conversations with the network owner and emergency planners.

## 6. Land tenure is a flag, never a ranking

Building on Aboriginal land needs a lease under section 19 of the Aboriginal Land
Rights (Northern Territory) Act 1976, with traditional owner consent through the
land council. The Central Land Council says this takes at least six months. A new tower on
native title land is a future act under section 24KA of the Native Title Act
1993. Any recommendation Underlink makes about new links would carry these as
lead-time and consent flags. Tenure is never used to score or rank places.

## 7. No sacred site data

We do not collect, derive or display sacred site locations. The NT Aboriginal
Sacred Sites Act 1989 protects them, and section 38 restricts recording or
passing on information of a secret nature. The AAPA register is not complete, so
the absence of a recorded site proves nothing. Any suggestion of a place for
new equipment must say it is subject to an AAPA Authority Certificate.

## 8. No machine translation

The community card is in plain English only. The NT has many Aboriginal
languages, and the Aboriginal Interpreter Service works in about 39 of them. We
do not machine-translate into any Aboriginal language. A translated version
would be made by a qualified interpreter and checked by the community.

## 9. Safety wording about 000 must be accurate

The card says what works in an outage and what does not. It must never tell
people to go outside during a cyclone to find signal, and it must not suggest
that 000 can be reached by SMS. `tests/test_card_strings.py` checks the
required and forbidden phrases. Emergency advice on the card should be checked
by NT Emergency Service before any real use.

## 10. Honest about consultation

We say plainly, in the README, the report and on the card, that no community has
reviewed this work. We do not describe the project as co-designed, and we do
not claim community support we do not have.

## Sources

- Global Indigenous Data Alliance (2019). CARE Principles for Indigenous Data Governance: Collective benefit, Authority to control, Responsibility, Ethics.
- Maiam nayri Wingara Indigenous Data Sovereignty Collective (2018). Indigenous Data Sovereignty Communique, Indigenous Data Sovereignty Summit, Canberra.
- AIATSIS (2020). AIATSIS Code of Ethics for Aboriginal and Torres Strait Islander Research.
- NHMRC (2018). Ethical conduct in research with Aboriginal and Torres Strait Islander Peoples and communities: Guidelines for researchers and stakeholders.
- National Agreement on Closing the Gap (2020). Priority Reform 4: Shared access to data and information at a regional level.
- Aboriginal Land Rights (Northern Territory) Act 1976 (Cth), sections 19 and 70.
- Native Title Act 1993 (Cth), section 24KA.
- Northern Territory Aboriginal Sacred Sites Act 1989 (NT), sections 33 to 38.
- Information Act 2002 (NT), Schedule 2 Information Privacy Principles, including IPP 8 (anonymity) and IPP 10 (sensitive information).
