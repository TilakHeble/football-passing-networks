-- Minutes played per player per match.
-- On  = kick-off for starters, otherwise the time they came on as a substitute.
-- Off = the time they were substituted or sent off, otherwise the final whistle.
-- Position changes ("Tactical Shift") and temporary treatment ("Player Off/On") are ignored.
-- StatsBomb's clock restarts at 45:00 for the second half, so second-half times are
-- converted to elapsed match time: end of first half + (clock - 45:00).
CREATE OR REPLACE TEMP VIEW minutes_played AS
WITH events AS (
    SELECT
        a.*,
        c.h1_end,
        c.h1_end + (c.h2_end - 45 * 60) AS match_end,
        CASE WHEN a.from_period = 1 THEN a.from_clock
             ELSE c.h1_end + (a.from_clock - 45 * 60) END AS from_elapsed,
        CASE WHEN a.to_period = 1 THEN a.to_clock
             WHEN a.to_period = 2 THEN c.h1_end + (a.to_clock - 45 * 60) END AS to_elapsed
    FROM appearances AS a
    JOIN clock AS c USING (match_id)
),
per_player AS (
    SELECT
        match_id, team, player,
        any_value(jersey_number) AS jersey_number,
        arg_min(position, from_elapsed) AS main_position,
        bool_or(start_reason = 'Starting XI') AS started,
        min(CASE WHEN start_reason = 'Starting XI' THEN 0
                 WHEN start_reason LIKE 'Substitution - On%' THEN from_elapsed END) AS on_s,
        min(CASE WHEN end_reason LIKE 'Substitution - Off%'
                   OR end_reason LIKE 'Foul Committed%' THEN to_elapsed END) AS off_s,
        any_value(match_end) AS match_end
    FROM events
    GROUP BY match_id, team, player
)
SELECT
    match_id, team, player, jersey_number, main_position, started,
    round((coalesce(off_s, match_end) - on_s) / 60.0, 1) AS minutes
FROM per_player
WHERE on_s IS NOT NULL;
