-- Pass-level features. Elapsed match time lets us compare passes with substitution times.
-- Open play = not a set piece (corners, free kicks, throw-ins, goal kicks, kick-offs).
-- Progressive pass (a common definition): ends at least 25% closer to the centre of the
-- opponent's goal (120, 40) than it started, and ends in the opponent's half.
CREATE OR REPLACE TEMP VIEW pass_features AS
SELECT
    p.*,
    CASE WHEN p.period = 1 THEN p.clock ELSE c.h1_end + (p.clock - 45 * 60) END AS elapsed,
    p.outcome IS NULL                                            AS is_complete,
    coalesce(p.pass_type, 'Open play') IN ('Open play', 'Recovery', 'Interception') AS is_open_play,
    sqrt(power(120 - p.end_x, 2) + power(40 - p.end_y, 2))
        <= 0.75 * sqrt(power(120 - p.x, 2) + power(40 - p.y, 2))
        AND p.end_x >= 60                                        AS is_progressive
FROM passes AS p
JOIN clock AS c USING (match_id);
