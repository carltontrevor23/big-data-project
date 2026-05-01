-- name: q1_top_inventors
SELECT
    i.inventor_id,
    i.name,
    COUNT(DISTINCT pi.patent_id) AS patent_count
FROM patent_inventors pi
JOIN inventors i
    ON pi.inventor_id = i.inventor_id
GROUP BY i.inventor_id, i.name
ORDER BY patent_count DESC, i.name
LIMIT 10;

-- name: q2_top_companies
SELECT
    c.company_id,
    c.name,
    COUNT(DISTINCT pc.patent_id) AS patent_count
FROM patent_companies pc
JOIN companies c
    ON pc.company_id = c.company_id
GROUP BY c.company_id, c.name
ORDER BY patent_count DESC, c.name
LIMIT 10;

-- name: q3_top_countries
SELECT
    i.country,
    COUNT(DISTINCT pi.patent_id) AS patent_count
FROM patent_inventors pi
JOIN inventors i
    ON pi.inventor_id = i.inventor_id
GROUP BY i.country
ORDER BY patent_count DESC, i.country
LIMIT 10;

-- name: q4_yearly_trends
SELECT
    year,
    COUNT(*) AS patent_count
FROM patents
GROUP BY year
ORDER BY year;

-- name: q5_join_query
SELECT
    p.patent_id,
    p.title,
    p.year,
    i.name AS inventor_name,
    c.name AS company_name
FROM relationships r
JOIN patents p
    ON r.patent_id = p.patent_id
JOIN inventors i
    ON r.inventor_id = i.inventor_id
LEFT JOIN companies c
    ON r.company_id = c.company_id
ORDER BY p.year DESC, p.patent_id
LIMIT 20;

-- name: q6_cte_query
WITH inventor_totals AS (
    SELECT
        i.country,
        i.inventor_id,
        i.name,
        COUNT(DISTINCT pi.patent_id) AS patent_count
    FROM patent_inventors pi
    JOIN inventors i
        ON pi.inventor_id = i.inventor_id
    GROUP BY i.country, i.inventor_id, i.name
),
country_totals AS (
    SELECT
        country,
        COUNT(*) AS inventors_in_country,
        AVG(patent_count) AS avg_patents_per_inventor
    FROM inventor_totals
    GROUP BY country
)
SELECT
    country,
    inventors_in_country,
    ROUND(avg_patents_per_inventor, 2) AS avg_patents_per_inventor
FROM country_totals
ORDER BY inventors_in_country DESC, country
LIMIT 10;

-- name: q7_ranking_query
SELECT
    inventor_id,
    name,
    patent_count,
    DENSE_RANK() OVER (ORDER BY patent_count DESC) AS inventor_rank
FROM (
    SELECT
        i.inventor_id,
        i.name,
        COUNT(DISTINCT pi.patent_id) AS patent_count
    FROM patent_inventors pi
    JOIN inventors i
        ON pi.inventor_id = i.inventor_id
    GROUP BY i.inventor_id, i.name
)
ORDER BY inventor_rank, name
LIMIT 20;
