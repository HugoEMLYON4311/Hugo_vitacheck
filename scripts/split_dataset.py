# %%
"""Prepare the diabetes dataset for concatenation and merge exercises.

Outputs (in data/):
- diabetes_part1.csv: first half of the rows, gender replaced by gender_code
- diabetes_part2.csv: second half of the rows, gender replaced by gender_code
- gender_mapping.csv: mapping table gender_code -> gender
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# %% Load the raw dataset
df = pd.read_csv(DATA_DIR / "diabetes_prediction_dataset.csv")

# %% Build the mapping table
gender_mapping = pd.DataFrame(
    {
        "gender_code": ["F", "M", "O"],
        "gender": ["Female", "Male", "Other"],
    }
)

# %% Replace the gender column by its code (same position in the columns)
code_by_gender = dict(zip(gender_mapping["gender"], gender_mapping["gender_code"]))
df.insert(0, "gender_code", df["gender"].map(code_by_gender))
df = df.drop(columns="gender")
assert df["gender_code"].notna().all(), "Unknown gender value in the dataset"

# %% Split the rows into two parts
half = len(df) // 2
part1 = df.iloc[:half]
part2 = df.iloc[half:]

# %% Save
part1.to_csv(DATA_DIR / "diabetes_part1.csv", index=False)
part2.to_csv(DATA_DIR / "diabetes_part2.csv", index=False)
gender_mapping.to_csv(DATA_DIR / "gender_mapping.csv", index=False)

print(f"part1: {part1.shape}, part2: {part2.shape}, mapping: {gender_mapping.shape}")
