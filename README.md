# Community Development Priority Dashboard

This project was created for a data visualization assignment focused on community development planning. The dashboard compares state-level indicators from 2022-2024 and lets users explore patterns by year, population group, Census region, and metric.

## Data sources

- U.S. Census Bureau American Community Survey (ACS)
- U.S. Bureau of Labor Statistics Local Area Unemployment Statistics (LAUS)

The dashboard uses poverty, unemployment, household internet access, educational attainment, and public-transit commuting. A 0-100 priority score combines the indicators using within-year percentile ranks.

## Files

- `app.py` - Streamlit dashboard
- `build_data.py` - downloads, cleans, merges, validates, and saves the public data
- `requirements.txt` - Python packages needed by Streamlit Community Cloud
- `.streamlit/config.toml` - dashboard theme settings
- `data/` - location where the prepared CSV is created

## Run locally

```bash
pip install -r requirements.txt
python build_data.py
streamlit run app.py
```

If the CSV does not exist, the deployed app also attempts to build it automatically from the public Census and BLS sources.

## Responsible use

The priority score is a screening tool for comparing patterns. State averages can hide local differences, so the results should be combined with local data and community input before making real funding decisions.
