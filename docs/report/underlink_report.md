---
title: Underlink
subtitle: Revealing the Hidden Dependencies Behind NT Connectivity
kind: Data analysis report
event: "CDU IT Code Fair 2026, Data Innovation Challenge: Remote Connectivity"
team: Team DIC017
members:
  - "Harsh Rastogi: network and spatial analysis, data pipeline, prototype"
  - "Aashish: New Zealand research, suggestions on report and slides"
date: 30 September 2026
acknowledgement: We acknowledge the Larrakia people, Traditional Owners of the land on which Charles Darwin University's Darwin campuses stand, and the Traditional Owners of all the Country this report discusses. This report contains no images, names or voices of people.
---

# Summary

Coverage maps show where a phone should get signal on a normal day. They do not show what that signal depends on, and recent Northern Territory outages hit places the maps show as covered. Wadeye lost service on and off for nine weeks in early 2026 after floods damaged its fibre link and cut power.

We read the public ACMA licence register as a network: 358 Telstra radio sites joined by 313 point-to-point links. For each remote place we traced the path to fibre and found every single-path relay (a relay that all licensed radio paths from the place to fibre must pass through). Of the 23 larger places that reach fibre over a radio chain, 18 (about 7,100 people) depend on at least one single-path relay, and 16 of those 18 sit inside Telstra's predicted 4G coverage. None of the 68 single-path relays is in the Mobile Network Hardening Program, so their battery hours are not public. In the wet season, repairs for 17 of the 23 places wait on crews reaching radio sites off the sealed road.

The Python prototype runs offline and gives each audience its own output: a draft card for communities, regional counts for government, and a restricted relay register for carriers. It uses public data only; no community has reviewed it. We recommend that the NT Government make backhaul type, battery hours and outage logs a condition of co-investment, and that each community decide how outputs about it are used.

# 1 Introduction

The challenge asks teams to find areas of limited or unreliable connectivity. Public data describes limited coverage well. The NT Government estimates that mobile coverage reaches about 5% of the Territory's land area, against about 30% nationally [1], and that about 130 remote communities have a payphone as their only telecommunications service [2]. Carriers publish coverage predictions, the ACCC publishes carrier site lists [3], and the Australian Digital Inclusion Index scores access and affordability [4].

Unreliable service is harder to see, because it happens in places that count as covered. In March 2024, solar-powered sites near Borroloola failed during Ex-Tropical Cyclone Megan when their batteries could not recharge under cloud, and crews could reach them only by helicopter [5]. In late 2024, Ampilatwatja lost mobile service for about a week while Telstra upgraded its site, and the community's health service lost contact with its outstation clinics [6]. From February to April 2026, Wadeye had rolling outages for nine weeks, and people could not reach 000 or top up prepaid power cards [7]. In June 2026 a fibre break left parts of the Territory offline for about a day while crews travelled about 1,000 km to fix it [8].

Planners need to know what each place's service depends on and how long it could stay down. Carriers hold that information and do not publish it. The 2024 Regional Telecommunications Review recommended a national data platform that gives governments restricted access to infrastructure locations for investment and emergency planning (Recommendation 6) [9]. The First Nations Digital Inclusion Advisory Group asked for formal data sharing with telcos and a granular national connectivity map (recommendations 2.2 and 2.4) [10].

Underlink rebuilds part of that picture from public data, in a way we have not seen for the NT. It reads the ACMA licence register as a network and finds, for every place, the relays its service cannot route around. The closest published work maps climate-hazard exposure of cell sites worldwide but does not trace backhaul [13]. Underlink then adds cyclone tracks, published backup power, road access for repair crews, and the phones that may still work when the tower is down. It serves three audiences: people in remote communities, managers in the NT Department of Corporate and Digital Development (DCDD), and carrier field teams. No community has reviewed it, and Section 4 sets out what has to happen before anyone releases an output about a named community.

# 2 Methodology

## 2.1 Data

We used the eight datasets the organisers suggested and ten more (Table 1). A manifest records each source's URL, licence, retrieval date, MD5 hash and row count. A preparation script turns about 2 GB of downloads into 0.7 MB of tables. In that step it replaces radio site identifiers with salted hashes (the salt stays in the restricted folder and is not shipped) and rounds every radio-site and place coordinate to 0.01 degrees (about 1 km).

TABLE: Table 1. Data sources. An asterisk marks the datasets the organisers suggested. Licences and URLs are in DATA_LICENCES.md and data/manifest.csv.
| Source (publisher) | What Underlink takes from it | Decision it informs |
|---|---|---|
| Register of Radiocommunications Licences, bulk extract (ACMA)* | 808 NT point-to-point link records licensed to Telstra | Which relays get battery and satellite checks first |
| Remote communities with mobile coverage, 2021 (NTG)* | 782 places, their type and recorded mobile status | Place list; register refresh |
| Remote communities with backhaul transmission, 2019 (NTG) | 44 towns with optic-fibre backhaul | Where radio chains end |
| Mobile Infrastructure Report data, 2018 to 2026 (ACCC)* | Telstra 4G outdoor prediction; other carriers' sites | Predicted coverage; second network for 000 |
| Tropical cyclone best track (BoM)* | Five replayed tracks; exposure since 1980 | Where to act before the wet |
| First Nations Connectivity Mapping Tool layers (DITRDCSA, NIAA)* | Satellite Wi-Fi phones, payphones, Wi-Fi hubs | Which fallbacks the community card lists |
| NBN footprints, 2024 (NBN Co)* | Fixed-line and fixed-wireless extent | Whether fixed nbn is a fallback (for 96% of places it is not) |
| ADII 2025 (RMIT and partners)*; Census (ABS)* | Access scores; last small-area internet data (2016) | Context only |
| Mobile Network Hardening Program, STAND Sky Muster, Mobile Black Spot Program, First Nations Community Wi-Fi 2026 funded list (DITRDCSA) | Backup-power items; satellite sites; funded towers and Wi-Fi | Power measure; fallbacks; avoid funded work |
| National Roads (Geoscape); land council boundaries (NTLIS) | Sealed roads; four regions | Repair access; public aggregation |
| Remote communities bushfire risk, 2020 (NTG) | Population estimates | Aggregated people counts |
| Outage register (nbn); mobile coverage audit (DITRDCSA) | NT outage durations; 595 audited road tiles | Outage table; coverage checks |

## 2.2 Tracing each place back to fibre

We built a graph from the 808 NT point-to-point link records licensed to Telstra Limited in the ACMA register [11]. Each direction and frequency of a link is licensed separately, so merging the records that describe the same pair of sites leaves 358 sites and 313 links in 51 separate pieces. A radio site within 10 km of a fibre town counts as fibre-connected. The fibre towns are the 44 places the NT Government's 2019 register lists with optic-fibre backhaul, plus five regional centres. Each of the 782 places in the NT Government's 2021 community register is matched to the nearest licensed radio site within 10 km, which stands in for the site serving the place.

A single-path relay for a place is a relay that every licensed radio path from the place's site to fibre must pass through. We find these relays exactly with a dominator tree [12, 25]. Every fibre-connected site is joined to one imaginary source, and a relay dominates a place's site when removing it cuts the site off from that source. Each place then falls into one class: at a fibre town, on a radio chain, on a radio island (licensed links but no radio path to fibre, so probably satellite or backhaul we cannot see), or with no licensed radio site nearby. We report place results for the 116 larger places (NT Government types Town, Major, Minor and Village), whose names and locations we could check by hand. Relay counts use all 782 places.

FIGURE: outputs/public/figures/fig2_pipeline.png | 14.5 | Figure 1. How Underlink works. The chain analysis and four other measures are reported side by side and never merged into one score.

## 2.3 Four measures reported beside the chains

Four measures sit beside the chain analysis (Figure 1). We keep them separate because one combined score hides trade-offs. Given $10 million and the 394 places with no predicted coverage or funded work nearby, a single people-per-dollar score picked 42 satellite Wi-Fi sites and no towers, even with a tower costed at $1 million (Appendix C). It cannot see roads, travel or whether service lasts.

**Hazard replay.** We join each cyclone's six-hourly positions into a line, remove every relay within 100 km of it, and re-trace every place. A place is exposed if it loses its path to fibre. We call the exposure upstream-only when the storm missed the place and its own site but cut a relay further along the chain. We replay Monica (2006), Lam (2015), Trevor (2019), Megan (2024) and Narelle (2026) from the Bureau of Meteorology best-track database [14]. This measures exposure; it does not claim these outages happened.

**Power.** We match the 25 Mobile Network Hardening Program items (21 locations) [15] to radio sites within 3 km. A relay that matches nothing may still have batteries, since remote repeaters are usually solar-powered. What is missing is public information on how long those batteries last.

**Repair window.** Days to restore a radio site are 0.5 days on site, plus travel from the nearest of five assumed crew bases (Darwin, Katherine, Tennant Creek, Alice Springs and Nhulunbuy), plus a wet-season delay of 30 days from November to April when the site is more than 10 km from a sealed road. These values are assumptions. We sweep the delay (14, 30 and 60 days) and the distance (5, 10 and 20 km) and report the resulting range.

**What still works.** For each place we count satellite Wi-Fi phones, Sky Muster sites and payphones within 3 km, and other carriers' sites within 10 km. A mobile 000 call uses any carrier's network in range [16], so a second carrier's tower nearby can carry 000 calls when Telstra's is down.

## 2.4 Checks

Automated tests check the graph counts, the headline numbers and the privacy rules. We rerun the chain classes across nine combinations of fibre radius and site radius (5, 10 and 15 km each), and compare the results with outages reported in the news (Section 3.5). One command regenerates every number and figure in this report from the shipped data.

# 3 Findings

## 3.1 Most radio-chain places depend on a single-path relay

Of the 116 larger places, 71 have a licensed radio site within 10 km. Of these, 34 sit at a fibre town, 23 reach fibre over a radio chain and 14 are radio islands. The 23 radio-chain places are home to about 9,000 people (NT Government 2020 estimates). Their chains have a median of 4 radio links and a maximum of 6. Eighteen of the 23, about 7,100 people, depend on at least one single-path relay, and 12 depend on three or more (Figure 3). Across the nine sensitivity runs the number of radio-chain places moves from 18 to 30, but the share with a single-path relay stays between 78% and 84% (Table C2), and 18 of the 23 places stay on a radio chain in every run. Fibre or satellite links the register cannot show can only remove single-path relays from these 23 chains, so for them 18 is an upper bound; such links could also join a radio island to fibre and add a chain. Recommendation 1 is how to check both.

Sixteen of the 18 sit inside Telstra's predicted 4G coverage for 2026. Ampilatwatja is one of them (Figure 2). Its site reaches fibre through five single-path relays in a row. Its week without mobile service in late 2024 came from planned upgrade works [6]. Galiwin'ku, home to about 2,450 people, also reaches fibre through five single-path relays in a row. In March and April 2024 it lost reception every night for 12 nights because a solar-powered Telstra site could not keep its batteries charged [17]. None of the five single-path relays on its chain is in the Hardening Program, and public data cannot show whether one of them is that solar site.

FIGURE: outputs/public/figures/fig1_hero_chain.png | 13 | Figure 2. Ampilatwatja's licensed radio path to fibre, drawn without locations. Five single-path relays sit in a row, and the community is inside Telstra's predicted 4G coverage.

Fibre may close some chains. The licensed radio links form 6 loops on their own, and 20 once all fibre towns are treated as linked. Fibre towns carry their own risk. Of the 23 radio-chain places, 18 (16 of them also in the single-path group) reach only one fibre town over licensed radio, so a fibre break like June 2026's [8] would cut them too.

FIGURE: outputs/public/figures/fig3_spof_distribution.png | 9 | Figure 3. 18 of the 23 larger radio-chain places depend on at least one single-path relay, and 16 of those 18 sit inside Telstra's predicted 4G area.

## 3.2 No single-path relay is in the Hardening Program

Across all 782 places there are 68 single-path relays. None of them is in the Mobile Network Hardening Program, so how long each runs on battery is not public. The 11 radio sites that do match a Hardening Program item sit at communities or fibre towns. Nineteen of the 68 are within 150 km of a portable-generator depot listed in the program [15]. For the other 49, no public source names any backup power (Figure 5). Twenty-seven of the 68 had the tracks of five or more cyclones, including their low stages, pass within 100 km between 1980 and 2026. Forty-three are more than 10 km from a sealed road, and 26 sit on Aboriginal Land Trust land, where new works need a section 19 lease.

## 3.3 Most cyclone exposure is local

Across the five replays at 100 km there were 22 cases of a larger radio-chain place losing its path to fibre (Figure 4). In 18 of them the storm passed within 100 km of the place or its own site. The other 4 were upstream-only, three in Lam (2015) and one in Narelle (2026). Across six variants (50, 100 and 150 km; whole track or the gale-strength part only), exposures range from 9 to 25 and upstream-only cases from 0 to 4.

FIGURE: outputs/public/figures/fig4_replay.png | 10 | Figure 4. Cases of a larger radio-chain place losing its path to fibre when relays within 100 km of each cyclone track are removed. Whiskers show the range across six variants. Bars show exposure, not recorded outages.

## 3.4 In the wet, road access sets the repair time

In July, 17 of the 23 radio-chain places fall in the under-one-day band and the other 6 in one to three days; the median drive from a crew base is about four hours. January looks different. Seventeen of the 23 rise above 14 days, including 11 that take under a day in July. Each of the 17 has a radio site on its chain more than 10 km from a sealed road, a single-path relay for 15 of them and the place's own site for 2. That count stays between 16 and 18 across all nine combinations of delay and distance. The day counts rest on our assumed delay; the list of 17 places comes from road distance alone.

FIGURE: outputs/public/figures/fig5_repair_power.png | 13.5 | Figure 5. Top: indicative repair window for the 23 radio-chain places in July and January; the wet-season delay is an assumption swept from 14 to 60 days. Bottom: public information about backup power at the 68 single-path relays.

## 3.5 What still works, and where the model fails

Only 1 of the 23 radio-chain places has another carrier's site within 10 km, so in the other 22 a mobile 000 call has no second network to use. A second carrier on a shared tower may also share its backhaul. Eight have a satellite Wi-Fi phone or a Sky Muster site within 3 km. Twenty-one have a payphone within 3 km, but no public source says which payphones use satellite and which share the mobile tower's path.

The model puts Ampilatwatja and Galiwin'ku on long single-path chains, which fits their reported outages (Table 2). It does not flag four events: Borroloola in 2024, a fibre town where batteries ran flat; Milingimbi in 2024, which it shows with no single-path relay; Wadeye in 2026, which has no licensed radio site within 10 km and failed through fibre and power; and the June 2026 fibre break. Each miss traces to data carriers hold and do not publish: battery hours, fibre routes and which sites serve which places. We cannot measure how often the model flags a place that never loses service, because no community-level outage history was public before carrier registers began in 2026 [18]. Communities hold that history, and Recommendation 6 lets them record it under their own control.

TABLE: Table 2. Underlink against reported outages. The four misses trace to fibre, battery or site data that only carriers hold.
| Reported event | Reported cause | Underlink, from public radio data | Result |
|---|---|---|---|
| Ampilatwatja, late 2024 [6] | Planned upgrade works, about one week | Radio chain; 5 single-path relays | Consistent, though the outage was planned works |
| Galiwin'ku, March to April 2024 [17] | Solar Telstra site ran its batteries flat at night, 12 nights | Radio chain; 5 single-path relays, none in the Hardening Program | Fits, if the solar site is on its chain |
| Milingimbi, March to April 2024 [17] | Nightly losses for 10 days; cause not given | Radio chain; no single-path relay | Not flagged. The register does not show which site serves which place |
| Borroloola, March 2024 [5] | Solar batteries flat under Ex-TC Megan | Fibre town; not flagged | Missed. Battery hours are not public |
| Wadeye, February to April 2026 [7] | Flood damage to fibre; power cut | No licensed radio site within 10 km | Missed. Fibre routes are not public |
| Parts of the NT, June 2026 [8] | Fibre break | Not flagged | Missed. Fibre routes are not public |

# 4 Discussion: ethical, cultural and community impacts

Underlink studies a carrier's network, so every finding describes equipment, links and missing data. This report names a community only where news reports already named it, and only to test the model against that event; the prototype's public outputs name none. We avoid what Walter calls BADDR data, data that is blaming, aggregate, decontextualised, deficit-based and restricted [19]. We follow the CARE principles [20] and the Maiam nayri Wingara principles of Indigenous data sovereignty [21]. Table 3 lists the rules and how the code enforces them.

TABLE: Table 3. Rules the prototype follows.
| Rule | Source | How Underlink applies it |
|---|---|---|
| Analyse the network and never rank communities | CARE principles; Walter's BADDR critique | Public outputs hold only regional counts; a test rejects any public table with place keys or names |
| Communities see and control data about them | Closing the Gap Priority Reform 4; Maiam nayri Wingara | Automated steps can compute a result but cannot publish it; only a custodian the community chooses can approve or withhold (tested) |
| Protect small places | NT Information Act 2002; ABS practice | A dot on an NT map names a community, so public outputs use land council regions only, suppress counts under 3 places or 10 people, and round coordinates |
| Limit who sees relay details | RTIRC Recommendation 6 | Relay register only for DCDD and carriers; hashed identifiers in shipped data |
| Use land tenure only to flag permit lead time | Aboriginal Land Rights (NT) Act 1976; Native Title Act 1993; NT Aboriginal Sacred Sites Act 1989 | The relay register flags the 26 single-path relays on Aboriginal Land Trust land, where new works need a section 19 lease (at least six months [26]); no sacred-site data is used or inferred |
| Translation by paid interpreters only | AIATSIS Code of Ethics 2020 | Blank language panel for paid interpreters; no machine translation |
| Safe emergency wording | ACMA emergency call rules [16] | Card text tested for required and forbidden phrases |


The community card is a draft for co-design. Each item on the card has a colour, one word and a symbol, and a blank panel is left for text in the community's language, written and voiced by paid interpreters from the Aboriginal Interpreter Service. We will not machine-translate it. The card never shows the Underlink name next to a community's name. Following Kutay [22], the card's layout, symbols and wording are all open to change in co-design. Only the 000 facts are fixed, because they are ACMA safety rules: make a voice call, which will use any network in range; 000 is free from payphones; 000 cannot be reached by SMS; in a cyclone, stay in shelter.

About 90% of mobile users in remote First Nations communities are on prepaid plans [10]. At Wadeye in 2026, the same outages stopped people topping up prepaid power cards [7], so households could lose electricity as well as phones. Satellite service that connects straight to ordinary phones will cover part of this. The Universal Outdoor Mobile Obligation Bill, if passed, requires outdoor voice and SMS coverage from 1 December 2027 [23]. It will not carry telehealth, store card payments or power top-ups, so the dependencies mapped here still matter after 2027.

**Limitations.** The ACMA register shows only licensed radio. Fibre and satellite backhaul are missing, fibre towns are assumed to be sound, and the nearest site is not proof of the serving site. Replays show exposure without probabilities. Repair parameters are assumptions. Population figures are 2020 estimates, and homeland populations change with the seasons.

# 5 Recommendations

1. DCDD makes three restricted fields per site a condition of NT co-investment in the next round with carriers: backhaul type (fibre, radio or satellite), battery hours, and a three-year outage log. This extends the restricted government access to asset locations that RTIRC Recommendation 6 proposes. Measure: all three fields held for the 68 single-path relays before the 2027-28 wet season.
2. By 1 October each year, DCDD sends Telstra the list of single-path relays, starting with the 43 more than 10 km from a sealed road, and asks for confirmed battery hours and satellite failover at each. Measure: the share of the 43 with confirmed battery hours by 1 November.
3. DCDD's data warehouse loads the carrier outage registers into Underlink's outage table each month and reports one KPI, outage hours per radio-chain place per wet season. The registers list only significant outages (250 or more services in remote areas), so DCDD also asks carriers for smaller ones. Observed repair times then replace our assumed ones.
4. The NT Government refreshes its 2019, 2021 and 2022 connectivity registers with an "as at" date. In the 2021 register, 698 of 782 places have no recorded mobile status, and 11 of the 17 places listed without coverage now sit inside Telstra's predicted coverage.
5. Governments keep payphones on homelands, as the Central Land Council asked in 2024 [24], keep the satellite Wi-Fi phones working, and publish which payphones use satellite, so the card can say which ones work when the tower is down.
6. After the 2026-27 wet season, CDU and DCDD test the card with one community that chooses to take part, under CDU human research ethics approval and land council permits, with paid interpreters and a custodian the community chooses (for example its Aboriginal community-controlled organisation or local authority). That community decides what the card says, holds the data, and can record the outages it notices under its own control.

# References

1. Northern Territory Government (2024, July). Regional Telecommunications Review 2024: Northern Territory Government submission. https://www.infrastructure.gov.au/sites/default/files/documents/rtirc-2024-ntg-submission.pdf
2. Northern Territory Government (2024, February). Better delivery of baseline universal telecommunications services: Northern Territory Government submission. https://www.infrastructure.gov.au/sites/default/files/documents/bdus2024-nt-government.pdf
3. Australian Competition and Consumer Commission (2026). Mobile Infrastructure Report data release. https://data.gov.au/data/dataset/accc-mobile-infrastructure-report-data-release
4. Thomas, J. et al. (2025). Australian Digital Inclusion Index 2025. RMIT University, Swinburne University of Technology and Telstra. https://digitalinclusionindex.org.au/
5. Australian Associated Press (2024). Phone towers down as ex-tropical cyclone heads west. https://aapnews.aap.com.au/news/phone-towers-down-as-ex-tropical-cyclone-heads-west
6. SBS NITV (2024, November). 'Lives at risk' as Telstra cuts remote phone connection. https://www.sbs.com.au/nitv/article/lives-at-risk-as-telstra-cuts-remote-phone-connection/7e3b5yzhe
7. ABC News (2026, 7 April). NT community Wadeye experiences weeks of rolling Telstra outages. https://www.abc.net.au/news/2026-04-07/nt-community-wadeye-experiences-weeks-of-rolling-telstra-outages/106535008
8. NT Independent (2026). Ongoing Telstra outage affecting parts of NT, crews coming from 1000 kms away. https://ntindependent.com.au/ongoing-telstra-outage-affecting-parts-of-nt-crews-coming-from-1000-kms-away/
9. Regional Telecommunications Independent Review Committee (2024). 2024 Regional Telecommunications Review: final report. https://www.infrastructure.gov.au/department/media/news/2024-regional-telecommunications-review-report-now-available
10. First Nations Digital Inclusion Advisory Group (2023). Initial report. https://www.digitalinclusion.gov.au/sites/default/files/documents/first-nations-digital-inclusion-advisory-group-initial-report.pdf
11. Australian Communications and Media Authority (2026). Register of Radiocommunications Licences, bulk data (retrieved 29 September 2026). https://www.acma.gov.au/radiocomms-licence-data
12. Hagberg, A., Schult, D. and Swart, P. (2008). Exploring network structure, dynamics, and function using NetworkX. Proceedings of the 7th Python in Science Conference, 11-15.
13. Oughton, E. et al. (2026). Global vulnerability assessment of mobile telecommunications infrastructure to climate hazards using crowdsourced open data. Nature Communications. https://doi.org/10.1038/s41467-026-76197-w
14. Bureau of Meteorology (2026). Australian tropical cyclone best track database (IDCKMSTM0S). https://www.bom.gov.au/clim_data/IDCKMSTM0S.csv
15. Department of Infrastructure, Transport, Regional Development, Communications, Sport and the Arts (2026). Mobile Network Hardening Program, STAND and Mobile Black Spot Program spatial services. https://spatial.infrastructure.gov.au/server/rest/services
16. Australian Communications and Media Authority (2026). Emergency calls. https://www.acma.gov.au/emergency-calls
17. ABC News (2024, 4 April). Telstra leaves Galiwin'ku without mobile reception for 12 consecutive nights, Milingimbi also impacted. https://www.abc.net.au/news/2024-04-04/galiwinku-and-milingimbi-without-telstra-mobile-coverage-nt/103658508
18. Australian Communications and Media Authority (2026). Telcos required to publish outage registers from 30 June. https://www.acma.gov.au/articles/2026-03/telcos-required-publish-outage-registers-30-june
19. Walter, M. (2018). The voice of Indigenous data: beyond the markers of disadvantage. Griffith Review, 60. https://www.griffithreview.com/articles/voice-indigenous-data-beyond-disadvantage/
20. Global Indigenous Data Alliance (2019). CARE Principles for Indigenous Data Governance. https://www.gida-global.org/care
21. Maiam nayri Wingara Indigenous Data Sovereignty Collective (2018). Indigenous Data Sovereignty Summit communique. https://www.maiamnayriwingara.org/
22. Kutay, C. (2021). Knowledge elicitation with Aboriginal Australian communities. Australasian Journal of Information Systems, 25. https://doi.org/10.3127/ajis.v25i0.2907
23. Parliament of Australia (2026). Telecommunications Legislation Amendment (Universal Outdoor Mobile Obligation) Bill 2026 (introduced as the 2025 Bill; passed the House of Representatives 9 September 2026). https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_Search_Results/Result?bId=r7414
24. Central Land Council (2024, August). Submission to the 2024 Regional Telecommunications Independent Review. https://www.clc.org.au/wp-content/uploads/CLC-Submission-2024-Regional-Telecommunications-Independent-Review-August-2024.pdf
25. Cooper, K. D., Harvey, T. J. and Kennedy, K. (2001). A simple, fast dominance algorithm. Rice University Computer Science Technical Report TR-06-33870.
26. Central Land Council (2026). Leasing and licensing Aboriginal land. https://www.clc.org.au/leasing-and-licensing-aboriginal-land/

# Appendix A: AI usage declaration

We used Claude (Anthropic), an AI assistant, to search for and check sources, to write and test Python code, to draw figures and to edit this report. Every analysis number in the report is produced by run_all.py (outputs/public/numbers.json and outputs/public/single_score_probe.json), and we checked quoted facts against the source documents in the references. We made the design decisions, including the ethics rules, and we are responsible for the content.

# Appendix B: Reproducing the analysis

The submitted ZIP contains the processed data (0.7 MB), the code and the outputs. On macOS with Python 3.12 (tested; Windows untested):

CODE:
pip install -r requirements.txt
python run_all.py
panel serve app/app.py

run_all.py regenerates the numbers and every figure in this report in a few seconds, and pytest -q tests/ runs the checks. notebooks/01_walkthrough.ipynb walks through each step. python run_all.py --prepare rebuilds the processed data from the raw downloads (about 2 GB, not shipped; sources in data/manifest.csv).

# Appendix C: Parameters and sensitivity

TABLE: Table C1. Parameters. Values tagged as assumptions are swept or stated as indicative.
| Parameter | Value | Basis | Swept |
|---|---|---|---|
| Fibre town radius | 10 km | Assumption | 5, 10, 15 km |
| Nearest-site radius | 10 km | Assumption | 5, 10, 15 km |
| Hazard footprint | 100 km either side of the track | Assumption | 50, 100, 150 km; whole track or gale-strength part |
| Gale threshold | 17.5 m/s | 34 knots, BoM tropical cyclone definition | No |
| Hardening Program match | 3 km | Assumption | No |
| Time on site | 0.5 days | Assumption | No |
| Crew bases | Darwin, Katherine, Tennant Creek, Alice Springs, Nhulunbuy | Assumption | No |
| Road distance factor | 1.3 x straight line | Assumption | No |
| Driving speed | 70 km/h sealed, 40 km/h unsealed; 10 hours a day | Assumption | No |
| Wet-season delay | 30 days, November to April | Assumption | 14, 30, 60 days |
| Distance from sealed road that triggers the delay | 10 km | Assumption | 5, 10, 20 km |
| Single-score test costs | Satellite Wi-Fi $233,784 (GEO) or $398,510 (LEO); small cell $483,333 within 1.5 km; tower $1.5 million within 15 km | Wi-Fi: mean NT grants, 2026 funded list; small cell: NTG program, $5.8 million for 12 communities; tower: assumption | Tower $1 million to $3 million |
| Public suppression | fewer than 3 places or 10 people | Privacy rule | No |

TABLE: Table C2. Chain results across the nine fibre-radius and site-radius runs (larger places).
| Fibre radius | Site radius | Radio-chain places | With a single-path relay | Share | With 3 or more |
|---|---|---|---|---|---|
| 5 km | 5 km | 18 | 15 | 83% | 10 |
| 5 km | 10 km | 21 | 17 | 81% | 11 |
| 5 km | 15 km | 25 | 21 | 84% | 15 |
| 10 km | 5 km | 20 | 16 | 80% | 11 |
| 10 km | 10 km | 23 | 18 | 78% | 12 |
| 10 km | 15 km | 28 | 23 | 82% | 17 |
| 15 km | 5 km | 25 | 21 | 84% | 10 |
| 15 km | 10 km | 27 | 22 | 81% | 10 |
| 15 km | 15 km | 30 | 25 | 83% | 13 |

# Appendix D: What New Zealand already publishes

Aashish compared the NT with New Zealand, which also has remote rural areas, shared rural towers and severe weather. We checked every fact below against its source on 30 September 2026. The comparison supports Recommendations 1 to 3 and the community card.

TABLE: Table D1. New Zealand practice that bears on Underlink's recommendations.
| Practice in New Zealand | Evidence | Supports |
|---|---|---|
| Every reported fault is mapped live | Chorus, New Zealand's main wholesale fixed-line network, publishes a public map of all reported faults, searchable by address, with estimated restoration times. It updates every 10 minutes [D1]. | Rec 3; Rec 1 (outage logs) |
| Small rural providers log outages and their causes | WiFiConnect, a rural wireless provider on the West Coast, keeps a dated public list of outages by repeater. One entry reports continuous rain causing power problems at its Mt French repeaters [D2]. | Rec 2; Rec 1 |
| A mobile carrier maps planned and unplanned outages | One NZ's network status map covers mobile and Rural Broadband services and lists a power cut at a cell site as one cause of unplanned outages [D3]. | Rec 1; Rec 3 |
| Publicly funded rural towers are shared and carry backup power | Crown Infrastructure Partners approves towers built by the Rural Connectivity Group, which Spark, One NZ and 2degrees own. Its 2024 annual report lists 513 rural and black-spot towers live and describes a site with 30 solar panels and a backup generator [D4]. | Rec 1 |
| Public money pays for backhaul resilience | The same report says the West Coast and Southland fibre links, finished in 2023, increased network resilience and enabled 18 towers on State Highway 6 and 8 on the Milford Road [D4]. | Rec 1; Rec 2 |
| Schools and clinics come first, and towers must be shared | The Rural Broadband Initiative prioritised schools, hospitals and health centres, and every new tower had to allow other operators to co-locate [D5]. | Rec 1; Rec 6 |
| The regulator's map shows coverage only | The Commerce Commission's connectivity map shows where providers say service is available and what people connect with. Providers self-report the data, it is updated once a year, and it has no backhaul, backup-power or outage layer [D6]. | Finding in Section 3.1 |
| Telehealth guidance stops at getting connected | The New Zealand Telehealth Forum explains how rural clinics can connect but gives no advice on what to do when the link fails [D7]. | Community card (Rec 6) |

None of the New Zealand sources we checked shows which towers depend on a single backhaul path. That is the gap Underlink fills for the NT.

D1. Chorus Limited (2026). Internet outages map. Retrieved 30 September 2026. https://www.chorus.co.nz/optimise/internet-outages-map
D2. WiFiConnect Ltd (2026). Network status: outages. Retrieved 30 September 2026. https://wificonnect.co.nz/outages/
D3. One New Zealand (2026). Our network status. Retrieved 30 September 2026. https://one.nz/help/network-status/
D4. Crown Infrastructure Partners (2024). Annual Report 2024, year ended 30 June 2024. https://nationalinfrastructure.govt.nz/wp-content/uploads/Crown-Infrastructure-Partners-Annual-Report-2024-Online-2.pdf
D5. Ministry of Business, Innovation and Employment (2016). Rural Broadband Initiative Phase 1, August 2016. https://www.mbie.govt.nz/assets/0b55b27a15/rural-broadband-initiative-phase-1-august-2016.pdf
D6. Commerce Commission New Zealand (2025). Telecommunications connectivity map, data as at 30 June 2025. https://www.comcom.govt.nz/regulated-industries/telecommunications/monitoring-the-telecommunications-market/telecommunications-connectivity-map/
D7. New Zealand Telehealth Forum and Resource Centre. Internet connectivity in rural areas. https://www.telehealth.org.nz/telehealth-resources/technology/technology/internet-connectivity-in-rural-areas/
