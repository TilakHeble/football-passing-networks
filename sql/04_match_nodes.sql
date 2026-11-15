-- Passing-network nodes for one team in one match, up to their first substitution.
-- Node position = average location of the player's completed open-play passes, made AND received.
WITH window_passes AS (
    SELECT f.*
    FROM pass_features AS f
    JOIN first_change AS fc USING (match_id, team)
    WHERE f.match_id = $match_id AND f.team = $team
      AND f.is_complete AND f.is_open_play
      AND f.elapsed < fc.cutoff_elapsed
),
touches AS (
    SELECT player,    x,     y,     1 AS made, 0 AS received FROM window_passes
    UNION ALL
    SELECT recipient, end_x, end_y, 0 AS made, 1 AS received FROM window_passes
)
SELECT
    t.player,
    mp.jersey_number,
    mp.main_position,
    avg(t.x)          AS x,
    avg(t.y)          AS y,
    sum(t.made)       AS passes_made,
    sum(t.received)   AS passes_received,
    count(*)          AS involvement
FROM touches AS t
LEFT JOIN minutes_played AS mp
       ON mp.match_id = $match_id AND mp.team = $team AND mp.player = t.player
GROUP BY t.player, mp.jersey_number, mp.main_position
ORDER BY involvement DESC;
