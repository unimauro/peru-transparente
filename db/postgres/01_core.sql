-- Perú Transparente — esquema canónico (core) + procedencia (meta)
-- PostgreSQL 15+ con extensiones uuid-ossp y vector (pgvector)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS btree_gist;  -- para exclusion constraints SCD2

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS meta;

-- ───────────────────────── Catálogos ─────────────────────────
CREATE TABLE core.sector (
    id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        text NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.entity_type (
    id    uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code  text NOT NULL UNIQUE,        -- MINISTERIO, OPD, GR, MUNI, EMPRESA, ORG_CONST...
    name  text NOT NULL
);

-- ───────────────────────── Entidades ─────────────────────────
CREATE TABLE core.entity (
    id               uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    ruc              varchar(11),
    name             text NOT NULL,
    acronym          text,
    entity_type_id   uuid REFERENCES core.entity_type(id),
    sector_id        uuid REFERENCES core.sector(id),
    level            text CHECK (level IN ('nacional','regional','local')),
    ubigeo           char(6),
    website          text,
    transparency_url text,
    parent_entity_id uuid REFERENCES core.entity(id),
    valid_from       timestamptz NOT NULL DEFAULT now(),
    valid_to         timestamptz,
    is_current       boolean NOT NULL DEFAULT true,
    created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_entity_ruc    ON core.entity(ruc) WHERE ruc IS NOT NULL;
CREATE INDEX idx_entity_sector ON core.entity(sector_id);
CREATE INDEX idx_entity_ubigeo ON core.entity(ubigeo);
COMMENT ON TABLE core.entity IS 'Entidad pública (ministerio, OPD, GR, municipalidad, empresa, organismo constitucional).';

-- ───────────────────────── Personas ─────────────────────────
CREATE TABLE core.person (
    id                 uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name          text NOT NULL,
    normalized_name    text NOT NULL,                 -- sin tildes, mayúsculas, apellidos ordenados
    doc_type           text,
    doc_number_public  varchar(15),                   -- solo si la fuente lo publica
    birth_year         smallint,
    canonical_key      uuid,                           -- agrupa variaciones (entity resolution)
    embedding          vector(1536),                   -- búsqueda semántica
    created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_person_norm      ON core.person(normalized_name);
CREATE INDEX idx_person_canonical ON core.person(canonical_key);

-- ───────────────────────── Cargos ─────────────────────────
CREATE TABLE core.position (
    id               uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id        uuid NOT NULL REFERENCES core.entity(id),
    title            text NOT NULL,
    normalized_title text NOT NULL,
    hierarchy_level  smallint,                          -- 1 = titular
    regime           text,                              -- DL276/DL728/CAS/FAG/confianza
    is_confianza     boolean DEFAULT false
);
CREATE INDEX idx_position_entity ON core.position(entity_id);

-- ─────────────── Designaciones / nombramientos (SCD2) ───────────────
CREATE TABLE core.appointment (
    id                      uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id               uuid NOT NULL REFERENCES core.person(id),
    position_id             uuid NOT NULL REFERENCES core.position(id),
    entity_id               uuid NOT NULL REFERENCES core.entity(id),
    start_date              date NOT NULL,
    end_date                date,
    appointment_resolution  text,
    appointment_res_url     text,
    cessation_resolution    text,
    remuneration_amount     numeric(12,2),
    remuneration_currency   char(3) DEFAULT 'PEN',
    status                  text CHECK (status IN ('vigente','cesado','encargatura','rotacion')),
    is_current              boolean NOT NULL DEFAULT true,
    created_at              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_appt_person ON core.appointment(person_id);
CREATE INDEX idx_appt_entity ON core.appointment(entity_id);
CREATE INDEX idx_appt_current ON core.appointment(is_current) WHERE is_current;

-- ───────────────────── Declaraciones juradas ─────────────────────
CREATE TABLE core.asset_declaration (
    id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id     uuid NOT NULL REFERENCES core.person(id),
    entity_id     uuid REFERENCES core.entity(id),
    period        text NOT NULL,
    presented_at  date,
    assets_total  numeric(14,2),
    income_total  numeric(14,2),
    interests     jsonb,
    source_url    text,
    raw_pdf_ref   text,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_decl_person ON core.asset_declaration(person_id);

CREATE TABLE core.declaration_item (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id  uuid NOT NULL REFERENCES core.asset_declaration(id) ON DELETE CASCADE,
    kind            text CHECK (kind IN ('bien','renta','interes')),
    description     text,
    amount          numeric(14,2),
    currency        char(3)
);

-- ───────────────────── Empresas del Estado (FONAFE) ─────────────────────
CREATE TABLE core.company (
    id                    uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id             uuid REFERENCES core.entity(id),
    name                  text NOT NULL,
    ruc                   varchar(11),
    fonafe_classification text,
    sector_id             uuid REFERENCES core.sector(id),
    financials_ref        text,
    created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.company_role (
    id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id  uuid NOT NULL REFERENCES core.company(id),
    person_id   uuid NOT NULL REFERENCES core.person(id),
    role        text NOT NULL,                 -- director, gerente_general, ...
    start_date  date,
    end_date    date,
    is_current  boolean DEFAULT true
);

-- ───────────────────── Presupuesto ─────────────────────
CREATE TABLE core.budget_line (
    id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id    uuid NOT NULL REFERENCES core.entity(id),
    fiscal_year  smallint NOT NULL,
    pia          numeric(16,2),
    pim          numeric(16,2),
    devengado    numeric(16,2),
    source       text,
    UNIQUE (entity_id, fiscal_year)
);

-- ───────────────────── Contrataciones (OSCE/OECE OCDS) ─────────────────────
CREATE TABLE core.supplier (
    id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    ruc           varchar(11),
    name          text NOT NULL,
    is_state_owned boolean DEFAULT false,
    risk_flags    jsonb,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_supplier_ruc ON core.supplier(ruc);

CREATE TABLE core.contract (
    id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    ocid          text UNIQUE,
    entity_id     uuid REFERENCES core.entity(id),     -- contratante
    supplier_id   uuid REFERENCES core.supplier(id),
    title         text,
    amount        numeric(16,2),
    currency      char(3) DEFAULT 'PEN',
    sign_date     date,
    process_type  text,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_contract_entity   ON core.contract(entity_id);
CREATE INDEX idx_contract_supplier ON core.contract(supplier_id);
CREATE INDEX idx_contract_signdate ON core.contract(sign_date);

-- ───────────────────── Procedencia (provenance) ─────────────────────
CREATE TABLE meta.provenance (
    id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_table  text NOT NULL,
    target_id     uuid NOT NULL,
    field         text,
    source        text NOT NULL,            -- 'OSCE_OCDS', 'FONAFE', 'PTE', ...
    source_url    text,
    captured_at   timestamptz NOT NULL,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    confidence    numeric(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    method        text CHECK (method IN ('api','scrape','ocr','ai','manual')),
    raw_ref       text
);
CREATE INDEX idx_prov_target ON meta.provenance(target_table, target_id);

-- registro de corridas de scraping
CREATE TABLE meta.scrape_run (
    id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    source       text NOT NULL,
    started_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz,
    new_records      integer DEFAULT 0,
    changed_records  integer DEFAULT 0,
    failed_records   integer DEFAULT 0,
    status       text DEFAULT 'running',
    log          jsonb
);

-- fusiones de entidad/persona (auditable)
CREATE TABLE meta.entity_merge (
    id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    kind          text CHECK (kind IN ('person','entity','supplier')),
    canonical_id  uuid NOT NULL,
    merged_id     uuid NOT NULL,
    confidence    numeric(3,2),
    evidence      jsonb,
    created_at    timestamptz NOT NULL DEFAULT now()
);
