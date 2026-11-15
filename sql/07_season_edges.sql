-- Season edges: completed open-play passes between each pair of players (both directions).
SELECT
    least(player, recipient)    AS player_a,
    greatest(player, recipient) AS player_b,
    count(*)                    AS passes,
    count(*) / 34.0             AS passes_per_match
FROM pass_features
WHERE team = $team AND is_complete AND is_open_play AND recipient IS NOT NULL
GROUP BY player_a, player_b
ORDER BY passes DESC;
