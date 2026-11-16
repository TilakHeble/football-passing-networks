-- Passing-network edges: completed open-play passes between each pair of players,
-- both directions combined (up to the team's first substitution by default).
SELECT
    least(f.player, f.recipient)    AS player_a,
    greatest(f.player, f.recipient) AS player_b,
    count(*)                        AS passes
FROM pass_features AS f
LEFT JOIN first_change AS fc USING (match_id, team)
WHERE f.match_id = $match_id AND f.team = $team
  AND f.is_complete AND f.is_open_play
  -- $full_match = true uses the whole match; otherwise stop at the first substitution
      AND ($full_match OR f.elapsed < coalesce(fc.cutoff_elapsed, 1e9))
  AND f.recipient IS NOT NULL
GROUP BY player_a, player_b
ORDER BY passes DESC;
