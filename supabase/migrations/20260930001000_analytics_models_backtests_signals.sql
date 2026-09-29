-- Lot 3: reproducible analytical outputs and future ML/backtest persistence.
-- These are persistence contracts only; no strategy, indicator or model is executed here.

CREATE TABLE brvm.calculation_run (
    calculation_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_kind text NOT NULL CHECK (length(btrim(run_kind)) > 0),
    code_version text NOT NULL CHECK (length(btrim(code_version)) > 0),
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    input_set_sha256 varchar(64),
    as_of timestamptz,
    run_status text NOT NULL DEFAULT 'pending'
        CHECK (run_status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')),
    started_at timestamptz,
    finished_at timestamptz,
    error_code text,
    error_summary text,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT calculation_parameters_object CHECK (jsonb_typeof(parameters) = 'object'),
    CONSTRAINT calculation_input_hash_format CHECK (
        input_set_sha256 IS NULL OR input_set_sha256 ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT calculation_run_time_order CHECK (
        finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at
    ),
    CONSTRAINT calculation_run_completion_consistent CHECK (
        (run_status IN ('succeeded', 'failed', 'cancelled') AND finished_at IS NOT NULL)
        OR (run_status IN ('pending', 'running') AND finished_at IS NULL)
    ),
    CONSTRAINT calculation_run_error_consistent CHECK (
        run_status <> 'failed' OR error_summary IS NOT NULL
    )
);

COMMENT ON TABLE brvm.calculation_run IS
    'Versioned execution metadata for reproducible analytics; it does not execute a pipeline or model.';

CREATE INDEX calculation_run_kind_time_idx
    ON brvm.calculation_run (run_kind, created_at DESC);
CREATE INDEX calculation_run_status_idx
    ON brvm.calculation_run (run_status, created_at DESC)
    WHERE run_status IN ('pending', 'running', 'failed');

CREATE TABLE brvm.calculation_input (
    calculation_input_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    calculation_run_id uuid NOT NULL REFERENCES brvm.calculation_run (calculation_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    raw_ingest_record_id uuid REFERENCES brvm.raw_ingest_record (raw_ingest_record_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    market_bar_id uuid REFERENCES brvm.market_bar (market_bar_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    financial_fact_id uuid REFERENCES brvm.financial_fact (financial_fact_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    corporate_action_id uuid REFERENCES brvm.corporate_action (corporate_action_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    content_sha256 varchar(64),
    input_role text NOT NULL DEFAULT 'feature' CHECK (length(btrim(input_role)) > 0),
    CONSTRAINT calculation_input_one_reference CHECK (
        num_nonnulls(raw_ingest_record_id, market_bar_id, financial_fact_id, corporate_action_id) = 1
    ),
    CONSTRAINT calculation_input_hash_format CHECK (
        content_sha256 IS NULL OR content_sha256 ~ '^[0-9a-f]{64}$'
    )
);

CREATE INDEX calculation_input_run_idx
    ON brvm.calculation_input (calculation_run_id);
CREATE INDEX calculation_input_market_bar_idx
    ON brvm.calculation_input (market_bar_id)
    WHERE market_bar_id IS NOT NULL;
CREATE INDEX calculation_input_financial_fact_idx
    ON brvm.calculation_input (financial_fact_id)
    WHERE financial_fact_id IS NOT NULL;

CREATE TABLE brvm.indicator_definition (
    indicator_definition_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL CHECK (code = lower(btrim(code)) AND length(code) > 0),
    version text NOT NULL CHECK (length(btrim(version)) > 0),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    category text NOT NULL CHECK (length(btrim(category)) > 0),
    unit_code text,
    definition text NOT NULL CHECK (length(btrim(definition)) > 0),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT indicator_definition_code_version_unique UNIQUE (code, version),
    CONSTRAINT indicator_definition_unit_nonempty CHECK (
        unit_code IS NULL OR length(btrim(unit_code)) > 0
    )
);

COMMENT ON TABLE brvm.indicator_definition IS
    'Explicit, versioned indicator formula registry; no indicator definitions are seeded by this migration.';

CREATE TABLE brvm.indicator_value (
    indicator_value_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    indicator_definition_id uuid NOT NULL REFERENCES brvm.indicator_definition (indicator_definition_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    calculation_run_id uuid NOT NULL REFERENCES brvm.calculation_run (calculation_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    security_id uuid REFERENCES brvm.security (security_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    company_id uuid REFERENCES brvm.company (company_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    market_id uuid REFERENCES brvm.market (market_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    observation_at timestamptz NOT NULL,
    interval_code text NOT NULL CHECK (interval_code = lower(btrim(interval_code)) AND length(interval_code) > 0),
    value numeric(30, 10) NOT NULL,
    unit_code text NOT NULL CHECK (length(btrim(unit_code)) > 0),
    calculated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT indicator_value_one_target CHECK (num_nonnulls(security_id, company_id, market_id) = 1)
);

CREATE INDEX indicator_value_security_series_idx
    ON brvm.indicator_value (security_id, interval_code, observation_at DESC)
    WHERE security_id IS NOT NULL;
CREATE INDEX indicator_value_company_series_idx
    ON brvm.indicator_value (company_id, interval_code, observation_at DESC)
    WHERE company_id IS NOT NULL;
CREATE INDEX indicator_value_market_series_idx
    ON brvm.indicator_value (market_id, interval_code, observation_at DESC)
    WHERE market_id IS NOT NULL;
CREATE INDEX indicator_value_definition_run_idx
    ON brvm.indicator_value (indicator_definition_id, calculation_run_id, observation_at DESC);

CREATE TABLE brvm.analysis_result (
    analysis_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    calculation_run_id uuid NOT NULL REFERENCES brvm.calculation_run (calculation_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    analysis_kind text NOT NULL CHECK (length(btrim(analysis_kind)) > 0),
    security_id uuid REFERENCES brvm.security (security_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    company_id uuid REFERENCES brvm.company (company_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    market_id uuid REFERENCES brvm.market (market_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    sector_id uuid REFERENCES brvm.sector (sector_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    period_start date,
    period_end date,
    as_of timestamptz,
    result jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT analysis_result_period_order CHECK (
        period_start IS NULL OR period_end IS NULL OR period_end >= period_start
    ),
    CONSTRAINT analysis_result_one_target CHECK (
        num_nonnulls(security_id, company_id, market_id, sector_id) = 1
    ),
    CONSTRAINT analysis_result_object CHECK (jsonb_typeof(result) = 'object')
);

COMMENT ON TABLE brvm.analysis_result IS
    'Versioned analysis output. target_id is a typed domain identifier documented by target_kind; source rows are linked below.';

CREATE INDEX analysis_result_target_time_idx
    ON brvm.analysis_result (security_id, created_at DESC)
    WHERE security_id IS NOT NULL;
CREATE INDEX analysis_result_company_time_idx
    ON brvm.analysis_result (company_id, created_at DESC)
    WHERE company_id IS NOT NULL;
CREATE INDEX analysis_result_market_time_idx
    ON brvm.analysis_result (market_id, created_at DESC)
    WHERE market_id IS NOT NULL;
CREATE INDEX analysis_result_sector_time_idx
    ON brvm.analysis_result (sector_id, created_at DESC)
    WHERE sector_id IS NOT NULL;
CREATE INDEX analysis_result_run_idx
    ON brvm.analysis_result (calculation_run_id);

CREATE TABLE brvm.analysis_result_source (
    analysis_result_source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_result_id uuid NOT NULL REFERENCES brvm.analysis_result (analysis_result_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    market_bar_id uuid REFERENCES brvm.market_bar (market_bar_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    financial_fact_id uuid REFERENCES brvm.financial_fact (financial_fact_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    corporate_action_id uuid REFERENCES brvm.corporate_action (corporate_action_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    raw_ingest_record_id uuid REFERENCES brvm.raw_ingest_record (raw_ingest_record_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT analysis_result_source_one_input CHECK (
        num_nonnulls(market_bar_id, financial_fact_id, corporate_action_id, raw_ingest_record_id) = 1
    )
);

CREATE INDEX analysis_result_source_market_idx
    ON brvm.analysis_result_source (market_bar_id) WHERE market_bar_id IS NOT NULL;
CREATE INDEX analysis_result_source_financial_idx
    ON brvm.analysis_result_source (financial_fact_id) WHERE financial_fact_id IS NOT NULL;

CREATE TABLE brvm.strategy (
    strategy_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE CHECK (code = lower(btrim(code)) AND length(code) > 0),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    description text,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp()
);

CREATE TABLE brvm.strategy_version (
    strategy_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id uuid NOT NULL REFERENCES brvm.strategy (strategy_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    version text NOT NULL CHECK (length(btrim(version)) > 0),
    code_version text NOT NULL CHECK (length(btrim(code_version)) > 0),
    parameters_schema jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT strategy_version_unique UNIQUE (strategy_id, version),
    CONSTRAINT strategy_parameters_schema_object CHECK (jsonb_typeof(parameters_schema) = 'object')
);

CREATE TABLE brvm.backtest_run (
    backtest_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_version_id uuid NOT NULL REFERENCES brvm.strategy_version (strategy_version_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    calculation_run_id uuid NOT NULL UNIQUE REFERENCES brvm.calculation_run (calculation_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    period_start date NOT NULL,
    period_end date NOT NULL,
    initial_capital numeric(30, 8) NOT NULL CHECK (initial_capital > 0),
    currency_code varchar(3) REFERENCES brvm.currency (currency_code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    fees_basis_points numeric(12, 6) NOT NULL DEFAULT 0 CHECK (fees_basis_points >= 0),
    slippage_basis_points numeric(12, 6) CHECK (slippage_basis_points IS NULL OR slippage_basis_points >= 0),
    availability_cutoff timestamptz,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT backtest_run_period_order CHECK (period_end >= period_start)
);

CREATE INDEX backtest_run_strategy_time_idx
    ON brvm.backtest_run (strategy_version_id, created_at DESC);

CREATE TABLE brvm.backtest_instrument (
    backtest_run_id uuid NOT NULL REFERENCES brvm.backtest_run (backtest_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    security_id uuid NOT NULL REFERENCES brvm.security (security_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    total_return numeric(18, 10),
    maximum_drawdown numeric(18, 10),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT backtest_instrument_pk PRIMARY KEY (backtest_run_id, security_id)
);

CREATE TABLE brvm.backtest_trade (
    backtest_trade_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_run_id uuid NOT NULL REFERENCES brvm.backtest_run (backtest_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    security_id uuid NOT NULL REFERENCES brvm.security (security_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    side text NOT NULL CHECK (side IN ('long', 'short')),
    entry_at timestamptz NOT NULL,
    exit_at timestamptz,
    entry_price numeric(24, 8) NOT NULL CHECK (entry_price > 0),
    exit_price numeric(24, 8) CHECK (exit_price IS NULL OR exit_price > 0),
    quantity numeric(28, 8) NOT NULL CHECK (quantity > 0),
    fees numeric(24, 8) NOT NULL DEFAULT 0 CHECK (fees >= 0),
    slippage numeric(24, 8) CHECK (slippage IS NULL OR slippage >= 0),
    realized_return numeric(18, 10),
    CONSTRAINT backtest_trade_exit_after_entry CHECK (exit_at IS NULL OR exit_at >= entry_at),
    CONSTRAINT backtest_trade_exit_values CHECK (
        (exit_at IS NULL AND exit_price IS NULL AND realized_return IS NULL)
        OR (exit_at IS NOT NULL AND exit_price IS NOT NULL)
    )
);

CREATE INDEX backtest_trade_run_time_idx
    ON brvm.backtest_trade (backtest_run_id, entry_at);
CREATE INDEX backtest_trade_security_time_idx
    ON brvm.backtest_trade (security_id, entry_at DESC);

CREATE TABLE brvm.backtest_metric (
    backtest_run_id uuid NOT NULL REFERENCES brvm.backtest_run (backtest_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    metric_code text NOT NULL CHECK (length(btrim(metric_code)) > 0),
    metric_value numeric(30, 10) NOT NULL,
    unit_code text,
    CONSTRAINT backtest_metric_pk PRIMARY KEY (backtest_run_id, metric_code),
    CONSTRAINT backtest_metric_unit_nonempty CHECK (unit_code IS NULL OR length(btrim(unit_code)) > 0)
);

CREATE TABLE brvm.ml_dataset_version (
    dataset_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_code text NOT NULL CHECK (dataset_code = lower(btrim(dataset_code)) AND length(dataset_code) > 0),
    version text NOT NULL CHECK (length(btrim(version)) > 0),
    period_start date NOT NULL,
    period_end date NOT NULL,
    as_of timestamptz,
    split_method text NOT NULL CHECK (length(btrim(split_method)) > 0),
    definition jsonb NOT NULL,
    input_set_sha256 varchar(64),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ml_dataset_version_unique UNIQUE (dataset_code, version),
    CONSTRAINT ml_dataset_period_order CHECK (period_end >= period_start),
    CONSTRAINT ml_dataset_definition_object CHECK (jsonb_typeof(definition) = 'object'),
    CONSTRAINT ml_dataset_hash_format CHECK (
        input_set_sha256 IS NULL OR input_set_sha256 ~ '^[0-9a-f]{64}$'
    )
);

CREATE TABLE brvm.ml_dataset_feature (
    dataset_version_id uuid NOT NULL REFERENCES brvm.ml_dataset_version (dataset_version_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    feature_code text NOT NULL CHECK (length(btrim(feature_code)) > 0),
    definition jsonb NOT NULL,
    unit_code text,
    CONSTRAINT ml_dataset_feature_pk PRIMARY KEY (dataset_version_id, feature_code),
    CONSTRAINT ml_dataset_feature_definition_object CHECK (jsonb_typeof(definition) = 'object')
);

CREATE TABLE brvm.ml_dataset_label (
    dataset_version_id uuid NOT NULL REFERENCES brvm.ml_dataset_version (dataset_version_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    label_code text NOT NULL CHECK (length(btrim(label_code)) > 0),
    definition jsonb NOT NULL,
    forecast_horizon text,
    CONSTRAINT ml_dataset_label_pk PRIMARY KEY (dataset_version_id, label_code),
    CONSTRAINT ml_dataset_label_definition_object CHECK (jsonb_typeof(definition) = 'object')
);

CREATE TABLE brvm.ml_dataset_sample (
    dataset_sample_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_version_id uuid NOT NULL REFERENCES brvm.ml_dataset_version (dataset_version_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    security_id uuid NOT NULL REFERENCES brvm.security (security_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    observation_at timestamptz NOT NULL,
    sample_available_at timestamptz,
    data_split text NOT NULL CHECK (data_split IN ('train', 'validation', 'test', 'inference')),
    feature_values jsonb NOT NULL,
    label_values jsonb,
    CONSTRAINT ml_dataset_sample_unique UNIQUE (dataset_version_id, security_id, observation_at),
    CONSTRAINT ml_dataset_sample_features_object CHECK (jsonb_typeof(feature_values) = 'object'),
    CONSTRAINT ml_dataset_sample_labels_object CHECK (
        label_values IS NULL OR jsonb_typeof(label_values) = 'object'
    ),
    CONSTRAINT ml_dataset_sample_no_future_availability CHECK (
        sample_available_at IS NULL OR sample_available_at <= observation_at
    )
);

CREATE INDEX ml_dataset_sample_time_idx
    ON brvm.ml_dataset_sample (dataset_version_id, observation_at, data_split);

CREATE TABLE brvm.ml_model (
    ml_model_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE CHECK (code = lower(btrim(code)) AND length(code) > 0),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    description text,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp()
);

CREATE TABLE brvm.ml_model_version (
    model_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ml_model_id uuid NOT NULL REFERENCES brvm.ml_model (ml_model_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    version text NOT NULL CHECK (length(btrim(version)) > 0),
    framework text,
    hyperparameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    artifact_uri text,
    artifact_sha256 varchar(64),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ml_model_version_unique UNIQUE (ml_model_id, version),
    CONSTRAINT ml_model_hyperparameters_object CHECK (jsonb_typeof(hyperparameters) = 'object'),
    CONSTRAINT ml_model_artifact_hash_format CHECK (
        artifact_sha256 IS NULL OR artifact_sha256 ~ '^[0-9a-f]{64}$'
    )
);

CREATE TABLE brvm.ml_model_evaluation (
    model_evaluation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id uuid NOT NULL REFERENCES brvm.ml_model_version (model_version_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    dataset_version_id uuid NOT NULL REFERENCES brvm.ml_dataset_version (dataset_version_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    calculation_run_id uuid NOT NULL REFERENCES brvm.calculation_run (calculation_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    data_split text NOT NULL CHECK (data_split IN ('train', 'validation', 'test')),
    metric_code text NOT NULL CHECK (length(btrim(metric_code)) > 0),
    metric_value numeric(30, 10) NOT NULL,
    evaluated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ml_evaluation_unique UNIQUE (model_version_id, dataset_version_id, data_split, metric_code, calculation_run_id)
);

CREATE TABLE brvm.ml_prediction (
    prediction_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id uuid NOT NULL REFERENCES brvm.ml_model_version (model_version_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    dataset_sample_id uuid REFERENCES brvm.ml_dataset_sample (dataset_sample_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    security_id uuid NOT NULL REFERENCES brvm.security (security_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    calculation_run_id uuid NOT NULL REFERENCES brvm.calculation_run (calculation_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    predicted_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    target_at timestamptz,
    prediction jsonb NOT NULL,
    confidence numeric(8, 7) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    CONSTRAINT ml_prediction_object CHECK (jsonb_typeof(prediction) = 'object'),
    CONSTRAINT ml_prediction_horizon CHECK (target_at IS NULL OR target_at >= predicted_at)
);

CREATE INDEX ml_prediction_security_time_idx
    ON brvm.ml_prediction (security_id, predicted_at DESC);

CREATE TABLE brvm.ml_prediction_outcome (
    prediction_outcome_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id uuid NOT NULL REFERENCES brvm.ml_prediction (prediction_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    observed_at timestamptz NOT NULL,
    outcome jsonb NOT NULL,
    source_fact_id uuid REFERENCES brvm.financial_fact (financial_fact_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_market_bar_id uuid REFERENCES brvm.market_bar (market_bar_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT ml_prediction_outcome_one_source CHECK (
        num_nonnulls(source_fact_id, source_market_bar_id) = 1
    ),
    CONSTRAINT ml_prediction_outcome_object CHECK (jsonb_typeof(outcome) = 'object')
);

CREATE TABLE brvm.signal (
    signal_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id uuid NOT NULL REFERENCES brvm.security (security_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    calculation_run_id uuid NOT NULL REFERENCES brvm.calculation_run (calculation_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    model_version_id uuid REFERENCES brvm.ml_model_version (model_version_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    strategy_version_id uuid REFERENCES brvm.strategy_version (strategy_version_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    generated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    valid_until timestamptz,
    direction text NOT NULL CHECK (length(btrim(direction)) > 0),
    score numeric(18, 10),
    confidence numeric(8, 7) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    status text NOT NULL DEFAULT 'provisional'
        CHECK (status IN ('provisional', 'active', 'expired', 'retracted', 'evaluated')),
    explanation text,
    outcome jsonb,
    CONSTRAINT signal_one_generator CHECK (num_nonnulls(model_version_id, strategy_version_id) = 1),
    CONSTRAINT signal_validity_order CHECK (valid_until IS NULL OR valid_until >= generated_at),
    CONSTRAINT signal_outcome_object CHECK (outcome IS NULL OR jsonb_typeof(outcome) = 'object')
);

CREATE INDEX signal_security_time_idx
    ON brvm.signal (security_id, generated_at DESC);
CREATE INDEX signal_status_time_idx
    ON brvm.signal (status, generated_at DESC);

CREATE TABLE brvm.signal_factor (
    signal_factor_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id uuid NOT NULL REFERENCES brvm.signal (signal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    factor_code text NOT NULL CHECK (length(btrim(factor_code)) > 0),
    contribution numeric(18, 10),
    explanation text,
    source_market_bar_id uuid REFERENCES brvm.market_bar (market_bar_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_financial_fact_id uuid REFERENCES brvm.financial_fact (financial_fact_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT signal_factor_one_source CHECK (
        num_nonnulls(source_market_bar_id, source_financial_fact_id) = 1
    )
);

CREATE INDEX signal_factor_signal_idx ON brvm.signal_factor (signal_id);
