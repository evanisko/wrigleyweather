#!/usr/bin/env python3

from __future__ import annotations

import csv
from pathlib import Path


FIELDNAMES = [
    "date",
    "game_number",
    "day_of_week",
    "visiting_team",
    "visiting_league",
    "visiting_team_game_number",
    "home_team",
    "home_league",
    "home_team_game_number",
    "visiting_score",
    "home_score",
    "game_length_outs",
    "day_night",
    "completion_info",
    "forfeit_info",
    "protest_info",
    "park_id",
    "attendance",
    "game_time_minutes",
    "visiting_line_score",
    "home_line_score",
    "visiting_at_bats",
    "visiting_hits",
    "visiting_doubles",
    "visiting_triples",
    "visiting_home_runs",
    "visiting_rbi",
    "visiting_sacrifice_hits",
    "visiting_sacrifice_flies",
    "visiting_hit_by_pitch",
    "visiting_walks",
    "visiting_intentional_walks",
    "visiting_strikeouts",
    "visiting_stolen_bases",
    "visiting_caught_stealing",
    "visiting_grounded_into_double_plays",
    "visiting_awarded_first_on_catcher_interference",
    "visiting_left_on_base",
    "visiting_pitchers_used",
    "visiting_individual_earned_runs",
    "visiting_team_earned_runs",
    "visiting_wild_pitches",
    "visiting_balks",
    "visiting_putouts",
    "visiting_assists",
    "visiting_errors",
    "visiting_passed_balls",
    "visiting_double_plays",
    "visiting_triple_plays",
    "home_at_bats",
    "home_hits",
    "home_doubles",
    "home_triples",
    "home_home_runs",
    "home_rbi",
    "home_sacrifice_hits",
    "home_sacrifice_flies",
    "home_hit_by_pitch",
    "home_walks",
    "home_intentional_walks",
    "home_strikeouts",
    "home_stolen_bases",
    "home_caught_stealing",
    "home_grounded_into_double_plays",
    "home_awarded_first_on_catcher_interference",
    "home_left_on_base",
    "home_pitchers_used",
    "home_individual_earned_runs",
    "home_team_earned_runs",
    "home_wild_pitches",
    "home_balks",
    "home_putouts",
    "home_assists",
    "home_errors",
    "home_passed_balls",
    "home_double_plays",
    "home_triple_plays",
    "home_plate_umpire_id",
    "home_plate_umpire_name",
    "first_base_umpire_id",
    "first_base_umpire_name",
    "second_base_umpire_id",
    "second_base_umpire_name",
    "third_base_umpire_id",
    "third_base_umpire_name",
    "left_field_umpire_id",
    "left_field_umpire_name",
    "right_field_umpire_id",
    "right_field_umpire_name",
    "visiting_manager_id",
    "visiting_manager_name",
    "home_manager_id",
    "home_manager_name",
    "winning_pitcher_id",
    "winning_pitcher_name",
    "losing_pitcher_id",
    "losing_pitcher_name",
    "saving_pitcher_id",
    "saving_pitcher_name",
    "game_winning_rbi_batter_id",
    "game_winning_rbi_batter_name",
    "visiting_starting_pitcher_id",
    "visiting_starting_pitcher_name",
    "home_starting_pitcher_id",
    "home_starting_pitcher_name",
    "visiting_starting_player_1_id",
    "visiting_starting_player_1_name",
    "visiting_starting_player_1_position",
    "visiting_starting_player_2_id",
    "visiting_starting_player_2_name",
    "visiting_starting_player_2_position",
    "visiting_starting_player_3_id",
    "visiting_starting_player_3_name",
    "visiting_starting_player_3_position",
    "visiting_starting_player_4_id",
    "visiting_starting_player_4_name",
    "visiting_starting_player_4_position",
    "visiting_starting_player_5_id",
    "visiting_starting_player_5_name",
    "visiting_starting_player_5_position",
    "visiting_starting_player_6_id",
    "visiting_starting_player_6_name",
    "visiting_starting_player_6_position",
    "visiting_starting_player_7_id",
    "visiting_starting_player_7_name",
    "visiting_starting_player_7_position",
    "visiting_starting_player_8_id",
    "visiting_starting_player_8_name",
    "visiting_starting_player_8_position",
    "visiting_starting_player_9_id",
    "visiting_starting_player_9_name",
    "visiting_starting_player_9_position",
    "home_starting_player_1_id",
    "home_starting_player_1_name",
    "home_starting_player_1_position",
    "home_starting_player_2_id",
    "home_starting_player_2_name",
    "home_starting_player_2_position",
    "home_starting_player_3_id",
    "home_starting_player_3_name",
    "home_starting_player_3_position",
    "home_starting_player_4_id",
    "home_starting_player_4_name",
    "home_starting_player_4_position",
    "home_starting_player_5_id",
    "home_starting_player_5_name",
    "home_starting_player_5_position",
    "home_starting_player_6_id",
    "home_starting_player_6_name",
    "home_starting_player_6_position",
    "home_starting_player_7_id",
    "home_starting_player_7_name",
    "home_starting_player_7_position",
    "home_starting_player_8_id",
    "home_starting_player_8_name",
    "home_starting_player_8_position",
    "home_starting_player_9_id",
    "home_starting_player_9_name",
    "home_starting_player_9_position",
    "additional_info",
    "acquisition_info",
]


def normalize_row(row: list[str]) -> list[str]:
    if len(row) < len(FIELDNAMES):
        row = row + ["NULL"] * (len(FIELDNAMES) - len(row))
    elif len(row) > len(FIELDNAMES):
        raise ValueError(
            f"Expected {len(FIELDNAMES)} fields, found {len(row)} fields in row starting with {row[:5]!r}"
        )

    return [value if value != "" else "NULL" for value in row]


def convert_file(source: Path) -> tuple[Path, int]:
    destination = source.with_suffix(".csv")
    row_count = 0

    with source.open(newline="", encoding="utf-8") as infile, destination.open(
        "w", newline="", encoding="utf-8"
    ) as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        writer.writerow(FIELDNAMES)

        for row in reader:
            if not row:
                continue
            writer.writerow(normalize_row(row))
            row_count += 1

    return destination, row_count


def main() -> None:
    base_dir = Path("gl2020_25")
    sources = sorted(base_dir.glob("*.txt"))

    if not sources:
        raise SystemExit("No .txt files found in gl2020_25")

    for source in sources:
        destination, row_count = convert_file(source)
        print(f"{source} -> {destination} ({row_count} rows)")


if __name__ == "__main__":
    main()
