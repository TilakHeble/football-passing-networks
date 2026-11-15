-- When each team first changed personnel (substitution or red card).
-- Match passing networks are cut here so the same 11 players are on the pitch throughout.
CREATE OR REPLACE TEMP VIEW first_change AS
SELECT
    a.match_id,
    a.team,
    min(CASE WHEN a.to_period = 1 THEN a.to_clock
             ELSE c.h1_end + (a.to_clock - 45 * 60) END) AS cutoff_elapsed
FROM appearances AS a
JOIN clock AS c USING (match_id)
WHERE a.end_reason LIKE 'Substitution - Off%' OR a.end_reason LIKE 'Foul Committed%'
GROUP BY a.match_id, a.team;
