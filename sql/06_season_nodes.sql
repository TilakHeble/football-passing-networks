-- Season passing profile for every player with at least $min_minutes minutes.
-- Node position = average location of completed open-play passes made and received.
WITH team_passes AS (
    SELECT * FROM pass_features
    WHERE team = $team AND is_complete AND is_open_play
),
touches AS (
    SELECT player,    x,     y,     1 AS made, 0 AS received, is_progressive AS prog FROM team_passes
    UNION ALL
    SELECT recipient, end_x, end_y, 0, 1, false FROM team_passes WHERE recipient IS NOT NULL
),
minutes AS (
    SELECT player,
           sum(minutes) AS minutes,
           mode(main_position) AS usual_position,
           mode(jersey_number) AS jersey_number
    FROM minutes_played WHERE team = $team
    GROUP BY player
),
team_total AS (SELECT count(*) AS n FROM team_passes)
SELECT
    t.player,
    m.jersey_number,
    m.usual_position,
    round(m.minutes)                                        AS minutes,
    avg(t.x)                                                AS x,
    avg(t.y)                                                AS y,
    sum(t.made)                                             AS passes_made,
    sum(t.received)                                         AS passes_received,
    sum(t.made)     * 90.0 / m.minutes                      AS passes_made_p90,
    sum(t.prog::INT) * 90.0 / m.minutes                     AS progressive_p90,
    -- share of all the team's completed open-play passes this player made or received
    100.0 * (sum(t.made) + sum(t.received)) / any_value(tt.n) AS involvement_pct
FROM touches AS t
JOIN minutes AS m USING (player)
CROSS JOIN team_total AS tt
WHERE m.minutes >= $min_minutes
GROUP BY t.player, m.jersey_number, m.usual_position, m.minutes
ORDER BY involvement_pct DESC;
