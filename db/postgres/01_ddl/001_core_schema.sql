-- SPDX-License-Identifier: Apache-2.0
-- ============================================================================
-- 房满乐 PMS · 生产数据库 Schema (PostgreSQL 16, 单租户)
--
-- 本文件由本地 fml_seed 容器 (postgres:16) 经 pg_dump --schema-only 生成，
-- 与运行时 ensure_single_hotel_schema 产出的单租户 schema 完全一致（零 SQLite 依赖）。
-- 生成命令: docker exec fml-pg pg_dump -U fml -d fml_seed --schema-only --no-owner --no-privileges
-- 重新生成: 修改 demo 数据后运行 db/postgres/03_demo/refresh_demo.sh
-- ============================================================================

--
--






--
--

CREATE TABLE public.acquisition_contents (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    channel character varying(30),
    title character varying(200) NOT NULL,
    topic character varying(80),
    status character varying(20),
    impressions integer,
    engagements integer,
    spend numeric(12,2),
    campaign_id integer,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.acquisition_contents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.acquisition_contents_id_seq OWNED BY public.acquisition_contents.id;


--
--

CREATE TABLE public.acquisition_leads (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    channel character varying(30),
    lead_type character varying(20),
    external_id character varying(120),
    nickname character varying(80),
    phone character varying(30),
    wechat character varying(80),
    stage character varying(20),
    intent character varying(20),
    note_title character varying(200),
    source_note_url character varying(500),
    xhs_plan_id character varying(80),
    xhs_creative_id character varying(80),
    xhs_unit_id character varying(80),
    payload_type character varying(40),
    campaign_json text,
    content_id integer,
    guest_id integer,
    order_id integer,
    remark character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.acquisition_leads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.acquisition_leads_id_seq OWNED BY public.acquisition_leads.id;


--
--

CREATE TABLE public.ai_action_confirmations (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    interpretation_id integer NOT NULL,
    action_index integer NOT NULL,
    action_kind character varying(40) NOT NULL,
    action_payload text,
    decision character varying(20) NOT NULL,
    decided_by character varying(80),
    decided_at timestamp without time zone,
    decision_remark character varying(200),
    exec_result text,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.ai_action_confirmations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.ai_action_confirmations_id_seq OWNED BY public.ai_action_confirmations.id;


--
--

CREATE TABLE public.ai_ask_queries (
    id integer NOT NULL,
    session_id character varying(64) NOT NULL,
    hotel_id integer NOT NULL,
    parent_query_id integer,
    raw_question text,
    normalized_question text,
    resolved_question text,
    intent_id character varying(64),
    intent_label character varying(120),
    metric_id character varying(64),
    operator_id character varying(32),
    slots_json text,
    tier0_candidates text,
    need_clarify boolean,
    clarify_round integer,
    confirmed_at timestamp without time zone,
    query_ref character varying(80),
    result_json text,
    answer_json text,
    playbook_tips text,
    model_name character varying(80),
    snapshot_hash character varying(64),
    pii_accessed boolean,
    pii_ack_by character varying(40),
    pii_ack_at timestamp without time zone,
    created_by character varying(40),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.ai_ask_queries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.ai_ask_queries_id_seq OWNED BY public.ai_ask_queries.id;


--
--

CREATE TABLE public.ai_ask_sessions (
    session_id character varying(64) NOT NULL,
    hotel_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    last_active_at timestamp without time zone DEFAULT now()
);


--
--

CREATE TABLE public.ai_commands (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    user_id integer,
    utterance character varying(255),
    intent character varying(40),
    result text,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.ai_commands_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.ai_commands_id_seq OWNED BY public.ai_commands.id;


--
--

CREATE TABLE public.ai_diagnosis_results (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    generated_at timestamp without time zone NOT NULL,
    snapshot_json text,
    model_name character varying(80),
    issues_json text,
    status character varying(20),
    created_by character varying(40),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.ai_diagnosis_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.ai_diagnosis_results_id_seq OWNED BY public.ai_diagnosis_results.id;


--
--

CREATE TABLE public.ai_report_interpretations (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    report_code character varying(40) NOT NULL,
    report_type character varying(60) NOT NULL,
    period_start date,
    period_end date,
    period_label character varying(80),
    compare character varying(20),
    snapshot_hash character varying(64),
    snapshot_json text,
    insight text,
    findings_json text,
    suggestions_json text,
    actions_json text,
    raw_response text,
    model_name character varying(80),
    prompt_version character varying(40),
    status character varying(20),
    created_by character varying(60),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.ai_report_interpretations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.ai_report_interpretations_id_seq OWNED BY public.ai_report_interpretations.id;


--
--

CREATE TABLE public.ap_invoices (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    invoice_no character varying(32) NOT NULL,
    ap_type character varying(30) NOT NULL,
    vendor_name character varying(120) NOT NULL,
    channel_id integer,
    ota_settlement_id integer,
    doc_label character varying(120),
    amount numeric(14,2),
    paid_amount numeric(14,2),
    due_date date,
    status character varying(20),
    note character varying(120),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.ap_invoices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.ap_invoices_id_seq OWNED BY public.ap_invoices.id;


--
--

CREATE TABLE public.app_settings (
    key character varying(80) NOT NULL,
    value_json text,
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE TABLE public.ar_ap_logs (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    action character varying(30) NOT NULL,
    ref_type character varying(10),
    ref_id integer,
    operator_id integer,
    operator_name character varying(60),
    amount numeric(14,2),
    reason text,
    meta text,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.ar_ap_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.ar_ap_logs_id_seq OWNED BY public.ar_ap_logs.id;


--
--

CREATE TABLE public.ar_invoices (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    invoice_no character varying(32) NOT NULL,
    ar_type character varying(30) NOT NULL,
    customer_name character varying(120) NOT NULL,
    corp_id integer,
    channel_id integer,
    order_id integer,
    ota_settlement_id integer,
    pms_ar_entry_id integer,
    doc_label character varying(120),
    amount numeric(14,2),
    paid_amount numeric(14,2),
    due_date date,
    status character varying(20),
    credit_limit_snapshot numeric(14,2),
    pill_note character varying(80),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.ar_invoices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.ar_invoices_id_seq OWNED BY public.ar_invoices.id;


--
--

CREATE TABLE public.asset_alerts (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_date date NOT NULL,
    asset_id integer,
    room_no character varying(20),
    floor character varying(20),
    asset_name character varying(120),
    alert_type character varying(20),
    severity character varying(20),
    message character varying(200),
    status character varying(20),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.asset_alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.asset_alerts_id_seq OWNED BY public.asset_alerts.id;


--
--

CREATE TABLE public.asset_audit_items (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_date date NOT NULL,
    name character varying(120) NOT NULL,
    theoretical_qty integer,
    actual_qty integer,
    risk character varying(200),
    severity character varying(20),
    status character varying(20),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.asset_audit_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.asset_audit_items_id_seq OWNED BY public.asset_audit_items.id;


--
--

CREATE TABLE public.asset_events (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    asset_id integer NOT NULL,
    event_type character varying(40),
    title character varying(120) NOT NULL,
    happened_at timestamp without time zone,
    note character varying(300),
    cost numeric(10,2),
    owner character varying(40),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.asset_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.asset_events_id_seq OWNED BY public.asset_events.id;


--
--

CREATE TABLE public.asset_insights (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_date date NOT NULL,
    asset_id integer,
    title character varying(120) NOT NULL,
    recommendation character varying(300),
    impact_amount numeric(12,2),
    category character varying(20),
    status character varying(20),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.asset_insights_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.asset_insights_id_seq OWNED BY public.asset_insights.id;


--
--

CREATE TABLE public.asset_maintenance (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    asset_id integer NOT NULL,
    task_type character varying(40),
    due_date date,
    status character varying(20),
    cost numeric(10,2),
    note character varying(200),
    owner character varying(40),
    completed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.asset_maintenance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.asset_maintenance_id_seq OWNED BY public.asset_maintenance.id;


--
--

CREATE TABLE public.assets (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    name character varying(120) NOT NULL,
    asset_no character varying(40),
    category character varying(40),
    location character varying(80),
    room_no character varying(20),
    sn character varying(60),
    brand_model character varying(80),
    purchase_date date,
    purchase_value numeric(12,2),
    current_value numeric(12,2),
    repair_cost_total numeric(12,2),
    health_score integer,
    insight character varying(200),
    warranty_until date,
    runtime_hours integer,
    avg_power_w numeric(10,2),
    next_maintain_date date,
    supplier character varying(80),
    dept character varying(40),
    status character varying(20)
);


--
--

CREATE SEQUENCE public.assets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.assets_id_seq OWNED BY public.assets.id;


--
--

CREATE TABLE public.campaigns (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    channel character varying(30),
    name character varying(120),
    external_plan_id character varying(80),
    status character varying(20),
    spend numeric(12,2),
    attributed_rev numeric(12,2),
    roi numeric(8,2),
    start_date date,
    end_date date
);


--
--

CREATE SEQUENCE public.campaigns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.campaigns_id_seq OWNED BY public.campaigns.id;


--
--

CREATE TABLE public.channel_attribution (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    order_id integer,
    source character varying(30),
    attributed_rev numeric(12,2),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.channel_attribution_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.channel_attribution_id_seq OWNED BY public.channel_attribution.id;


--
--

CREATE TABLE public.channel_commission (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    channel_code character varying(32) NOT NULL,
    room_type_id integer,
    rate_code character varying(32),
    commission_rate numeric(5,4) NOT NULL,
    settle_cycle character varying(16),
    is_enabled boolean,
    effective_from date,
    effective_to date,
    owner_role character varying(32),
    updated_at timestamp without time zone DEFAULT now(),
    updated_by character varying(32),
    note character varying(255)
);


--
--

CREATE SEQUENCE public.channel_commission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.channel_commission_id_seq OWNED BY public.channel_commission.id;


--
--

CREATE TABLE public.channel_contracts (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    channel_id integer NOT NULL,
    room_type_id integer NOT NULL,
    contract_price numeric(10,2),
    valid_from date,
    valid_to date
);


--
--

CREATE SEQUENCE public.channel_contracts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.channel_contracts_id_seq OWNED BY public.channel_contracts.id;


--
--

CREATE TABLE public.channels (
    id integer NOT NULL,
    code character varying(30) NOT NULL,
    name character varying(80) NOT NULL,
    type character varying(30),
    commission_rate numeric(5,4),
    is_active boolean,
    settle_cycle character varying(16),
    note character varying(255),
    owner_role character varying(32),
    updated_at timestamp without time zone DEFAULT now(),
    updated_by character varying(32)
);


--
--

CREATE SEQUENCE public.channels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.channels_id_seq OWNED BY public.channels.id;


--
--

CREATE TABLE public.competitor_property (
    id integer NOT NULL,
    comp_id character varying(48) NOT NULL,
    set_id character varying(48) NOT NULL,
    hotel_id integer NOT NULL,
    comp_name character varying(128),
    comp_lat numeric(10,6),
    comp_lng numeric(10,6),
    address character varying(255),
    star_rating smallint,
    review_score numeric(3,1),
    distance_km numeric(5,2),
    data_source character varying(32),
    source_ref character varying(64),
    ota_public_url character varying(255),
    is_active boolean
);


--
--

CREATE SEQUENCE public.competitor_property_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.competitor_property_id_seq OWNED BY public.competitor_property.id;


--
--

CREATE TABLE public.competitor_rate_snapshot (
    id integer NOT NULL,
    snapshot_id character varying(64) NOT NULL,
    comp_id character varying(48) NOT NULL,
    hotel_id integer NOT NULL,
    stay_date date NOT NULL,
    room_type_eq character varying(64),
    channel character varying(32),
    observed_price numeric(10,2),
    observed_currency character varying(8),
    rate_plan_code character varying(64),
    captured_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.competitor_rate_snapshot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.competitor_rate_snapshot_id_seq OWNED BY public.competitor_rate_snapshot.id;


--
--

CREATE TABLE public.competitor_room_map (
    id integer NOT NULL,
    map_id character varying(64) NOT NULL,
    comp_id character varying(48) NOT NULL,
    self_room_type_id integer NOT NULL,
    hotel_id integer NOT NULL,
    comp_room_type_raw character varying(64),
    weight numeric(4,3),
    is_active boolean,
    mapped_by character varying(32),
    mapped_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.competitor_room_map_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.competitor_room_map_id_seq OWNED BY public.competitor_room_map.id;


--
--

CREATE TABLE public.competitor_set (
    id integer NOT NULL,
    set_id character varying(48) NOT NULL,
    hotel_id integer NOT NULL,
    set_name character varying(64),
    segment_tag character varying(32),
    default_radius_km numeric(5,2),
    is_active boolean,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.competitor_set_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.competitor_set_id_seq OWNED BY public.competitor_set.id;


--
--

CREATE TABLE public.corp_accounts (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    code character varying(40) NOT NULL,
    name character varying(120) NOT NULL,
    industry character varying(60),
    contact_name character varying(60),
    contact_phone character varying(30),
    settlement_mode character varying(20),
    price_policy character varying(20),
    annual_commit_nights integer,
    used_nights_ytd integer,
    credit_limit numeric(14,2),
    credit_used numeric(14,2),
    settle_cycle character varying(20),
    valid_from date,
    valid_to date,
    status character varying(20),
    note text
);


--
--

CREATE SEQUENCE public.corp_accounts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.corp_accounts_id_seq OWNED BY public.corp_accounts.id;


--
--

CREATE TABLE public.corp_price_ladders (
    id integer NOT NULL,
    corp_id integer NOT NULL,
    room_type_id integer NOT NULL,
    tier_name character varying(60) NOT NULL,
    min_annual_nights integer,
    max_annual_nights integer,
    contract_price numeric(10,2) NOT NULL,
    sort_order smallint,
    seasonal_float boolean
);


--
--

CREATE SEQUENCE public.corp_price_ladders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.corp_price_ladders_id_seq OWNED BY public.corp_price_ladders.id;


--
--

CREATE TABLE public.crm_tasks (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    guest_id integer,
    segment_id integer,
    task_type character varying(30),
    status character varying(20),
    title character varying(200),
    payload_json text,
    created_at timestamp without time zone DEFAULT now(),
    done_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.crm_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.crm_tasks_id_seq OWNED BY public.crm_tasks.id;


--
--

CREATE TABLE public.damage_tickets (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    line character varying(20),
    room_no character varying(20),
    item_name character varying(120),
    asset_category character varying(80),
    severity character varying(20),
    description text,
    photos text,
    ai_suggestion text,
    ai_risk text,
    ai_tags character varying(200),
    fee numeric(12,2),
    status character varying(20),
    note character varying(200),
    created_at timestamp without time zone DEFAULT now(),
    resolved_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.damage_tickets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.damage_tickets_id_seq OWNED BY public.damage_tickets.id;


--
--

CREATE TABLE public.demand_forecast (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    room_type_id integer NOT NULL,
    biz_date date NOT NULL,
    predicted_occ numeric(5,4),
    predicted_adr numeric(10,2),
    model_version character varying(40),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.demand_forecast_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.demand_forecast_id_seq OWNED BY public.demand_forecast.id;


--
--

CREATE TABLE public.deposit_ledger_entries (
    id integer NOT NULL,
    deposit_id character varying(32) NOT NULL,
    event character varying(32) NOT NULL,
    from_status character varying(32),
    to_status character varying(32),
    amount_delta integer,
    operator_id character varying(32),
    channel_ref character varying(64),
    memo character varying(255),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.deposit_ledger_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.deposit_ledger_entries_id_seq OWNED BY public.deposit_ledger_entries.id;


--
--

CREATE TABLE public.deposits (
    deposit_id character varying(32) NOT NULL,
    hotel_id integer NOT NULL,
    order_id integer NOT NULL,
    customer_id character varying(64) NOT NULL,
    guest_id integer,
    room_no character varying(8) NOT NULL,
    form character varying(24) NOT NULL,
    original_amount integer NOT NULL,
    captured_amount integer NOT NULL,
    remaining_refund integer NOT NULL,
    status character varying(32) NOT NULL,
    auth_code character varying(64),
    auth_expire_at timestamp without time zone,
    ar_account_id character varying(32),
    receipt_no character varying(32),
    operator_id character varying(32) NOT NULL,
    idempotency_key character varying(64),
    guest_name character varying(80),
    order_no character varying(40),
    created_at timestamp without time zone DEFAULT now(),
    released_at timestamp without time zone,
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE TABLE public.event_calendar (
    id integer NOT NULL,
    event_id character varying(48) NOT NULL,
    hotel_id integer,
    event_type character varying(32),
    event_name character varying(128),
    start_at timestamp without time zone NOT NULL,
    end_at timestamp without time zone NOT NULL,
    distance_km numeric(5,2),
    intensity character varying(8),
    heat_score numeric(5,2),
    price_uplift_max numeric(5,2),
    source character varying(32),
    source_ref character varying(64),
    venue_address character varying(255),
    venue_lat numeric(10,6),
    venue_lng numeric(10,6),
    note character varying(255),
    is_active boolean
);


--
--

CREATE SEQUENCE public.event_calendar_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.event_calendar_id_seq OWNED BY public.event_calendar.id;


--
--

CREATE TABLE public.finance_acquiring_channels (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    channel_code character varying(40) NOT NULL,
    channel_name character varying(80) NOT NULL,
    rate_pct numeric(8,4),
    rate_cap numeric(10,2),
    settle_label character varying(20),
    min_settle numeric(10,2),
    withdraw_fee_pct numeric(8,4),
    month_fee numeric(14,2),
    month_gmv numeric(14,2),
    enabled boolean,
    status_label character varying(20),
    sort_order smallint,
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.finance_acquiring_channels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.finance_acquiring_channels_id_seq OWNED BY public.finance_acquiring_channels.id;


--
--

CREATE TABLE public.finance_bad_debt_rates (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    bucket character varying(20) NOT NULL,
    bucket_label character varying(40),
    rate_pct numeric(6,2),
    description character varying(120),
    sort_order smallint,
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.finance_bad_debt_rates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.finance_bad_debt_rates_id_seq OWNED BY public.finance_bad_debt_rates.id;


--
--

CREATE TABLE public.finance_credit_customers (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    name character varying(120) NOT NULL,
    customer_type character varying(40),
    grade character varying(4),
    credit_limit numeric(14,2),
    credit_used numeric(14,2),
    term_label character varying(40),
    rated_at date,
    status_label character varying(40),
    enabled boolean,
    sort_order smallint,
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.finance_credit_customers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.finance_credit_customers_id_seq OWNED BY public.finance_credit_customers.id;


--
--

CREATE TABLE public.finance_float_carry (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    amount numeric(14,2) NOT NULL,
    currency character varying(8),
    denom_ratios text,
    effective_date date,
    change_reason text,
    old_amount numeric(14,2),
    status character varying(24),
    applicant_user_id integer,
    finance_approver_user_id integer,
    finance_approved_at timestamp without time zone,
    manager_approver_user_id integer,
    manager_approved_at timestamp without time zone,
    rejected_by_user_id integer,
    rejected_at timestamp without time zone,
    reject_reason text,
    activated_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.finance_float_carry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.finance_float_carry_id_seq OWNED BY public.finance_float_carry.id;


--
--

CREATE TABLE public.finance_param_audits (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    domain character varying(40) NOT NULL,
    action_type character varying(40),
    target character varying(120),
    change_text character varying(255),
    reason text,
    effective_date date,
    actor_names character varying(160),
    status character varying(24),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.finance_param_audits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.finance_param_audits_id_seq OWNED BY public.finance_param_audits.id;


--
--

CREATE TABLE public.finance_payment_terms (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    customer_type character varying(60) NOT NULL,
    term_label character varying(40) NOT NULL,
    description character varying(200),
    effective_date date,
    sort_order smallint,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.finance_payment_terms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.finance_payment_terms_id_seq OWNED BY public.finance_payment_terms.id;


--
--

CREATE TABLE public.finance_report_exports (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    report_code character varying(40) NOT NULL,
    report_name character varying(120),
    format character varying(10) NOT NULL,
    status character varying(20),
    file_name character varying(200),
    file_path character varying(500),
    size_bytes integer,
    row_count integer,
    async_job integer,
    period_start date,
    period_end date,
    generated_at timestamp without time zone,
    generated_by character varying(60),
    expires_at timestamp without time zone,
    snapshot_json text,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.finance_report_exports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.finance_report_exports_id_seq OWNED BY public.finance_report_exports.id;


--
--

CREATE TABLE public.finance_reports (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    period character varying(20),
    metric character varying(40),
    value numeric(14,2),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.finance_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.finance_reports_id_seq OWNED BY public.finance_reports.id;


--
--

CREATE TABLE public.finance_tax_configs (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    version integer,
    taxpayer_type character varying(40),
    main_rate numeric(6,4),
    price_mode character varying(20),
    tax_code character varying(40),
    tax_no character varying(40),
    surcharge_note character varying(120),
    effective_date date,
    status character varying(24),
    change_reason text,
    maintainer_name character varying(80),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.finance_tax_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.finance_tax_configs_id_seq OWNED BY public.finance_tax_configs.id;


--
--

CREATE TABLE public.guest_aliases (
    id integer NOT NULL,
    guest_id integer NOT NULL,
    alias_name character varying(80) NOT NULL,
    source character varying(40),
    merged_from_guest_id integer,
    note character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.guest_aliases_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.guest_aliases_id_seq OWNED BY public.guest_aliases.id;


--
--

CREATE TABLE public.guest_coupons (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    guest_id integer NOT NULL,
    grant_id integer,
    code character varying(40) NOT NULL,
    name character varying(120) NOT NULL,
    recipient_name character varying(80),
    channel character varying(40),
    coupon_type character varying(40),
    discount_rate numeric(4,3) NOT NULL,
    source character varying(40),
    status character varying(20),
    redeem_status character varying(20),
    valid_from timestamp without time zone,
    valid_until timestamp without time zone,
    note text,
    created_at timestamp without time zone DEFAULT now(),
    used_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.guest_coupons_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.guest_coupons_id_seq OWNED BY public.guest_coupons.id;


--
--

CREATE TABLE public.guest_identities (
    id integer NOT NULL,
    guest_id integer NOT NULL,
    source character varying(30) NOT NULL,
    external_id character varying(120),
    confidence numeric(3,2),
    linked_at timestamp without time zone DEFAULT now(),
    is_primary boolean,
    merge_method character varying(30),
    matched_by character varying(60)
);


--
--

CREATE SEQUENCE public.guest_identities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.guest_identities_id_seq OWNED BY public.guest_identities.id;


--
--

CREATE TABLE public.guest_tags (
    id integer NOT NULL,
    guest_id integer NOT NULL,
    tag_id integer NOT NULL,
    confidence numeric(3,2),
    source character varying(30),
    assigned_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.guest_tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.guest_tags_id_seq OWNED BY public.guest_tags.id;


--
--

CREATE TABLE public.guests (
    id integer NOT NULL,
    one_id character varying(40) NOT NULL,
    name character varying(80) NOT NULL,
    phone character varying(20),
    phone_cipher text,
    phone_mask character varying(20),
    phone_hash character varying(64),
    gender character varying(10),
    birthday date,
    vip_level character varying(20),
    city character varying(60),
    ltv numeric(12,2),
    churn_risk numeric(3,2),
    merged_into_guest_id integer,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.guests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.guests_id_seq OWNED BY public.guests.id;


--
--

CREATE TABLE public.hotel_channel_bindings (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    channel character varying(30) NOT NULL,
    label character varying(120),
    xhs_ad_account_id character varying(80),
    xhs_professional_id character varying(80),
    xhs_page_ids character varying(255),
    binding_token character varying(64) NOT NULL,
    webhook_secret character varying(128),
    status character varying(20),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.hotel_channel_bindings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.hotel_channel_bindings_id_seq OWNED BY public.hotel_channel_bindings.id;


--
--

CREATE TABLE public.hotel_mkt_settings (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    default_receiver_userid character varying(80),
    welcome_text text,
    welcome_landing_page_id integer,
    member_landing_page_id integer,
    returning_landing_page_id integer,
    points_json text,
    level_rule_json text,
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.hotel_mkt_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.hotel_mkt_settings_id_seq OWNED BY public.hotel_mkt_settings.id;


--
--

CREATE TABLE public.hotels (
    id integer NOT NULL,
    code character varying(40) NOT NULL,
    name character varying(120) NOT NULL,
    city character varying(60),
    address character varying(255),
    timezone character varying(40),
    currency character varying(3),
    star_rating smallint,
    is_active boolean,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.hotels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.hotels_id_seq OWNED BY public.hotels.id;


--
--

CREATE TABLE public.housekeeping_tasks (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    room_id integer,
    task_type character varying(30),
    assignee_id integer,
    priority smallint,
    status character varying(20),
    due_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    done_at timestamp without time zone,
    inspect_by integer,
    inspect_at timestamp without time zone,
    fail_reason character varying(200),
    fail_count smallint
);


--
--

CREATE SEQUENCE public.housekeeping_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.housekeeping_tasks_id_seq OWNED BY public.housekeeping_tasks.id;


--
--

CREATE TABLE public.insight_diagnosis_results (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_range character varying(64) NOT NULL,
    compare_baseline character varying(20),
    dimension character varying(40) NOT NULL,
    severity character varying(8),
    evidence_json text,
    revenue_impact character varying(80),
    suggested_action character varying(240),
    confidence character varying(8),
    snapshot_hash character varying(64),
    created_by character varying(40),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.insight_diagnosis_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.insight_diagnosis_results_id_seq OWNED BY public.insight_diagnosis_results.id;


--
--

CREATE TABLE public.inventory_allocation (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    room_type_id integer NOT NULL,
    channel_id integer NOT NULL,
    biz_date date NOT NULL,
    allotment integer,
    sold integer
);


--
--

CREATE SEQUENCE public.inventory_allocation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.inventory_allocation_id_seq OWNED BY public.inventory_allocation.id;


--
--

CREATE TABLE public.invoices (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    order_id integer,
    invoice_no character varying(40),
    amount numeric(12,2),
    tax numeric(12,2),
    status character varying(20),
    issued_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.invoices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.invoices_id_seq OWNED BY public.invoices.id;


--
--

CREATE TABLE public.ledger_entries (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_date date NOT NULL,
    account character varying(40),
    debit numeric(12,2),
    credit numeric(12,2),
    currency character varying(3),
    ref_type character varying(30),
    ref_id integer,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.ledger_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.ledger_entries_id_seq OWNED BY public.ledger_entries.id;


--
--

CREATE TABLE public.linen (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    room_id integer,
    item_type character varying(40),
    status character varying(20),
    wash_count integer,
    lifecycle_stage character varying(20),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.linen_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.linen_id_seq OWNED BY public.linen.id;


--
--

CREATE TABLE public.linen_snapshots (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_date date NOT NULL,
    item_type character varying(40) NOT NULL,
    in_room integer,
    pending_wash integer,
    in_wash integer,
    in_storage integer,
    discarded integer
);


--
--

CREATE SEQUENCE public.linen_snapshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.linen_snapshots_id_seq OWNED BY public.linen_snapshots.id;


--
--

CREATE TABLE public.mkt_automations (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    name character varying(64) NOT NULL,
    trigger_type character varying(32) NOT NULL,
    trigger_json text,
    action_type character varying(32),
    action_json text,
    frequency_cap_days integer,
    is_enabled boolean,
    last_run_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.mkt_automations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_automations_id_seq OWNED BY public.mkt_automations.id;


--
--

CREATE TABLE public.mkt_campaigns (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    name character varying(128) NOT NULL,
    type character varying(32),
    status character varying(16),
    start_at timestamp without time zone,
    end_at timestamp without time zone,
    template_id character varying(48),
    config_json text,
    created_by character varying(32),
    approved_by character varying(32),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.mkt_campaigns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_campaigns_id_seq OWNED BY public.mkt_campaigns.id;


--
--

CREATE TABLE public.mkt_coupon_auto_rule (
    id integer NOT NULL,
    property_id integer NOT NULL,
    name character varying(128) NOT NULL,
    description character varying(255),
    event_type character varying(24) NOT NULL,
    event_params text,
    scan_frequency character varying(16),
    max_per_customer_day integer,
    rule_cooldown_days integer,
    global_silence_days integer,
    active_window_start character varying(8),
    active_window_end character varying(8),
    push_channel character varying(32),
    status character varying(16),
    effective_from timestamp without time zone,
    effective_to timestamp without time zone,
    last_triggered_at timestamp without time zone,
    trigger_count_7d integer,
    created_at timestamp without time zone DEFAULT now(),
    created_by character varying(32),
    updated_at timestamp without time zone DEFAULT now(),
    updated_by character varying(32)
);


--
--

CREATE TABLE public.mkt_coupon_auto_rule_coupon (
    id integer NOT NULL,
    rule_id integer NOT NULL,
    batch_id integer NOT NULL,
    priority integer
);


--
--

CREATE SEQUENCE public.mkt_coupon_auto_rule_coupon_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_coupon_auto_rule_coupon_id_seq OWNED BY public.mkt_coupon_auto_rule_coupon.id;


--
--

CREATE TABLE public.mkt_coupon_auto_rule_filter (
    id integer NOT NULL,
    rule_id integer NOT NULL,
    group_id integer NOT NULL,
    field character varying(64) NOT NULL,
    op character varying(16) NOT NULL,
    value_json text,
    sort_order integer
);


--
--

CREATE SEQUENCE public.mkt_coupon_auto_rule_filter_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_coupon_auto_rule_filter_id_seq OWNED BY public.mkt_coupon_auto_rule_filter.id;


--
--

CREATE SEQUENCE public.mkt_coupon_auto_rule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_coupon_auto_rule_id_seq OWNED BY public.mkt_coupon_auto_rule.id;


--
--

CREATE TABLE public.mkt_coupon_auto_rule_trigger (
    id integer NOT NULL,
    rule_id integer NOT NULL,
    property_id integer NOT NULL,
    customer_id integer NOT NULL,
    batch_id integer,
    instance_id integer,
    matched integer,
    reason character varying(255),
    triggered_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.mkt_coupon_auto_rule_trigger_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_coupon_auto_rule_trigger_id_seq OWNED BY public.mkt_coupon_auto_rule_trigger.id;


--
--

CREATE TABLE public.mkt_coupon_grant_logs (
    id integer NOT NULL,
    trigger_id integer,
    auto_rule_id integer,
    batch_id integer NOT NULL,
    customer_id integer NOT NULL,
    instance_id integer NOT NULL,
    grant_event character varying(32),
    granted_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.mkt_coupon_grant_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_coupon_grant_logs_id_seq OWNED BY public.mkt_coupon_grant_logs.id;


--
--

CREATE TABLE public.mkt_coupon_grants (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    coupon_id integer NOT NULL,
    guest_id integer NOT NULL,
    code character varying(48) NOT NULL,
    coupon_type character varying(16),
    face_text character varying(128),
    valid_from timestamp without time zone,
    valid_to timestamp without time zone,
    grant_event character varying(32),
    grant_channel character varying(32),
    grant_at timestamp without time zone DEFAULT now(),
    claim_at timestamp without time zone,
    used_at timestamp without time zone,
    used_order_id integer,
    used_amount numeric(10,2),
    redeemed_by character varying(32),
    status character varying(16)
);


--
--

CREATE SEQUENCE public.mkt_coupon_grants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_coupon_grants_id_seq OWNED BY public.mkt_coupon_grants.id;


--
--

CREATE TABLE public.mkt_coupon_redeems (
    id integer NOT NULL,
    instance_id integer NOT NULL,
    property_id integer NOT NULL,
    order_id integer,
    amount_saved numeric(10,2),
    cashier character varying(32),
    redeemed_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.mkt_coupon_redeems_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_coupon_redeems_id_seq OWNED BY public.mkt_coupon_redeems.id;


--
--

CREATE TABLE public.mkt_coupon_triggers (
    id integer NOT NULL,
    property_id integer NOT NULL,
    batch_id integer NOT NULL,
    name character varying(128),
    event_type character varying(24) NOT NULL,
    event_params text,
    is_enabled integer,
    last_run_at timestamp without time zone,
    granted_total integer,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.mkt_coupon_triggers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_coupon_triggers_id_seq OWNED BY public.mkt_coupon_triggers.id;


--
--

CREATE TABLE public.mkt_coupons (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    batch_no character varying(40) NOT NULL,
    name character varying(128) NOT NULL,
    type character varying(16) NOT NULL,
    coupon_type character varying(16),
    face_value numeric(10,2),
    reduce_amount numeric(10,2),
    threshold numeric(10,2),
    discount_rate numeric(5,3),
    max_discount numeric(10,2),
    benefit_key character varying(32),
    benefit_value character varying(64),
    face_text character varying(128),
    scope_type character varying(16),
    scope_rooms text,
    total_qty integer,
    granted_qty integer,
    per_user_qty integer,
    validity_mode character varying(8),
    validity_days integer,
    batch_valid_from timestamp without time zone,
    batch_valid_to timestamp without time zone,
    valid_from timestamp without time zone,
    valid_to timestamp without time zone,
    scope_json text,
    status character varying(16),
    created_by character varying(32),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.mkt_coupons_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_coupons_id_seq OWNED BY public.mkt_coupons.id;


--
--

CREATE TABLE public.mkt_customer_notes (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    guest_id integer NOT NULL,
    note text NOT NULL,
    tag character varying(32),
    created_by character varying(32),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.mkt_customer_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_customer_notes_id_seq OWNED BY public.mkt_customer_notes.id;


--
--

CREATE TABLE public.mkt_guest_wallets (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    guest_id integer NOT NULL,
    level_code character varying(16),
    points_balance integer,
    stored_balance numeric(12,2),
    nights_ytd integer,
    spend_ytd numeric(12,2),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.mkt_guest_wallets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_guest_wallets_id_seq OWNED BY public.mkt_guest_wallets.id;


--
--

CREATE TABLE public.mkt_member_levels (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    level_code character varying(16) NOT NULL,
    level_name character varying(32) NOT NULL,
    upgrade_type character varying(16),
    upgrade_value integer,
    retention_type character varying(16),
    retention_value integer,
    color_hex character varying(8),
    upgrade_points integer,
    retain_points integer,
    valid_months integer,
    growth_rule_json text,
    benefits_json text,
    sort_order integer,
    is_active boolean
);


--
--

CREATE SEQUENCE public.mkt_member_levels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_member_levels_id_seq OWNED BY public.mkt_member_levels.id;


--
--

CREATE TABLE public.mkt_stored_value_plans (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    tier_name character varying(64),
    recharge_amt numeric(10,2) NOT NULL,
    bonus_amt numeric(10,2),
    bonus_type character varying(16),
    gift_points integer,
    first_time_only boolean,
    payment_methods_json text,
    is_active boolean,
    sort_order integer
);


--
--

CREATE SEQUENCE public.mkt_stored_value_plans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.mkt_stored_value_plans_id_seq OWNED BY public.mkt_stored_value_plans.id;


--
--

CREATE TABLE public.night_audit_exceptions (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    audit_log_id integer,
    biz_date date NOT NULL,
    code character varying(40),
    title character varying(120),
    detail text,
    severity character varying(20),
    status character varying(20),
    fixed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.night_audit_exceptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.night_audit_exceptions_id_seq OWNED BY public.night_audit_exceptions.id;


--
--

CREATE TABLE public.night_audit_logs (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_date date NOT NULL,
    status character varying(20),
    exceptions integer,
    revenue numeric(12,2),
    room_nights integer,
    ran_at timestamp without time zone,
    operator_id integer
);


--
--

CREATE SEQUENCE public.night_audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.night_audit_logs_id_seq OWNED BY public.night_audit_logs.id;


--
--

CREATE TABLE public.oneid_merge_events (
    id integer NOT NULL,
    guest_id integer NOT NULL,
    action character varying(30) NOT NULL,
    source character varying(30),
    external_id character varying(120),
    confidence numeric(3,2),
    merge_method character varying(30),
    operator character varying(60),
    note text,
    occurred_at timestamp without time zone NOT NULL
);


--
--

CREATE SEQUENCE public.oneid_merge_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.oneid_merge_events_id_seq OWNED BY public.oneid_merge_events.id;


--
--

CREATE TABLE public.oneid_phone_conflicts (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    status character varying(20),
    phone_submitted character varying(30) NOT NULL,
    phone_last4 character varying(6) NOT NULL,
    match_type character varying(40),
    external_userid character varying(120) NOT NULL,
    nickname character varying(80),
    follow_userid character varying(80),
    bind_ticket_id integer,
    candidate_guest_ids_json text NOT NULL,
    resolved_guest_id integer,
    resolved_by character varying(60),
    note text,
    created_at timestamp without time zone DEFAULT now(),
    resolved_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.oneid_phone_conflicts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.oneid_phone_conflicts_id_seq OWNED BY public.oneid_phone_conflicts.id;


--
--

CREATE TABLE public.order_items (
    id integer NOT NULL,
    order_id integer NOT NULL,
    item_type character varying(30),
    description character varying(120),
    qty numeric(8,2),
    unit_price numeric(10,2),
    amount numeric(12,2)
);


--
--

CREATE SEQUENCE public.order_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.order_items_id_seq OWNED BY public.order_items.id;


--
--

CREATE TABLE public.orders (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    order_no character varying(40) NOT NULL,
    guest_id integer,
    channel_id integer,
    room_type_id integer,
    order_type smallint,
    agreement_id integer,
    rate_strategy character varying(20),
    one_id character varying(64),
    guest_phone character varying(20),
    deposit_amount numeric(12,2),
    allow_on_account boolean,
    credit_occupy numeric(12,2),
    longstay_cycle character varying(20),
    monthly_rent numeric(12,2),
    longstay_start date,
    longstay_end date,
    skip_daily_room_charge boolean,
    check_in date NOT NULL,
    check_out date NOT NULL,
    nights smallint,
    rooms smallint,
    adults smallint,
    children smallint,
    total_amount numeric(12,2),
    status character varying(20) NOT NULL,
    payment_status character varying(20),
    arrival_time character varying(5),
    created_by integer,
    note text,
    external_order_no character varying(80),
    voucher_code character varying(80),
    channel_prepaid boolean,
    group_name character varying(120),
    group_type character varying(40),
    settle_mode character varying(40),
    settle_party character varying(120),
    sales_name character varying(80),
    other_amount numeric(12,2),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
--

CREATE TABLE public.ota_settlements (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    channel_id integer,
    platform character varying(40) NOT NULL,
    period character varying(7) NOT NULL,
    gross_amount numeric(14,2),
    commission_amount numeric(14,2),
    net_amount numeric(14,2),
    paid_net numeric(14,2),
    recon_batch_id integer,
    status character varying(20),
    due_date date,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.ota_settlements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.ota_settlements_id_seq OWNED BY public.ota_settlements.id;


--
--

CREATE TABLE public.pace_snapshot (
    id integer NOT NULL,
    pace_id character varying(64) NOT NULL,
    hotel_id integer NOT NULL,
    room_type_id integer,
    stay_date date NOT NULL,
    booked integer,
    expected integer,
    pace_ratio numeric(5,2),
    captured_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pace_snapshot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pace_snapshot_id_seq OWNED BY public.pace_snapshot.id;


--
--

CREATE TABLE public.parity_alert (
    id integer NOT NULL,
    alert_id character varying(48) NOT NULL,
    hotel_id integer NOT NULL,
    channel_a character varying(32) NOT NULL,
    channel_b character varying(32) NOT NULL,
    room_type_id integer,
    stay_date date NOT NULL,
    price_a numeric(10,2),
    price_b numeric(10,2),
    delta_pct numeric(5,2),
    duration_hours integer,
    severity character varying(8),
    status character varying(16),
    alert_type character varying(32),
    title character varying(255),
    detail text,
    suggested_action text,
    detected_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.parity_alert_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.parity_alert_id_seq OWNED BY public.parity_alert.id;


--
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    order_id integer,
    folio_id integer,
    method character varying(30),
    amount numeric(12,2),
    received_amount numeric(12,2),
    pos_slip_no character varying(60),
    settle_type character varying(20),
    operator_id integer,
    paid_at timestamp without time zone DEFAULT now(),
    note text
);


--
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
--

CREATE TABLE public.permissions (
    id integer NOT NULL,
    code character varying(80) NOT NULL,
    name character varying(120) NOT NULL,
    kind character varying(20) NOT NULL,
    module character varying(40) NOT NULL,
    sort_order integer
);


--
--

CREATE SEQUENCE public.permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;


--
--

CREATE TABLE public.pms_ar_entries (
    id integer NOT NULL,
    ar_ledger_id integer NOT NULL,
    entry_type character varying(20) NOT NULL,
    order_id integer,
    folio_id integer,
    amount numeric(12,2) NOT NULL,
    ref_no character varying(80),
    note text,
    operator_id integer,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pms_ar_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pms_ar_entries_id_seq OWNED BY public.pms_ar_entries.id;


--
--

CREATE TABLE public.pms_ar_ledgers (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    corp_id integer NOT NULL,
    charged_total numeric(14,2),
    settled_total numeric(14,2),
    balance numeric(14,2),
    credit_limit numeric(14,2),
    credit_used numeric(14,2),
    settle_cycle character varying(20),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pms_ar_ledgers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pms_ar_ledgers_id_seq OWNED BY public.pms_ar_ledgers.id;


--
--

CREATE TABLE public.pms_checkins (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    order_id integer NOT NULL,
    reservation_id integer,
    room_id integer,
    guest_id integer,
    guest_name character varying(80),
    status character varying(20),
    actual_checkin_at timestamp without time zone,
    actual_checkout_at timestamp without time zone,
    id_doc_type character varying(20),
    id_doc_cipher text,
    id_doc_mask character varying(40),
    id_doc_hash character varying(64),
    id_doc_no character varying(40),
    face_registered boolean,
    floor smallint,
    room_no character varying(20),
    master_checkin_id integer,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pms_checkins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pms_checkins_id_seq OWNED BY public.pms_checkins.id;


--
--

CREATE TABLE public.pms_folio_entries (
    id integer NOT NULL,
    folio_id integer NOT NULL,
    entry_type character varying(30) NOT NULL,
    biz_date date,
    description character varying(160),
    amount numeric(12,2) NOT NULL,
    qty numeric(8,2),
    unit_price numeric(10,2),
    source character varying(30),
    operator_id integer,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pms_folio_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pms_folio_entries_id_seq OWNED BY public.pms_folio_entries.id;


--
--

CREATE TABLE public.pms_folios (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    folio_no character varying(40) NOT NULL,
    order_id integer NOT NULL,
    checkin_id integer,
    guest_id integer,
    status character varying(20),
    balance numeric(12,2),
    charge_total numeric(12,2),
    payment_total numeric(12,2),
    opened_at timestamp without time zone DEFAULT now(),
    closed_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.pms_folios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pms_folios_id_seq OWNED BY public.pms_folios.id;


--
--

CREATE TABLE public.pms_group_room_blocks (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    order_id integer NOT NULL,
    room_type_id integer,
    qty smallint,
    unit_price numeric(10,2),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pms_group_room_blocks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pms_group_room_blocks_id_seq OWNED BY public.pms_group_room_blocks.id;


--
--

CREATE TABLE public.pms_group_room_lines (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    order_id integer NOT NULL,
    line_no smallint,
    room_type_id integer,
    guest_name character varying(80),
    guest_phone character varying(30),
    id_last4 character varying(8),
    room_id integer,
    checkin_id integer,
    stay_check_in date,
    stay_check_out date,
    status character varying(20),
    note character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pms_group_room_lines_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pms_group_room_lines_id_seq OWNED BY public.pms_group_room_lines.id;


--
--

CREATE TABLE public.pms_id_doc_audits (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    checkin_id integer,
    order_id integer,
    operator_id integer,
    action character varying(40),
    reason character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pms_id_doc_audits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pms_id_doc_audits_id_seq OWNED BY public.pms_id_doc_audits.id;


--
--

CREATE TABLE public.pms_room_assignments (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    order_id integer NOT NULL,
    checkin_id integer,
    from_room_id integer,
    to_room_id integer,
    assign_type character varying(20) NOT NULL,
    operator_id integer,
    reason character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pms_room_assignments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pms_room_assignments_id_seq OWNED BY public.pms_room_assignments.id;


--
--

CREATE TABLE public.price_suggestions (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    room_type_id integer NOT NULL,
    biz_date date NOT NULL,
    current_price numeric(10,2),
    suggested_price numeric(10,2),
    confidence character varying(10),
    status character varying(20),
    guardrail_msg character varying(200),
    model_version character varying(40),
    created_at timestamp without time zone DEFAULT now(),
    decided_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.price_suggestions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.price_suggestions_id_seq OWNED BY public.price_suggestions.id;


--
--

CREATE TABLE public.pricing_assistant_config (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    execution_mode character varying(16),
    delegated_enabled boolean,
    commission_json text,
    comp_compare_enabled boolean,
    params_json text,
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pricing_assistant_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pricing_assistant_config_id_seq OWNED BY public.pricing_assistant_config.id;


--
--

CREATE TABLE public.pricing_decision (
    id integer NOT NULL,
    decision_id character varying(48) NOT NULL,
    reco_id character varying(48) NOT NULL,
    hotel_id integer NOT NULL,
    decision character varying(16) NOT NULL,
    decided_by character varying(32),
    decided_at timestamp without time zone,
    before_price numeric(10,2),
    after_price numeric(10,2),
    reason_note character varying(255),
    audit_id character varying(48)
);


--
--

CREATE SEQUENCE public.pricing_decision_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pricing_decision_id_seq OWNED BY public.pricing_decision.id;


--
--

CREATE TABLE public.pricing_effect (
    id integer NOT NULL,
    effect_id character varying(48) NOT NULL,
    decision_id character varying(48) NOT NULL,
    reco_id character varying(48) NOT NULL,
    hotel_id integer NOT NULL,
    stay_date date NOT NULL,
    metric character varying(32),
    baseline_value numeric(10,2),
    actual_value numeric(10,2),
    delta_pct numeric(5,2),
    recorded_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.pricing_effect_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pricing_effect_id_seq OWNED BY public.pricing_effect.id;


--
--

CREATE TABLE public.pricing_recommendation (
    id integer NOT NULL,
    reco_id character varying(48) NOT NULL,
    hotel_id integer NOT NULL,
    room_type_id integer NOT NULL,
    channel character varying(32) NOT NULL,
    stay_date date NOT NULL,
    current_price numeric(10,2),
    suggested_price numeric(10,2) NOT NULL,
    suggested_base numeric(10,2) NOT NULL,
    est_n numeric(10,2),
    est_occ_pct numeric(5,2),
    est_revpar_delta numeric(10,2),
    confidence character varying(8),
    top_reasons text,
    features_snapshot text,
    explain_json text,
    execution_mode character varying(16),
    status character varying(16),
    snapshot_hash character varying(64),
    created_at timestamp without time zone DEFAULT now(),
    expires_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.pricing_recommendation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.pricing_recommendation_id_seq OWNED BY public.pricing_recommendation.id;


--
--

CREATE TABLE public.profit_insights (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_date date NOT NULL,
    title character varying(120),
    recommendation text,
    impact_amount numeric(12,2),
    category character varying(40),
    status character varying(20),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.profit_insights_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.profit_insights_id_seq OWNED BY public.profit_insights.id;


--
--

CREATE TABLE public.rate_strategies (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    name character varying(80),
    min_floor_price numeric(10,2),
    max_ceiling_price numeric(10,2),
    auto_cruise boolean,
    effective_from date,
    effective_to date,
    is_active boolean
);


--
--

CREATE SEQUENCE public.rate_strategies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.rate_strategies_id_seq OWNED BY public.rate_strategies.id;


--
--

CREATE TABLE public.recon_batches (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_date date NOT NULL,
    channel character varying(40),
    status character varying(20),
    pms_total numeric(14,2),
    channel_total numeric(14,2),
    variance numeric(14,2),
    note character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.recon_batches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.recon_batches_id_seq OWNED BY public.recon_batches.id;


--
--

CREATE TABLE public.recon_items (
    id integer NOT NULL,
    batch_id integer NOT NULL,
    hotel_id integer NOT NULL,
    side character varying(20),
    ref_no character varying(60),
    amount numeric(12,2),
    match_status character varying(20),
    note character varying(200),
    order_id integer
);


--
--

CREATE SEQUENCE public.recon_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.recon_items_id_seq OWNED BY public.recon_items.id;


--
--

CREATE TABLE public.refund_adjust_audits (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    ticket_id integer,
    event character varying(40) NOT NULL,
    actor_id character varying(40),
    memo character varying(255),
    before_json text,
    after_json text,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.refund_adjust_audits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.refund_adjust_audits_id_seq OWNED BY public.refund_adjust_audits.id;


--
--

CREATE TABLE public.refund_adjust_configs (
    hotel_id integer NOT NULL,
    refund_threshold_yuan integer NOT NULL,
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE TABLE public.refund_adjust_tickets (
    id integer NOT NULL,
    ticket_no character varying(40) NOT NULL,
    hotel_id integer NOT NULL,
    op_type character varying(20) NOT NULL,
    status character varying(32) NOT NULL,
    title character varying(120) NOT NULL,
    detail character varying(255),
    order_id integer,
    order_no character varying(40),
    guest_name_masked character varying(40),
    amount_cents integer,
    reason character varying(200),
    refund_method character varying(40),
    applicant_id character varying(40),
    auth_mgr_done integer,
    auth_fin_done integer,
    auth_mgr_by character varying(40),
    auth_fin_by character varying(40),
    payload_json text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.refund_adjust_tickets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.refund_adjust_tickets_id_seq OWNED BY public.refund_adjust_tickets.id;


--
--

CREATE TABLE public.reservations (
    id integer NOT NULL,
    order_id integer NOT NULL,
    room_id integer,
    assigned_by integer,
    assigned_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.reservations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.reservations_id_seq OWNED BY public.reservations.id;


--
--

CREATE TABLE public.restock_items (
    id integer NOT NULL,
    order_id integer NOT NULL,
    hotel_id integer NOT NULL,
    supply_id integer,
    name character varying(120),
    qty numeric(10,2),
    unit_cost numeric(10,2),
    amount numeric(12,2),
    urgency character varying(20)
);


--
--

CREATE SEQUENCE public.restock_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.restock_items_id_seq OWNED BY public.restock_items.id;


--
--

CREATE TABLE public.restock_orders (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    order_no character varying(40),
    vendor character varying(80),
    status character varying(20),
    total_amount numeric(12,2),
    note character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.restock_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.restock_orders_id_seq OWNED BY public.restock_orders.id;


--
--

CREATE TABLE public.revenue_anomalies (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    code character varying(40),
    category character varying(20),
    title character varying(120),
    subtitle character varying(200),
    score integer,
    tone character varying(10),
    description text,
    detail_title character varying(80),
    actor character varying(80),
    room_label character varying(80),
    event_time character varying(40),
    orig_amount numeric(12,2),
    new_amount numeric(12,2),
    diff_label character varying(40),
    timeline_json text,
    ai_hint text,
    status character varying(20),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.revenue_anomalies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.revenue_anomalies_id_seq OWNED BY public.revenue_anomalies.id;


--
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    guest_id integer,
    channel_id integer,
    rating numeric(2,1),
    content text,
    replied boolean,
    reply_content text,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
--

CREATE TABLE public.risk_alerts (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    alert_type character varying(40),
    level character varying(20),
    message text,
    status character varying(20),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.risk_alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.risk_alerts_id_seq OWNED BY public.risk_alerts.id;


--
--

CREATE TABLE public.role_permissions (
    role_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    code character varying(40) NOT NULL,
    name character varying(60) NOT NULL,
    description character varying(255),
    is_system boolean
);


--
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
--

CREATE TABLE public.room_inspections (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    room_id integer,
    room_no character varying(20),
    inspector character varying(80),
    status character varying(20),
    score integer,
    summary character varying(255),
    findings_json text,
    inspected_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.room_inspections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.room_inspections_id_seq OWNED BY public.room_inspections.id;


--
--

CREATE TABLE public.room_iot_metrics (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    floor character varying(20),
    recorded_at timestamp without time zone NOT NULL,
    energy_kw numeric(10,2),
    temp_c numeric(6,1),
    humidity_pct numeric(6,1)
);


--
--

CREATE SEQUENCE public.room_iot_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.room_iot_metrics_id_seq OWNED BY public.room_iot_metrics.id;


--
--

CREATE TABLE public.room_night_inventory (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    room_id integer NOT NULL,
    biz_date date NOT NULL,
    status character varying(20) NOT NULL,
    order_id integer,
    guest_name character varying(80),
    order_no character varying(40),
    check_in date,
    check_out date,
    source character varying(30),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.room_night_inventory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.room_night_inventory_id_seq OWNED BY public.room_night_inventory.id;


--
--

CREATE TABLE public.room_status_log (
    id integer NOT NULL,
    room_id integer NOT NULL,
    from_status character varying(20),
    to_status character varying(20),
    operator_id integer,
    reason character varying(120),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.room_status_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.room_status_log_id_seq OWNED BY public.room_status_log.id;


--
--

CREATE TABLE public.room_type_base_rate (
    id integer NOT NULL,
    room_type_id integer NOT NULL,
    hotel_id integer NOT NULL,
    base_rate numeric(10,2) NOT NULL,
    bar_upper numeric(10,2) NOT NULL,
    bar_lower numeric(10,2) NOT NULL,
    n_floor numeric(10,2) NOT NULL,
    seasonal_modifier text,
    effective_from date,
    effective_to date,
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.room_type_base_rate_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.room_type_base_rate_id_seq OWNED BY public.room_type_base_rate.id;


--
--

CREATE TABLE public.room_types (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    code character varying(40) NOT NULL,
    name character varying(80) NOT NULL,
    bed_type character varying(30),
    capacity smallint,
    area integer,
    amenities text,
    base_price numeric(10,2) NOT NULL,
    breakfast_included boolean,
    is_active boolean,
    description text,
    image_url character varying(500),
    has_window boolean,
    orientation character varying(40)
);


--
--

CREATE SEQUENCE public.room_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.room_types_id_seq OWNED BY public.room_types.id;


--
--

CREATE TABLE public.rooms (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    room_type_id integer,
    room_no character varying(20) NOT NULL,
    building character varying(20),
    floor smallint,
    status character varying(20) NOT NULL,
    status_note character varying(200),
    status_until date,
    smoking boolean,
    features character varying(200),
    lock_id character varying(60),
    physical_status character varying(20)
);


--
--

CREATE SEQUENCE public.rooms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.rooms_id_seq OWNED BY public.rooms.id;


--
--

CREATE TABLE public.segment_members (
    id integer NOT NULL,
    segment_id integer NOT NULL,
    guest_id integer NOT NULL
);


--
--

CREATE SEQUENCE public.segment_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.segment_members_id_seq OWNED BY public.segment_members.id;


--
--

CREATE TABLE public.segments (
    id integer NOT NULL,
    hotel_id integer,
    name character varying(80) NOT NULL,
    filter_rule text,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.segments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.segments_id_seq OWNED BY public.segments.id;


--
--

CREATE TABLE public.service_requests (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    order_id integer,
    guest_id integer,
    room_id integer,
    content character varying(255),
    priority smallint,
    status character varying(20),
    assignee_id integer,
    created_at timestamp without time zone DEFAULT now(),
    resolved_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.service_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.service_requests_id_seq OWNED BY public.service_requests.id;


--
--

CREATE TABLE public.shift_asset_counts (
    id integer NOT NULL,
    handover_id integer NOT NULL,
    asset_type character varying(40) NOT NULL,
    asset_name character varying(80) NOT NULL,
    hint character varying(120),
    expected_qty integer,
    actual_qty integer,
    received_qty integer,
    received_ack boolean,
    diff_reason text,
    supply_id integer,
    reorder_triggered boolean
);


--
--

CREATE SEQUENCE public.shift_asset_counts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.shift_asset_counts_id_seq OWNED BY public.shift_asset_counts.id;


--
--

CREATE TABLE public.shift_audit_logs (
    id integer NOT NULL,
    handover_id integer NOT NULL,
    hotel_id integer NOT NULL,
    action character varying(40) NOT NULL,
    actor_user_id integer,
    actor_name character varying(80),
    payload text,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.shift_audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.shift_audit_logs_id_seq OWNED BY public.shift_audit_logs.id;


--
--

CREATE TABLE public.shift_float_counts (
    id integer NOT NULL,
    handover_id integer NOT NULL,
    denom numeric(8,2) NOT NULL,
    label character varying(20),
    expected_qty integer,
    actual_qty integer,
    received_qty integer,
    subtotal numeric(14,2)
);


--
--

CREATE SEQUENCE public.shift_float_counts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.shift_float_counts_id_seq OWNED BY public.shift_float_counts.id;


--
--

CREATE TABLE public.shift_handover_tasks (
    id integer NOT NULL,
    handover_id integer NOT NULL,
    hotel_id integer NOT NULL,
    priority character varying(4),
    content text NOT NULL,
    owner_name character varying(80),
    owner_user_id integer,
    due_at timestamp without time zone,
    status character varying(20),
    linked_order_id integer,
    source_shift_no smallint,
    is_carryover boolean,
    task_type character varying(20),
    created_by character varying(40),
    approved_by integer,
    ai_session_id character varying(64),
    source character varying(40),
    escalated_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.shift_handover_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.shift_handover_tasks_id_seq OWNED BY public.shift_handover_tasks.id;


--
--

CREATE TABLE public.shift_handovers (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    shift_no smallint NOT NULL,
    shift_date date NOT NULL,
    start_at timestamp without time zone,
    end_at timestamp without time zone,
    scheduled_handover_at timestamp without time zone,
    outgoing_user_id integer,
    incoming_user_id integer,
    manager_user_id integer,
    status character varying(30),
    total_revenue numeric(14,2),
    float_expected numeric(14,2),
    float_actual numeric(14,2),
    float_diff numeric(14,2),
    diff_type character varying(10),
    diff_reason text,
    float_confirmed boolean,
    assets_confirmed boolean,
    deposit_collected numeric(14,2),
    deposit_refunded numeric(14,2),
    deposit_net numeric(14,2),
    deposit_collected_count smallint,
    deposit_refunded_count smallint,
    incoming_ack_money boolean,
    incoming_ack_assets boolean,
    incoming_ack_tasks boolean,
    received_revenue_ok boolean,
    deposit_ack boolean,
    float_received_confirmed boolean,
    assets_received_confirmed boolean,
    matters_confirmed boolean,
    received_float_actual numeric(14,2),
    received_float_match_outgoing boolean,
    guest_situation_acks text,
    task_claims text,
    carryover_acks text,
    narrative text,
    ai_draft_json text,
    ai_approved_json text,
    guest_situations_snapshot text,
    ai_session_id character varying(64),
    ai_draft_confirmed_at timestamp without time zone,
    ai_draft_confirmed_by integer,
    manager_required boolean,
    outgoing_signed_at timestamp without time zone,
    incoming_signed_at timestamp without time zone,
    manager_signed_at timestamp without time zone,
    completed_at timestamp without time zone,
    archived_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.shift_handovers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.shift_handovers_id_seq OWNED BY public.shift_handovers.id;


--
--

CREATE TABLE public.shift_receive_diffs (
    id integer NOT NULL,
    handover_id integer NOT NULL,
    hotel_id integer NOT NULL,
    item_type character varying(40) NOT NULL,
    item_key character varying(80),
    declared_val numeric(14,2),
    received_val numeric(14,2),
    diff_val numeric(14,2),
    reason text,
    suggestion character varying(20),
    reporter_user_id integer,
    status character varying(24),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.shift_receive_diffs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.shift_receive_diffs_id_seq OWNED BY public.shift_receive_diffs.id;


--
--

CREATE TABLE public.staff_roster_templates (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    name character varying(80),
    payload_json text,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.staff_roster_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.staff_roster_templates_id_seq OWNED BY public.staff_roster_templates.id;


--
--

CREATE TABLE public.staff_shift_requests (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    user_id integer NOT NULL,
    kind character varying(20),
    shift_date date NOT NULL,
    from_shift character varying(20),
    to_shift character varying(20),
    swap_user_id integer,
    status character varying(20),
    note character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.staff_shift_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.staff_shift_requests_id_seq OWNED BY public.staff_shift_requests.id;


--
--

CREATE TABLE public.staff_shifts (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    user_id integer NOT NULL,
    shift_date date NOT NULL,
    shift character varying(20),
    handover_note text,
    source character varying(20),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.staff_shifts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.staff_shifts_id_seq OWNED BY public.staff_shifts.id;


--
--

CREATE TABLE public.stock_movements (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    supply_id integer NOT NULL,
    movement_type character varying(20),
    qty numeric(10,2),
    operator_id integer,
    note character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.stock_movements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.stock_movements_id_seq OWNED BY public.stock_movements.id;


--
--

CREATE TABLE public.supplies (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    category_id integer,
    sku character varying(40),
    name character varying(120) NOT NULL,
    unit character varying(20),
    safety_stock numeric(10,2),
    current_stock numeric(10,2),
    unit_cost numeric(10,2)
);


--
--

CREATE SEQUENCE public.supplies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.supplies_id_seq OWNED BY public.supplies.id;


--
--

CREATE TABLE public.supply_alerts (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_date date NOT NULL,
    line character varying(20),
    room_no character varying(20),
    floor character varying(20),
    supply_name character varying(120),
    severity character varying(20),
    message character varying(200),
    status character varying(20),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.supply_alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.supply_alerts_id_seq OWNED BY public.supply_alerts.id;


--
--

CREATE TABLE public.supply_categories (
    id integer NOT NULL,
    hotel_id integer,
    name character varying(80) NOT NULL,
    parent_id integer
);


--
--

CREATE SEQUENCE public.supply_categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.supply_categories_id_seq OWNED BY public.supply_categories.id;


--
--

CREATE TABLE public.supply_insights (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    biz_date date NOT NULL,
    line character varying(20),
    title character varying(120),
    recommendation text,
    impact_amount numeric(12,2),
    category character varying(40),
    status character varying(20),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.supply_insights_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.supply_insights_id_seq OWNED BY public.supply_insights.id;


--
--

CREATE TABLE public.supply_requisitions (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    supply_id integer,
    supply_name character varying(120),
    qty numeric(10,2),
    dept character varying(40),
    requester character varying(40),
    status character varying(20),
    note character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.supply_requisitions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.supply_requisitions_id_seq OWNED BY public.supply_requisitions.id;


--
--

CREATE TABLE public.tag_definitions (
    id integer NOT NULL,
    code character varying(40) NOT NULL,
    name character varying(80) NOT NULL,
    category character varying(40),
    rule_expr text,
    is_active boolean
);


--
--

CREATE SEQUENCE public.tag_definitions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.tag_definitions_id_seq OWNED BY public.tag_definitions.id;


--
--

CREATE TABLE public.tax_filings (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    period character varying(20),
    filing_type character varying(40),
    tax_amount numeric(14,2),
    invoice_count integer,
    status character varying(20),
    filed_at timestamp without time zone,
    note character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.tax_filings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.tax_filings_id_seq OWNED BY public.tax_filings.id;


--
--

CREATE TABLE public.users (
    id integer NOT NULL,
    hotel_id integer,
    role_id integer,
    username character varying(60) NOT NULL,
    password_hash character varying(128),
    full_name character varying(80),
    phone character varying(20),
    is_active boolean,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
--

CREATE TABLE public.venue_bookings (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    venue_id integer NOT NULL,
    event_name character varying(120),
    event_date date,
    attendees integer,
    amount numeric(12,2),
    status character varying(20)
);


--
--

CREATE SEQUENCE public.venue_bookings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.venue_bookings_id_seq OWNED BY public.venue_bookings.id;


--
--

CREATE TABLE public.venues (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    name character varying(120) NOT NULL,
    capacity integer,
    hourly_rate numeric(10,2)
);


--
--

CREATE SEQUENCE public.venues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.venues_id_seq OWNED BY public.venues.id;


--
--

CREATE TABLE public.webhook_event_logs (
    id integer NOT NULL,
    hotel_id integer,
    binding_id integer,
    channel character varying(30),
    external_event_id character varying(120),
    payload_json text,
    status character varying(20),
    error_message character varying(255),
    lead_id integer,
    created_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.webhook_event_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.webhook_event_logs_id_seq OWNED BY public.webhook_event_logs.id;


--
--

CREATE TABLE public.wecom_bind_tickets (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    token character varying(64) NOT NULL,
    external_userid character varying(120) NOT NULL,
    follow_userid character varying(80),
    nickname character varying(80),
    state character varying(64),
    status character varying(20),
    guest_id integer,
    phone_submitted character varying(30),
    welcome_sent boolean,
    welcome_mode character varying(30),
    error_message character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    bound_at timestamp without time zone,
    expires_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.wecom_bind_tickets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.wecom_bind_tickets_id_seq OWNED BY public.wecom_bind_tickets.id;


--
--

CREATE TABLE public.wecom_callback_events (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    change_type character varying(60),
    external_userid character varying(120),
    follow_userid character varying(80),
    state character varying(64),
    welcome_code character varying(128),
    raw_json text,
    status character varying(20),
    error_message character varying(255),
    is_deleted boolean,
    deleted_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    processed_at timestamp without time zone
);


--
--

CREATE SEQUENCE public.wecom_callback_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.wecom_callback_events_id_seq OWNED BY public.wecom_callback_events.id;


--
--

CREATE TABLE public.wecom_msg_tasks (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    guest_id integer,
    external_userid character varying(120) NOT NULL,
    sender_userid character varying(80) NOT NULL,
    content text NOT NULL,
    msgid character varying(120),
    fail_list_json text,
    status character varying(30),
    error_message character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
--

CREATE SEQUENCE public.wecom_msg_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.wecom_msg_tasks_id_seq OWNED BY public.wecom_msg_tasks.id;


--
--

CREATE TABLE public.wx_landing_pages (
    id integer NOT NULL,
    hotel_id integer NOT NULL,
    page_key character varying(64) NOT NULL,
    title character varying(128),
    template_id character varying(48),
    page_role character varying(16),
    blocks_json text,
    published_blocks_json text,
    published_title character varying(128),
    published_coupon_id integer,
    coupon_id integer,
    status character varying(16),
    published_url character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    updated_by character varying(32)
);


--
--

CREATE SEQUENCE public.wx_landing_pages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.wx_landing_pages_id_seq OWNED BY public.wx_landing_pages.id;


--
--

CREATE TABLE public.wx_landing_templates (
    id integer NOT NULL,
    template_key character varying(48) NOT NULL,
    name character varying(64) NOT NULL,
    category character varying(32),
    thumbnail character varying(255),
    blocks_json text,
    is_system boolean
);


--
--

CREATE SEQUENCE public.wx_landing_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
--

ALTER SEQUENCE public.wx_landing_templates_id_seq OWNED BY public.wx_landing_templates.id;


--
--

ALTER TABLE ONLY public.acquisition_contents ALTER COLUMN id SET DEFAULT nextval('public.acquisition_contents_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.acquisition_leads ALTER COLUMN id SET DEFAULT nextval('public.acquisition_leads_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.ai_action_confirmations ALTER COLUMN id SET DEFAULT nextval('public.ai_action_confirmations_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.ai_ask_queries ALTER COLUMN id SET DEFAULT nextval('public.ai_ask_queries_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.ai_commands ALTER COLUMN id SET DEFAULT nextval('public.ai_commands_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.ai_diagnosis_results ALTER COLUMN id SET DEFAULT nextval('public.ai_diagnosis_results_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.ai_report_interpretations ALTER COLUMN id SET DEFAULT nextval('public.ai_report_interpretations_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.ap_invoices ALTER COLUMN id SET DEFAULT nextval('public.ap_invoices_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.ar_ap_logs ALTER COLUMN id SET DEFAULT nextval('public.ar_ap_logs_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.ar_invoices ALTER COLUMN id SET DEFAULT nextval('public.ar_invoices_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.asset_alerts ALTER COLUMN id SET DEFAULT nextval('public.asset_alerts_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.asset_audit_items ALTER COLUMN id SET DEFAULT nextval('public.asset_audit_items_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.asset_events ALTER COLUMN id SET DEFAULT nextval('public.asset_events_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.asset_insights ALTER COLUMN id SET DEFAULT nextval('public.asset_insights_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.asset_maintenance ALTER COLUMN id SET DEFAULT nextval('public.asset_maintenance_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.assets ALTER COLUMN id SET DEFAULT nextval('public.assets_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.campaigns ALTER COLUMN id SET DEFAULT nextval('public.campaigns_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.channel_attribution ALTER COLUMN id SET DEFAULT nextval('public.channel_attribution_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.channel_commission ALTER COLUMN id SET DEFAULT nextval('public.channel_commission_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.channel_contracts ALTER COLUMN id SET DEFAULT nextval('public.channel_contracts_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.channels ALTER COLUMN id SET DEFAULT nextval('public.channels_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.competitor_property ALTER COLUMN id SET DEFAULT nextval('public.competitor_property_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.competitor_rate_snapshot ALTER COLUMN id SET DEFAULT nextval('public.competitor_rate_snapshot_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.competitor_room_map ALTER COLUMN id SET DEFAULT nextval('public.competitor_room_map_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.competitor_set ALTER COLUMN id SET DEFAULT nextval('public.competitor_set_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.corp_accounts ALTER COLUMN id SET DEFAULT nextval('public.corp_accounts_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.corp_price_ladders ALTER COLUMN id SET DEFAULT nextval('public.corp_price_ladders_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.crm_tasks ALTER COLUMN id SET DEFAULT nextval('public.crm_tasks_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.damage_tickets ALTER COLUMN id SET DEFAULT nextval('public.damage_tickets_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.demand_forecast ALTER COLUMN id SET DEFAULT nextval('public.demand_forecast_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.deposit_ledger_entries ALTER COLUMN id SET DEFAULT nextval('public.deposit_ledger_entries_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.event_calendar ALTER COLUMN id SET DEFAULT nextval('public.event_calendar_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.finance_acquiring_channels ALTER COLUMN id SET DEFAULT nextval('public.finance_acquiring_channels_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.finance_bad_debt_rates ALTER COLUMN id SET DEFAULT nextval('public.finance_bad_debt_rates_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.finance_credit_customers ALTER COLUMN id SET DEFAULT nextval('public.finance_credit_customers_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.finance_float_carry ALTER COLUMN id SET DEFAULT nextval('public.finance_float_carry_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.finance_param_audits ALTER COLUMN id SET DEFAULT nextval('public.finance_param_audits_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.finance_payment_terms ALTER COLUMN id SET DEFAULT nextval('public.finance_payment_terms_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.finance_report_exports ALTER COLUMN id SET DEFAULT nextval('public.finance_report_exports_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.finance_reports ALTER COLUMN id SET DEFAULT nextval('public.finance_reports_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.finance_tax_configs ALTER COLUMN id SET DEFAULT nextval('public.finance_tax_configs_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.guest_aliases ALTER COLUMN id SET DEFAULT nextval('public.guest_aliases_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.guest_coupons ALTER COLUMN id SET DEFAULT nextval('public.guest_coupons_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.guest_identities ALTER COLUMN id SET DEFAULT nextval('public.guest_identities_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.guest_tags ALTER COLUMN id SET DEFAULT nextval('public.guest_tags_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.guests ALTER COLUMN id SET DEFAULT nextval('public.guests_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.hotel_channel_bindings ALTER COLUMN id SET DEFAULT nextval('public.hotel_channel_bindings_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.hotel_mkt_settings ALTER COLUMN id SET DEFAULT nextval('public.hotel_mkt_settings_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.hotels ALTER COLUMN id SET DEFAULT nextval('public.hotels_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.housekeeping_tasks ALTER COLUMN id SET DEFAULT nextval('public.housekeeping_tasks_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.insight_diagnosis_results ALTER COLUMN id SET DEFAULT nextval('public.insight_diagnosis_results_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.inventory_allocation ALTER COLUMN id SET DEFAULT nextval('public.inventory_allocation_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.invoices ALTER COLUMN id SET DEFAULT nextval('public.invoices_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.ledger_entries ALTER COLUMN id SET DEFAULT nextval('public.ledger_entries_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.linen ALTER COLUMN id SET DEFAULT nextval('public.linen_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.linen_snapshots ALTER COLUMN id SET DEFAULT nextval('public.linen_snapshots_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_automations ALTER COLUMN id SET DEFAULT nextval('public.mkt_automations_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_campaigns ALTER COLUMN id SET DEFAULT nextval('public.mkt_campaigns_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule ALTER COLUMN id SET DEFAULT nextval('public.mkt_coupon_auto_rule_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_coupon ALTER COLUMN id SET DEFAULT nextval('public.mkt_coupon_auto_rule_coupon_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_filter ALTER COLUMN id SET DEFAULT nextval('public.mkt_coupon_auto_rule_filter_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_trigger ALTER COLUMN id SET DEFAULT nextval('public.mkt_coupon_auto_rule_trigger_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_coupon_grant_logs ALTER COLUMN id SET DEFAULT nextval('public.mkt_coupon_grant_logs_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_coupon_grants ALTER COLUMN id SET DEFAULT nextval('public.mkt_coupon_grants_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_coupon_redeems ALTER COLUMN id SET DEFAULT nextval('public.mkt_coupon_redeems_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_coupon_triggers ALTER COLUMN id SET DEFAULT nextval('public.mkt_coupon_triggers_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_coupons ALTER COLUMN id SET DEFAULT nextval('public.mkt_coupons_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_customer_notes ALTER COLUMN id SET DEFAULT nextval('public.mkt_customer_notes_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_guest_wallets ALTER COLUMN id SET DEFAULT nextval('public.mkt_guest_wallets_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_member_levels ALTER COLUMN id SET DEFAULT nextval('public.mkt_member_levels_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.mkt_stored_value_plans ALTER COLUMN id SET DEFAULT nextval('public.mkt_stored_value_plans_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.night_audit_exceptions ALTER COLUMN id SET DEFAULT nextval('public.night_audit_exceptions_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.night_audit_logs ALTER COLUMN id SET DEFAULT nextval('public.night_audit_logs_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.oneid_merge_events ALTER COLUMN id SET DEFAULT nextval('public.oneid_merge_events_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.oneid_phone_conflicts ALTER COLUMN id SET DEFAULT nextval('public.oneid_phone_conflicts_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.order_items ALTER COLUMN id SET DEFAULT nextval('public.order_items_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.ota_settlements ALTER COLUMN id SET DEFAULT nextval('public.ota_settlements_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pace_snapshot ALTER COLUMN id SET DEFAULT nextval('public.pace_snapshot_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.parity_alert ALTER COLUMN id SET DEFAULT nextval('public.parity_alert_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pms_ar_entries ALTER COLUMN id SET DEFAULT nextval('public.pms_ar_entries_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pms_ar_ledgers ALTER COLUMN id SET DEFAULT nextval('public.pms_ar_ledgers_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pms_checkins ALTER COLUMN id SET DEFAULT nextval('public.pms_checkins_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pms_folio_entries ALTER COLUMN id SET DEFAULT nextval('public.pms_folio_entries_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pms_folios ALTER COLUMN id SET DEFAULT nextval('public.pms_folios_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pms_group_room_blocks ALTER COLUMN id SET DEFAULT nextval('public.pms_group_room_blocks_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pms_group_room_lines ALTER COLUMN id SET DEFAULT nextval('public.pms_group_room_lines_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pms_id_doc_audits ALTER COLUMN id SET DEFAULT nextval('public.pms_id_doc_audits_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pms_room_assignments ALTER COLUMN id SET DEFAULT nextval('public.pms_room_assignments_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.price_suggestions ALTER COLUMN id SET DEFAULT nextval('public.price_suggestions_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pricing_assistant_config ALTER COLUMN id SET DEFAULT nextval('public.pricing_assistant_config_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pricing_decision ALTER COLUMN id SET DEFAULT nextval('public.pricing_decision_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pricing_effect ALTER COLUMN id SET DEFAULT nextval('public.pricing_effect_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.pricing_recommendation ALTER COLUMN id SET DEFAULT nextval('public.pricing_recommendation_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.profit_insights ALTER COLUMN id SET DEFAULT nextval('public.profit_insights_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.rate_strategies ALTER COLUMN id SET DEFAULT nextval('public.rate_strategies_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.recon_batches ALTER COLUMN id SET DEFAULT nextval('public.recon_batches_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.recon_items ALTER COLUMN id SET DEFAULT nextval('public.recon_items_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.refund_adjust_audits ALTER COLUMN id SET DEFAULT nextval('public.refund_adjust_audits_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.refund_adjust_tickets ALTER COLUMN id SET DEFAULT nextval('public.refund_adjust_tickets_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.reservations ALTER COLUMN id SET DEFAULT nextval('public.reservations_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.restock_items ALTER COLUMN id SET DEFAULT nextval('public.restock_items_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.restock_orders ALTER COLUMN id SET DEFAULT nextval('public.restock_orders_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.revenue_anomalies ALTER COLUMN id SET DEFAULT nextval('public.revenue_anomalies_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.risk_alerts ALTER COLUMN id SET DEFAULT nextval('public.risk_alerts_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.room_inspections ALTER COLUMN id SET DEFAULT nextval('public.room_inspections_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.room_iot_metrics ALTER COLUMN id SET DEFAULT nextval('public.room_iot_metrics_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.room_night_inventory ALTER COLUMN id SET DEFAULT nextval('public.room_night_inventory_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.room_status_log ALTER COLUMN id SET DEFAULT nextval('public.room_status_log_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.room_type_base_rate ALTER COLUMN id SET DEFAULT nextval('public.room_type_base_rate_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.room_types ALTER COLUMN id SET DEFAULT nextval('public.room_types_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.rooms ALTER COLUMN id SET DEFAULT nextval('public.rooms_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.segment_members ALTER COLUMN id SET DEFAULT nextval('public.segment_members_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.segments ALTER COLUMN id SET DEFAULT nextval('public.segments_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.service_requests ALTER COLUMN id SET DEFAULT nextval('public.service_requests_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.shift_asset_counts ALTER COLUMN id SET DEFAULT nextval('public.shift_asset_counts_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.shift_audit_logs ALTER COLUMN id SET DEFAULT nextval('public.shift_audit_logs_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.shift_float_counts ALTER COLUMN id SET DEFAULT nextval('public.shift_float_counts_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.shift_handover_tasks ALTER COLUMN id SET DEFAULT nextval('public.shift_handover_tasks_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.shift_handovers ALTER COLUMN id SET DEFAULT nextval('public.shift_handovers_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.shift_receive_diffs ALTER COLUMN id SET DEFAULT nextval('public.shift_receive_diffs_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.staff_roster_templates ALTER COLUMN id SET DEFAULT nextval('public.staff_roster_templates_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.staff_shift_requests ALTER COLUMN id SET DEFAULT nextval('public.staff_shift_requests_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.staff_shifts ALTER COLUMN id SET DEFAULT nextval('public.staff_shifts_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.stock_movements ALTER COLUMN id SET DEFAULT nextval('public.stock_movements_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.supplies ALTER COLUMN id SET DEFAULT nextval('public.supplies_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.supply_alerts ALTER COLUMN id SET DEFAULT nextval('public.supply_alerts_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.supply_categories ALTER COLUMN id SET DEFAULT nextval('public.supply_categories_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.supply_insights ALTER COLUMN id SET DEFAULT nextval('public.supply_insights_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.supply_requisitions ALTER COLUMN id SET DEFAULT nextval('public.supply_requisitions_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.tag_definitions ALTER COLUMN id SET DEFAULT nextval('public.tag_definitions_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.tax_filings ALTER COLUMN id SET DEFAULT nextval('public.tax_filings_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.venue_bookings ALTER COLUMN id SET DEFAULT nextval('public.venue_bookings_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.venues ALTER COLUMN id SET DEFAULT nextval('public.venues_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.webhook_event_logs ALTER COLUMN id SET DEFAULT nextval('public.webhook_event_logs_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.wecom_bind_tickets ALTER COLUMN id SET DEFAULT nextval('public.wecom_bind_tickets_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.wecom_callback_events ALTER COLUMN id SET DEFAULT nextval('public.wecom_callback_events_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.wecom_msg_tasks ALTER COLUMN id SET DEFAULT nextval('public.wecom_msg_tasks_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.wx_landing_pages ALTER COLUMN id SET DEFAULT nextval('public.wx_landing_pages_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.wx_landing_templates ALTER COLUMN id SET DEFAULT nextval('public.wx_landing_templates_id_seq'::regclass);


--
--

ALTER TABLE ONLY public.acquisition_contents
    ADD CONSTRAINT acquisition_contents_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.acquisition_leads
    ADD CONSTRAINT acquisition_leads_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.ai_action_confirmations
    ADD CONSTRAINT ai_action_confirmations_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.ai_ask_queries
    ADD CONSTRAINT ai_ask_queries_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.ai_ask_sessions
    ADD CONSTRAINT ai_ask_sessions_pkey PRIMARY KEY (session_id);


--
--

ALTER TABLE ONLY public.ai_commands
    ADD CONSTRAINT ai_commands_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.ai_diagnosis_results
    ADD CONSTRAINT ai_diagnosis_results_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.ai_report_interpretations
    ADD CONSTRAINT ai_report_interpretations_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.ap_invoices
    ADD CONSTRAINT ap_invoices_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.app_settings
    ADD CONSTRAINT app_settings_pkey PRIMARY KEY (key);


--
--

ALTER TABLE ONLY public.ar_ap_logs
    ADD CONSTRAINT ar_ap_logs_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.ar_invoices
    ADD CONSTRAINT ar_invoices_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.asset_alerts
    ADD CONSTRAINT asset_alerts_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.asset_audit_items
    ADD CONSTRAINT asset_audit_items_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.asset_events
    ADD CONSTRAINT asset_events_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.asset_insights
    ADD CONSTRAINT asset_insights_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.asset_maintenance
    ADD CONSTRAINT asset_maintenance_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.channel_attribution
    ADD CONSTRAINT channel_attribution_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.channel_commission
    ADD CONSTRAINT channel_commission_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.channel_contracts
    ADD CONSTRAINT channel_contracts_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_code_key UNIQUE (code);


--
--

ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.competitor_property
    ADD CONSTRAINT competitor_property_comp_id_key UNIQUE (comp_id);


--
--

ALTER TABLE ONLY public.competitor_property
    ADD CONSTRAINT competitor_property_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.competitor_rate_snapshot
    ADD CONSTRAINT competitor_rate_snapshot_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.competitor_rate_snapshot
    ADD CONSTRAINT competitor_rate_snapshot_snapshot_id_key UNIQUE (snapshot_id);


--
--

ALTER TABLE ONLY public.competitor_room_map
    ADD CONSTRAINT competitor_room_map_map_id_key UNIQUE (map_id);


--
--

ALTER TABLE ONLY public.competitor_room_map
    ADD CONSTRAINT competitor_room_map_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.competitor_set
    ADD CONSTRAINT competitor_set_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.competitor_set
    ADD CONSTRAINT competitor_set_set_id_key UNIQUE (set_id);


--
--

ALTER TABLE ONLY public.corp_accounts
    ADD CONSTRAINT corp_accounts_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.corp_price_ladders
    ADD CONSTRAINT corp_price_ladders_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.crm_tasks
    ADD CONSTRAINT crm_tasks_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.damage_tickets
    ADD CONSTRAINT damage_tickets_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.demand_forecast
    ADD CONSTRAINT demand_forecast_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.deposit_ledger_entries
    ADD CONSTRAINT deposit_ledger_entries_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.deposits
    ADD CONSTRAINT deposits_idempotency_key_key UNIQUE (idempotency_key);


--
--

ALTER TABLE ONLY public.deposits
    ADD CONSTRAINT deposits_pkey PRIMARY KEY (deposit_id);


--
--

ALTER TABLE ONLY public.event_calendar
    ADD CONSTRAINT event_calendar_event_id_key UNIQUE (event_id);


--
--

ALTER TABLE ONLY public.event_calendar
    ADD CONSTRAINT event_calendar_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.finance_acquiring_channels
    ADD CONSTRAINT finance_acquiring_channels_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.finance_bad_debt_rates
    ADD CONSTRAINT finance_bad_debt_rates_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.finance_credit_customers
    ADD CONSTRAINT finance_credit_customers_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.finance_float_carry
    ADD CONSTRAINT finance_float_carry_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.finance_param_audits
    ADD CONSTRAINT finance_param_audits_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.finance_payment_terms
    ADD CONSTRAINT finance_payment_terms_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.finance_report_exports
    ADD CONSTRAINT finance_report_exports_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.finance_reports
    ADD CONSTRAINT finance_reports_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.finance_tax_configs
    ADD CONSTRAINT finance_tax_configs_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.guest_aliases
    ADD CONSTRAINT guest_aliases_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.guest_coupons
    ADD CONSTRAINT guest_coupons_code_key UNIQUE (code);


--
--

ALTER TABLE ONLY public.guest_coupons
    ADD CONSTRAINT guest_coupons_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.guest_identities
    ADD CONSTRAINT guest_identities_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.guest_tags
    ADD CONSTRAINT guest_tags_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.guests
    ADD CONSTRAINT guests_one_id_key UNIQUE (one_id);


--
--

ALTER TABLE ONLY public.guests
    ADD CONSTRAINT guests_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.hotel_channel_bindings
    ADD CONSTRAINT hotel_channel_bindings_binding_token_key UNIQUE (binding_token);


--
--

ALTER TABLE ONLY public.hotel_channel_bindings
    ADD CONSTRAINT hotel_channel_bindings_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.hotel_mkt_settings
    ADD CONSTRAINT hotel_mkt_settings_hotel_id_key UNIQUE (hotel_id);


--
--

ALTER TABLE ONLY public.hotel_mkt_settings
    ADD CONSTRAINT hotel_mkt_settings_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.hotels
    ADD CONSTRAINT hotels_code_key UNIQUE (code);


--
--

ALTER TABLE ONLY public.hotels
    ADD CONSTRAINT hotels_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.housekeeping_tasks
    ADD CONSTRAINT housekeeping_tasks_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.insight_diagnosis_results
    ADD CONSTRAINT insight_diagnosis_results_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.inventory_allocation
    ADD CONSTRAINT inventory_allocation_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_invoice_no_key UNIQUE (invoice_no);


--
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.ledger_entries
    ADD CONSTRAINT ledger_entries_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.linen
    ADD CONSTRAINT linen_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.linen_snapshots
    ADD CONSTRAINT linen_snapshots_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_automations
    ADD CONSTRAINT mkt_automations_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_campaigns
    ADD CONSTRAINT mkt_campaigns_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_coupon
    ADD CONSTRAINT mkt_coupon_auto_rule_coupon_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_filter
    ADD CONSTRAINT mkt_coupon_auto_rule_filter_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule
    ADD CONSTRAINT mkt_coupon_auto_rule_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_trigger
    ADD CONSTRAINT mkt_coupon_auto_rule_trigger_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_coupon_grant_logs
    ADD CONSTRAINT mkt_coupon_grant_logs_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_coupon_grants
    ADD CONSTRAINT mkt_coupon_grants_code_key UNIQUE (code);


--
--

ALTER TABLE ONLY public.mkt_coupon_grants
    ADD CONSTRAINT mkt_coupon_grants_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_coupon_redeems
    ADD CONSTRAINT mkt_coupon_redeems_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_coupon_triggers
    ADD CONSTRAINT mkt_coupon_triggers_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_coupons
    ADD CONSTRAINT mkt_coupons_batch_no_key UNIQUE (batch_no);


--
--

ALTER TABLE ONLY public.mkt_coupons
    ADD CONSTRAINT mkt_coupons_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_customer_notes
    ADD CONSTRAINT mkt_customer_notes_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_guest_wallets
    ADD CONSTRAINT mkt_guest_wallets_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_member_levels
    ADD CONSTRAINT mkt_member_levels_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_stored_value_plans
    ADD CONSTRAINT mkt_stored_value_plans_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.night_audit_exceptions
    ADD CONSTRAINT night_audit_exceptions_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.night_audit_logs
    ADD CONSTRAINT night_audit_logs_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.oneid_merge_events
    ADD CONSTRAINT oneid_merge_events_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.oneid_phone_conflicts
    ADD CONSTRAINT oneid_phone_conflicts_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_order_no_key UNIQUE (order_no);


--
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.ota_settlements
    ADD CONSTRAINT ota_settlements_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pace_snapshot
    ADD CONSTRAINT pace_snapshot_pace_id_key UNIQUE (pace_id);


--
--

ALTER TABLE ONLY public.pace_snapshot
    ADD CONSTRAINT pace_snapshot_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.parity_alert
    ADD CONSTRAINT parity_alert_alert_id_key UNIQUE (alert_id);


--
--

ALTER TABLE ONLY public.parity_alert
    ADD CONSTRAINT parity_alert_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_code_key UNIQUE (code);


--
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pms_ar_entries
    ADD CONSTRAINT pms_ar_entries_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pms_ar_ledgers
    ADD CONSTRAINT pms_ar_ledgers_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pms_checkins
    ADD CONSTRAINT pms_checkins_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pms_folio_entries
    ADD CONSTRAINT pms_folio_entries_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pms_folios
    ADD CONSTRAINT pms_folios_folio_no_key UNIQUE (folio_no);


--
--

ALTER TABLE ONLY public.pms_folios
    ADD CONSTRAINT pms_folios_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pms_group_room_blocks
    ADD CONSTRAINT pms_group_room_blocks_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pms_group_room_lines
    ADD CONSTRAINT pms_group_room_lines_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pms_id_doc_audits
    ADD CONSTRAINT pms_id_doc_audits_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pms_room_assignments
    ADD CONSTRAINT pms_room_assignments_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.price_suggestions
    ADD CONSTRAINT price_suggestions_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pricing_assistant_config
    ADD CONSTRAINT pricing_assistant_config_hotel_id_key UNIQUE (hotel_id);


--
--

ALTER TABLE ONLY public.pricing_assistant_config
    ADD CONSTRAINT pricing_assistant_config_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pricing_decision
    ADD CONSTRAINT pricing_decision_decision_id_key UNIQUE (decision_id);


--
--

ALTER TABLE ONLY public.pricing_decision
    ADD CONSTRAINT pricing_decision_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pricing_effect
    ADD CONSTRAINT pricing_effect_effect_id_key UNIQUE (effect_id);


--
--

ALTER TABLE ONLY public.pricing_effect
    ADD CONSTRAINT pricing_effect_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pricing_recommendation
    ADD CONSTRAINT pricing_recommendation_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.pricing_recommendation
    ADD CONSTRAINT pricing_recommendation_reco_id_key UNIQUE (reco_id);


--
--

ALTER TABLE ONLY public.profit_insights
    ADD CONSTRAINT profit_insights_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.rate_strategies
    ADD CONSTRAINT rate_strategies_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.recon_batches
    ADD CONSTRAINT recon_batches_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.recon_items
    ADD CONSTRAINT recon_items_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.refund_adjust_audits
    ADD CONSTRAINT refund_adjust_audits_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.refund_adjust_configs
    ADD CONSTRAINT refund_adjust_configs_pkey PRIMARY KEY (hotel_id);


--
--

ALTER TABLE ONLY public.refund_adjust_tickets
    ADD CONSTRAINT refund_adjust_tickets_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.refund_adjust_tickets
    ADD CONSTRAINT refund_adjust_tickets_ticket_no_key UNIQUE (ticket_no);


--
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.restock_items
    ADD CONSTRAINT restock_items_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.restock_orders
    ADD CONSTRAINT restock_orders_order_no_key UNIQUE (order_no);


--
--

ALTER TABLE ONLY public.restock_orders
    ADD CONSTRAINT restock_orders_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.revenue_anomalies
    ADD CONSTRAINT revenue_anomalies_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.risk_alerts
    ADD CONSTRAINT risk_alerts_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (role_id, permission_id);


--
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_code_key UNIQUE (code);


--
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.room_inspections
    ADD CONSTRAINT room_inspections_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.room_iot_metrics
    ADD CONSTRAINT room_iot_metrics_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.room_night_inventory
    ADD CONSTRAINT room_night_inventory_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.room_status_log
    ADD CONSTRAINT room_status_log_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.room_type_base_rate
    ADD CONSTRAINT room_type_base_rate_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.room_types
    ADD CONSTRAINT room_types_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.segment_members
    ADD CONSTRAINT segment_members_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.segments
    ADD CONSTRAINT segments_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.service_requests
    ADD CONSTRAINT service_requests_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.shift_asset_counts
    ADD CONSTRAINT shift_asset_counts_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.shift_audit_logs
    ADD CONSTRAINT shift_audit_logs_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.shift_float_counts
    ADD CONSTRAINT shift_float_counts_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.shift_handover_tasks
    ADD CONSTRAINT shift_handover_tasks_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.shift_handovers
    ADD CONSTRAINT shift_handovers_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.shift_receive_diffs
    ADD CONSTRAINT shift_receive_diffs_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.staff_roster_templates
    ADD CONSTRAINT staff_roster_templates_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.staff_shift_requests
    ADD CONSTRAINT staff_shift_requests_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.staff_shifts
    ADD CONSTRAINT staff_shifts_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.stock_movements
    ADD CONSTRAINT stock_movements_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.supplies
    ADD CONSTRAINT supplies_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.supply_alerts
    ADD CONSTRAINT supply_alerts_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.supply_categories
    ADD CONSTRAINT supply_categories_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.supply_insights
    ADD CONSTRAINT supply_insights_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.supply_requisitions
    ADD CONSTRAINT supply_requisitions_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.tag_definitions
    ADD CONSTRAINT tag_definitions_code_key UNIQUE (code);


--
--

ALTER TABLE ONLY public.tag_definitions
    ADD CONSTRAINT tag_definitions_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.tax_filings
    ADD CONSTRAINT tax_filings_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule
    ADD CONSTRAINT uk_auto_rule_name UNIQUE (property_id, name);


--
--

ALTER TABLE ONLY public.mkt_coupon_grant_logs
    ADD CONSTRAINT uk_mkt_grant_dedup UNIQUE (trigger_id, customer_id, batch_id);


--
--

ALTER TABLE ONLY public.mkt_guest_wallets
    ADD CONSTRAINT uk_mkt_guest_wallet UNIQUE (hotel_id, guest_id);


--
--

ALTER TABLE ONLY public.mkt_member_levels
    ADD CONSTRAINT uk_mkt_level UNIQUE (hotel_id, level_code);


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_coupon
    ADD CONSTRAINT uk_rule_batch UNIQUE (rule_id, batch_id);


--
--

ALTER TABLE ONLY public.wx_landing_pages
    ADD CONSTRAINT uk_wx_landing_key UNIQUE (hotel_id, page_key);


--
--

ALTER TABLE ONLY public.inventory_allocation
    ADD CONSTRAINT uq_allocation UNIQUE (hotel_id, room_type_id, channel_id, biz_date);


--
--

ALTER TABLE ONLY public.ap_invoices
    ADD CONSTRAINT uq_ap_invoice_no UNIQUE (hotel_id, invoice_no);


--
--

ALTER TABLE ONLY public.pms_ar_ledgers
    ADD CONSTRAINT uq_ar_hotel_corp UNIQUE (hotel_id, corp_id);


--
--

ALTER TABLE ONLY public.ar_invoices
    ADD CONSTRAINT uq_ar_invoice_no UNIQUE (hotel_id, invoice_no);


--
--

ALTER TABLE ONLY public.channel_commission
    ADD CONSTRAINT uq_channel_commission_dim UNIQUE (hotel_id, channel_code, room_type_id, rate_code, effective_from);


--
--

ALTER TABLE ONLY public.channel_contracts
    ADD CONSTRAINT uq_channel_contract UNIQUE (hotel_id, channel_id, room_type_id);


--
--

ALTER TABLE ONLY public.corp_accounts
    ADD CONSTRAINT uq_corp_hotel_code UNIQUE (hotel_id, code);


--
--

ALTER TABLE ONLY public.corp_price_ladders
    ADD CONSTRAINT uq_corp_ladder_tier UNIQUE (corp_id, room_type_id, tier_name);


--
--

ALTER TABLE ONLY public.guest_aliases
    ADD CONSTRAINT uq_guest_alias UNIQUE (guest_id, alias_name);


--
--

ALTER TABLE ONLY public.guest_identities
    ADD CONSTRAINT uq_guest_identity UNIQUE (guest_id, source, external_id);


--
--

ALTER TABLE ONLY public.guest_tags
    ADD CONSTRAINT uq_guest_tag UNIQUE (guest_id, tag_id);


--
--

ALTER TABLE ONLY public.linen_snapshots
    ADD CONSTRAINT uq_linen_snap UNIQUE (hotel_id, biz_date, item_type);


--
--

ALTER TABLE ONLY public.night_audit_logs
    ADD CONSTRAINT uq_nightaudit_hotel_date UNIQUE (hotel_id, biz_date);


--
--

ALTER TABLE ONLY public.ota_settlements
    ADD CONSTRAINT uq_ota_settle_period UNIQUE (hotel_id, channel_id, period);


--
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT uq_room_hotel_no UNIQUE (hotel_id, room_no);


--
--

ALTER TABLE ONLY public.room_night_inventory
    ADD CONSTRAINT uq_room_night UNIQUE (hotel_id, room_id, biz_date);


--
--

ALTER TABLE ONLY public.room_types
    ADD CONSTRAINT uq_roomtype_hotel_code UNIQUE (hotel_id, code);


--
--

ALTER TABLE ONLY public.segment_members
    ADD CONSTRAINT uq_segment_member UNIQUE (segment_id, guest_id);


--
--

ALTER TABLE ONLY public.supplies
    ADD CONSTRAINT uq_supply_sku UNIQUE (hotel_id, sku);


--
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
--

ALTER TABLE ONLY public.venue_bookings
    ADD CONSTRAINT venue_bookings_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.venues
    ADD CONSTRAINT venues_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.webhook_event_logs
    ADD CONSTRAINT webhook_event_logs_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.wecom_bind_tickets
    ADD CONSTRAINT wecom_bind_tickets_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.wecom_bind_tickets
    ADD CONSTRAINT wecom_bind_tickets_token_key UNIQUE (token);


--
--

ALTER TABLE ONLY public.wecom_callback_events
    ADD CONSTRAINT wecom_callback_events_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.wecom_msg_tasks
    ADD CONSTRAINT wecom_msg_tasks_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.wx_landing_pages
    ADD CONSTRAINT wx_landing_pages_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.wx_landing_templates
    ADD CONSTRAINT wx_landing_templates_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY public.wx_landing_templates
    ADD CONSTRAINT wx_landing_templates_template_key_key UNIQUE (template_key);


--
--

CREATE INDEX ix_ai_ask_queries_session_id ON public.ai_ask_queries USING btree (session_id);


--
--

CREATE INDEX ix_ai_ask_sessions_hotel_id ON public.ai_ask_sessions USING btree (hotel_id);


--
--

CREATE INDEX ix_mkt_coupon_auto_rule_coupon_batch_id ON public.mkt_coupon_auto_rule_coupon USING btree (batch_id);


--
--

CREATE INDEX ix_mkt_coupon_auto_rule_coupon_rule_id ON public.mkt_coupon_auto_rule_coupon USING btree (rule_id);


--
--

CREATE INDEX ix_mkt_coupon_auto_rule_filter_rule_id ON public.mkt_coupon_auto_rule_filter USING btree (rule_id);


--
--

CREATE INDEX ix_mkt_coupon_auto_rule_property_id ON public.mkt_coupon_auto_rule USING btree (property_id);


--
--

CREATE INDEX ix_mkt_coupon_auto_rule_trigger_customer_id ON public.mkt_coupon_auto_rule_trigger USING btree (customer_id);


--
--

CREATE INDEX ix_mkt_coupon_auto_rule_trigger_property_id ON public.mkt_coupon_auto_rule_trigger USING btree (property_id);


--
--

CREATE INDEX ix_mkt_coupon_auto_rule_trigger_rule_id ON public.mkt_coupon_auto_rule_trigger USING btree (rule_id);


--
--

ALTER TABLE ONLY public.acquisition_contents
    ADD CONSTRAINT acquisition_contents_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.acquisition_contents
    ADD CONSTRAINT acquisition_contents_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.acquisition_leads
    ADD CONSTRAINT acquisition_leads_content_id_fkey FOREIGN KEY (content_id) REFERENCES public.acquisition_contents(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.acquisition_leads
    ADD CONSTRAINT acquisition_leads_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.acquisition_leads
    ADD CONSTRAINT acquisition_leads_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.acquisition_leads
    ADD CONSTRAINT acquisition_leads_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ai_action_confirmations
    ADD CONSTRAINT ai_action_confirmations_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ai_action_confirmations
    ADD CONSTRAINT ai_action_confirmations_interpretation_id_fkey FOREIGN KEY (interpretation_id) REFERENCES public.ai_report_interpretations(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ai_ask_queries
    ADD CONSTRAINT ai_ask_queries_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ai_ask_queries
    ADD CONSTRAINT ai_ask_queries_parent_query_id_fkey FOREIGN KEY (parent_query_id) REFERENCES public.ai_ask_queries(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ai_ask_sessions
    ADD CONSTRAINT ai_ask_sessions_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ai_commands
    ADD CONSTRAINT ai_commands_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ai_commands
    ADD CONSTRAINT ai_commands_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ai_diagnosis_results
    ADD CONSTRAINT ai_diagnosis_results_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ai_report_interpretations
    ADD CONSTRAINT ai_report_interpretations_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ap_invoices
    ADD CONSTRAINT ap_invoices_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ap_invoices
    ADD CONSTRAINT ap_invoices_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ap_invoices
    ADD CONSTRAINT ap_invoices_ota_settlement_id_fkey FOREIGN KEY (ota_settlement_id) REFERENCES public.ota_settlements(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ar_ap_logs
    ADD CONSTRAINT ar_ap_logs_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ar_ap_logs
    ADD CONSTRAINT ar_ap_logs_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ar_invoices
    ADD CONSTRAINT ar_invoices_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ar_invoices
    ADD CONSTRAINT ar_invoices_corp_id_fkey FOREIGN KEY (corp_id) REFERENCES public.corp_accounts(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ar_invoices
    ADD CONSTRAINT ar_invoices_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ar_invoices
    ADD CONSTRAINT ar_invoices_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ar_invoices
    ADD CONSTRAINT ar_invoices_ota_settlement_id_fkey FOREIGN KEY (ota_settlement_id) REFERENCES public.ota_settlements(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ar_invoices
    ADD CONSTRAINT ar_invoices_pms_ar_entry_id_fkey FOREIGN KEY (pms_ar_entry_id) REFERENCES public.pms_ar_entries(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.asset_alerts
    ADD CONSTRAINT asset_alerts_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.asset_alerts
    ADD CONSTRAINT asset_alerts_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.asset_audit_items
    ADD CONSTRAINT asset_audit_items_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.asset_events
    ADD CONSTRAINT asset_events_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.asset_events
    ADD CONSTRAINT asset_events_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.asset_insights
    ADD CONSTRAINT asset_insights_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.asset_insights
    ADD CONSTRAINT asset_insights_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.asset_maintenance
    ADD CONSTRAINT asset_maintenance_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.asset_maintenance
    ADD CONSTRAINT asset_maintenance_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.channel_attribution
    ADD CONSTRAINT channel_attribution_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.channel_attribution
    ADD CONSTRAINT channel_attribution_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.channel_commission
    ADD CONSTRAINT channel_commission_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.channel_commission
    ADD CONSTRAINT channel_commission_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.channel_contracts
    ADD CONSTRAINT channel_contracts_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.channel_contracts
    ADD CONSTRAINT channel_contracts_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.channel_contracts
    ADD CONSTRAINT channel_contracts_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.competitor_property
    ADD CONSTRAINT competitor_property_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.competitor_rate_snapshot
    ADD CONSTRAINT competitor_rate_snapshot_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.competitor_room_map
    ADD CONSTRAINT competitor_room_map_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.competitor_room_map
    ADD CONSTRAINT competitor_room_map_self_room_type_id_fkey FOREIGN KEY (self_room_type_id) REFERENCES public.room_types(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.competitor_set
    ADD CONSTRAINT competitor_set_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.corp_accounts
    ADD CONSTRAINT corp_accounts_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.corp_price_ladders
    ADD CONSTRAINT corp_price_ladders_corp_id_fkey FOREIGN KEY (corp_id) REFERENCES public.corp_accounts(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.corp_price_ladders
    ADD CONSTRAINT corp_price_ladders_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.crm_tasks
    ADD CONSTRAINT crm_tasks_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.crm_tasks
    ADD CONSTRAINT crm_tasks_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.crm_tasks
    ADD CONSTRAINT crm_tasks_segment_id_fkey FOREIGN KEY (segment_id) REFERENCES public.segments(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.damage_tickets
    ADD CONSTRAINT damage_tickets_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.demand_forecast
    ADD CONSTRAINT demand_forecast_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.demand_forecast
    ADD CONSTRAINT demand_forecast_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.deposit_ledger_entries
    ADD CONSTRAINT deposit_ledger_entries_deposit_id_fkey FOREIGN KEY (deposit_id) REFERENCES public.deposits(deposit_id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.deposits
    ADD CONSTRAINT deposits_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.deposits
    ADD CONSTRAINT deposits_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.deposits
    ADD CONSTRAINT deposits_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.event_calendar
    ADD CONSTRAINT event_calendar_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.finance_acquiring_channels
    ADD CONSTRAINT finance_acquiring_channels_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.finance_bad_debt_rates
    ADD CONSTRAINT finance_bad_debt_rates_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.finance_credit_customers
    ADD CONSTRAINT finance_credit_customers_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.finance_float_carry
    ADD CONSTRAINT finance_float_carry_applicant_user_id_fkey FOREIGN KEY (applicant_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.finance_float_carry
    ADD CONSTRAINT finance_float_carry_finance_approver_user_id_fkey FOREIGN KEY (finance_approver_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.finance_float_carry
    ADD CONSTRAINT finance_float_carry_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.finance_float_carry
    ADD CONSTRAINT finance_float_carry_manager_approver_user_id_fkey FOREIGN KEY (manager_approver_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.finance_float_carry
    ADD CONSTRAINT finance_float_carry_rejected_by_user_id_fkey FOREIGN KEY (rejected_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.finance_param_audits
    ADD CONSTRAINT finance_param_audits_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.finance_payment_terms
    ADD CONSTRAINT finance_payment_terms_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.finance_report_exports
    ADD CONSTRAINT finance_report_exports_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.finance_reports
    ADD CONSTRAINT finance_reports_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.finance_tax_configs
    ADD CONSTRAINT finance_tax_configs_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.guest_aliases
    ADD CONSTRAINT guest_aliases_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.guest_coupons
    ADD CONSTRAINT guest_coupons_grant_id_fkey FOREIGN KEY (grant_id) REFERENCES public.mkt_coupon_grants(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.guest_coupons
    ADD CONSTRAINT guest_coupons_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.guest_coupons
    ADD CONSTRAINT guest_coupons_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.guest_identities
    ADD CONSTRAINT guest_identities_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.guest_tags
    ADD CONSTRAINT guest_tags_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.guest_tags
    ADD CONSTRAINT guest_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.tag_definitions(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.guests
    ADD CONSTRAINT guests_merged_into_guest_id_fkey FOREIGN KEY (merged_into_guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.hotel_channel_bindings
    ADD CONSTRAINT hotel_channel_bindings_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.hotel_mkt_settings
    ADD CONSTRAINT hotel_mkt_settings_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.hotel_mkt_settings
    ADD CONSTRAINT hotel_mkt_settings_member_landing_page_id_fkey FOREIGN KEY (member_landing_page_id) REFERENCES public.wx_landing_pages(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.hotel_mkt_settings
    ADD CONSTRAINT hotel_mkt_settings_returning_landing_page_id_fkey FOREIGN KEY (returning_landing_page_id) REFERENCES public.wx_landing_pages(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.hotel_mkt_settings
    ADD CONSTRAINT hotel_mkt_settings_welcome_landing_page_id_fkey FOREIGN KEY (welcome_landing_page_id) REFERENCES public.wx_landing_pages(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.housekeeping_tasks
    ADD CONSTRAINT housekeeping_tasks_assignee_id_fkey FOREIGN KEY (assignee_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.housekeeping_tasks
    ADD CONSTRAINT housekeeping_tasks_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.housekeeping_tasks
    ADD CONSTRAINT housekeeping_tasks_inspect_by_fkey FOREIGN KEY (inspect_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.housekeeping_tasks
    ADD CONSTRAINT housekeeping_tasks_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.insight_diagnosis_results
    ADD CONSTRAINT insight_diagnosis_results_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.inventory_allocation
    ADD CONSTRAINT inventory_allocation_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.inventory_allocation
    ADD CONSTRAINT inventory_allocation_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.inventory_allocation
    ADD CONSTRAINT inventory_allocation_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ledger_entries
    ADD CONSTRAINT ledger_entries_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.linen
    ADD CONSTRAINT linen_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.linen
    ADD CONSTRAINT linen_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.linen_snapshots
    ADD CONSTRAINT linen_snapshots_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_automations
    ADD CONSTRAINT mkt_automations_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_campaigns
    ADD CONSTRAINT mkt_campaigns_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_coupon
    ADD CONSTRAINT mkt_coupon_auto_rule_coupon_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.mkt_coupons(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_coupon
    ADD CONSTRAINT mkt_coupon_auto_rule_coupon_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES public.mkt_coupon_auto_rule(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_filter
    ADD CONSTRAINT mkt_coupon_auto_rule_filter_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES public.mkt_coupon_auto_rule(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule
    ADD CONSTRAINT mkt_coupon_auto_rule_property_id_fkey FOREIGN KEY (property_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_trigger
    ADD CONSTRAINT mkt_coupon_auto_rule_trigger_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.mkt_coupons(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_trigger
    ADD CONSTRAINT mkt_coupon_auto_rule_trigger_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_trigger
    ADD CONSTRAINT mkt_coupon_auto_rule_trigger_instance_id_fkey FOREIGN KEY (instance_id) REFERENCES public.mkt_coupon_grants(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_trigger
    ADD CONSTRAINT mkt_coupon_auto_rule_trigger_property_id_fkey FOREIGN KEY (property_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_auto_rule_trigger
    ADD CONSTRAINT mkt_coupon_auto_rule_trigger_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES public.mkt_coupon_auto_rule(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_grant_logs
    ADD CONSTRAINT mkt_coupon_grant_logs_auto_rule_id_fkey FOREIGN KEY (auto_rule_id) REFERENCES public.mkt_coupon_auto_rule(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.mkt_coupon_grant_logs
    ADD CONSTRAINT mkt_coupon_grant_logs_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.mkt_coupons(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_grant_logs
    ADD CONSTRAINT mkt_coupon_grant_logs_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_grant_logs
    ADD CONSTRAINT mkt_coupon_grant_logs_instance_id_fkey FOREIGN KEY (instance_id) REFERENCES public.mkt_coupon_grants(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_grant_logs
    ADD CONSTRAINT mkt_coupon_grant_logs_trigger_id_fkey FOREIGN KEY (trigger_id) REFERENCES public.mkt_coupon_triggers(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.mkt_coupon_grants
    ADD CONSTRAINT mkt_coupon_grants_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.mkt_coupons(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_grants
    ADD CONSTRAINT mkt_coupon_grants_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_grants
    ADD CONSTRAINT mkt_coupon_grants_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_grants
    ADD CONSTRAINT mkt_coupon_grants_used_order_id_fkey FOREIGN KEY (used_order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.mkt_coupon_redeems
    ADD CONSTRAINT mkt_coupon_redeems_instance_id_fkey FOREIGN KEY (instance_id) REFERENCES public.mkt_coupon_grants(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_redeems
    ADD CONSTRAINT mkt_coupon_redeems_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.mkt_coupon_redeems
    ADD CONSTRAINT mkt_coupon_redeems_property_id_fkey FOREIGN KEY (property_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_triggers
    ADD CONSTRAINT mkt_coupon_triggers_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.mkt_coupons(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupon_triggers
    ADD CONSTRAINT mkt_coupon_triggers_property_id_fkey FOREIGN KEY (property_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_coupons
    ADD CONSTRAINT mkt_coupons_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_customer_notes
    ADD CONSTRAINT mkt_customer_notes_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_customer_notes
    ADD CONSTRAINT mkt_customer_notes_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_guest_wallets
    ADD CONSTRAINT mkt_guest_wallets_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_guest_wallets
    ADD CONSTRAINT mkt_guest_wallets_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_member_levels
    ADD CONSTRAINT mkt_member_levels_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.mkt_stored_value_plans
    ADD CONSTRAINT mkt_stored_value_plans_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.night_audit_exceptions
    ADD CONSTRAINT night_audit_exceptions_audit_log_id_fkey FOREIGN KEY (audit_log_id) REFERENCES public.night_audit_logs(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.night_audit_exceptions
    ADD CONSTRAINT night_audit_exceptions_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.night_audit_logs
    ADD CONSTRAINT night_audit_logs_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.night_audit_logs
    ADD CONSTRAINT night_audit_logs_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.oneid_merge_events
    ADD CONSTRAINT oneid_merge_events_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.oneid_phone_conflicts
    ADD CONSTRAINT oneid_phone_conflicts_bind_ticket_id_fkey FOREIGN KEY (bind_ticket_id) REFERENCES public.wecom_bind_tickets(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.oneid_phone_conflicts
    ADD CONSTRAINT oneid_phone_conflicts_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.oneid_phone_conflicts
    ADD CONSTRAINT oneid_phone_conflicts_resolved_guest_id_fkey FOREIGN KEY (resolved_guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_agreement_id_fkey FOREIGN KEY (agreement_id) REFERENCES public.corp_accounts(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ota_settlements
    ADD CONSTRAINT ota_settlements_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.ota_settlements
    ADD CONSTRAINT ota_settlements_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.ota_settlements
    ADD CONSTRAINT ota_settlements_recon_batch_id_fkey FOREIGN KEY (recon_batch_id) REFERENCES public.recon_batches(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pace_snapshot
    ADD CONSTRAINT pace_snapshot_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pace_snapshot
    ADD CONSTRAINT pace_snapshot_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.parity_alert
    ADD CONSTRAINT parity_alert_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.parity_alert
    ADD CONSTRAINT parity_alert_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_folio_id_fkey FOREIGN KEY (folio_id) REFERENCES public.pms_folios(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_ar_entries
    ADD CONSTRAINT pms_ar_entries_ar_ledger_id_fkey FOREIGN KEY (ar_ledger_id) REFERENCES public.pms_ar_ledgers(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_ar_entries
    ADD CONSTRAINT pms_ar_entries_folio_id_fkey FOREIGN KEY (folio_id) REFERENCES public.pms_folios(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_ar_entries
    ADD CONSTRAINT pms_ar_entries_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_ar_entries
    ADD CONSTRAINT pms_ar_entries_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_ar_ledgers
    ADD CONSTRAINT pms_ar_ledgers_corp_id_fkey FOREIGN KEY (corp_id) REFERENCES public.corp_accounts(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_ar_ledgers
    ADD CONSTRAINT pms_ar_ledgers_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_checkins
    ADD CONSTRAINT pms_checkins_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_checkins
    ADD CONSTRAINT pms_checkins_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_checkins
    ADD CONSTRAINT pms_checkins_master_checkin_id_fkey FOREIGN KEY (master_checkin_id) REFERENCES public.pms_checkins(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_checkins
    ADD CONSTRAINT pms_checkins_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_checkins
    ADD CONSTRAINT pms_checkins_reservation_id_fkey FOREIGN KEY (reservation_id) REFERENCES public.reservations(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_checkins
    ADD CONSTRAINT pms_checkins_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_folio_entries
    ADD CONSTRAINT pms_folio_entries_folio_id_fkey FOREIGN KEY (folio_id) REFERENCES public.pms_folios(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_folio_entries
    ADD CONSTRAINT pms_folio_entries_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_folios
    ADD CONSTRAINT pms_folios_checkin_id_fkey FOREIGN KEY (checkin_id) REFERENCES public.pms_checkins(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_folios
    ADD CONSTRAINT pms_folios_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_folios
    ADD CONSTRAINT pms_folios_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_folios
    ADD CONSTRAINT pms_folios_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_group_room_blocks
    ADD CONSTRAINT pms_group_room_blocks_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_group_room_blocks
    ADD CONSTRAINT pms_group_room_blocks_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_group_room_blocks
    ADD CONSTRAINT pms_group_room_blocks_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_group_room_lines
    ADD CONSTRAINT pms_group_room_lines_checkin_id_fkey FOREIGN KEY (checkin_id) REFERENCES public.pms_checkins(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_group_room_lines
    ADD CONSTRAINT pms_group_room_lines_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_group_room_lines
    ADD CONSTRAINT pms_group_room_lines_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_group_room_lines
    ADD CONSTRAINT pms_group_room_lines_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_group_room_lines
    ADD CONSTRAINT pms_group_room_lines_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_id_doc_audits
    ADD CONSTRAINT pms_id_doc_audits_checkin_id_fkey FOREIGN KEY (checkin_id) REFERENCES public.pms_checkins(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_id_doc_audits
    ADD CONSTRAINT pms_id_doc_audits_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_id_doc_audits
    ADD CONSTRAINT pms_id_doc_audits_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_id_doc_audits
    ADD CONSTRAINT pms_id_doc_audits_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_room_assignments
    ADD CONSTRAINT pms_room_assignments_checkin_id_fkey FOREIGN KEY (checkin_id) REFERENCES public.pms_checkins(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_room_assignments
    ADD CONSTRAINT pms_room_assignments_from_room_id_fkey FOREIGN KEY (from_room_id) REFERENCES public.rooms(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_room_assignments
    ADD CONSTRAINT pms_room_assignments_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_room_assignments
    ADD CONSTRAINT pms_room_assignments_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.pms_room_assignments
    ADD CONSTRAINT pms_room_assignments_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pms_room_assignments
    ADD CONSTRAINT pms_room_assignments_to_room_id_fkey FOREIGN KEY (to_room_id) REFERENCES public.rooms(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.price_suggestions
    ADD CONSTRAINT price_suggestions_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.price_suggestions
    ADD CONSTRAINT price_suggestions_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pricing_assistant_config
    ADD CONSTRAINT pricing_assistant_config_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pricing_decision
    ADD CONSTRAINT pricing_decision_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pricing_effect
    ADD CONSTRAINT pricing_effect_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pricing_recommendation
    ADD CONSTRAINT pricing_recommendation_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.pricing_recommendation
    ADD CONSTRAINT pricing_recommendation_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.profit_insights
    ADD CONSTRAINT profit_insights_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.rate_strategies
    ADD CONSTRAINT rate_strategies_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.recon_batches
    ADD CONSTRAINT recon_batches_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.recon_items
    ADD CONSTRAINT recon_items_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.recon_batches(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.recon_items
    ADD CONSTRAINT recon_items_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.recon_items
    ADD CONSTRAINT recon_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.refund_adjust_audits
    ADD CONSTRAINT refund_adjust_audits_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.refund_adjust_audits
    ADD CONSTRAINT refund_adjust_audits_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES public.refund_adjust_tickets(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.refund_adjust_configs
    ADD CONSTRAINT refund_adjust_configs_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.refund_adjust_tickets
    ADD CONSTRAINT refund_adjust_tickets_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.refund_adjust_tickets
    ADD CONSTRAINT refund_adjust_tickets_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_assigned_by_fkey FOREIGN KEY (assigned_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.restock_items
    ADD CONSTRAINT restock_items_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.restock_items
    ADD CONSTRAINT restock_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.restock_orders(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.restock_items
    ADD CONSTRAINT restock_items_supply_id_fkey FOREIGN KEY (supply_id) REFERENCES public.supplies(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.restock_orders
    ADD CONSTRAINT restock_orders_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.revenue_anomalies
    ADD CONSTRAINT revenue_anomalies_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.risk_alerts
    ADD CONSTRAINT risk_alerts_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.room_inspections
    ADD CONSTRAINT room_inspections_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.room_inspections
    ADD CONSTRAINT room_inspections_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.room_iot_metrics
    ADD CONSTRAINT room_iot_metrics_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.room_night_inventory
    ADD CONSTRAINT room_night_inventory_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.room_night_inventory
    ADD CONSTRAINT room_night_inventory_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.room_night_inventory
    ADD CONSTRAINT room_night_inventory_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.room_status_log
    ADD CONSTRAINT room_status_log_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.room_status_log
    ADD CONSTRAINT room_status_log_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.room_type_base_rate
    ADD CONSTRAINT room_type_base_rate_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.room_type_base_rate
    ADD CONSTRAINT room_type_base_rate_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.room_types
    ADD CONSTRAINT room_types_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES public.room_types(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.segment_members
    ADD CONSTRAINT segment_members_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.segment_members
    ADD CONSTRAINT segment_members_segment_id_fkey FOREIGN KEY (segment_id) REFERENCES public.segments(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.segments
    ADD CONSTRAINT segments_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.service_requests
    ADD CONSTRAINT service_requests_assignee_id_fkey FOREIGN KEY (assignee_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.service_requests
    ADD CONSTRAINT service_requests_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.service_requests
    ADD CONSTRAINT service_requests_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.service_requests
    ADD CONSTRAINT service_requests_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.service_requests
    ADD CONSTRAINT service_requests_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.shift_asset_counts
    ADD CONSTRAINT shift_asset_counts_handover_id_fkey FOREIGN KEY (handover_id) REFERENCES public.shift_handovers(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.shift_asset_counts
    ADD CONSTRAINT shift_asset_counts_supply_id_fkey FOREIGN KEY (supply_id) REFERENCES public.supplies(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.shift_audit_logs
    ADD CONSTRAINT shift_audit_logs_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.shift_audit_logs
    ADD CONSTRAINT shift_audit_logs_handover_id_fkey FOREIGN KEY (handover_id) REFERENCES public.shift_handovers(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.shift_audit_logs
    ADD CONSTRAINT shift_audit_logs_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.shift_float_counts
    ADD CONSTRAINT shift_float_counts_handover_id_fkey FOREIGN KEY (handover_id) REFERENCES public.shift_handovers(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.shift_handover_tasks
    ADD CONSTRAINT shift_handover_tasks_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.shift_handover_tasks
    ADD CONSTRAINT shift_handover_tasks_handover_id_fkey FOREIGN KEY (handover_id) REFERENCES public.shift_handovers(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.shift_handover_tasks
    ADD CONSTRAINT shift_handover_tasks_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.shift_handover_tasks
    ADD CONSTRAINT shift_handover_tasks_linked_order_id_fkey FOREIGN KEY (linked_order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.shift_handover_tasks
    ADD CONSTRAINT shift_handover_tasks_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.shift_handovers
    ADD CONSTRAINT shift_handovers_ai_draft_confirmed_by_fkey FOREIGN KEY (ai_draft_confirmed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.shift_handovers
    ADD CONSTRAINT shift_handovers_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.shift_handovers
    ADD CONSTRAINT shift_handovers_incoming_user_id_fkey FOREIGN KEY (incoming_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.shift_handovers
    ADD CONSTRAINT shift_handovers_manager_user_id_fkey FOREIGN KEY (manager_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.shift_handovers
    ADD CONSTRAINT shift_handovers_outgoing_user_id_fkey FOREIGN KEY (outgoing_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.shift_receive_diffs
    ADD CONSTRAINT shift_receive_diffs_handover_id_fkey FOREIGN KEY (handover_id) REFERENCES public.shift_handovers(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.shift_receive_diffs
    ADD CONSTRAINT shift_receive_diffs_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.shift_receive_diffs
    ADD CONSTRAINT shift_receive_diffs_reporter_user_id_fkey FOREIGN KEY (reporter_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.staff_roster_templates
    ADD CONSTRAINT staff_roster_templates_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.staff_shift_requests
    ADD CONSTRAINT staff_shift_requests_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.staff_shift_requests
    ADD CONSTRAINT staff_shift_requests_swap_user_id_fkey FOREIGN KEY (swap_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.staff_shift_requests
    ADD CONSTRAINT staff_shift_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.staff_shifts
    ADD CONSTRAINT staff_shifts_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.staff_shifts
    ADD CONSTRAINT staff_shifts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.stock_movements
    ADD CONSTRAINT stock_movements_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.stock_movements
    ADD CONSTRAINT stock_movements_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.stock_movements
    ADD CONSTRAINT stock_movements_supply_id_fkey FOREIGN KEY (supply_id) REFERENCES public.supplies(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.supplies
    ADD CONSTRAINT supplies_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.supply_categories(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.supplies
    ADD CONSTRAINT supplies_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.supply_alerts
    ADD CONSTRAINT supply_alerts_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.supply_categories
    ADD CONSTRAINT supply_categories_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.supply_categories
    ADD CONSTRAINT supply_categories_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.supply_categories(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.supply_insights
    ADD CONSTRAINT supply_insights_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.supply_requisitions
    ADD CONSTRAINT supply_requisitions_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.supply_requisitions
    ADD CONSTRAINT supply_requisitions_supply_id_fkey FOREIGN KEY (supply_id) REFERENCES public.supplies(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.tax_filings
    ADD CONSTRAINT tax_filings_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
--

ALTER TABLE ONLY public.venue_bookings
    ADD CONSTRAINT venue_bookings_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.venue_bookings
    ADD CONSTRAINT venue_bookings_venue_id_fkey FOREIGN KEY (venue_id) REFERENCES public.venues(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.venues
    ADD CONSTRAINT venues_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.webhook_event_logs
    ADD CONSTRAINT webhook_event_logs_binding_id_fkey FOREIGN KEY (binding_id) REFERENCES public.hotel_channel_bindings(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.webhook_event_logs
    ADD CONSTRAINT webhook_event_logs_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.webhook_event_logs
    ADD CONSTRAINT webhook_event_logs_lead_id_fkey FOREIGN KEY (lead_id) REFERENCES public.acquisition_leads(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.wecom_bind_tickets
    ADD CONSTRAINT wecom_bind_tickets_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.wecom_bind_tickets
    ADD CONSTRAINT wecom_bind_tickets_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.wecom_callback_events
    ADD CONSTRAINT wecom_callback_events_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.wecom_msg_tasks
    ADD CONSTRAINT wecom_msg_tasks_guest_id_fkey FOREIGN KEY (guest_id) REFERENCES public.guests(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.wecom_msg_tasks
    ADD CONSTRAINT wecom_msg_tasks_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.wx_landing_pages
    ADD CONSTRAINT wx_landing_pages_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.mkt_coupons(id) ON DELETE SET NULL;


--
--

ALTER TABLE ONLY public.wx_landing_pages
    ADD CONSTRAINT wx_landing_pages_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
--

ALTER TABLE ONLY public.wx_landing_pages
    ADD CONSTRAINT wx_landing_pages_published_coupon_id_fkey FOREIGN KEY (published_coupon_id) REFERENCES public.mkt_coupons(id) ON DELETE SET NULL;


--
--


