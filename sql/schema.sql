DROP TABLE IF EXISTS relationships;
DROP TABLE IF EXISTS patent_companies;
DROP TABLE IF EXISTS patent_inventors;
DROP TABLE IF EXISTS patents;
DROP TABLE IF EXISTS inventors;
DROP TABLE IF EXISTS companies;

CREATE TABLE patents (
    patent_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT,
    filing_date TEXT NOT NULL,
    year INTEGER NOT NULL
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

CREATE INDEX idx_patents_year ON patents(year);
CREATE INDEX idx_patent_inventors_patent ON patent_inventors(patent_id);
CREATE INDEX idx_patent_inventors_inventor ON patent_inventors(inventor_id);
CREATE INDEX idx_patent_companies_patent ON patent_companies(patent_id);
CREATE INDEX idx_patent_companies_company ON patent_companies(company_id);
CREATE INDEX idx_relationships_patent ON relationships(patent_id);
CREATE INDEX idx_relationships_inventor ON relationships(inventor_id);
CREATE INDEX idx_relationships_company ON relationships(company_id);
