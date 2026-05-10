-- name: q1_top_inventors
SELECT
    i.inventor_id,
    i.name,
    COUNT(DISTINCT pi.patent_id) AS patent_count
FROM patent_inventors pi
JOIN patents p
    ON pi.patent_id = p.patent_id
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
JOIN patents p
    ON pc.patent_id = p.patent_id
JOIN companies c
    ON pc.company_id = c.company_id
GROUP BY c.company_id, c.name
ORDER BY patent_count DESC, c.name
LIMIT 10;

-- name: q3_top_countries
WITH country_counts AS (
SELECT
    i.country,
    COUNT(DISTINCT pi.patent_id) AS patent_count
FROM patent_inventors pi
JOIN patents p
    ON pi.patent_id = p.patent_id
JOIN inventors i
    ON pi.inventor_id = i.inventor_id
GROUP BY i.country
)
SELECT
    country,
    patent_count,
    ROUND(1.0 * patent_count / SUM(patent_count) OVER (), 4) AS share
FROM country_counts
ORDER BY patent_count DESC, country
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
    JOIN patents p
        ON pi.patent_id = p.patent_id
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
    JOIN patents p
        ON pi.patent_id = p.patent_id
    JOIN inventors i
        ON pi.inventor_id = i.inventor_id
    GROUP BY i.inventor_id, i.name
)
ORDER BY inventor_rank, name
LIMIT 20;

-- name: q8_company_concentration
WITH company_counts AS (
    SELECT
        c.company_id,
        c.name,
        COUNT(DISTINCT pc.patent_id) AS patent_count
    FROM patent_companies pc
    JOIN patents p
        ON pc.patent_id = p.patent_id
    JOIN companies c
        ON pc.company_id = c.company_id
    GROUP BY c.company_id, c.name
)
SELECT
    company_id,
    name,
    patent_count
FROM company_counts
ORDER BY patent_count DESC, name;

-- name: q9_country_yearly_share
WITH country_year_counts AS (
    SELECT
        p.year,
        i.country,
        COUNT(DISTINCT pi.patent_id) AS patent_count
    FROM patent_inventors pi
    JOIN patents p
        ON pi.patent_id = p.patent_id
    JOIN inventors i
        ON pi.inventor_id = i.inventor_id
    GROUP BY p.year, i.country
),
year_totals AS (
    SELECT
        year,
        SUM(patent_count) AS yearly_country_patents
    FROM country_year_counts
    GROUP BY year
)
SELECT
    c.year,
    c.country,
    c.patent_count,
    ROUND(1.0 * c.patent_count / y.yearly_country_patents, 4) AS share
FROM country_year_counts c
JOIN year_totals y
    ON c.year = y.year
ORDER BY c.year, c.country;

-- name: q10_processing_time
SELECT
    run_id,
    run_finished_at,
    processing_seconds,
    ROUND(processing_seconds / 60.0, 2) AS processing_minutes,
    notes
FROM pipeline_runs
ORDER BY run_id DESC
LIMIT 5;

-- name: q11_patent_weight_distribution
SELECT
    p.year,
    COUNT(*) AS patent_count,
    ROUND(AVG(pm.patent_weight), 2) AS avg_patent_weight,
    ROUND(AVG(pm.claim_count), 2) AS avg_claim_count,
    ROUND(AVG(pm.dependency_count), 2) AS avg_dependencies,
    MAX(pm.patent_weight) AS max_patent_weight
FROM patent_metrics pm
JOIN patents p
    ON pm.patent_id = p.patent_id
GROUP BY p.year
ORDER BY p.year;

-- name: q12_top_weighted_patents
SELECT
    p.patent_id,
    p.title,
    p.year,
    p.patent_type,
    pm.claim_count,
    pm.inventor_count,
    pm.company_count,
    pm.dependency_count,
    pm.title_word_count,
    pm.abstract_word_count,
    pm.patent_weight
FROM patent_metrics pm
JOIN patents p
    ON pm.patent_id = p.patent_id
ORDER BY pm.patent_weight DESC, p.year DESC, p.patent_id
LIMIT 20;

-- name: q13_dependency_distribution
SELECT
    p.year,
    pm.dependency_count,
    COUNT(*) AS patent_count
FROM patent_metrics pm
JOIN patents p
    ON pm.patent_id = p.patent_id
GROUP BY p.year, pm.dependency_count
ORDER BY p.year, pm.dependency_count;

-- name: q14_type_distribution_over_time
SELECT
    year,
    COALESCE(NULLIF(patent_type, ''), 'Unknown') AS patent_type,
    COUNT(*) AS patent_count,
    ROUND(1.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY year), 4) AS yearly_share
FROM patents
GROUP BY year, COALESCE(NULLIF(patent_type, ''), 'Unknown')
ORDER BY year, patent_type;
