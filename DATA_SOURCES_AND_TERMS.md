# Data sources, retrieval record, and reuse notice

This file documents the five source-package groups used by the project. The
original packages supplied with the project were inspected on 14 August 2026;
their archive integrity, source inventories, embedded URLs, timestamps, and
SHA-256 hashes were checked before the records below were added.

Two timestamp rules are important:

1. An exact time is reported only when it is preserved in an original download
   manifest or source filename.
2. A ZIP member timestamp is labelled as a package timestamp. It is not silently
   substituted for an unrecorded original download time.

`ORIGINAL_SOURCE_PACKAGES.csv` is the machine-readable package-level record.
The `provenance/` folder contains file-level source URLs, timestamps, sizes, and
hashes. These compact manifests are included instead of the four large source
ZIPs, one of which exceeds GitHub's normal per-file size limit.

## 1. CAISO SP15 day-ahead hourly LMP

- Included analysis extract: `source_data/CAISO_SP15_daily_outcome.csv`.
- Coverage: 1 May 2023 through 31 December 2025; 976 daily outcomes built from
  23,425 validated hourly intervals.
- Dataset: OASIS `PRC_LMP`, day-ahead market, node `TH_SP15_GEN-APND`, version
  12.
- Official OASIS entry point: https://oasis.caiso.com/
- OASIS information page:
  https://www.caiso.com/systems-applications/portals-applications/open-access-same-time-information-system-oasis
- Retained manifest range: 140 weekly source ZIP queries from
  `2026-08-11T16:28:31.579Z` through `2026-08-11T16:47:54.500Z`. The manifest
  labels 139 rows `downloaded` and one row `reused_valid_file`; the timestamp
  on the reused row documents validation/reuse, not its earlier acquisition.
- Exact query URLs, UTC manifest timestamps, status values, row counts, byte sizes, and
  SHA-256 hashes: `provenance/CAISO_SP15_OASIS_download_manifest.csv`.
- Original workbook SHA-256:
  `b8c8f963d04a9edba3050e8f5991b86f87acb7e476fdf56cdc33f3174cb3ccd9`.
- Included daily extract SHA-256:
  `2c00643f58d02052eda6c4040ae4add5f305ff704e5448415305752b9add6ba9`.

The separately supplied daily CSV has the same SHA-256 as the included analysis
extract, confirming that the published project uses the retained SP15 result.

## 2. EIA-860M battery capacity

- Included analysis extract:
  `source_data/EIA860M_CISO_daily_lagged_battery_capacity.csv`.
- Coverage: 33 monthly workbooks, April 2023 through December 2025, assigned to
  the following month under the pre-specified lag rule.
- Official EIA-860M page: https://www.eia.gov/electricity/data/eia860m/
- Exact workbook URLs and source-file hashes:
  `provenance/EIA860M_source_manifest.csv`.
- Download and validation completion date retained in the package README:
  `2026-08-11`.
- Exact original download time: not recorded.
- ZIP member timestamp: approximately `2026-08-11T23:02:48`; ZIP does not store
  its timezone, so this is reported only as package evidence.
- Original source-package SHA-256:
  `b3a0862fb67c939392959cd59d2455f3ab13aa26cf5d9ed8c9d5b6e36664d3d7`.
- Included extract SHA-256:
  `b27fcd5a8192c12858a4a40c78eb616dc9276fa1fe747293ab2ba2776bacc657`.

## 3. EIA-930 demand and solar

- Included analysis extract:
  `source_data/EIA930_CISO_hourly_adjusted_demand_solar.csv`.
- Coverage: six half-year balancing-authority CSVs for 2023 through 2025; the
  project retains 23,425 hourly CISO rows used in the analysis windows.
- Official EIA-930 information page:
  https://www.eia.gov/electricity/gridmonitor/about
- Exact six-month file URLs and hashes:
  `provenance/EIA930_source_manifest.csv`.
- Download and validation completion date retained in the package README:
  `2026-08-11`.
- Exact original download time: not recorded.
- ZIP member timestamp: approximately `2026-08-11T23:02:48`; ZIP does not store
  its timezone, so this is reported only as package evidence.
- Original source-package SHA-256:
  `85b0d87cad6ae4f4dbab96a78c01859c17887e9773f952f93d7a40590c2ba6b3`.
- Included extract SHA-256:
  `e623346483cad72988a149ccf0432496d328177365ac42d79b2a66d2b5118909`.

The official adjusted-demand and adjusted-solar fields are blank for all 24
hours of 2 November 2024. The analysis does not impute that window, leaving 975
complete regression days.

## 4. CAISO PRC_FUEL / FRSCE3 delivered gas cost

- Included analysis extract: `source_data/CAISO_PRC_FUEL_FRSCE3_daily.csv`.
- Coverage: 1 May 2023 through 31 December 2025; 976 daily observations.
- Dataset: OASIS `PRC_FUEL`, version 1; `FRSCE3` non-GHG SoCal Citygate
  delivered-cost proxy.
- Official OASIS entry point: https://oasis.caiso.com/
- Retained filename timestamps: `2026-08-11T10:41:03` through
  `2026-08-11T10:46:33`. The timezone was not retained, so none is inferred.
- Exact reconstructed OASIS query URLs, filename timestamps, source-file sizes,
  and hashes: `provenance/CAISO_PRC_FUEL_OASIS_download_manifest.csv`.
- Original source-package SHA-256:
  `48afacd4b813b357417b4db95578d488985bee0a4b4b580aee31e03042c8c68d`.
- Included extract SHA-256:
  `64d86921dc35029b264ed519bbd7cbec9e6beb08923e4f1f4bcd95f193df184e`.

`FRSCE3` includes transportation and fuel-reimbursement components. It is a
delivered fuel-cost proxy, not the ICE SoCal-Citygate weighted-average index.

## 5. CAISO contextual reports

This group contains 32 monthly renewables performance reports for May 2023
through December 2025 and the 2023, 2024, and 2025 Annual Reports on Market
Issues and Performance. They support interpretation and validation but are not
regression observations.

- Monthly renewables report collection:
  https://www.caiso.com/library/monthly-renewables-performance-report
- Annual market reports collection:
  https://www.caiso.com/market-operations/market-monitoring/market-issues-and-performance-reports
- File inventory, collection URLs, package timestamps, sizes, and hashes:
  `provenance/CAISO_contextual_reports_source_manifest.csv`.
- Download and validation completion date retained in the package README:
  `2026-08-11`.
- Exact original download time: not recorded.
- ZIP member timestamp: approximately `2026-08-11T23:02:48`; ZIP does not store
  its timezone, so this is reported only as package evidence.
- Original source-package SHA-256:
  `a4dc1c556edc20f5d57fc4a394eb3c27584ff0c9f878c2209f6acc523c906130`.

## Attribution and reuse

Suggested acknowledgment for the repository and all derived tables and figures:

> Source: Author's calculations using California ISO OASIS data and U.S.
> Energy Information Administration EIA-860M and EIA-930 data. CAISO and EIA
> do not endorse this analysis.

EIA's copyright and reuse policy is:
https://www.eia.gov/about/copyrights_reuse.php

CAISO's website terms are:
https://www.caiso.com/privacy-terms-of-use

A repository code license applies only to the repository's original code and
documentation; it does not relicense underlying CAISO or EIA data. Preserve
agency names, source URLs, and existing notices, and check the current source
terms before redistributing source files.
