# Battery build-out and the shape of California electricity prices

This is the corrected, complete, runnable Python package for the revised
research design covering 1 May 2023 through 31 December 2025.

## Run the project

The merged real-data input is already included. Open this folder in VS Code,
then run:

```text
python -m pip install statsmodels
python battery_price_analysis.py
```

The script resolves paths from its own location and creates `results`
automatically. It therefore does not matter which current folder VS Code uses.

To reproduce the merge from the four compact source extracts, run:

```text
python prepare_analysis_data.py
python battery_price_analysis.py
```

No manual merge, folder creation, file renaming, or path editing is required.

The final reproducibility run must use that two-command order. The preparation
script creates the additional one-month timing exposure before the analysis
script estimates and saves `results/16_timing_robustness.csv`.

## Folder contents

- `battery_price_analysis.py`: textbook-supported econometric analysis.
- `prepare_analysis_data.py`: approved transparent pandas preparation and merge.
- `data/CAISO_daily_analysis.csv`: real merged 976-date input.
- `source_data/`: four compact validated source extracts used by preparation.
- `results/`: real-data tables, audit files, log, and vector-PDF figures.
- `ANALYSIS_INPUT_DICTIONARY.csv`: definitions, units, and construction rules.
- `report/Results_Diagnostics_Limitations_Conclusion.docx`: the selected,
  report-ready empirical narrative, tables, and figures.
- `report/table_01_baseline_coefficients.csv` and
  `report/table_02_focused_checks.csv`: machine-readable versions of the two
  tables selected for the assessed report.
- `FINAL_REPRODUCIBILITY_AUDIT.md`: final run, integrity, and security checks.

## Cleaning and validation result

- 976 calendar dates and 976 unique date keys are present.
- There are no duplicate daily keys in any merged source.
- Price, battery capacity, and `FRSCE3` gas values have no missing dates.
- EIA-930 adjusted demand and adjusted solar are missing for all 24 hours of
  2 November 2024 in the official source. The script does not interpolate or
  impute them; the locked complete-window rule leaves 975 regression days.
- EIA solar uses its adjusted field. From July 2024, the separate adjusted
  solar categories are combined consistently. This recovers valid adjusted
  observations that the earlier processed raw-solar column had incorrectly
  shown as blank.
- EIA hour-ending numbers are shifted conceptually to match the SP15
  interval-start windows: hour endings 11-16 correspond to price starts 10-15,
  and hour endings 18-21 correspond to price starts 17-20.
- No market-price extremes are automatically removed. Days with absolute
  externally studentized residuals above 3 are listed for source review, and a
  labelled exclusion model is reported only as sensitivity analysis.

## Econometric scope

The analysis estimates conditional historical associations, not causal effects.
It includes three nested OLS specifications, seven-lag Newey-West/HAC inference,
calendar controls, trend, diagnostics, outlier sensitivity, component-price
models, the `FRSCE3` tariff-break check, monthly first differences, the
pre-specified additional one-month battery-capacity lag, battery energy
capacity, and negative-price hours. The timing regression starts on 1 June
2023 because May has no earlier validated monthly exposure; after the official
EIA blank it uses 944 observations.

The econometric routines follow code patterns documented in *Using Python for
Introductory Econometrics, 2nd Ed.* The project-specific pandas date alignment
and merging in `prepare_analysis_data.py` are the narrow exception explicitly
approved by the user.

## Security

Both scripts operate only on fixed local project files. They contain no network
requests, downloads, shell commands, subprocesses, dynamic code evaluation,
credential access, deserialization of executable objects, deletion, or changes
to the source extracts. Re-running the project overwrites only predetermined
derived files inside `data` and `results`.
