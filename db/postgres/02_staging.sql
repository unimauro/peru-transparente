-- Esquema de staging: contrato de ingesta. Tablas efímeras y re-creables.
CREATE SCHEMA IF NOT EXISTS staging;

-- Landing genérico: cada connector escribe aquí su payload tipado como jsonb,
-- junto con su procedencia. El ETL valida y promueve a core.*
CREATE TABLE staging.ingest (
    id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    source       text NOT NULL,
    record_type  text NOT NULL,        -- 'entity','person','contract','company',...
    natural_key  text,                 -- ruc/ocid/etc. para dedupe
    payload      jsonb NOT NULL,
    source_url   text,
    captured_at  timestamptz NOT NULL,
    sha256       char(64) NOT NULL,    -- hash del RAW para detección de cambios
    processed    boolean DEFAULT false,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_ingest_unprocessed ON staging.ingest(processed) WHERE NOT processed;
CREATE INDEX idx_ingest_natkey      ON staging.ingest(source, record_type, natural_key);
CREATE UNIQUE INDEX idx_ingest_hash ON staging.ingest(source, record_type, sha256);

-- Cuarentena: registros que fallan validación; no contaminan core.
CREATE TABLE staging.quarantine (
    id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    ingest_id   uuid REFERENCES staging.ingest(id),
    reason      text NOT NULL,
    details     jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);
