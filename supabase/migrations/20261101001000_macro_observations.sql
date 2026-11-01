-- BRVM-AI — observations macroéconomiques sourcées BCEAO/UEMOA.

CREATE TABLE brvm.macro_observation (
    macro_observation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES brvm.data_source (source_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_document_id uuid REFERENCES brvm.source_document (source_document_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    raw_ingest_record_id uuid NOT NULL,
    series_code text NOT NULL CHECK (length(btrim(series_code)) > 0),
    country_or_zone text NOT NULL CHECK (length(btrim(country_or_zone)) > 0),
    statistical_period_start date NOT NULL,
    statistical_period_end date NOT NULL,
    published_at timestamptz,
    value numeric(30, 8) NOT NULL,
    unit_code text NOT NULL CHECK (length(btrim(unit_code)) > 0),
    validation_status text NOT NULL DEFAULT 'pending'
        CHECK (validation_status IN ('pending', 'validated', 'rejected', 'quarantined')),
    collected_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT macro_observation_period_order
        CHECK (statistical_period_end >= statistical_period_start),
    CONSTRAINT macro_observation_source_record_fk
        FOREIGN KEY (raw_ingest_record_id, source_id)
        REFERENCES brvm.raw_ingest_record (raw_ingest_record_id, source_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE UNIQUE INDEX macro_observation_identity_unique
    ON brvm.macro_observation
       (source_id, series_code, country_or_zone, statistical_period_start,
        statistical_period_end, unit_code, raw_ingest_record_id);

CREATE INDEX macro_observation_series_period_idx
    ON brvm.macro_observation (series_code, country_or_zone, statistical_period_end DESC);

CREATE INDEX macro_observation_validation_idx
    ON brvm.macro_observation (validation_status, collected_at DESC)
    WHERE validation_status <> 'validated';

COMMENT ON TABLE brvm.macro_observation IS
    'Observation macroéconomique publiée; la période statistique reste distincte de la publication.';
