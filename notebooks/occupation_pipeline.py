"""
occupation_pipeline.py

Standardizes free-text job titles to a controlled occupation list using an LLM,
then attaches gender-composition data at the occupation and industry level.

Usage: import into a driver notebook and call `run_pipeline()` with a list of
dataset configs and shared settings.
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_dartmouth.llms import ChatDartmouthCloud
from tqdm.auto import tqdm


# ---------------------------------------------------------------------------
# Occupation list loaders
# ---------------------------------------------------------------------------

def load_bls_occupation_map(directory: str, year_range=range(2015, 2025)) -> dict[str, list[str]]:
    """Load year-specific BLS occupation lists from text files."""
    occ_map = {}
    for year in year_range:
        path = Path(directory) / f"occupations_{year}.txt"
        with open(path) as f:
            occ_map[str(year)] = f.read().splitlines()
    return occ_map


def load_jen_occupation_list(path: str, sheet: str, col: str) -> list[str]:
    """Load the supplemental occupation list from Jen's Excel file."""
    df = pd.read_excel(path, sheet_name=sheet)
    return list(set(df[col].values))


# ---------------------------------------------------------------------------
# LLM mapping
# ---------------------------------------------------------------------------

def get_census_occupation(student_record: pd.Series, occupations: list[str]) -> dict:
    """Call the LLM to map a single record's job title to a standardized occupation."""
    llm = ChatDartmouthCloud(
        model_name="vertex_ai.gemini-3-flash-preview",
        max_tokens=1024,
    )
    prompt = ChatPromptTemplate(
        [
            (
                "system",
                "Your task is to standardize a collection of occupation titles to a fixed, pre-defined set "
                "of occupation titles. "
                "You will receive a record of student employment that already includes an occupation title. "
                "Map this title to the best-fitting one from the provided list of allowed titles. "
                "Discuss the provided data before responding with your "
                "final decision with a valid JSON with the following keys:\n"
                "- assessment\n"
                "- occupation\n"
                "If none of the provided options are a good fit, label it as N/A."
                "The available occupation titles are:\n\n{{occupation_titles}}.",
            ),
            ("human", "Here is the employment record: \n\n {{record}}"),
        ],
        template_format="jinja2",
    )
    chain = prompt | llm | JsonOutputParser()
    return chain.invoke(
        input={
            "occupation_titles": occupations,
            "record": student_record.to_json(),
        }
    )


# ---------------------------------------------------------------------------
# Batch processing with checkpointing and retries
# ---------------------------------------------------------------------------

def _resolve_occupations(record, occupation_source):
    """Pick the right occupation list for a record given the source config."""
    if isinstance(occupation_source, dict):
        # BLS year-based map
        year = str(int(record["year"]))
        return occupation_source.get(year, occupation_source.get("2024"))
    elif isinstance(occupation_source, list):
        # Static list (e.g. Jen's)
        return occupation_source
    else:
        raise ValueError(
            f"occupation_source must be a dict (year map) or list, got {type(occupation_source)}"
        )


def _process_single_record(idx, record, id_name, results_dir, occupation_source):
    """Map one record, writing results/errors to disk for checkpointing."""
    result_file = Path(results_dir) / f"result_{idx}.json"
    if result_file.exists():
        return {"idx": idx, "status": "skipped"}

    try:
        occupations = _resolve_occupations(record, occupation_source)
        response = get_census_occupation(record, occupations)
        response[id_name] = record[id_name]

        with open(result_file, "w") as f:
            json.dump({"idx": idx, "result": response}, f, indent=2)

        return {"idx": idx, "id": record[id_name], "status": "success", "result": response}

    except Exception as e:
        error_file = Path(results_dir) / f"error_{idx}.json"
        with open(error_file, "w") as f:
            json.dump({"idx": idx, "id": record[id_name], "error": str(e)}, f, indent=2)
        return {"idx": idx, "id": record[id_name], "status": "failed", "error": str(e)}


def map_occupations(
    df: pd.DataFrame,
    columns: list[str],
    id_name: str,
    occupation_source,
    results_dir: str,
    max_retries: int = 7,
    max_workers: int | None = None,
) -> pd.DataFrame:
    """
    Run LLM occupation mapping on a dataframe with threaded execution,
    disk checkpointing, and automatic retries.

    Uses threads instead of processes — the workload is I/O-bound (LLM API
    calls), so threads avoid the macOS semlock issue with loky/multiprocessing
    and skip the overhead of serializing data across process boundaries.

    The progress bar updates as records *complete*, not when they're queued.

    Returns a DataFrame with columns: idx, <id_name>, occupation, assessment.
    """
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    records = df[columns]

    if max_workers is None:
        max_workers = min(32, (os.cpu_count() or 1) + 4)

    for attempt in range(max_retries + 1):
        # Find already-completed record indices
        completed_idxs = set()
        for rf in results_dir.glob("result_*.json"):
            with open(rf) as f:
                completed_idxs.add(json.load(f)["idx"])

        # Clean up error files from previous attempts
        for ef in results_dir.glob("error_*.json"):
            ef.unlink()

        # Figure out what still needs processing
        pending = [(idx, row) for idx, row in records.iterrows() if idx not in completed_idxs]

        if not pending:
            print(f"  ✅ All {len(completed_idxs)} records processed.")
            break

        label = "Processing" if attempt == 0 else f"Retry {attempt}/{max_retries}"
        print(f"  {label}: {len(pending)} records ({len(completed_idxs)} already done)")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _process_single_record, idx, row, id_name, str(results_dir), occupation_source
                ): idx
                for idx, row in pending
            }

            with tqdm(total=len(futures), desc=label) as pbar:
                for future in as_completed(futures):
                    future.result()  # surface any unexpected exceptions
                    pbar.update(1)

    else:
        remaining_errors = list(results_dir.glob("error_*.json"))
        print(f"  ⚠️  Reached max retries. {len(remaining_errors)} errors remain.")

    # Collect all successful results
    records_out = []
    for rf in sorted(results_dir.glob("result_*.json")):
        with open(rf) as f:
            d = json.load(f)
            d["result"]["idx"] = d["idx"]
            records_out.append(d["result"])

    return pd.DataFrame.from_records(records_out)


# ---------------------------------------------------------------------------
# Merge mapped occupations back into the source dataframe
# ---------------------------------------------------------------------------

def merge_mapped_occupations(
    df: pd.DataFrame,
    mapped: pd.DataFrame,
    id_name: str,
    merge_on_idx: bool = False,
) -> pd.DataFrame:
    """
    Merge LLM-mapped occupations back into the original dataframe.

    For datasets where a student can have multiple rows (interviews, outcomes),
    set merge_on_idx=True so the merge uses the dataframe index as well.
    """
    mapped = mapped.rename(columns={"occupation": "census_occupation"})

    if merge_on_idx:
        df = df.reset_index(names="idx")
        result = df.merge(mapped, on=["idx", id_name])
        result = result.drop(columns=["idx"])
    else:
        result = df.merge(mapped, on=id_name)

    if "assessment" in result.columns:
        result = result.drop(columns=["assessment"])

    return result


# ---------------------------------------------------------------------------
# Year extraction + cleaning
# ---------------------------------------------------------------------------

def extract_year(value):
    if pd.isna(value):
        return None
    match = re.search(r"\b(\d{4})\b", str(value))
    return int(match.group(1)) if match else None


def prepare_dataset(
    path: str,
    date_col: str,
    year_fixes: dict | None = None,
    drop_missing_year: bool = False,
) -> pd.DataFrame:
    """Load a CSV, extract year from the date column, apply manual fixes."""
    df = pd.read_csv(path)
    df["year"] = df[date_col].apply(extract_year)

    if year_fixes:
        for wrong, correct in year_fixes.items():
            df.loc[df["year"] == wrong, "year"] = correct

    if drop_missing_year:
        df = df[df["year"].notna()]

    return df


# ---------------------------------------------------------------------------
# Top-level pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    dataset_configs: list[dict],
    occupation_sources: dict,
    max_retries: int = 7,
):
    """
    Run the occupation-mapping pipeline.

    Parameters
    ----------
    dataset_configs : list of dicts, each with keys:
        - name:             human label (e.g. "admissions")
        - path:             path to source CSV
        - date_col:         column to extract year from
        - year_fixes:       dict of {wrong_year: correct_year} or None
        - drop_missing_year: whether to drop rows with no year
        - columns:          list of columns to send to the LLM
        - id_name:          student ID column name
        - merge_on_idx:     True if students can have multiple rows
        - output_path:      where to save the final Excel ({source} placeholder)

    occupation_sources : dict mapping a label to the occupation source, e.g.
        {"bls": <year_map_dict>, "jen": <list>}

    max_retries : retry count for failed LLM calls
    """
    for cfg in dataset_configs:
        name = cfg["name"]
        print(f"\n{'='*60}")
        print(f"Processing: {name}")
        print(f"{'='*60}")

        # Load and prepare
        df = prepare_dataset(
            cfg["path"],
            cfg["date_col"],
            cfg.get("year_fixes"),
            cfg.get("drop_missing_year", False),
        )

        # Run each occupation source
        for source_label, source_data in occupation_sources.items():
            print(f"\n--- Occupation source: {source_label} ---")
            results_dir = f"results/occupations/{name}/{source_label}"

            mapped = map_occupations(
                df=df,
                columns=cfg["columns"],
                id_name=cfg["id_name"],
                occupation_source=source_data,
                results_dir=results_dir,
                max_retries=max_retries,
            )

            merged = merge_mapped_occupations(
                df=df,
                mapped=mapped,
                id_name=cfg["id_name"],
                merge_on_idx=cfg.get("merge_on_idx", False),
            )

            # Save
            output = cfg["output_path"].format(source=source_label)
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            merged.to_excel(output, index=False)
            print(f"  💾 Saved: {output}")