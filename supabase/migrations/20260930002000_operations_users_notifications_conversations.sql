-- Lot 4: operational history and future user-facing persistence contracts.
-- No scheduler, notification sender, chat agent, or authentication flow is enabled here.

CREATE TABLE brvm.pipeline_definition (
    pipeline_definition_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL CHECK (code = lower(btrim(code)) AND length(code) > 0),
    version text NOT NULL CHECK (length(btrim(version)) > 0),
    description text,
    is_enabled boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT pipeline_definition_code_version_unique UNIQUE (code, version)
);

CREATE TABLE brvm.pipeline_run (
    pipeline_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_definition_id uuid NOT NULL REFERENCES brvm.pipeline_definition (pipeline_definition_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    idempotency_key text,
    attempt_number smallint NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    run_status text NOT NULL DEFAULT 'pending'
        CHECK (run_status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')),
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz,
    finished_at timestamptz,
    rows_processed bigint NOT NULL DEFAULT 0 CHECK (rows_processed >= 0),
    rows_rejected bigint NOT NULL DEFAULT 0 CHECK (rows_rejected >= 0),
    safe_error_summary text,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT pipeline_run_parameters_object CHECK (jsonb_typeof(parameters) = 'object'),
    CONSTRAINT pipeline_run_time_order CHECK (
        finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at
    ),
    CONSTRAINT pipeline_run_completion_consistent CHECK (
        (run_status IN ('succeeded', 'failed', 'cancelled') AND finished_at IS NOT NULL)
        OR (run_status IN ('pending', 'running') AND finished_at IS NULL)
    ),
    CONSTRAINT pipeline_run_error_consistent CHECK (
        run_status <> 'failed' OR safe_error_summary IS NOT NULL
    )
);

CREATE UNIQUE INDEX pipeline_run_idempotency_idx
    ON brvm.pipeline_run (pipeline_definition_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE INDEX pipeline_run_status_time_idx
    ON brvm.pipeline_run (run_status, created_at DESC);

CREATE TABLE brvm.pipeline_step_run (
    pipeline_step_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id uuid NOT NULL REFERENCES brvm.pipeline_run (pipeline_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    step_code text NOT NULL CHECK (length(btrim(step_code)) > 0),
    attempt_number smallint NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    step_status text NOT NULL DEFAULT 'pending'
        CHECK (step_status IN ('pending', 'running', 'succeeded', 'failed', 'skipped', 'cancelled')),
    started_at timestamptz,
    finished_at timestamptz,
    rows_processed bigint NOT NULL DEFAULT 0 CHECK (rows_processed >= 0),
    rows_rejected bigint NOT NULL DEFAULT 0 CHECK (rows_rejected >= 0),
    safe_error_summary text,
    CONSTRAINT pipeline_step_run_time_order CHECK (
        finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at
    ),
    CONSTRAINT pipeline_step_run_error_consistent CHECK (
        step_status <> 'failed' OR (safe_error_summary IS NOT NULL AND length(btrim(safe_error_summary)) > 0)
    ),
    CONSTRAINT pipeline_step_run_completion_consistent CHECK (
        (step_status IN ('pending', 'running') AND finished_at IS NULL)
        OR (step_status IN ('succeeded', 'failed', 'skipped', 'cancelled') AND finished_at IS NOT NULL)
    ),
    CONSTRAINT pipeline_step_attempt_unique UNIQUE (pipeline_run_id, step_code, attempt_number),
    CONSTRAINT pipeline_step_parent_pair_unique UNIQUE (pipeline_step_run_id, pipeline_run_id)
);

CREATE INDEX pipeline_step_run_parent_idx
    ON brvm.pipeline_step_run (pipeline_run_id, started_at);

CREATE TABLE brvm.pipeline_run_source (
    pipeline_run_source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id uuid NOT NULL REFERENCES brvm.pipeline_run (pipeline_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_id uuid NOT NULL REFERENCES brvm.data_source (source_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_document_id uuid,
    CONSTRAINT pipeline_run_source_document_fk
        FOREIGN KEY (source_document_id, source_id)
        REFERENCES brvm.source_document (source_document_id, source_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE TABLE brvm.pipeline_run_error (
    pipeline_run_error_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id uuid NOT NULL REFERENCES brvm.pipeline_run (pipeline_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    pipeline_step_run_id uuid,
    error_code text NOT NULL CHECK (length(btrim(error_code)) > 0),
    error_type text,
    safe_summary text NOT NULL CHECK (length(btrim(safe_summary)) > 0),
    occurred_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT pipeline_run_error_step_parent_fk
        FOREIGN KEY (pipeline_step_run_id, pipeline_run_id)
        REFERENCES brvm.pipeline_step_run (pipeline_step_run_id, pipeline_run_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE INDEX pipeline_run_error_time_idx
    ON brvm.pipeline_run_error (pipeline_run_id, occurred_at DESC);

CREATE TABLE brvm.app_user (
    app_user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_subject uuid UNIQUE,
    display_name text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT app_user_display_name_nonempty CHECK (
        display_name IS NULL OR length(btrim(display_name)) > 0
    )
);

COMMENT ON TABLE brvm.app_user IS
    'Application profile only. auth_subject is an optional future identity link, not an authentication credential.';

CREATE TRIGGER app_user_touch_updated_at
BEFORE UPDATE ON brvm.app_user
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

CREATE TABLE brvm.user_preference (
    app_user_id uuid PRIMARY KEY REFERENCES brvm.app_user (app_user_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    timezone_name text,
    market_preferences jsonb NOT NULL DEFAULT '{}'::jsonb,
    assistant_preferences jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT user_market_preferences_object CHECK (jsonb_typeof(market_preferences) = 'object'),
    CONSTRAINT user_assistant_preferences_object CHECK (jsonb_typeof(assistant_preferences) = 'object'),
    CONSTRAINT user_timezone_nonempty CHECK (timezone_name IS NULL OR length(btrim(timezone_name)) > 0)
);

CREATE TABLE brvm.notification_preference (
    notification_preference_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    app_user_id uuid NOT NULL REFERENCES brvm.app_user (app_user_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    channel_code text NOT NULL CHECK (length(btrim(channel_code)) > 0),
    is_enabled boolean NOT NULL DEFAULT false,
    quiet_hours_start time,
    quiet_hours_end time,
    timezone_name text,
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT notification_preference_user_channel_unique UNIQUE (app_user_id, channel_code),
    CONSTRAINT notification_quiet_hours_pair CHECK (
        (quiet_hours_start IS NULL AND quiet_hours_end IS NULL)
        OR (quiet_hours_start IS NOT NULL AND quiet_hours_end IS NOT NULL)
    ),
    CONSTRAINT notification_quiet_hours_timezone CHECK (
        quiet_hours_start IS NULL OR timezone_name IS NOT NULL
    )
);

CREATE TABLE brvm.alert_rule (
    alert_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    app_user_id uuid REFERENCES brvm.app_user (app_user_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    code text NOT NULL CHECK (length(btrim(code)) > 0),
    rule_definition jsonb NOT NULL,
    is_enabled boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT alert_rule_definition_object CHECK (jsonb_typeof(rule_definition) = 'object')
);

CREATE INDEX alert_rule_owner_idx ON brvm.alert_rule (app_user_id, created_at DESC);

CREATE TABLE brvm.alert_event (
    alert_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_rule_id uuid NOT NULL REFERENCES brvm.alert_rule (alert_rule_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    deduplication_key text,
    event_status text NOT NULL DEFAULT 'created'
        CHECK (event_status IN ('created', 'suppressed', 'delivered', 'failed', 'resolved')),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    resolved_at timestamptz,
    CONSTRAINT alert_event_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT alert_event_resolution_time CHECK (
        (event_status <> 'resolved' AND resolved_at IS NULL)
        OR (event_status = 'resolved' AND resolved_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX alert_event_dedup_idx
    ON brvm.alert_event (alert_rule_id, deduplication_key)
    WHERE deduplication_key IS NOT NULL;
CREATE INDEX alert_event_status_time_idx
    ON brvm.alert_event (event_status, created_at DESC);

CREATE TABLE brvm.notification_delivery (
    notification_delivery_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_event_id uuid NOT NULL REFERENCES brvm.alert_event (alert_event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    app_user_id uuid NOT NULL REFERENCES brvm.app_user (app_user_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    channel_code text NOT NULL CHECK (length(btrim(channel_code)) > 0),
    delivery_status text NOT NULL DEFAULT 'pending'
        CHECK (delivery_status IN ('pending', 'sending', 'sent', 'failed', 'cancelled')),
    attempt_count smallint NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    sent_at timestamptz,
    safe_error_code text,
    safe_error_summary text,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT notification_delivery_sent_time CHECK (
        (delivery_status = 'sent' AND sent_at IS NOT NULL)
        OR (delivery_status <> 'sent' AND sent_at IS NULL)
    ),
    CONSTRAINT notification_delivery_logical_unique
        UNIQUE (alert_event_id, app_user_id, channel_code)
);

CREATE INDEX notification_delivery_pending_idx
    ON brvm.notification_delivery (created_at)
    WHERE delivery_status IN ('pending', 'failed');
CREATE INDEX notification_delivery_user_time_idx
    ON brvm.notification_delivery (app_user_id, created_at DESC);

CREATE TABLE brvm.conversation (
    conversation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    app_user_id uuid NOT NULL REFERENCES brvm.app_user (app_user_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    title text,
    conversation_status text NOT NULL DEFAULT 'open'
        CHECK (conversation_status IN ('open', 'closed', 'archived')),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    closed_at timestamptz,
    CONSTRAINT conversation_title_nonempty CHECK (title IS NULL OR length(btrim(title)) > 0),
    CONSTRAINT conversation_closed_time CHECK (
        (conversation_status = 'open' AND closed_at IS NULL)
        OR (conversation_status <> 'open' AND closed_at IS NOT NULL)
    )
);

CREATE INDEX conversation_user_time_idx
    ON brvm.conversation (app_user_id, created_at DESC);

CREATE TABLE brvm.conversation_message (
    conversation_message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES brvm.conversation (conversation_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    sequence_number bigint NOT NULL CHECK (sequence_number >= 1),
    role_code text NOT NULL CHECK (role_code IN ('user', 'assistant', 'system', 'tool')),
    message_content text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT conversation_message_sequence_unique UNIQUE (conversation_id, sequence_number)
);

CREATE INDEX conversation_message_time_idx
    ON brvm.conversation_message (conversation_id, created_at);

CREATE TABLE brvm.conversation_tool_call (
    conversation_tool_call_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_message_id uuid NOT NULL REFERENCES brvm.conversation_message (conversation_message_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    tool_name text NOT NULL CHECK (length(btrim(tool_name)) > 0),
    call_status text NOT NULL DEFAULT 'requested'
        CHECK (call_status IN ('requested', 'succeeded', 'failed', 'rejected')),
    safe_arguments jsonb NOT NULL DEFAULT '{}'::jsonb,
    safe_result jsonb,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    finished_at timestamptz,
    CONSTRAINT conversation_tool_arguments_object CHECK (jsonb_typeof(safe_arguments) = 'object'),
    CONSTRAINT conversation_tool_result_object CHECK (
        safe_result IS NULL OR jsonb_typeof(safe_result) = 'object'
    ),
    CONSTRAINT conversation_tool_completion_time CHECK (
        (call_status = 'requested' AND finished_at IS NULL)
        OR (call_status <> 'requested' AND finished_at IS NOT NULL)
    )
);

CREATE TABLE brvm.conversation_message_source (
    conversation_message_source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_message_id uuid NOT NULL REFERENCES brvm.conversation_message (conversation_message_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    market_bar_id uuid REFERENCES brvm.market_bar (market_bar_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    financial_fact_id uuid REFERENCES brvm.financial_fact (financial_fact_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    analysis_result_id uuid REFERENCES brvm.analysis_result (analysis_result_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    signal_id uuid REFERENCES brvm.signal (signal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT conversation_message_source_one_reference CHECK (
        num_nonnulls(market_bar_id, financial_fact_id, analysis_result_id, signal_id) = 1
    )
);

CREATE TABLE brvm.audit_event (
    audit_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    app_user_id uuid REFERENCES brvm.app_user (app_user_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    action_code text NOT NULL CHECK (length(btrim(action_code)) > 0),
    entity_kind text NOT NULL CHECK (length(btrim(entity_kind)) > 0),
    entity_id uuid,
    occurred_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    safe_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT audit_context_object CHECK (jsonb_typeof(safe_context) = 'object')
);

CREATE INDEX audit_event_time_idx ON brvm.audit_event (occurred_at DESC);
CREATE INDEX audit_event_entity_idx
    ON brvm.audit_event (entity_kind, entity_id, occurred_at DESC)
    WHERE entity_id IS NOT NULL;

CREATE TRIGGER user_preference_touch_updated_at
BEFORE UPDATE ON brvm.user_preference
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

CREATE TRIGGER notification_preference_touch_updated_at
BEFORE UPDATE ON brvm.notification_preference
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

CREATE TRIGGER alert_rule_touch_updated_at
BEFORE UPDATE ON brvm.alert_rule
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

CREATE TRIGGER alert_event_touch_updated_at
BEFORE UPDATE ON brvm.alert_event
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

CREATE TRIGGER notification_delivery_touch_updated_at
BEFORE UPDATE ON brvm.notification_delivery
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

CREATE TRIGGER conversation_touch_updated_at
BEFORE UPDATE ON brvm.conversation
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();
