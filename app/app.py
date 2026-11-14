"""VitaCheck - Diabetes Screening: Streamlit app.

Reproduces the whole pipeline (ingestion, transformation, macro analysis)
and lets the user export the insights.

Run it from the project root:

    uv run streamlit run app/app.py
"""

import io
import re
import zipfile
from pathlib import Path
from typing import IO

import matplotlib

matplotlib.use("Agg")  # no GUI backend: the figures are rendered by Streamlit

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from openpyxl.drawing.image import Image

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

PART_COLUMNS = {
    "gender_code",
    "age",
    "hypertension",
    "heart_disease",
    "smoking_history",
    "bmi",
    "HbA1c_level",
    "blood_glucose_level",
    "diabetes",
}
MAPPING_COLUMNS = {"gender_code", "gender"}

Source = str | Path | IO[bytes]


# --- Ingestion and transformation ----------------------------------------------


def read_csv(source: Source, required: set[str], name: str) -> pd.DataFrame:
    """Read a CSV file and check that it contains the expected columns."""
    df = pd.read_csv(source)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{name} is missing the columns: {sorted(missing)}")
    return df


def load_data(
    part1: Source, part2: Source, gender_mapping: Source
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Ingestion: load the two parts of the check-ups and the gender mapping table."""
    return (
        read_csv(part1, PART_COLUMNS, "diabetes_part1.csv"),
        read_csv(part2, PART_COLUMNS, "diabetes_part2.csv"),
        read_csv(gender_mapping, MAPPING_COLUMNS, "gender_mapping.csv"),
    )


def consolidate(
    part1: pd.DataFrame, part2: pd.DataFrame, gender_mapping: pd.DataFrame
) -> pd.DataFrame:
    """Transformation: concatenate the two parts, then merge the gender mapping table."""
    patients = pd.concat([part1, part2], ignore_index=True)
    df_final = patients.merge(gender_mapping, on="gender_code", how="left")

    if len(df_final) != len(patients):
        raise ValueError(
            "The merge changed the number of lines: "
            "gender_code must be unique in the mapping table"
        )
    unmapped = df_final.loc[df_final["gender"].isna(), "gender_code"].unique()
    if len(unmapped) > 0:
        raise ValueError(
            f"Gender codes missing from the mapping table: {list(unmapped)}"
        )
    return df_final


def quality_checks(
    part1: pd.DataFrame, part2: pd.DataFrame, df_final: pd.DataFrame
) -> pd.DataFrame:
    """Return a table of checks proving that the consolidation is correct."""
    same_length = len(df_final) == len(part1) + len(part2)
    checks = {
        "Check": [
            "Lines after concatenation = part1 + part2",
            "Lines unchanged by the gender merge",
            "Every patient has a gender",
            "Missing values in the final dataset",
        ],
        "Result": [
            same_length,
            same_length,
            bool(df_final["gender"].notna().all()),
            int(df_final.isna().sum().sum()),
        ],
    }
    return pd.DataFrame(checks).astype({"Result": str})


# --- Macro analysis ------------------------------------------------------------


def compute_shapes(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Number of lines and columns of each dataset."""
    shapes = {
        "dataset": list(datasets),
        "nb_lines": [df.shape[0] for df in datasets.values()],
        "nb_columns": [df.shape[1] for df in datasets.values()],
    }
    return pd.DataFrame(shapes)


def prevalence_by(df: pd.DataFrame, column: str) -> pd.Series:
    """Prevalence of diabetes (mean of the 0/1 `diabetes` column) for each value of `column`."""
    return df.groupby(column)["diabetes"].mean()


def headline_kpis(df: pd.DataFrame) -> dict[str, float]:
    """The key figures displayed at the top of the analysis page."""
    return {
        "Patients screened": len(df),
        "Diabetic patients": int(df["diabetes"].sum()),
        "Prevalence of diabetes": df["diabetes"].mean(),
        "Average age": df["age"].mean(),
    }


def answer_business_questions(df: pd.DataFrame) -> dict[str, object]:
    """Return a dictionary {question: answer} for the business questions."""
    by_gender = prevalence_by(df, "gender")
    age_by_diabetes = df.groupby("diabetes")["age"].mean()
    markers = df.groupby("diabetes")[["HbA1c_level", "blood_glucose_level"]].mean()
    by_hypertension = prevalence_by(df, "hypertension")
    by_smoking = prevalence_by(df, "smoking_history").sort_values(ascending=False)
    is_obese = df["bmi"] >= 30

    return {
        "How many patients were screened": len(df),
        "How many patients are diabetic": int(df["diabetes"].sum()),
        "What is the prevalence of diabetes": df["diabetes"].mean(),
        "What is the prevalence of diabetes for women": by_gender.get("Female"),
        "What is the prevalence of diabetes for men": by_gender.get("Male"),
        "What is the average age of diabetic patients": age_by_diabetes.get(1),
        "What is the average age of non-diabetic patients": age_by_diabetes.get(0),
        "What is the prevalence of diabetes for patients with BMI >= 30": df.loc[
            is_obese, "diabetes"
        ].mean(),
        "What is the prevalence of diabetes for patients with BMI < 30": df.loc[
            ~is_obese, "diabetes"
        ].mean(),
        "What is the average HbA1c_level of diabetic patients": markers[
            "HbA1c_level"
        ].get(1),
        "What is the average HbA1c_level of non-diabetic patients": markers[
            "HbA1c_level"
        ].get(0),
        "What is the average blood_glucose_level of diabetic patients": markers[
            "blood_glucose_level"
        ].get(1),
        "What is the average blood_glucose_level of non-diabetic patients": markers[
            "blood_glucose_level"
        ].get(0),
        "How many times higher is the prevalence with hypertension": by_hypertension.get(
            1
        )
        / by_hypertension.get(0),
        "Which smoking_history category has the highest prevalence": by_smoking.index[
            0
        ],
    }


def build_insights_table(
    part1: pd.DataFrame,
    part2: pd.DataFrame,
    gender_mapping: pd.DataFrame,
    df_final: pd.DataFrame,
) -> pd.DataFrame:
    """Question / Answer table combining dataset sizes and business questions."""
    # Duplicates are kept: without a patient identifier, two patients can share the same profile
    answers = {
        "How many lines are in diabetes_part1.csv": len(part1),
        "How many lines are in diabetes_part2.csv": len(part2),
        "How many lines are in gender_mapping.csv": len(gender_mapping),
        "How many lines are exact duplicates": int(df_final.duplicated().sum()),
        **answer_business_questions(df_final),
    }
    return pd.DataFrame(list(answers.items()), columns=["Question", "Answer"]).astype(
        {"Answer": str}
    )


# --- Charts --------------------------------------------------------------------


def bar_chart(series: pd.Series, title: str) -> Figure:
    """Bar chart of a series."""
    fig, ax = plt.subplots()
    series.plot.bar(ax=ax, title=title, rot=0)
    return fig


def histogram_by_diabetes(df: pd.DataFrame, column: str, title: str) -> Figure:
    """Distribution of `column` for non-diabetic and diabetic patients."""
    fig, ax = plt.subplots()
    for value, label in [(0, "non-diabetic"), (1, "diabetic")]:
        ax.hist(
            df.loc[df["diabetes"] == value, column],
            bins=40,
            alpha=0.5,
            density=True,
            label=label,
        )
    ax.set_title(title)
    ax.legend()
    return fig


def make_graphs(df: pd.DataFrame) -> dict[str, Figure]:
    """Create the graphs of the analysis, keyed by title."""
    return {
        "Number of patients per gender": bar_chart(
            df["gender"].value_counts(), "Number of patients per gender"
        ),
        "Prevalence of diabetes per gender": bar_chart(
            prevalence_by(df, "gender"), "Prevalence of diabetes per gender"
        ),
        "Distribution of age": histogram_by_diabetes(df, "age", "Distribution of age"),
        "Distribution of blood glucose level": histogram_by_diabetes(
            df, "blood_glucose_level", "Distribution of blood glucose level"
        ),
    }


# --- Export --------------------------------------------------------------------


def figure_to_png(fig: Figure) -> bytes:
    """Render a figure as PNG bytes."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    return buffer.getvalue()


def png_file_name(title: str) -> str:
    """File name of a graph, built from its title."""
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") + ".png"


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """The final dataset as CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(
    df_shapes: pd.DataFrame,
    df_describe: pd.DataFrame,
    df_insights: pd.DataFrame,
    graphs: dict[str, Figure],
) -> bytes:
    """The analysis report as Excel bytes: one sheet per table, plus a sheet of graphs."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_shapes.to_excel(writer, sheet_name="shapes", index=False)
        df_describe.to_excel(writer, sheet_name="describe")
        df_insights.to_excel(writer, sheet_name="business_questions", index=False)

        sheet = writer.book.create_sheet("graphs")
        for i, fig in enumerate(graphs.values()):
            sheet.add_image(Image(io.BytesIO(figure_to_png(fig))), f"A{1 + 25 * i}")
    return buffer.getvalue()


def graphs_to_zip_bytes(graphs: dict[str, Figure]) -> bytes:
    """All the graphs as PNG files in a zip archive."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for title, fig in graphs.items():
            archive.writestr(png_file_name(title), figure_to_png(fig))
    return buffer.getvalue()


# --- User interface ------------------------------------------------------------


def choose_inputs() -> tuple[Source, Source, Source]:
    """Sidebar: let the user choose the data source and return the three files."""
    st.sidebar.header("1. Data source")
    source = st.sidebar.radio(
        "Where do the files come from?",
        ["Project data/ folder", "Upload my own files"],
    )

    if source == "Project data/ folder":
        return (
            DATA_DIR / "diabetes_part1.csv",
            DATA_DIR / "diabetes_part2.csv",
            DATA_DIR / "gender_mapping.csv",
        )

    up_part1 = st.sidebar.file_uploader("diabetes_part1.csv", type="csv")
    up_part2 = st.sidebar.file_uploader("diabetes_part2.csv", type="csv")
    up_mapping = st.sidebar.file_uploader("gender_mapping.csv", type="csv")
    if not (up_part1 and up_part2 and up_mapping):
        st.info("Upload the three CSV files in the sidebar to start.")
        st.stop()
    return up_part1, up_part2, up_mapping


def main() -> None:
    """Run the pipeline and display the four tabs."""
    st.set_page_config(page_title="VitaCheck - Diabetes Screening", layout="wide")
    st.title("VitaCheck - Diabetes Screening")
    st.caption("Ingestion → Transformation → Analysis → Export")

    try:
        part1, part2, gender_mapping = load_data(*choose_inputs())
        df_final = consolidate(part1, part2, gender_mapping)
    except (FileNotFoundError, ValueError) as error:
        st.error(f"Could not run the pipeline: {error}")
        st.stop()

    df_shapes = compute_shapes(
        {
            "diabetes_part1.csv": part1,
            "diabetes_part2.csv": part2,
            "gender_mapping.csv": gender_mapping,
            "final dataset": df_final,
        }
    )
    df_describe = df_final.describe(include="all")
    df_insights = build_insights_table(part1, part2, gender_mapping, df_final)

    tab_ingest, tab_transform, tab_analysis, tab_export = st.tabs(
        ["1. Ingestion", "2. Transformation", "3. Analysis", "4. Export"]
    )

    with tab_ingest:
        st.subheader("Raw files")
        st.dataframe(df_shapes.iloc[:3], hide_index=True)
        for name, df in [
            ("diabetes_part1.csv", part1),
            ("diabetes_part2.csv", part2),
            ("gender_mapping.csv", gender_mapping),
        ]:
            with st.expander(f"{name} ({df.shape[0]} lines)"):
                st.dataframe(df.head(20))

    with tab_transform:
        st.subheader("Consolidation")
        st.markdown(
            "1. Concatenate `diabetes_part1.csv` and `diabetes_part2.csv`\n"
            "2. Left-merge `gender_mapping.csv` on `gender_code`"
        )
        st.dataframe(quality_checks(part1, part2, df_final), hide_index=True)
        st.write(
            f"Final dataset: {df_final.shape[0]} lines, {df_final.shape[1]} columns"
        )
        st.dataframe(df_final.head(50))
        st.subheader("Summary statistics")
        st.dataframe(df_final.describe())
        st.dataframe(df_final.describe(include=["str"]).astype(str))

    with tab_analysis:
        kpis = headline_kpis(df_final)
        cols = st.columns(len(kpis))
        cols[0].metric("Patients screened", f"{kpis['Patients screened']:,}")
        cols[1].metric("Diabetic patients", f"{kpis['Diabetic patients']:,}")
        cols[2].metric(
            "Prevalence of diabetes", f"{kpis['Prevalence of diabetes']:.1%}"
        )
        cols[3].metric("Average age", f"{kpis['Average age']:.1f}")

        st.subheader("Business questions")
        st.dataframe(df_insights, hide_index=True, width="stretch")

        st.subheader("Graphs")
        graphs = make_graphs(df_final)
        left, right = st.columns(2)
        for i, fig in enumerate(graphs.values()):
            (left if i % 2 == 0 else right).pyplot(fig)

    with tab_export:
        st.subheader("Download the insights")
        st.download_button(
            "Analysis report (Excel)",
            to_excel_bytes(df_shapes, df_describe, df_insights, graphs),
            file_name="diabetes_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.download_button(
            "Final dataset (CSV)",
            to_csv_bytes(df_final),
            file_name="diabetes_final.csv",
            mime="text/csv",
        )
        st.download_button(
            "Graphs (PNG, zip)",
            graphs_to_zip_bytes(graphs),
            file_name="diabetes_graphs.zip",
            mime="application/zip",
        )
    plt.close("all")


main()
