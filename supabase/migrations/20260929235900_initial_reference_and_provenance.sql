-- BRVM-AI database foundation: reference entities and source provenance.
-- No market/provider data is seeded by this migration.
-- The schema is intentionally separate from Supabase's exposed `public` schema.

CREATE SCHEMA IF NOT EXISTS brvm;

COMMENT ON SCHEMA brvm IS
    'Private BRVM-AI relational data. Do not expose through the Supabase Data API without reviewed grants and RLS.';

CREATE FUNCTION brvm.touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, brvm
AS $$
BEGIN
    NEW.updated_at := clock_timestamp();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION brvm.touch_updated_at() IS
    'Sets updated_at on updates to mutable BRVM-AI reference records.';

CREATE TABLE brvm.country (
    country_code varchar(2) PRIMARY KEY,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT country_code_format CHECK (country_code ~ '^[A-Z]{2}$')
);

COMMENT ON TABLE brvm.country IS
    'Country reference data. Populated only from a verified reference source.';

CREATE TABLE brvm.currency (
    currency_code varchar(3) PRIMARY KEY,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT currency_code_format CHECK (currency_code ~ '^[A-Z]{3}$')
);

COMMENT ON TABLE brvm.currency IS
    'Currency reference data. No currency records are assumed or seeded.';

CREATE TABLE brvm.market (
    market_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE CHECK (code = upper(btrim(code)) AND length(code) > 0),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    country_code varchar(2) REFERENCES brvm.country (country_code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    currency_code varchar(3) REFERENCES brvm.currency (currency_code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    timezone_name text,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT market_timezone_nonempty CHECK (
        timezone_name IS NULL OR length(btrim(timezone_name)) > 0
    )
);

COMMENT ON TABLE brvm.market IS
    'A trading venue or market. Time zone and reference values must come from a verified source.';

CREATE TABLE brvm.sector (
    sector_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    parent_sector_id uuid REFERENCES brvm.sector (sector_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT sector_not_own_parent CHECK (
        parent_sector_id IS NULL OR parent_sector_id <> sector_id
    ),
    CONSTRAINT sector_parent_name_unique UNIQUE (parent_sector_id, name)
);

COMMENT ON TABLE brvm.sector IS
    'Hierarchical sector taxonomy; the taxonomy and its source are selected by the project owner.';

CREATE TABLE brvm.company (
    company_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    legal_name text NOT NULL CHECK (length(btrim(legal_name)) > 0),
    country_code varchar(2) REFERENCES brvm.country (country_code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    registration_identifier text,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT company_registration_identifier_nonempty CHECK (
        registration_identifier IS NULL OR length(btrim(registration_identifier)) > 0
    )
);

COMMENT ON TABLE brvm.company IS
    'Issuer/company identity; external identifiers are optional and source-specific.';

CREATE TABLE brvm.company_sector_history (
    company_id uuid NOT NULL REFERENCES brvm.company (company_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    sector_id uuid NOT NULL REFERENCES brvm.sector (sector_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    valid_from date NOT NULL,
    valid_to date,
    source_document_id uuid,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT company_sector_history_pk PRIMARY KEY (company_id, sector_id, valid_from),
    CONSTRAINT company_sector_valid_range CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

COMMENT ON TABLE brvm.company_sector_history IS
    'Effective-dated company-sector relationships preserve historical classifications.';

CREATE TABLE brvm.security (
    security_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id uuid NOT NULL REFERENCES brvm.company (company_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    market_id uuid NOT NULL REFERENCES brvm.market (market_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    currency_code varchar(3) REFERENCES brvm.currency (currency_code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    isin varchar(12),
    valid_from date,
    valid_to date,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT security_market_pair_unique UNIQUE (security_id, market_id),
    CONSTRAINT security_isin_format CHECK (
        isin IS NULL OR isin ~ '^[A-Z]{2}[A-Z0-9]{9}[0-9]$'
    ),
    CONSTRAINT security_valid_range CHECK (
        valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from
    )
);

COMMENT ON TABLE brvm.security IS
    'A financial instrument listed or traded on a market; no instrument types or records are fabricated.';

CREATE INDEX security_company_idx ON brvm.security (company_id);
CREATE INDEX security_market_idx ON brvm.security (market_id);

CREATE TABLE brvm.security_symbol_history (
    security_symbol_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id uuid NOT NULL,
    market_id uuid NOT NULL,
    symbol text NOT NULL CHECK (length(btrim(symbol)) > 0),
    valid_from date NOT NULL,
    valid_to date,
    source_document_id uuid,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT security_symbol_security_market_fk
        FOREIGN KEY (security_id, market_id)
        REFERENCES brvm.security (security_id, market_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT security_symbol_valid_range CHECK (valid_to IS NULL OR valid_to >= valid_from),
    CONSTRAINT security_symbol_start_unique UNIQUE (market_id, symbol, valid_from)
);

COMMENT ON TABLE brvm.security_symbol_history IS
    'Effective-dated ticker/symbol history; supports symbol changes without rewriting past observations.';

CREATE INDEX security_symbol_lookup_idx
    ON brvm.security_symbol_history (market_id, symbol, valid_from DESC, valid_to);
CREATE INDEX security_symbol_security_idx
    ON brvm.security_symbol_history (security_id, valid_from DESC);

CREATE TABLE brvm.data_source (
    source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE CHECK (code = upper(btrim(code)) AND length(code) > 0),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    source_type text NOT NULL CHECK (length(btrim(source_type)) > 0),
    base_url text,
    terms_url text,
    is_enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT data_source_base_url_nonempty CHECK (
        base_url IS NULL OR length(btrim(base_url)) > 0
    ),
    CONSTRAINT data_source_terms_url_nonempty CHECK (
        terms_url IS NULL OR length(btrim(terms_url)) > 0
    )
);

COMMENT ON TABLE brvm.data_source IS
    'Registry of data origins. A row represents a source only after the owner verifies it and its terms.';

CREATE TABLE brvm.source_document (
    source_document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES brvm.data_source (source_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    external_identifier text,
    source_url text,
    storage_bucket text,
    storage_object_key text,
    mime_type text,
    content_sha256 varchar(64),
    published_at timestamptz,
    retrieved_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT source_document_external_identifier_nonempty CHECK (
        external_identifier IS NULL OR length(btrim(external_identifier)) > 0
    ),
    CONSTRAINT source_document_url_nonempty CHECK (
        source_url IS NULL OR length(btrim(source_url)) > 0
    ),
    CONSTRAINT source_document_storage_pair CHECK (
        (storage_bucket IS NULL) = (storage_object_key IS NULL)
    ),
    CONSTRAINT source_document_storage_values_nonempty CHECK (
        (storage_bucket IS NULL OR length(btrim(storage_bucket)) > 0)
        AND (storage_object_key IS NULL OR length(btrim(storage_object_key)) > 0)
    ),
    CONSTRAINT source_document_sha256_format CHECK (
        content_sha256 IS NULL OR content_sha256 ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT source_document_source_external_unique UNIQUE (source_id, external_identifier)
);

COMMENT ON TABLE brvm.source_document IS
    'Traceable source artifacts and optional private Storage object references; no Storage bucket is created here.';

CREATE INDEX source_document_source_retrieved_idx
    ON brvm.source_document (source_id, retrieved_at DESC);
CREATE INDEX source_document_published_idx
    ON brvm.source_document (published_at DESC)
    WHERE published_at IS NOT NULL;

ALTER TABLE brvm.company_sector_history
    ADD CONSTRAINT company_sector_source_document_fk
    FOREIGN KEY (source_document_id)
    REFERENCES brvm.source_document (source_document_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT;

ALTER TABLE brvm.security_symbol_history
    ADD CONSTRAINT security_symbol_source_document_fk
    FOREIGN KEY (source_document_id)
    REFERENCES brvm.source_document (source_document_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT;

CREATE INDEX company_sector_source_document_idx
    ON brvm.company_sector_history (source_document_id)
    WHERE source_document_id IS NOT NULL;

CREATE INDEX security_symbol_source_document_idx
    ON brvm.security_symbol_history (source_document_id)
    WHERE source_document_id IS NOT NULL;

CREATE TRIGGER market_touch_updated_at
BEFORE UPDATE ON brvm.market
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

CREATE TRIGGER sector_touch_updated_at
BEFORE UPDATE ON brvm.sector
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

CREATE TRIGGER company_touch_updated_at
BEFORE UPDATE ON brvm.company
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

CREATE TRIGGER security_touch_updated_at
BEFORE UPDATE ON brvm.security
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

CREATE TRIGGER data_source_touch_updated_at
BEFORE UPDATE ON brvm.data_source
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();
