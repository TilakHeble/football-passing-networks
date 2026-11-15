"""Run the SQL files in sql/ against the DuckDB database and return DataFrames."""
from pathlib import Path
import re

import pandas as pd

from src.database import DB_PATH, connect

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
VIEWS = ["01_minutes_played", "02_pass_features", "03_first_substitution"]


class PassAnalysis:
    """Every analysis step is a named .sql file in sql/. Files 01-03 create views."""

    def __init__(self, db_path: Path = DB_PATH):
        self.con = connect(db_path)
        for v in VIEWS:
            self.con.execute(self.sql(v))

    @staticmethod
    def sql(name: str) -> str:
        return (SQL_DIR / f"{name}.sql").read_text()

    def run(self, name: str, **params) -> pd.DataFrame:
        query = self.sql(name)
        used = set(re.findall(r"\$(\w+)", query))
        missing = used - params.keys()
        if missing:
            raise ValueError(f"{name}.sql needs parameters: {sorted(missing)}")
        return self.con.execute(query, {k: v for k, v in params.items() if k in used}).df()

    def match_id(self, team: str, opponent: str, date: str) -> int:
        return self.con.execute(
            "SELECT match_id FROM matches WHERE $t IN (home_team, away_team) "
            "AND $o IN (home_team, away_team) AND match_date = $d::DATE",
            {"t": team, "o": opponent, "d": date}).fetchall()[0][0]
