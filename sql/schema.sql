DROP TABLE IF EXISTS relationships;
DROP TABLE IF EXISTS pipeline_runs;
DROP TABLE IF EXISTS patent_metrics;
DROP TABLE IF EXISTS patent_companies;
DROP TABLE IF EXISTS patent_inventors;
DROP TABLE IF EXISTS patents;
DROP TABLE IF EXISTS inventors;
DROP TABLE IF EXISTS companies;

CREATE TABLE patents (
    patent_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT,
    grant_date TEXT NOT NULL,
    year INTEGER NOT NULL,
    patent_type TEXT,
    num_claims INTEGER,
    title_word_count INTEGER,
    abstract_word_count INTEGER,
    patent_weight REAL
);

CREATE TABLE inventors (
    inventor_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE companies (
    company_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE patent_inventors (
    patent_id TEXT NOT NULL,
    inventor_id TEXT NOT NULL
);

CREATE TABLE patent_companies (
    patent_id TEXT NOT NULL,
    company_id TEXT NOT NULL
);

CREATE TABLE relationships (
    patent_id TEXT NOT NULL,
    inventor_id TEXT NOT NULL,
    company_id TEXT
);

CREATE TABLE patent_metrics (
    patent_id TEXT PRIMARY KEY,
    inventor_count INTEGER NOT NULL,
    company_count INTEGER NOT NULL,
    dependency_count INTEGER NOT NULL,
    claim_count INTEGER NOT NULL,
    title_word_count INTEGER NOT NULL,
    abstract_word_count INTEGER NOT NULL,
    patent_weight REAL NOT NULL
);

CREATE TABLE pipeline_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_finished_at TEXT NOT NULL,
    processing_seconds REAL NOT NULL,
    notes TEXT
);

CREATE INDEX idx_patents_year ON patents(year);
CREATE INDEX idx_patents_type ON patents(patent_type);
CREATE INDEX idx_patent_inventors_patent ON patent_inventors(patent_id);
CREATE INDEX idx_patent_inventors_inventor ON patent_inventors(inventor_id);
CREATE INDEX idx_patent_companies_patent ON patent_companies(patent_id);
CREATE INDEX idx_patent_companies_company ON patent_companies(company_id);
CREATE INDEX idx_relationships_patent ON relationships(patent_id);
CREATE INDEX idx_relationships_inventor ON relationships(inventor_id);
CREATE INDEX idx_relationships_company ON relationships(company_id);
CREATE INDEX idx_patent_metrics_weight ON patent_metrics(patent_weight);
CREATE INDEX idx_patent_metrics_dependency ON patent_metrics(dependency_count);
