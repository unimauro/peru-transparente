-- Vistas materializadas para dashboards (refresco incremental por el ETL).
CREATE SCHEMA IF NOT EXISTS analytics;

-- KPIs nacionales (Dashboard Ejecutivo)
CREATE MATERIALIZED VIEW analytics.national_kpis AS
SELECT
    (SELECT count(*) FROM core.entity     WHERE is_current)                         AS total_entities,
    (SELECT count(*) FROM core.person)                                              AS total_persons,
    (SELECT count(*) FROM core.appointment WHERE is_current)                        AS total_active_appointments,
    (SELECT count(*) FROM core.company)                                             AS total_companies,
    (SELECT count(*) FROM core.contract)                                            AS total_contracts,
    (SELECT coalesce(sum(amount),0) FROM core.contract)                             AS total_contract_amount,
    (SELECT coalesce(sum(pim),0) FROM core.budget_line
        WHERE fiscal_year = extract(year FROM now()))                              AS total_budget_pim;

-- Funcionarios por sector (Dashboard Funcionarios)
CREATE MATERIALIZED VIEW analytics.officials_by_sector AS
SELECT s.name AS sector, count(DISTINCT a.person_id) AS officials
FROM core.appointment a
JOIN core.entity e ON e.id = a.entity_id AND e.is_current
JOIN core.sector s ON s.id = e.sector_id
WHERE a.is_current
GROUP BY s.name
ORDER BY officials DESC;

-- Distribución salarial por entidad (Dashboard Salarial)
CREATE MATERIALIZED VIEW analytics.salary_by_entity AS
SELECT e.id AS entity_id, e.name AS entity, e.acronym,
       count(*)                          AS n,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY a.remuneration_amount) AS median_salary,
       max(a.remuneration_amount)        AS max_salary
FROM core.appointment a
JOIN core.entity e ON e.id = a.entity_id
WHERE a.is_current AND a.remuneration_amount IS NOT NULL
GROUP BY e.id, e.name, e.acronym;

-- Contratos por entidad/región (Dashboard Contrataciones)
CREATE MATERIALIZED VIEW analytics.contracts_by_entity AS
SELECT e.id AS entity_id, e.name AS entity, e.ubigeo,
       count(*) AS n_contracts, coalesce(sum(c.amount),0) AS total_amount
FROM core.contract c
JOIN core.entity e ON e.id = c.entity_id
GROUP BY e.id, e.name, e.ubigeo;

-- Designaciones recientes (Dashboard Designaciones)
CREATE MATERIALIZED VIEW analytics.recent_appointments AS
SELECT a.id, p.full_name, e.name AS entity, pos.title AS position,
       a.start_date, a.status
FROM core.appointment a
JOIN core.person p   ON p.id = a.person_id
JOIN core.entity e   ON e.id = a.entity_id
JOIN core.position pos ON pos.id = a.position_id
WHERE a.start_date >= (now() - interval '180 days')
ORDER BY a.start_date DESC;

-- Índices para refresco concurrente
CREATE UNIQUE INDEX ON analytics.officials_by_sector (sector);
CREATE UNIQUE INDEX ON analytics.salary_by_entity (entity_id);
CREATE UNIQUE INDEX ON analytics.contracts_by_entity (entity_id);
CREATE UNIQUE INDEX ON analytics.recent_appointments (id);
