-- Lot 2: traceable raw records and normalized financial/market observations.
-- This migration defines storage only; it does not collect or seed market data.

ALTER TABLE brvm.source_document
    ADD CONSTRAINT source_document_id_source_unique UNIQUE (source_document_id, source_id);

CREATE TABLE brvm.raw_ingest_record (
    raw_ingest_record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES brvm.data_source (source_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_document_id uuid,
    dataset_kind text NOT NULL CHECK (length(btrim(dataset_kind)) > 0),
    source_record_key text,
    raw_payload jsonb NOT NULL,
    payload_sha256 varchar(64),
    received_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    published_at timestamptz,
    processing_status text NOT NULL DEFAULT 'received'
        CHECK (processing_status IN ('received', 'normalized', 'rejected', 'quarantined')),
    processed_at timestamptz,
    CONSTRAINT raw_ingest_source_document_fk
        FOREIGN KEY (source_document_id, source_id)
        REFERENCES brvm.source_document (source_document_id, source_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT raw_ingest_payload_hash_format CHECK (
        payload_sha256 IS NULL OR payload_sha256 ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT raw_ingest_source_record_key_nonempty CHECK (
        source_record_key IS NULL OR length(btrim(source_record_key)) > 0
    ),
    CONSTRAINT raw_ingest_processed_timestamp CHECK (
        (processing_status = 'received' AND processed_at IS NULL)
        OR (processing_status <> 'received' AND processed_at IS NOT NULL)
    ),
    CONSTRAINT raw_ingest_id_source_unique UNIQUE (raw_ingest_record_id, source_id)
);

COMMENT ON TABLE brvm.raw_ingest_record IS
    'Structurally preserved source row before normalization; original documents may be referenced by source_document.';

CREATE INDEX raw_ingest_source_received_idx
    ON brvm.raw_ingest_record (source_id, received_at DESC);
CREATE INDEX raw_ingest_status_received_idx
    ON brvm.raw_ingest_record (processing_status, received_at DESC);
CREATE INDEX raw_ingest_document_idx
    ON brvm.raw_ingest_record (source_document_id)
    WHERE source_document_id IS NOT NULL;

CREATE TABLE brvm.market_bar (
    market_bar_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id uuid NOT NULL REFERENCES brvm.security (security_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_id uuid NOT NULL REFERENCES brvm.data_source (source_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    raw_ingest_record_id uuid NOT NULL,
    interval_code text NOT NULL CHECK (interval_code = lower(btrim(interval_code)) AND length(interval_code) > 0),
    period_start timestamptz NOT NULL,
    period_end timestamptz NOT NULL,
    market_date date NOT NULL,
    opening_price numeric(24, 8),
    high_price numeric(24, 8),
    low_price numeric(24, 8),
    closing_price numeric(24, 8),
    adjusted_close numeric(24, 8),
    adjustment_method text,
    volume numeric(28, 8),
    traded_value numeric(30, 8),
    trade_count bigint,
    validation_status text NOT NULL DEFAULT 'pending'
        CHECK (validation_status IN ('pending', 'validated', 'rejected', 'quarantined')),
    published_at timestamptz,
    collected_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT market_bar_source_record_fk
        FOREIGN KEY (raw_ingest_record_id, source_id)
        REFERENCES brvm.raw_ingest_record (raw_ingest_record_id, source_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT market_bar_period_order CHECK (period_end >= period_start),
    CONSTRAINT market_bar_has_price CHECK (
        opening_price IS NOT NULL OR high_price IS NOT NULL OR low_price IS NOT NULL
        OR closing_price IS NOT NULL OR adjusted_close IS NOT NULL
    ),
    CONSTRAINT market_bar_prices_positive CHECK (
        (opening_price IS NULL OR opening_price > 0)
        AND (high_price IS NULL OR high_price > 0)
        AND (low_price IS NULL OR low_price > 0)
        AND (closing_price IS NULL OR closing_price > 0)
        AND (adjusted_close IS NULL OR adjusted_close > 0)
    ),
    CONSTRAINT market_bar_ohlc_order CHECK (
        (low_price IS NULL OR high_price IS NULL OR low_price <= high_price)
        AND (opening_price IS NULL OR low_price IS NULL OR opening_price >= low_price)
        AND (opening_price IS NULL OR high_price IS NULL OR opening_price <= high_price)
        AND (closing_price IS NULL OR low_price IS NULL OR closing_price >= low_price)
        AND (closing_price IS NULL OR high_price IS NULL OR closing_price <= high_price)
    ),
    CONSTRAINT market_bar_adjustment_method CHECK (
        adjusted_close IS NULL OR (adjustment_method IS NOT NULL AND length(btrim(adjustment_method)) > 0)
    ),
    CONSTRAINT market_bar_volume_nonnegative CHECK (volume IS NULL OR volume >= 0),
    CONSTRAINT market_bar_traded_value_nonnegative CHECK (traded_value IS NULL OR traded_value >= 0),
    CONSTRAINT market_bar_trade_count_nonnegative CHECK (trade_count IS NULL OR trade_count >= 0),
    CONSTRAINT market_bar_record_natural_unique
        UNIQUE (raw_ingest_record_id, security_id, interval_code, period_start)
);

COMMENT ON TABLE brvm.market_bar IS
    'Normalized OHLCV observation. market_date is the venue-local session date; interval_code is source-defined, not assumed.';

CREATE INDEX market_bar_series_idx
    ON brvm.market_bar (security_id, interval_code, period_start DESC);
CREATE INDEX market_bar_market_date_idx
    ON brvm.market_bar (market_date DESC, security_id);
CREATE INDEX market_bar_validation_idx
    ON brvm.market_bar (validation_status, market_date DESC)
    WHERE validation_status <> 'validated';

CREATE TABLE brvm.market_calendar_session (
    session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id uuid NOT NULL REFERENCES brvm.market (market_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    session_date date NOT NULL,
    is_open boolean NOT NULL,
    opens_at timestamptz,
    closes_at timestamptz,
    source_id uuid NOT NULL REFERENCES brvm.data_source (source_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    raw_ingest_record_id uuid NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT market_calendar_record_unique UNIQUE (market_id, session_date, raw_ingest_record_id),
    CONSTRAINT market_calendar_source_record_fk
        FOREIGN KEY (raw_ingest_record_id, source_id)
        REFERENCES brvm.raw_ingest_record (raw_ingest_record_id, source_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT market_calendar_times_consistent CHECK (
        (is_open AND opens_at IS NOT NULL AND closes_at IS NOT NULL AND closes_at > opens_at)
        OR (NOT is_open AND opens_at IS NULL AND closes_at IS NULL)
    )
);

COMMENT ON TABLE brvm.market_calendar_session IS
    'Source-backed venue sessions. No BRVM dates or trading hours are assumed or seeded.';

CREATE INDEX market_calendar_date_idx
    ON brvm.market_calendar_session (session_date DESC, market_id);

CREATE TABLE brvm.financial_period (
    financial_period_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id uuid NOT NULL REFERENCES brvm.company (company_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    period_start date NOT NULL,
    period_end date NOT NULL,
    period_kind text NOT NULL CHECK (length(btrim(period_kind)) > 0),
    reporting_scope text,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT financial_period_order CHECK (period_end >= period_start),
    CONSTRAINT financial_period_identity_unique
        UNIQUE (company_id, period_start, period_end, period_kind, reporting_scope)
);

COMMENT ON TABLE brvm.financial_period IS
    'Accounting period container; publication/availability timestamps belong to each reported fact.';

CREATE TABLE brvm.financial_fact (
    financial_fact_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    financial_period_id uuid NOT NULL REFERENCES brvm.financial_period (financial_period_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_id uuid NOT NULL REFERENCES brvm.data_source (source_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    raw_ingest_record_id uuid NOT NULL,
    metric_code text NOT NULL CHECK (metric_code = lower(btrim(metric_code)) AND length(metric_code) > 0),
    value numeric(30, 8) NOT NULL,
    currency_code varchar(3) REFERENCES brvm.currency (currency_code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    unit_code text NOT NULL CHECK (length(btrim(unit_code)) > 0),
    published_at timestamptz,
    available_at timestamptz,
    collected_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    validation_status text NOT NULL DEFAULT 'pending'
        CHECK (validation_status IN ('pending', 'validated', 'rejected', 'quarantined')),
    CONSTRAINT financial_fact_source_record_fk
        FOREIGN KEY (raw_ingest_record_id, source_id)
        REFERENCES brvm.raw_ingest_record (raw_ingest_record_id, source_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT financial_fact_metric_record_unique
        UNIQUE (raw_ingest_record_id, financial_period_id, metric_code, unit_code)
);

COMMENT ON TABLE brvm.financial_fact IS
    'Point-in-time-capable reported numeric fact. Unknown publication/availability time stays NULL and must not be guessed.';

CREATE INDEX financial_period_company_idx
    ON brvm.financial_period (company_id, period_end DESC);
CREATE INDEX financial_fact_period_metric_idx
    ON brvm.financial_fact (financial_period_id, metric_code);
CREATE INDEX financial_fact_available_idx
    ON brvm.financial_fact (available_at DESC, financial_period_id)
    WHERE available_at IS NOT NULL;
CREATE INDEX financial_fact_validation_idx
    ON brvm.financial_fact (validation_status, financial_period_id)
    WHERE validation_status <> 'validated';

CREATE TABLE brvm.corporate_action (
    corporate_action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id uuid NOT NULL REFERENCES brvm.security (security_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_id uuid NOT NULL REFERENCES brvm.data_source (source_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    raw_ingest_record_id uuid NOT NULL,
    action_type text NOT NULL CHECK (action_type = lower(btrim(action_type)) AND length(action_type) > 0),
    announced_at timestamptz,
    ex_date date,
    record_date date,
    effective_date date,
    payment_date date,
    cash_amount_per_share numeric(24, 8),
    currency_code varchar(3) REFERENCES brvm.currency (currency_code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    ratio_numerator numeric(24, 8),
    ratio_denominator numeric(24, 8),
    description text,
    validation_status text NOT NULL DEFAULT 'pending'
        CHECK (validation_status IN ('pending', 'validated', 'rejected', 'quarantined')),
    collected_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT corporate_action_source_record_fk
        FOREIGN KEY (raw_ingest_record_id, source_id)
        REFERENCES brvm.raw_ingest_record (raw_ingest_record_id, source_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT corporate_action_amount_nonnegative CHECK (
        cash_amount_per_share IS NULL OR cash_amount_per_share >= 0
    ),
    CONSTRAINT corporate_action_ratio_positive CHECK (
        (ratio_numerator IS NULL AND ratio_denominator IS NULL)
        OR (
            ratio_numerator IS NOT NULL AND ratio_denominator IS NOT NULL
            AND ratio_numerator > 0 AND ratio_denominator > 0
        )
    ),
    CONSTRAINT corporate_action_dates_order CHECK (
        (record_date IS NULL OR ex_date IS NULL OR record_date >= ex_date)
        AND (payment_date IS NULL OR ex_date IS NULL OR payment_date >= ex_date)
    ),
    CONSTRAINT corporate_action_dividend_currency CHECK (
        cash_amount_per_share IS NULL OR currency_code IS NOT NULL
    )
);

COMMENT ON TABLE brvm.corporate_action IS
    'Source-backed corporate actions, including dividends and capital events; unreported terms remain NULL.';

CREATE INDEX corporate_action_security_date_idx
    ON brvm.corporate_action (security_id, COALESCE(ex_date, effective_date) DESC);
CREATE INDEX corporate_action_validation_idx
    ON brvm.corporate_action (validation_status, collected_at DESC)
    WHERE validation_status <> 'validated';

CREATE TABLE brvm.data_quality_issue (
    data_quality_issue_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_ingest_record_id uuid REFERENCES brvm.raw_ingest_record (raw_ingest_record_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    market_bar_id uuid REFERENCES brvm.market_bar (market_bar_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    financial_fact_id uuid REFERENCES brvm.financial_fact (financial_fact_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    corporate_action_id uuid REFERENCES brvm.corporate_action (corporate_action_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    rule_code text NOT NULL CHECK (length(btrim(rule_code)) > 0),
    severity text NOT NULL CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    issue_status text NOT NULL DEFAULT 'open' CHECK (issue_status IN ('open', 'resolved', 'accepted', 'rejected')),
    description text NOT NULL CHECK (length(btrim(description)) > 0),
    safe_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    detected_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    resolved_at timestamptz,
    CONSTRAINT data_quality_issue_one_target CHECK (
        num_nonnulls(raw_ingest_record_id, market_bar_id, financial_fact_id, corporate_action_id) = 1
    ),
    CONSTRAINT data_quality_safe_context_object CHECK (jsonb_typeof(safe_context) = 'object'),
    CONSTRAINT data_quality_resolution_time CHECK (
        (issue_status = 'open' AND resolved_at IS NULL)
        OR (issue_status <> 'open' AND resolved_at IS NOT NULL)
    )
);

COMMENT ON TABLE brvm.data_quality_issue IS
    'Auditable validation findings. safe_context must not contain credentials or unnecessary raw financial payloads.';

CREATE INDEX data_quality_open_idx
    ON brvm.data_quality_issue (severity, detected_at DESC)
    WHERE issue_status = 'open';
CREATE INDEX data_quality_raw_record_idx
    ON brvm.data_quality_issue (raw_ingest_record_id)
    WHERE raw_ingest_record_id IS NOT NULL;
CREATE INDEX data_quality_market_bar_idx
    ON brvm.data_quality_issue (market_bar_id)
    WHERE market_bar_id IS NOT NULL;
CREATE INDEX data_quality_financial_fact_idx
    ON brvm.data_quality_issue (financial_fact_id)
    WHERE financial_fact_id IS NOT NULL;
CREATE INDEX data_quality_corporate_action_idx
    ON brvm.data_quality_issue (corporate_action_id)
    WHERE corporate_action_id IS NOT NULL;
