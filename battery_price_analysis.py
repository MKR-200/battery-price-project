########################################################################
# Research project:
# "Battery build-out and the shape of California electricity prices"
#
# Purpose:
# Estimate the association between operating battery power capacity and
# the CAISO SP15 evening-minus-midday day-ahead price spread.
#
# Textbook constraint:
# This script uses programming and econometric patterns explicitly shown
# in "Using Python for Introductory Econometrics, 2nd Ed."  The mapping to
# the relevant textbook scripts is documented in README.md.
#
# Security design:
# - reads one local CSV file only;
# - creates and writes only to the local "results" folder;
# - contains no network calls, subprocesses, shell commands, eval, exec,
#   dynamic imports, credential access, deletion, or modification of raw
#   input data;
# - resolves fixed paths from this script's own location, so it works even
#   when VS Code launches it from a different current working directory.
#
# Important input boundary:
# The textbook does not show the project-specific code required to convert
# UTC hourly records to Pacific time and merge CAISO/EIA sources by date.
# Therefore, this compliant script starts from one daily, analysis-ready
# CSV whose exact columns are listed in ANALYSIS_INPUT_DICTIONARY.csv.
########################################################################

# This block imports only modules and aliases used in textbook scripts.
import sys
import datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import patsy as pt
import statsmodels.api as sm
import statsmodels.formula.api as smf
import statsmodels.stats.outliers_influence as smo
import matplotlib.pyplot as plt


# This block fixes all local input and output locations relative to the script,
# not the launch directory. It creates the results folder automatically.
PROJECT_FOLDER = Path(__file__).resolve().parent
INPUT_FILE = PROJECT_FOLDER / 'data' / 'CAISO_daily_analysis.csv'
OUTPUT_PATH = PROJECT_FOLDER / 'results'
OUTPUT_PATH.mkdir(exist_ok=True)
OUTPUT_FOLDER = str(OUTPUT_PATH) + '/'

# This block applies restrained, consistent figure styling. Labels retain the
# actual variables and units, and regression values are never transformed.
plt.rcParams.update({
    'font.size': 10,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'legend.fontsize': 9,
    'figure.dpi': 120,
    'savefig.bbox': 'tight',
})


# This function estimates OLS and requests Newey-West/HAC standard errors.
# It follows textbook Script 12.6, with seven daily lags as pre-specified.
def estimate_hac(formula, sample, lags):
    regression = smf.ols(formula=formula, data=sample)
    results = regression.fit(cov_type='HAC', cov_kwds={'maxlags': lags})
    return results


# This function makes an auditable coefficient table with estimates,
# Newey-West standard errors, t statistics, p values, and 95% intervals.
# It follows textbook Scripts 4.5 and 12.6.
def coefficient_table(results):
    ci95 = results.conf_int(0.05)
    table = pd.DataFrame({'coefficient': round(results.params, 4),
                          'standard_error': round(results.bse, 4),
                          't_statistic': round(results.tvalues, 4),
                          'p_value': round(results.pvalues, 4),
                          'ci_95_low': round(ci95[0], 4),
                          'ci_95_high': round(ci95[1], 4)})
    return table


# This function creates a compact table for the battery coefficient from
# several models.  It keeps model comparisons machine-readable.
def battery_comparison(model_names, results_list, battery_names):
    number_models = len(results_list)
    b = np.empty(number_models)
    se = np.empty(number_models)
    t_value = np.empty(number_models)
    p_value = np.empty(number_models)
    ci_low = np.empty(number_models)
    ci_high = np.empty(number_models)
    nobs = np.empty(number_models)

    for i in range(number_models):
        results = results_list[i]
        battery_name = battery_names[i]
        ci95 = results.conf_int(0.05)
        b[i] = results.params[battery_name]
        se[i] = results.bse[battery_name]
        t_value[i] = results.tvalues[battery_name]
        p_value[i] = results.pvalues[battery_name]
        ci_low[i] = ci95.loc[battery_name, 0]
        ci_high[i] = ci95.loc[battery_name, 1]
        nobs[i] = results.nobs

    table = pd.DataFrame({'model': model_names,
                          'battery_variable': battery_names,
                          'coefficient': np.round(b, 4),
                          'standard_error': np.round(se, 4),
                          't_statistic': np.round(t_value, 4),
                          'p_value': np.round(p_value, 4),
                          'ci_95_low': np.round(ci_low, 4),
                          'ci_95_high': np.round(ci_high, 4),
                          'observations': nobs})
    return table


# This function calculates a correlation matrix using the same np.corrcoef
# command shown in textbook Script 1.27.  No variables are deleted because
# of a high correlation; the matrix is diagnostic evidence only.
def correlation_table(sample, variable_names):
    number_variables = len(variable_names)
    correlations = np.empty((number_variables, number_variables))

    for i in range(number_variables):
        for j in range(number_variables):
            correlations[i, j] = np.corrcoef(
                sample[variable_names[i]], sample[variable_names[j]])[0, 1]

    table = pd.DataFrame(correlations,
                         index=variable_names,
                         columns=variable_names)
    return table


# This function calculates the residual autocorrelation function through
# 30 days using textbook operations: shifts/slices, np.corrcoef, loops,
# and a bar plot.  The textbook does not show plot_acf, so it is not used.
def residual_acf(residuals, maximum_lag):
    acf_values = np.empty(maximum_lag + 1)
    acf_values[0] = 1

    for lag in range(1, maximum_lag + 1):
        acf_values[lag] = np.corrcoef(
            residuals[lag:], residuals[:-lag])[0, 1]

    return acf_values


# This function runs the complete econometric workflow after the coverage,
# duplicate, and missing-value gates have passed.
def run_analysis(source_data, analysis):

    # This block defines the three locked model formulas.  Monday and January
    # are the reference categories, exactly as required by the execution plan.
    formula1 = 'spread_usd_mwh ~ battery_gw'
    formula2 = ('spread_usd_mwh ~ battery_gw + demand_gap_gw + '
                'solar_drop_gw + gas_usd_mmbtu')
    formula3 = ('spread_usd_mwh ~ battery_gw + demand_gap_gw + '
                'solar_drop_gw + gas_usd_mmbtu + '
                'C(weekday, Treatment("Monday")) + '
                'C(month, Treatment("January")) + trend_years')

    # This block creates summary statistics in the original measurement units.
    # Genuine negative prices and scarcity observations remain unchanged.
    summary_variables = ['spread_usd_mwh', 'evening_lmp_usd_mwh',
                         'midday_lmp_usd_mwh', 'battery_gw',
                         'demand_gap_gw', 'solar_drop_gw',
                         'gas_usd_mmbtu']
    number_variables = len(summary_variables)
    n = np.empty(number_variables)
    mean = np.empty(number_variables)
    median = np.empty(number_variables)
    standard_deviation = np.empty(number_variables)
    minimum = np.empty(number_variables)
    maximum = np.empty(number_variables)

    for i in range(number_variables):
        variable = analysis[summary_variables[i]]
        n[i] = len(variable)
        mean[i] = np.mean(variable)
        median[i] = np.median(variable)
        standard_deviation[i] = np.std(variable, ddof=1)
        minimum[i] = np.min(variable)
        maximum[i] = np.max(variable)

    summary_statistics = pd.DataFrame({
        'observations': n,
        'mean': np.round(mean, 4),
        'median': np.round(median, 4),
        'standard_deviation': np.round(standard_deviation, 4),
        'minimum': np.round(minimum, 4),
        'maximum': np.round(maximum, 4)}, index=summary_variables)
    summary_statistics.to_csv(OUTPUT_FOLDER + '03_summary_statistics.csv')

    # This block reports correlations, including the battery-trend correlation.
    correlation_variables = ['spread_usd_mwh', 'battery_gw',
                             'demand_gap_gw', 'solar_drop_gw',
                             'gas_usd_mmbtu', 'trend_years']
    correlations = correlation_table(analysis, correlation_variables)
    correlations.to_csv(OUTPUT_FOLDER + '04_correlations.csv')
    print(f'Battery-trend correlation: '
          f'{correlations.loc["battery_gw", "trend_years"]}\n')

    # This block estimates the three nested models with seven-lag HAC errors.
    results1 = estimate_hac(formula1, analysis, 7)
    results2 = estimate_hac(formula2, analysis, 7)
    results3 = estimate_hac(formula3, analysis, 7)

    nested_table = battery_comparison(
        ['Model 1: battery only',
         'Model 2: fundamentals',
         'Model 3: full baseline'],
        [results1, results2, results3],
        ['battery_gw', 'battery_gw', 'battery_gw'])
    nested_table.to_csv(
        OUTPUT_FOLDER + '05_nested_battery_coefficients.csv')

    full_table = coefficient_table(results3)
    full_table.to_csv(OUTPUT_FOLDER + '06_full_model_coefficients.csv')

    # This block compares conventional and HAC inference for the same full
    # model.  HAC is primary; conventional OLS is retained only for audit.
    regression3 = smf.ols(formula=formula3, data=analysis)
    results3_conventional = regression3.fit()
    results3_hac = regression3.fit(
        cov_type='HAC', cov_kwds={'maxlags': 7})
    conventional_hac = pd.DataFrame({
        'coefficient': round(results3_hac.params, 4),
        'conventional_se': round(results3_conventional.bse, 4),
        'hac_7lag_se': round(results3_hac.bse, 4),
        'conventional_p_value': round(results3_conventional.pvalues, 4),
        'hac_7lag_p_value': round(results3_hac.pvalues, 4)})
    conventional_hac.to_csv(
        OUTPUT_FOLDER + '07_conventional_vs_hac.csv')

    # This block calculates VIFs for the full regressor matrix using the exact
    # statsmodels routine shown in textbook Script 3.10.
    y_vif, X_vif = pt.dmatrices(
        formula3, data=analysis, return_type='dataframe')
    number_regressors = X_vif.shape[1]
    vif_values = np.empty(number_regressors)

    for i in range(number_regressors):
        vif_values[i] = smo.variance_inflation_factor(X_vif.values, i)

    vif_table = pd.DataFrame({'regressor': X_vif.columns,
                              'vif': np.round(vif_values, 4)})
    vif_table.to_csv(OUTPUT_FOLDER + '08_variance_inflation_factors.csv')

    # This block reports Durbin-Watson and the seven-lag Breusch-Godfrey test.
    # The tests diagnose dependence; the HAC covariance controls inference.
    durbin_watson = sm.stats.stattools.durbin_watson(
        results3_conventional.resid)
    bg_result = sm.stats.diagnostic.acorr_breusch_godfrey(
        results3_conventional, nlags=7)
    serial_diagnostics = pd.DataFrame({
        'diagnostic': ['Durbin-Watson statistic',
                       'Breusch-Godfrey F test, 7 lags'],
        'statistic': [durbin_watson, bg_result[2]],
        'p_value': [np.nan, bg_result[3]]})
    serial_diagnostics.to_csv(
        OUTPUT_FOLDER + '09_serial_correlation_diagnostics.csv')

    # This block runs supporting augmented Dickey-Fuller tests with a constant
    # and deterministic trend, following textbook Script 18.2.  These checks
    # do not convert the association design into causal inference.
    adf_variables = ['spread_usd_mwh', 'battery_gw', 'demand_gap_gw',
                     'solar_drop_gw', 'gas_usd_mmbtu']
    number_adf = len(adf_variables)
    adf_statistic = np.empty(number_adf)
    adf_p_value = np.empty(number_adf)

    for i in range(number_adf):
        adf_result = sm.tsa.stattools.adfuller(
            analysis[adf_variables[i]], maxlag=7, autolag=None,
            regression='ct', regresults=True)
        adf_statistic[i] = adf_result[0]
        adf_p_value[i] = adf_result[1]

    adf_table = pd.DataFrame({'variable': adf_variables,
                              'adf_statistic': np.round(adf_statistic, 4),
                              'p_value': np.round(adf_p_value, 4),
                              'deterministic_terms': 'constant and trend',
                              'lagged_differences': 7})
    adf_table.to_csv(OUTPUT_FOLDER + '10_adf_tests.csv')

    # This block flags potentially influential days using externally
    # studentized residuals, as in textbook Script 9.9.  It does not classify
    # a flag as an error and does not delete or winsorise the primary data.
    studentized = results3_conventional.get_influence().resid_studentized_external
    analysis['studentized_residual'] = studentized
    influence_flag = (abs(analysis['studentized_residual']) > 3)
    flagged_days = analysis.loc[
        influence_flag,
        ['date', 'spread_usd_mwh', 'evening_lmp_usd_mwh',
         'midday_lmp_usd_mwh', 'studentized_residual']]
    flagged_days.to_csv(OUTPUT_FOLDER + '11_flagged_extreme_days.csv')

    print(f'Maximum externally studentized residual: '
          f'{np.max(studentized)}\n')
    print(f'Minimum externally studentized residual: '
          f'{np.min(studentized)}\n')
    print(f'Days flagged at absolute studentized residual > 3: '
          f'{flagged_days.shape[0]}\n')

    # This labelled sensitivity removes only the flagged days.  The unchanged
    # non-winsorised model above remains the primary estimate because CAISO
    # negative prices and scarcity spikes can be genuine economic events.
    inlier_sample = pd.DataFrame(analysis.loc[influence_flag == False, :])
    results_inlier = estimate_hac(formula3, inlier_sample, 7)
    outlier_sensitivity = battery_comparison(
        ['Primary: all complete days',
         'Sensitivity: abs(studentized residual) <= 3'],
        [results3, results_inlier],
        ['battery_gw', 'battery_gw'])
    outlier_sensitivity.to_csv(
        OUTPUT_FOLDER + '12_outlier_sensitivity.csv')

    # This block estimates the two component-price regressions on exactly the
    # same complete sample and regressors as the spread regression.
    formula_evening = ('evening_lmp_usd_mwh ~ battery_gw + demand_gap_gw + '
                       'solar_drop_gw + gas_usd_mmbtu + '
                       'C(weekday, Treatment("Monday")) + '
                       'C(month, Treatment("January")) + trend_years')
    formula_midday = ('midday_lmp_usd_mwh ~ battery_gw + demand_gap_gw + '
                      'solar_drop_gw + gas_usd_mmbtu + '
                      'C(weekday, Treatment("Monday")) + '
                      'C(month, Treatment("January")) + trend_years')
    results_evening = estimate_hac(formula_evening, analysis, 7)
    results_midday = estimate_hac(formula_midday, analysis, 7)
    mechanism_table = battery_comparison(
        ['Spread outcome', 'Evening component', 'Midday component'],
        [results3, results_evening, results_midday],
        ['battery_gw', 'battery_gw', 'battery_gw'])
    mechanism_table.to_csv(
        OUTPUT_FOLDER + '13_mechanism_battery_coefficients.csv')

    # This block checks the material FRSCE3 tariff change from 15 February
    # 2025 by adding the pre-constructed indicator to the full model.
    formula_tariff = (formula3 + ' + tariff_break')
    results_tariff = estimate_hac(formula_tariff, analysis, 7)
    tariff_table = battery_comparison(
        ['Full baseline', 'Add FRSCE3 tariff-break indicator'],
        [results3, results_tariff],
        ['battery_gw', 'battery_gw'])
    tariff_table.to_csv(
        OUTPUT_FOLDER + '14_tariff_break_robustness.csv')

    # This block constructs a compact monthly first-difference sensitivity.
    # Monthly averaging uses groupby/mean; differencing uses diff, both shown
    # in the textbook.  It is a sensitivity, not the primary daily estimate.
    monthly_source = analysis[['month_id', 'spread_usd_mwh', 'battery_gw',
                               'demand_gap_gw', 'solar_drop_gw',
                               'gas_usd_mmbtu']]
    monthly = monthly_source.groupby('month_id').mean()
    monthly['d_spread'] = monthly['spread_usd_mwh'].diff()
    monthly['d_battery'] = monthly['battery_gw'].diff()
    monthly['d_demand_gap'] = monthly['demand_gap_gw'].diff()
    monthly['d_solar_drop'] = monthly['solar_drop_gw'].diff()
    monthly['d_gas'] = monthly['gas_usd_mmbtu'].diff()
    formula_difference = ('d_spread ~ d_battery + d_demand_gap + '
                          'd_solar_drop + d_gas')
    results_difference = estimate_hac(formula_difference, monthly, 1)
    difference_table = coefficient_table(results_difference)
    difference_table.to_csv(
        OUTPUT_FOLDER + '15_monthly_first_difference_model.csv')

    # This block estimates the pre-specified additional one-month capacity-lag
    # robustness. May 2023 has no earlier validated monthly exposure level, so
    # the timing sample starts on 1 June 2023. The official EIA blank on
    # 2 November 2024 then leaves exactly 944 observations.
    timing_complete = (analysis['battery_lag1_gw'].isna() == False)
    timing_sample = pd.DataFrame(analysis.loc[timing_complete, :])
    if timing_sample.shape[0] != 944:
        raise ValueError(
            'Timing robustness expected 944 complete observations; '
            f'found {timing_sample.shape[0]}.'
        )
    formula_lag = ('spread_usd_mwh ~ battery_lag1_gw + demand_gap_gw + '
                   'solar_drop_gw + gas_usd_mmbtu + '
                   'C(weekday, Treatment("Monday")) + '
                   'C(month, Treatment("January")) + trend_years')
    results_lag = estimate_hac(formula_lag, timing_sample, 7)
    timing_table = battery_comparison(
        ['Primary timing', 'Additional one-month lag'],
        [results3, results_lag],
        ['battery_gw', 'battery_lag1_gw'])
    timing_table.to_csv(
        OUTPUT_FOLDER + '16_timing_robustness.csv')

    # This optional block replaces power capacity with energy capacity.  It
    # never includes GW and GWh together, preventing mechanical collinearity.
    if 'battery_gwh' in analysis.columns:
        formula_energy = ('spread_usd_mwh ~ battery_gwh + demand_gap_gw + '
                          'solar_drop_gw + gas_usd_mmbtu + '
                          'C(weekday, Treatment("Monday")) + '
                          'C(month, Treatment("January")) + trend_years')
        results_energy = estimate_hac(formula_energy, analysis, 7)
        energy_table = battery_comparison(
            ['Power-capacity baseline', 'Energy-capacity alternative'],
            [results3, results_energy],
            ['battery_gw', 'battery_gwh'])
        energy_table.to_csv(
            OUTPUT_FOLDER + '17_energy_capacity_robustness.csv')
    else:
        print('Energy-capacity robustness skipped: battery_gwh not supplied.\n')

    # This optional block uses the pre-constructed 24-hour-equivalent count of
    # negative-price hours as the single alternative outcome.
    if 'negative_price_hours_24eq' in analysis.columns:
        negative_missing = analysis['negative_price_hours_24eq'].isna()
        negative_sample = pd.DataFrame(
            analysis.loc[negative_missing == False, :])
        formula_negative = (
            'negative_price_hours_24eq ~ battery_gw + demand_gap_gw + '
            'solar_drop_gw + gas_usd_mmbtu + '
            'C(weekday, Treatment("Monday")) + '
            'C(month, Treatment("January")) + trend_years')
        results_negative = estimate_hac(
            formula_negative, negative_sample, 7)
        negative_table = coefficient_table(results_negative)
        negative_table.to_csv(
            OUTPUT_FOLDER + '18_negative_price_hours_model.csv')
    else:
        print('Alternative outcome skipped: '
              'negative_price_hours_24eq not supplied.\n')

    # This block produces the locked capacity-and-price descriptive figure.
    # Both variables are standardized only for this plot so they can share a
    # truthful y-axis; all regressions remain in original units.
    spread_standardized = (
        (source_data['spread_usd_mwh'] -
         np.mean(source_data['spread_usd_mwh'])) /
        np.std(source_data['spread_usd_mwh'], ddof=1))
    capacity_standardized = (
        (source_data['battery_gw'] - np.mean(source_data['battery_gw'])) /
        np.std(source_data['battery_gw'], ddof=1))

    plt.figure(figsize=(8, 5))
    plt.plot(source_data['time_days'], spread_standardized,
             color='#2A6FBB', linewidth=1.1, alpha=0.75,
             label='SP15 price spread')
    plt.plot(source_data['time_days'], capacity_standardized,
             color='#D55E00', linewidth=2.2,
             label='Battery power capacity')
    plt.axhline(y=0, linewidth=0.5, linestyle='-', color='grey')
    plt.xticks([0, 245, 611, 975],
               ['May 2023', 'Jan 2024', 'Jan 2025', 'Dec 2025'])
    plt.title('SP15 price spread and CAISO battery build-out')
    plt.ylabel('Standard deviations from sample mean')
    plt.xlabel('Operating date')
    plt.legend()
    plt.savefig(OUTPUT_FOLDER + 'figure_01_capacity_and_price.pdf')
    plt.close()

    # This block plots the outcome and its component prices in USD/MWh.
    plt.figure(figsize=(8, 5))
    plt.plot(source_data['time_days'], source_data['evening_lmp_usd_mwh'],
             color='#D55E00', linewidth=1.1, alpha=0.8,
             label='Evening LMP, 17:00-20:59')
    plt.plot(source_data['time_days'], source_data['midday_lmp_usd_mwh'],
             color='#009E73', linewidth=1.1, alpha=0.8,
             label='Midday LMP, 10:00-15:59')
    plt.plot(source_data['time_days'], source_data['spread_usd_mwh'],
             color='#2A6FBB', linewidth=1.2,
             label='Evening-minus-midday spread')
    plt.axhline(y=0, linewidth=0.5, linestyle='-', color='grey')
    plt.xticks([0, 245, 611, 975],
               ['May 2023', 'Jan 2024', 'Jan 2025', 'Dec 2025'])
    plt.title('SP15 day-ahead price spread and components')
    plt.ylabel('USD/MWh')
    plt.xlabel('Operating date')
    plt.legend()
    plt.savefig(OUTPUT_FOLDER + 'figure_02_price_components.pdf')
    plt.close()

    # This block makes the battery-spread scatterplot and the Model 1 fitted
    # line.  Sorting by battery capacity prevents a misleading zig-zag line.
    scatter_data = pd.DataFrame({
        'battery_gw': analysis['battery_gw'],
        'spread_usd_mwh': analysis['spread_usd_mwh'],
        'fitted': results1.fittedvalues})
    scatter_data = scatter_data.sort_values(by=['battery_gw'])
    plt.figure(figsize=(7, 5))
    plt.plot('battery_gw', 'spread_usd_mwh', data=scatter_data,
             color='#2A6FBB', marker='o', linestyle='', alpha=0.45,
             label='Daily observations')
    plt.plot(scatter_data['battery_gw'], scatter_data['fitted'],
             color='#D55E00', linewidth=2.2,
             label='Model 1 fitted line')
    plt.axhline(y=0, linewidth=0.5, linestyle='-', color='grey')
    plt.title('Battery capacity and the daily SP15 price spread')
    plt.ylabel('Evening-minus-midday spread (USD/MWh)')
    plt.xlabel('Operating battery power capacity (GW)')
    plt.legend()
    plt.savefig(OUTPUT_FOLDER + 'figure_03_battery_spread_scatter.pdf')
    plt.close()

    # This block uses a box plot to show the distribution without treating
    # statistically unusual values as data errors.
    plt.figure(figsize=(7, 4))
    plt.boxplot(analysis['spread_usd_mwh'], orientation='horizontal')
    plt.axvline(0, linestyle='--', color='grey', linewidth=0.5)
    plt.yticks([1], ['SP15 spread'])
    plt.title('Distribution of the daily SP15 price spread')
    plt.xlabel('Evening-minus-midday spread (USD/MWh)')
    plt.savefig(OUTPUT_FOLDER + 'figure_04_spread_boxplot.pdf')
    plt.close()

    # This block plots residuals against fitted values to expose curvature,
    # changing dispersion, and isolated large residuals.
    plt.figure(figsize=(7, 5))
    plt.plot(results3_conventional.fittedvalues,
             results3_conventional.resid,
             color='#2A6FBB', marker='o', linestyle='', alpha=0.45)
    plt.axhline(y=0, linewidth=1, linestyle='--', color='black')
    plt.title('Baseline residuals against fitted values')
    plt.ylabel('Residual (USD/MWh)')
    plt.xlabel('Fitted spread (USD/MWh)')
    plt.savefig(OUTPUT_FOLDER + 'figure_05_residuals_fitted.pdf')
    plt.close()

    # This block plots residuals in chronological order.  time_days preserves
    # the one-day gap created by the complete-window rule.
    plt.figure(figsize=(8, 4.5))
    plt.plot(analysis['time_days'], results3_conventional.resid,
             color='#2A6FBB', linewidth=1)
    plt.axhline(y=0, linewidth=1, linestyle='--', color='black')
    plt.xticks([0, 245, 611, 975],
               ['May 2023', 'Jan 2024', 'Jan 2025', 'Dec 2025'])
    plt.title('Baseline residuals over time')
    plt.ylabel('Residual (USD/MWh)')
    plt.xlabel('Operating date')
    plt.savefig(OUTPUT_FOLDER + 'figure_06_residuals_time.pdf')
    plt.close()

    # This block plots the residual ACF through 30 days with approximate
    # +/-2/sqrt(n) reference lines.
    residuals = np.array(results3_conventional.resid)
    acf_values = residual_acf(residuals, 30)
    acf_reference = 2 / np.sqrt(len(residuals))
    plt.figure(figsize=(8, 4.5))
    plt.bar(range(1, 31), acf_values[1:],
            color='#2A6FBB')
    plt.axhline(y=0, linewidth=0.5, linestyle='-', color='black')
    plt.axhline(y=acf_reference, linewidth=1, linestyle='--', color='grey')
    plt.axhline(y=-acf_reference, linewidth=1, linestyle='--', color='grey')
    plt.title('Baseline residual autocorrelation through 30 days')
    plt.ylabel('Residual autocorrelation')
    plt.xlabel('Lag (days)')
    plt.savefig(OUTPUT_FOLDER + 'figure_07_residual_acf.pdf')
    plt.close()

    # This final block prints the principal interpretation inputs to the log.
    baseline_ci = results3.conf_int(0.05)
    print('PRIMARY BATTERY RESULT (conditional association, not causation)')
    print(f'Coefficient, USD/MWh per additional GW: '
          f'{results3.params["battery_gw"]}\n')
    print(f'HAC standard error, seven lags: {results3.bse["battery_gw"]}\n')
    print(f'Two-sided p value: {results3.pvalues["battery_gw"]}\n')
    print(f'95% confidence interval: '
          f'[{baseline_ci.loc["battery_gw", 0]}, '
          f'{baseline_ci.loc["battery_gw", 1]}]\n')
    print(f'Baseline observations: {results3.nobs}\n')
    print(f'Baseline R-squared: {results3.rsquared}\n')
    print('Interpret estimates as conditional historical associations only.\n')


# This block begins a reproducible log before reading or changing any data.
# It follows textbook Script 19.2. A clear error identifies a genuinely missing
# merged input rather than failing later inside pandas with an ambiguous path.
if not INPUT_FILE.is_file():
    raise FileNotFoundError(
        f'Missing analysis input: {INPUT_FILE}. '
        'Run prepare_analysis_data.py or restore the included data file.'
    )
sys.stdout = open(OUTPUT_FOLDER + '00_analysis_log.txt', 'w', encoding='utf-8')
timestamp = dt.datetime.now()
print(f'Battery-price analysis log\nCreated: {timestamp}\n')
print(f'Input file: {INPUT_FILE}\n')


# This block reads the one local analysis-ready CSV and sorts ISO-format dates.
# No network access or raw-file modification occurs.
data = pd.read_csv(INPUT_FILE)
data = data.sort_values(by=['date'])


# This block checks that every required column is present before referring to
# it.  Missing columns stop estimation rather than being guessed or imputed.
required_columns = ['date', 'time_days', 'month_id', 'weekday', 'month',
                    'spread_usd_mwh', 'evening_lmp_usd_mwh',
                    'midday_lmp_usd_mwh', 'battery_gw', 'battery_lag1_gw',
                    'demand_gap_gw',
                    'solar_drop_gw', 'gas_usd_mmbtu', 'trend_years',
                    'tariff_break']
missing_columns = []

for variable in required_columns:
    if variable not in data.columns:
        missing_columns.append(variable)

proceed = True
if len(missing_columns) > 0:
    proceed = False
    print(f'ESTIMATION STOPPED. Missing required columns: '
          f'{missing_columns}\n')


# This block checks duplicate dates, exact source-row coverage, and the sample
# boundaries.  Duplicate rows are not silently removed because that could
# conceal a failed merge or daylight-saving error.
if len(missing_columns) == 0:
    source_rows = data.shape[0]
    unique_dates = data['date'].drop_duplicates().shape[0]
    duplicate_dates = source_rows - unique_dates
    first_date = data['date'].iloc[0]
    last_date = data['date'].iloc[-1]

    if duplicate_dates > 0:
        proceed = False
    if source_rows != 976:
        proceed = False
    if first_date != '2023-05-01':
        proceed = False
    if last_date != '2025-12-31':
        proceed = False

    coverage_report = pd.DataFrame({
        'metric': ['source rows', 'unique dates', 'duplicate dates',
                   'first date', 'last date'],
        'value': [source_rows, unique_dates, duplicate_dates,
                  first_date, last_date]})
    coverage_report.to_csv(OUTPUT_FOLDER + '01_coverage_report.csv')

    print(f'Source rows: {source_rows}\n')
    print(f'Unique dates: {unique_dates}\n')
    print(f'Duplicate dates: {duplicate_dates}\n')
    print(f'Sample boundaries: {first_date} to {last_date}\n')


# This block reports missing values and applies the locked complete-window
# rule.  No interpolation, mean replacement, forward fill, or backfill is
# used.  The official EIA-930 blank on 2 November 2024 should appear here.
if len(missing_columns) == 0:
    analysis_variables = ['spread_usd_mwh', 'evening_lmp_usd_mwh',
                          'midday_lmp_usd_mwh', 'battery_gw',
                          'demand_gap_gw', 'solar_drop_gw',
                          'gas_usd_mmbtu', 'weekday', 'month',
                          'trend_years', 'tariff_break']
    missing_matrix = data[analysis_variables].isna()
    missing_counts = missing_matrix.sum(axis=0)
    complete_cases = (missing_matrix.sum(axis=1) == 0)
    complete_case_table = pd.crosstab(complete_cases, columns='count')
    analysis = pd.DataFrame(data.loc[complete_cases, :])
    dropped_dates = data.loc[
        complete_cases == False, ['date'] + analysis_variables]

    missing_counts.to_csv(OUTPUT_FOLDER + '02_missing_counts.csv')
    dropped_dates.to_csv(OUTPUT_FOLDER + '02_dropped_dates.csv')

    print(f'Missing values by variable:\n{missing_counts}\n')
    print(f'Complete-case frequency:\n{complete_case_table}\n')
    print(f'Dropped dates:\n{dropped_dates["date"]}\n')

    if analysis.shape[0] < 879:
        proceed = False
        print('ESTIMATION STOPPED. Fewer than 879 complete days.\n')
    if analysis.shape[0] != 975:
        print('WARNING: The complete-case count differs from the expected '
              '975 days. Review the missingness files before reporting.\n')


# This block runs estimation only after all validity gates pass.  Otherwise,
# the script ends with an audit log and quality-control files, not estimates.
if proceed:
    print('Coverage and complete-case gates passed. Estimation begins.\n')
    run_analysis(data, analysis)
    print('Analysis completed.\n')
else:
    print('No regression results were produced because a validity gate failed.\n')
