-- Passing-network edges: completed open-play passes between each pair of players,
-- both directions combined, up to the team's first substitution.
SELECT
    least(f.player, f.recipient)    AS player_a,
    greatest(f.player, f.recipient) AS player_b,
    count(*)                        AS passes
FROM pass_features AS f
JOIN first_change AS fc USING (match_id, team)
WHERE f.match_id = $match_id AND f.team = $team
  AND f.is_complete AND f.is_open_play
  AND f.elapsed < fc.cutoff_elapsed
  AND f.recipient IS NOT NULL
GROUP BY player_a, player_b
ORDER BY passes DESC;
