#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Restraint Score Calculator for Protein–Peptide Docking

Computes a composite restraint score using:
  - Distance weighting f(dij) = exp(-(dij - d0))
  - Protein spatial distribution (normalized by Lx, Ly, Lz)
  - Peptide sequence distribution (normalized by Ls)
  - Evolutionary weights wi

Input Excel layout:
  - B2..B5 contain:
      B2 = Ls, B3 = Lx, B4 = Ly, B5 = Lz
  - Restraint table header is on Excel row 7 

Required table columns:
  'prot x coor', 'prot y coor', 'prot z coor', 'sl', 'wi', 'dij'

Outputs:
  - <input>_output.xlsx with intermediate columns (fdij, omega_ij, sigma_P, sigma_L)

Author: Miriam Gulman
Date: 12.3.2025
"""

import pandas as pd
import numpy as np
import argparse
import os
from typing import Tuple

# -----------------------
# Configuration constants
# -----------------------
D0 = 1.8
LENGTH_CELLS = {
    "Ls": (1, 1),  # B2 
    "Lx": (2, 1),  # B3
    "Ly": (3, 1),  # B4
    "Lz": (4, 1),  # B5
}

TABLE_SKIPROWS = 6

REQUIRED_COLUMNS = (
    "prot x coor",
    "prot y coor",
    "prot z coor",
    "sl",
    "wi",
    "dij",
)


def read_lengths(excel_path: str) -> Tuple[float, float, float, float]:
    """Read Ls/Lx/Ly/Lz from fixed cells (B2..B5)."""
    sheet = pd.read_excel(excel_path, header=None)

    def _cell(name: str) -> float:
        r, c = LENGTH_CELLS[name]
        return float(sheet.iat[r, c])

    return _cell("Ls"), _cell("Lx"), _cell("Ly"), _cell("Lz")


def read_restraint_table(excel_path: str) -> pd.DataFrame:
    """Read the restraint table and coerce required columns to numeric."""
    df = pd.read_excel(excel_path, skiprows=TABLE_SKIPROWS)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    for c in REQUIRED_COLUMNS:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=REQUIRED_COLUMNS)
    if df.empty:
        raise ValueError("No valid rows found after cleaning (NaN/non-numeric values).")

    return df


def compute_restraint_score(excel_path: str) -> Tuple[pd.DataFrame, float]:
    """
    Compute restraint score and return:
      - dataframe with intermediate columns
      - final score (float)
    """
    Ls, Lx, Ly, Lz = read_lengths(excel_path)
    df = read_restraint_table(excel_path)
    n = len(df)

    # Distance weighting term
    df["fdij"] = np.exp(-(df["dij"] - D0))

    # Combined weight
    df["omega_ij"] = df["wi"] * df["fdij"]

    # Protein centroid of contacted atoms
    mu_x = df["prot x coor"].mean()
    mu_y = df["prot y coor"].mean()
    mu_z = df["prot z coor"].mean()

    # Protein distribution term (per restraint)
    df["sigma_P"] = (
        ((df["prot x coor"] - mu_x) / Lx) ** 2 +
        ((df["prot y coor"] - mu_y) / Ly) ** 2 +
        ((df["prot z coor"] - mu_z) / Lz) ** 2
    ) / n

    # Peptide distribution term (per restraint)
    mu_s = df["sl"].mean()
    df["sigma_L"] = ((df["sl"] - mu_s) / Ls) ** 2 / n

    # Final score
    score = float((df["omega_ij"] * (df["sigma_P"] + df["sigma_L"])).sum() * n)

    # Save output alongside input
    out_path = os.path.splitext(excel_path)[0] + "_output.xlsx"
    df.to_excel(out_path, index=False)

    print(f"File: {excel_path}")
    print(f"Lengths: Ls={Ls}, Lx={Lx}, Ly={Ly}, Lz={Lz}")
    print(f"Restraint Score (σ): {score:.6f}")
    print(f"Wrote: {out_path}")

    return df, score


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute restraint score from an Excel file."
    )
    parser.add_argument("excel_file", help="Path to the input .xlsx file")
    args = parser.parse_args()

    compute_restraint_score(args.excel_file)


if __name__ == "__main__":
    main()
