# Setup & Usage

## Activate the virtual environment

Always run this first from the project directory:

```bash
cd /Users/miyos/00_C/Fin/Prediction
source .venv/bin/activate
```

Your prompt will change to show `(.venv)` when active.

To deactivate when done:

```bash
deactivate
```

---

## Common commands

```bash
# Download historical data (run once, then weekly)
python scripts/backfill_data.py

# Launch the dashboard
streamlit run app/main.py

# Run tests
python -m pytest tests/ -v

# Daily data update (or add to cron)
python scripts/update_cache.py

# Validate indicators against known signal dates
python scripts/validate_indicators.py
```

---

## Adding dependencies

```bash
uv pip install <package>
```

To persist it, also add it to `pyproject.toml` under `dependencies`, then:

```bash
uv pip install -e ".[dev]"
```
