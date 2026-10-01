# Data licences and attribution

The code is MIT licensed (see `LICENSE`). The data are not ours. Each source
keeps its own licence, and the files in `data/processed/` and `outputs/` are
derived from them. `data/manifest.csv` lists every raw file with its URL,
retrieval date (29 September 2026), md5 and the processed table it feeds.

Three sources have no stated licence or a licence we have not confirmed. They
are marked below. We use them for counts and context only and would confirm
terms with the publisher before any wider release.

## Attribution lines

**ACMA Register of Radiocommunications Licences.** Contains data from the Australian Communications and Media Authority Register of Radiocommunications Licences, used under the ACMA RRL licence, which allows use and derivatives with attribution. https://www.acma.gov.au/radiocomms-licence-data

**NTG remote communities with mobile coverage (2021).** Northern Territory Government, licensed under Creative Commons Attribution. https://data.nt.gov.au/dataset/remote-communities-with-mobile-coverage

**NTG list of remote communities with mobile coverage, backhaul (2019).** Northern Territory Government, licensed under Creative Commons Attribution. https://data.nt.gov.au/dataset/list-of-remote-communities-with-mobile-coverage

**ACCC Mobile Infrastructure Report data release.** Australian Competition and Consumer Commission, licensed under CC BY 2.5 AU. https://data.gov.au/data/dataset/accc-mobile-infrastructure-report-data-release

**BoM tropical cyclone best track.** Copyright Commonwealth of Australia, Bureau of Meteorology. Used with attribution. https://www.bom.gov.au/clim_data/IDCKMSTM0S.csv

**First Nations Connectivity Mapping Tool, public layers** (AGIL locations, payphones, Wi-Fi telephones, Wi-Fi hubs, NBN community Wi-Fi). Department of Infrastructure, Transport, Regional Development, Communications, Sport and the Arts, with NIAA, licensed under CC BY 4.0. https://spatial.infrastructure.gov.au/portal/apps/experiencebuilder/experience/?id=81c5ae65fbf74ce3a89cf25b1f323d50

**nbn footprints.** NBN Co via data.gov.au, licensed under CC BY 4.0. https://data.gov.au/data/dataset/national-broadband-network

**Mobile Network Hardening Program, STAND and Mobile Black Spot Program layers.** Department of Infrastructure, Transport, Regional Development, Communications, Sport and the Arts, licensed under CC BY 4.0. https://spatial.infrastructure.gov.au/server/rest/services

**First Nations Community Wi-Fi Program 2026 funded list.** Department of Infrastructure, Transport, Regional Development, Communications, Sport and the Arts. *Licence not stated.* https://www.infrastructure.gov.au/media-communications/first-nations-digital-inclusion

**Geoscape National Roads.** Geoscape Australia, via the Digital Atlas of Australia (Geoscience Australia), licensed under CC BY 4.0. https://services-ap1.arcgis.com/ypkPEy1AmwPKGNNv/arcgis/rest/services/National_Roads/FeatureServer/0

**NTLIS land council boundaries, Aboriginal Land Trusts and counter disaster areas.** Northern Territory Government, NT Land Information System. CC BY 4.0, *to be confirmed*. https://ogc.ntlis.nt.gov.au/gs/ntlis/wfs

**Bushfire risk for remote communities in the Northern Territory (2020).** Bushfires NT, Northern Territory Government, licensed under CC BY 4.0. Used for 2020 population figures. https://data.nt.gov.au/dataset/bushfire-risk-for-remote-communities-in-the-northern-territory

**nbn outage register.** NBN Co. *Terms not stated.* https://www.nbnco.com.au/content/dam/nbnco/acma-content/nbn_outage_register.csv

**National Audit of Mobile Coverage non-alignment data, September 2026.** Department of Infrastructure, Transport, Regional Development, Communications, Sport and the Arts. *Licence to be confirmed.* https://www.infrastructure.gov.au/sites/default/files/documents/national_audit_of_mobile_coverage_non-alignment_data_september_2026.csv

## What we changed

- Radio site ids are replaced by salted hashes.
- Coordinates in shipped files are rounded to 0.01 degrees (about 1 km).
- Tables are filtered to the Northern Territory and to the columns we use.
- The Telstra 4G outdoor flag per place comes from intersecting the NTG 2021 list with the ACCC 2026 coverage prediction.

These changes are ours. The publishers have not reviewed or endorsed this work.
