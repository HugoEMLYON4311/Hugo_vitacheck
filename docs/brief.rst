=======================================================
Python Programming - Case Study: Diabetes Screening
=======================================================

:Authors:
    Cao Tri DO <do@em-lyon.com>
:Version: 2026-11

1. Context
==========

You are a data analyst at **VitaCheck**, a network of preventive health centres operating in Europe.
Every year, thousands of patients come for a check-up: the centres measure their age, BMI, HbA1c level
and blood glucose level, record their medical history (hypertension, heart disease, smoking) and
test whether they have diabetes.

The Medical Director asks you for a reporting in order to:

- Know **how many patients** were screened and **how many are diabetic** (the *prevalence*)
- Understand **which profiles are most at risk**: gender, age group, BMI category, smoking history, hypertension
- Check that the **biological markers** (HbA1c, blood glucose) clearly separate diabetic and non-diabetic patients
- Share the results with the prevention teams so they can **target the next awareness campaign**

.. note::

   The **prevalence** of diabetes is the share of patients who are diabetic:
   ``number of diabetic patients / number of patients``. Since ``diabetes`` is coded ``0`` / ``1``,
   it is simply the **mean** of the ``diabetes`` column.

2. About the Data
=================

The check-up data is split into 3 files:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - File
     - Content
   * - ``diabetes_part1.csv``
     - First half of the check-ups (50,000 lines)
   * - ``diabetes_part2.csv``
     - Second half of the check-ups (50,000 lines)
   * - ``gender_mapping.csv``
     - Mapping table between ``gender_code`` and ``gender``

Columns of ``diabetes_part1.csv`` and ``diabetes_part2.csv``:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Column
     - Description
   * - ``gender_code``
     - Gender of the patient, coded ``F``, ``M`` or ``O`` (see ``gender_mapping.csv``)
   * - ``age``
     - Age of the patient (in years)
   * - ``hypertension``
     - ``1`` if the patient has hypertension, ``0`` otherwise
   * - ``heart_disease``
     - ``1`` if the patient has a heart disease, ``0`` otherwise
   * - ``smoking_history``
     - ``never``, ``former``, ``current``, ``not current``, ``ever`` or ``No Info``
   * - ``bmi``
     - Body Mass Index (weight in kg / height in m²)
   * - ``HbA1c_level``
     - Average blood sugar level over the last 2-3 months (in %)
   * - ``blood_glucose_level``
     - Blood glucose level at the time of the check-up (in mg/dL)
   * - ``diabetes``
     - ``1`` if the patient is diabetic, ``0`` otherwise

Columns of ``gender_mapping.csv``: ``gender_code`` (``F``, ``M``, ``O``) and ``gender`` (``Female``, ``Male``, ``Other``).

3. To download the data: 2 options
==================================

With a Python script
--------------------

#. Copy the script below
#. Create a ``.py`` script in the ``scripts/`` folder named ``download_data.py``
#. Paste the script
#. Open a terminal
#. Run:

   **macOS / Linux:**

   .. code-block:: bash

      cd scripts && uv run download_data.py && cd ..

   **Windows (PowerShell):**

   .. code-block:: powershell

      cd scripts; uv run download_data.py; cd ..

Manually
--------

#. Download the 3 files from Brightspace
#. Paste them in the ``data/`` folder

Reference: ``download_data.py``
-------------------------------

.. code-block:: python

   # /// script
   # requires-python = ">=3.9"
   # dependencies = []
   # ///
   """Download the `diabetes` dataset into ../data/.

   Copy this file into your project folder and run:

       MacOS / Linux:
       cd scripts && uv run download_data.py && cd ..

       Windows:
       cd scripts ; uv run download_data.py ; cd ..

   Files are saved to `../data/` (relative to this script) and overwritten if
   they already exist. Only the Python standard library is used.
   """

   import json
   import sys
   import urllib.error
   import urllib.request
   from pathlib import Path

   OWNER = "emlyon-hids-python-2026"
   REPO = "course_dataset"
   BRANCH = "main"
   FOLDER = "diabetes"

   DEST = Path(__file__).resolve().parent.parent / "data"
   API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{FOLDER}?ref={BRANCH}"


   def fetch(url):
       req = urllib.request.Request(url, headers={"User-Agent": "download_data.py"})
       with urllib.request.urlopen(req) as resp:
           return resp.read()


   def main():
       try:
           entries = json.loads(fetch(API_URL))
           files = [e for e in entries if e["type"] == "file"]
           DEST.mkdir(parents=True, exist_ok=True)
           print(f"Downloading {len(files)} files to {DEST}")
           for entry in files:
               target = DEST / entry["name"]
               target.write_bytes(fetch(entry["download_url"]))
               print(f"  {entry['name']} ({target.stat().st_size:,} bytes)")
       except urllib.error.HTTPError as e:
           sys.exit(f"Download failed: HTTP {e.code} for {e.url}")
       except urllib.error.URLError as e:
           sys.exit(f"Network error: {e.reason}")
       print("Done.")


   if __name__ == "__main__":
       main()

4. Presentation of the Use Case: Technical pipeline
===================================================

Until now, each centre sent its check-up results in separate files, and the team consolidated them
by hand in Excel: copy-paste of thousands of lines, replacing the gender codes one by one with
``VLOOKUP``... This workflow leads to many manual errors and takes a lot of time.

.. code-block:: text

   diabetes_part1.csv ─┐
                       ├─ concat ──> patients ─┐
   diabetes_part2.csv ─┘                       ├─ merge (on gender_code) ──> final dataset ──> Excel
                         gender_mapping.csv ───┘

5. Objective 1: Automate the consolidation process
==================================================

#. Assemble the 3 files together into 1 unique table:

   - Load the data (``diabetes_part1``, ``diabetes_part2`` and ``gender_mapping``)
   - Assemble ``diabetes_part1`` and ``diabetes_part2`` together into ``patients`` (**concatenation**)
   - Assemble the ``patients`` table with the mapping table to get the ``gender`` column (**merge**)
   - Compute the ``bmi_category`` column with the WHO categories:

     .. list-table::
        :header-rows: 1

        * - BMI
          - ``bmi_category``
        * - below 18.5
          - ``Underweight``
        * - from 18.5 to below 25
          - ``Normal``
        * - from 25 to below 30
          - ``Overweight``
        * - 30 and above
          - ``Obese``

   - Compute the ``age_group`` column: ``0-17``, ``18-39``, ``40-59`` and ``60+``

#. Export the resulting table in an Excel file that could be used by any other team member.

.. tip::

   Look at ``pd.concat``, ``pd.merge`` (or ``DataFrame.merge``) and ``pd.cut``.
   After the merge, check that **no line was lost** and that the ``gender`` column has **no missing value**.

6. Objective 2: Answer some questions
=====================================

Technical questions from the Data Team
--------------------------------------

#. What is the number of lines and columns in our original datasets and in our final dataset?
#. What are the column names in the final dataset?
#. What are the top 5 lines of our dataset?
#. What are the last 5 lines of our dataset?
#. Make a general statistical description of all the dataset.
#. How many lines are exact duplicates? Should we keep them? (Explain your choice.)

Business questions from the Medical Team
----------------------------------------

#. How many patients were screened?
#. How many patients are diabetic, and what is the prevalence of diabetes?
#. What is the prevalence of diabetes for women and for men?
#. Which age group has the highest prevalence of diabetes?
#. What is the prevalence of diabetes for obese patients compared to patients with a normal BMI?
#. What is the average ``HbA1c_level`` and ``blood_glucose_level`` of diabetic patients compared to non-diabetic patients?
#. How many times higher is the prevalence of diabetes for patients with hypertension than for patients without?
#. Which ``smoking_history`` category has the highest prevalence of diabetes? Is it the one you expected?

7. Objective 3 (optional): Make some graph analysis
===================================================

- Make a graph of the number of patients per gender
- Make a graph of the prevalence of diabetes per age group
- Make a graph of the prevalence of diabetes per BMI category
- Make a graph comparing the distribution of ``blood_glucose_level`` for diabetic and non-diabetic patients

8. Objective 4: Export your analysis
====================================

The prevention teams would like you to export your analysis tables and your graphs in Excel so that
they can easily include your results in their next presentation (PowerPoint) for the board.

- Export the final combined dataset into an Excel file.
- **Technical team questions:** export questions 1 and 5 into distinct Excel tables, or into different sheets of the same Excel file.
- **Medical team questions:** export the questions and their answers in the same Excel file.

.. note::

   Writing Excel files with pandas needs the ``openpyxl`` package: ``uv add openpyxl``.

9. To help you export the data: create a dictionary, then a dataframe
=====================================================================

.. code-block:: python

   # %% Create a dictionary to store the analysis results
   dict_analysis = {
       "How many lines are in diabetes_part1.csv": nb_lines_part1,
       "How many lines are in diabetes_part2.csv": nb_lines_part2,
       "How many lines are in gender_mapping.csv": nb_lines_mapping,
       "How many patients were screened": nb_patients,
       "How many patients are diabetic": nb_diabetic,
       "What is the prevalence of diabetes": prevalence,
       "What is the prevalence of diabetes for women": prevalence_women,
       "What is the prevalence of diabetes for men": prevalence_men,
   }

   # %% Convert the dictionary to a DataFrame for better visualization
   df_analysis = pd.DataFrame(list(dict_analysis.items()), columns=["Question", "Answer"])

   # %% Export several tables into several sheets of the same Excel file
   with pd.ExcelWriter("data/analysis.xlsx") as writer:
       df_analysis.to_excel(writer, sheet_name="business_questions", index=False)
       df_describe.to_excel(writer, sheet_name="statistics")
