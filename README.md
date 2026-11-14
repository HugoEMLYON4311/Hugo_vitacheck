# do_course06

Python project for course 06 of the Python Programming course (emlyon business school).

## Installation

```bash
git clone <repository-url>
cd do_course06
uv sync
```

## Usage

```bash
uv run scripts/demo.py
```

Or with the Makefile:

```bash
make help   # list available commands
make run    # run the demo script
```

## Streamlit app

```bash
make run_app   # or: uv run streamlit run app/app.py
```

The app reproduces the pipeline (ingestion, transformation, macro analysis) on the CSV files loaded by the user
(any number of check-up parts plus the gender mapping), and exports the insights (Excel report, final CSV, PNG graphs).

## Project structure

- `data/`: datasets (not tracked by git)
- `notebooks/`: Jupyter notebooks
- `scripts/`: Python scripts
- `app/`: Streamlit app (`app/app.py`)
- `src/`: Python package

## Author

Cao Tri DO <do@em-lyon.com>
