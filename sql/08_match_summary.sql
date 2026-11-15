-- Team passing and outcome summary for every match (both teams).
WITH passing AS (
    SELECT
        match_id, team,
        count(*)                                               AS passes,
        count(*) FILTER (WHERE is_complete)                    AS completed,
        100.0 * avg(is_complete::INT)                          AS completion_pct,
        count(*) FILTER (WHERE is_complete AND is_progressive) AS progressive,
        -- share of completed passes made in the attacking half: a simple territory measure
        100.0 * avg((x >= 60)::INT) FILTER (WHERE is_complete) AS own_passes_in_opp_half_pct
    FROM pass_features
    GROUP BY match_id, team
),
shooting AS (
    SELECT match_id, team, sum(xg) AS xg FROM shots GROUP BY match_id, team
)
SELECT
    m.match_date,
    p.match_id,
    p.team,
    CASE WHEN p.team = m.home_team THEN m.away_team ELSE m.home_team END AS opponent,
    CASE WHEN p.team = m.home_team THEN 'H' ELSE 'A' END                AS venue,
    p.passes, p.completed, p.completion_pct, p.progressive, p.own_passes_in_opp_half_pct,
    -- possession proxy: share of the match's completed passes
    100.0 * p.completed / sum(p.completed) OVER (PARTITION BY p.match_id) AS pass_share_pct,
    -- goals from the official score (shots miss own goals)
    CASE WHEN p.team = m.home_team THEN m.home_score ELSE m.away_score END AS goals,
    CASE WHEN p.team = m.home_team THEN m.away_score ELSE m.home_score END AS goals_against,
    coalesce(s.xg, 0) AS xg
FROM passing AS p
JOIN matches AS m USING (match_id)
LEFT JOIN shooting AS s USING (match_id, team)
ORDER BY m.match_date, p.team;
