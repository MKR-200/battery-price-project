# Final reproducibility audit

Date: 12 August 2026

## Commands executed

```text
python prepare_analysis_data.py
python battery_price_analysis.py
```

Both commands completed with exit code 0 on the real archived source extracts.
They were then executed a second time in the same order. All 20 generated CSV
files had identical SHA-256 hashes across the two runs.

## Data gates

- Planned dates: 976, from 1 May 2023 through 31 December 2025.
- Unique merged date keys: 976.
- Duplicate merged date keys: 0.
- Baseline incomplete date: 2 November 2024 only.
- Baseline complete cases: 975.
- Additional one-month timing-lag complete cases: 944, beginning 1 June 2023.
- Missing one-month timing exposure: the 31 May 2023 dates only, as expected
  because the validated exposure series begins in May 2023.

## Principal estimates

- Full baseline battery coefficient: 0.6447 USD/MWh per GW.
- Seven-lag HAC standard error: 8.0124.
- Two-sided p value: 0.9359.
- 95% confidence interval: [-15.0593, 16.3487].
- Additional one-month lag coefficient: 2.2714 USD/MWh per lagged GW.
- Timing-model HAC standard error: 6.5238; p value: 0.7277.
- Timing-model 95% confidence interval: [-10.5150, 15.0578].

## Diagnostics and reporting checks

- Battery-trend correlation: 0.9975.
- Battery and trend VIFs: 391.3 and 387.2.
- Durbin-Watson statistic: 0.918.
- Seven-lag Breusch-Godfrey F statistic: 63.42; p value below 0.001.
- Ten genuine high-price days are flagged at an absolute externally
  studentized residual above three; the primary data are not winsorised.
- All seven generated figures were rendered and visually checked.
- The four-page Word report was rendered and visually checked page by page.
- Word table width, grid, indent, and cell-width geometry passed the structural
  audit.

## Static security review

The two executable research scripts contain no network calls, URLs, socket
access, subprocess or shell execution, dynamic evaluation, credential access,
executable deserialization, file deletion, or writes outside the fixed `data`
and `results` directories. The scripts read local CSV inputs only and never
modify the archived source extracts.

## Provenance update

On 14 August 2026, the four original source ZIPs and the SP15 source workbook
were inspected and passed archive/integrity checks. The revised package records
the official source URLs and SHA-256 hashes in `ORIGINAL_SOURCE_PACKAGES.csv`
and file-level manifests under `provenance/`. SP15 retains 140 exact UTC
manifest timestamps: 139 rows are marked downloaded and one is marked reused
after validation. PRC_FUEL retains exact filename clock times but no timezone.
The EIA-860M, EIA-930, and contextual-report package READMEs retain a
completion date of 11 August 2026 but no exact download time; ZIP timestamps are
therefore labelled as package evidence rather than original download times.
