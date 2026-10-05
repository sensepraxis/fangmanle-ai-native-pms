-- SPDX-License-Identifier: Apache-2.0
-- =====================================================================
-- 系统配置种子（演示版专属）
-- ---------------------------------------------------------------------
-- 本文件只属于「演示版（demo）」：docker-init.sh 的 03_demo 目录在
--   FML_DB_SKIP_DEMO != 1 时整目录加载；酒店生产版（hotel 模式）会跳过
--   整个 03_demo，因此本文件不会入库 —— 酒店的配置由酒店自己填写。
--
-- 数据来源：与 src/migrations/migrate_finance_params_ext.py /
--   migrate_finance_float_carry.py / migrate_llm.py / infra/map_config.py
--   的默认种子保持一致的「演示值」，便于给客户演示完整功能。
--   LLM / 地图的真实密钥（api_key / tianditu_tk 等）以 __DEMO_FILL__ 占位，
--   部署后在「系统配置」页补填即可。
--
-- 加载顺序：000_prepare(TRUNCATE RESTART IDENTITY) -> 010(业务数据)
--           -> 011(本文件，系统配置) -> setval
-- app_settings 用 UPSERT 覆盖 010 里的中立默认值；finance_* 为幂等 INSERT。
-- =====================================================================

-- ------------------------- 1. 大语言模型配置 -------------------------
-- 多 provider 结构：profiles 存各厂商 base_url/model/api_key，
-- 顶层 provider 为当前激活项（与 ai_core/llm_service.py 的读写约定一致）。
INSERT INTO public.app_settings (key, value_json, updated_at) VALUES (
  'llm',
  '{"enabled": true, "provider": "deepseek", "profiles": {"ollama": {"base_url": "http://127.0.0.1:11434", "model": "qwen3:8b", "api_key": ""}, "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat", "api_key": "__DEMO_FILL_DEEPSEEK_KEY__"}, "siliconflow": {"base_url": "https://api.siliconflow.cn/v1", "model": "Qwen/Qwen3-8B", "api_key": "__DEMO_FILL_SILICONFLOW_KEY__"}, "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus", "api_key": ""}, "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o", "api_key": ""}}, "base_url": "https://api.deepseek.com", "model": "deepseek-chat", "api_key": "__DEMO_FILL_DEEPSEEK_KEY__", "temperature": 0.7, "max_tokens": 2048, "timeout_sec": 120, "system_prompt": "你是房满乐酒店管理系统（PMS）的 AI 助理。请用简洁专业的中文回答酒店运营相关问题；涉及改价、房态、工单、客需、设备维保时给出可执行建议，并标明需人工确认的环节。"}',
  now()
)
ON CONFLICT (key) DO UPDATE SET value_json = EXCLUDED.value_json, updated_at = now();

-- ------------------------- 2. 地图配置（天地图） -------------------------
INSERT INTO public.app_settings (key, value_json, updated_at) VALUES (
  'map',
  '{"enabled": true, "provider": "tianditu", "tianditu_tk": "__DEMO_FILL_TIANDITU_TK__", "tianditu_js_tk": "__DEMO_FILL_TIANDITU_JS_TK__", "amap_web_key": "", "amap_js_key": "", "amap_security_code": ""}',
  now()
)
ON CONFLICT (key) DO UPDATE SET value_json = EXCLUDED.value_json, updated_at = now();

-- ------------------------- 3. 财务 · 门店备用金 -------------------------
INSERT INTO public.finance_float_carry (id, hotel_id, amount, currency, denom_ratios, effective_date, change_reason, old_amount, status, applicant_user_id, finance_approver_user_id, finance_approved_at, manager_approver_user_id, manager_approved_at, rejected_by_user_id, rejected_at, reject_reason, activated_at) VALUES (
  1, 1, 2000.00, 'CNY',
  '[{"denom": 100, "ratio": 0.5, "label": "100 元"}, {"denom": 50, "ratio": 0.25, "label": "50 元"}, {"denom": 20, "ratio": 0.15, "label": "20 元"}, {"denom": 10, "ratio": 0.05, "label": "10 元"}, {"denom": 5, "ratio": 0.025, "label": "5 元"}, {"denom": 1, "ratio": 0.025, "label": "1 元"}, {"denom": 0.5, "ratio": 0.004, "label": "5 角"}, {"denom": 0.1, "ratio": 0.004, "label": "1 角"}]',
  '2026-01-01', '门店开业初始化设置', NULL, 'active',
  NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2026-01-01 09:00:00'
);

-- ------------------------- 4. 财务 · 税率与账期 -------------------------
INSERT INTO public.finance_tax_configs (id, hotel_id, version, taxpayer_type, main_rate, price_mode, tax_code, tax_no, surcharge_note, effective_date, status, change_reason, maintainer_name) VALUES (
  1, 1, 3, '一般纳税人', 0.0600, '价外', '3070401000000000000', '91310101MA1FK****XQ', '城建 7% / 教育 3% / 地方教育 2%', '2026-04-01', 'active', '一般纳税人核定', '财务-周敏'
);

INSERT INTO public.finance_payment_terms (id, hotel_id, customer_type, term_label, description, effective_date, sort_order) VALUES
  (1, 1, '散客', '即付 · 0 天', '结账离店时现金/扫码/刷卡，0 账期', '2026-01-01', 1),
  (2, 1, '会员预付', '现结 · 0 天', '已收款，作为预收负债入账', '2026-01-01', 2),
  (3, 1, 'OTA 携程', 'T+15', '携程代收代付，平台 15 日结款', '2026-01-01', 3),
  (4, 1, 'OTA 美团', 'T+10', '美团代收代付', '2026-01-01', 4),
  (5, 1, 'OTA 飞猪', 'T+15', '飞猪代收代付', '2026-01-01', 5),
  (6, 1, 'OTA 抖音来客', 'T+7', '抖音代收代付', '2026-02-01', 6),
  (7, 1, '企业挂账', '30 天', '协议单位挂账，需在信用与账龄中维护额度', '2026-01-01', 7),
  (8, 1, '旅行社', '15 天', '地接社挂账，账期较短', '2026-01-01', 8);

-- ------------------------- 5. 财务 · 收单费率 -------------------------
INSERT INTO public.finance_acquiring_channels (id, hotel_id, channel_code, channel_name, rate_pct, rate_cap, settle_label, min_settle, withdraw_fee_pct, month_fee, month_gmv, enabled, status_label, sort_order) VALUES
  (1, 1, 'wechat', '微信支付', 0.6000, NULL, 'T+1', 0.01, 0.1000, 684.20, 114033.00, true, '上线', 1),
  (2, 1, 'alipay', '支付宝', 0.6000, NULL, 'T+1', 0.01, 0.1000, 412.36, 68727.00, true, '上线', 2),
  (3, 1, 'unionpay_qr', '银联二维码', 0.3800, NULL, 'T+1', 0.01, 0.0000, 98.40, 25895.00, true, '上线', 3),
  (4, 1, 'pos_debit', '银行卡 POS（借记卡）', 0.5000, 20.00, 'T+1', NULL, 0.0000, 39.60, 7920.00, true, '上线', 4),
  (5, 1, 'pos_credit', '银行卡 POS（贷记卡）', 0.6000, NULL, 'T+1', NULL, 0.0000, 0.00, 0.00, true, '低用量', 5),
  (6, 1, 'unionpay_nfc', '云闪付', NULL, NULL, NULL, NULL, NULL, 0.00, 0.00, false, '未启用', 6);

-- ------------------------- 6. 财务 · 信用与账龄 -------------------------
INSERT INTO public.finance_credit_customers (id, hotel_id, name, customer_type, grade, credit_limit, credit_used, term_label, rated_at, status_label, enabled, sort_order) VALUES
  (1, 1, '中青旅控股', '旅行社', 'A', 100000.00, 64000.00, '15 天', '2026-01-15', '正常', true, 1),
  (2, 1, '某商务旅行社', '旅行社', 'B', 50000.00, 22500.00, '15 天', '2026-02-01', '正常', true, 2),
  (3, 1, '本地科技公司', '企业挂账', 'B', 20000.00, 19500.00, '30 天', '2026-03-10', '超额预警', true, 3),
  (4, 1, '携程商旅', 'OTA', 'A', 50000.00, 28800.00, 'T+15', '2026-01-01', '正常', true, 4),
  (5, 1, '美团商旅', 'OTA', 'A', 30000.00, 15200.00, 'T+10', '2026-01-01', '正常', true, 5),
  (6, 1, '飞猪商旅', 'OTA', 'B', 30000.00, 8400.00, 'T+15', '2026-02-15', '正常', true, 6),
  (7, 1, '某小旅行社', '旅行社', 'C', 10000.00, 3600.00, '15 天', '2026-04-01', '降级观察', true, 7),
  (8, 1, '某问题客户', '企业挂账', 'D', 30000.00, 0.00, '—', '2026-05-10', '停用挂账', false, 8);

INSERT INTO public.finance_bad_debt_rates (id, hotel_id, bucket, bucket_label, rate_pct, description, sort_order) VALUES
  (1, 1, '0-30', '0–30 天', 0.00, '正常账期，不计提', 1),
  (2, 1, '30-60', '30–60 天', 5.00, '轻度逾期风险', 2),
  (3, 1, '60-90', '60–90 天', 20.00, '明显逾期', 3),
  (4, 1, '90+', '90+ 天', 50.00, '高风险，需总经理核销', 4);

-- ------------------------- 7. 财务参数变更审计（演示轨迹） -------------------------
INSERT INTO public.finance_param_audits (id, hotel_id, domain, action_type, target, change_text, reason, effective_date, actor_names, status, created_at) VALUES
  (1, 1, 'tax', '税率', '主营税率', '主营税率 6% → 6%（一般纳税人核定）', '一般纳税人核定', '2026-04-01', '财务-周敏 / 店长-李建国', '已生效', '2026-04-01 10:32:00'),
  (2, 1, 'tax', '初始化', '—', '初始化税率 6% + 8 类客户账期', '门店开业初始化', '2026-01-01', '系统初始化', '已生效', '2026-01-01 09:00:00'),
  (3, 1, 'tax', '账期', 'OTA 抖音来客', 'OTA 抖音来客 → T+7（新增渠道）', '新增渠道', '2026-02-01', '财务-周敏 / 店长-李建国', '已生效', '2026-02-01 09:11:00'),
  (4, 1, 'acquiring', '初始化', '微信支付', '— → 0.60%', '门店开业初始化', '2026-01-01', '财务-周敏', '已生效', '2026-01-01 09:00:00'),
  (5, 1, 'acquiring', '费率调整', '银联二维码', '0.60% → 0.38%', '银联标准类调整', '2026-01-15', '财务-周敏 / 店长-李建国', '已生效', '2026-01-15 14:20:00'),
  (6, 1, 'acquiring', '申请开通', '云闪付', '未启用 → 审核中', '门店支持 NFC 闪付', '2026-03-08', '店长-李建国', '审核中', '2026-03-08 11:00:00'),
  (7, 1, 'credit', '停用', '某问题客户', '正常 → 停用挂账', '多次逾期未回款', '2026-05-10', '销售-王芳 / 财务-周敏 / 总经理-张总', '已停用', '2026-05-10 14:20:00'),
  (8, 1, 'credit', '调额', '某小旅行社', '¥20,000 → ¥10,000', '3 次逾期，降级观察', '2026-04-01', '销售-王芳 / 财务-周敏', '已生效', '2026-04-01 10:00:00'),
  (9, 1, 'credit', '新增', '本地科技公司', '— → ¥20,000', '新增协议客户', '2026-03-10', '销售-王芳 / 财务-周敏 / 总经理-张总', '已生效', '2026-03-10 09:30:00'),
  (10, 1, 'credit', '评级', '中青旅控股', 'B → A 优', '近 6 个月回款 100% 准时', '2026-01-15', '财务-周敏 / 总经理-张总', '已生效', '2026-01-15 10:00:00'),
  (11, 1, 'credit', '初始化', '—', '初始化 4 客户 + 4 档坏账率', '门店开业初始化', '2026-01-01', '系统初始化', '已生效', '2026-01-01 09:00:00');

-- ------------------------- 8. 复位配置表自增序列 -------------------------
-- 000_prepare 已 RESTART IDENTITY，但 010 的 setval 在本文件之前执行，
-- 此处显式把配置表序列对齐到已插入的最大值，避免后续写入主键冲突。
SELECT pg_catalog.setval('public.finance_float_carry_id_seq',   COALESCE((SELECT MAX(id) FROM public.finance_float_carry), 1));
SELECT pg_catalog.setval('public.finance_tax_configs_id_seq',   COALESCE((SELECT MAX(id) FROM public.finance_tax_configs), 1));
SELECT pg_catalog.setval('public.finance_payment_terms_id_seq', COALESCE((SELECT MAX(id) FROM public.finance_payment_terms), 1));
SELECT pg_catalog.setval('public.finance_acquiring_channels_id_seq', COALESCE((SELECT MAX(id) FROM public.finance_acquiring_channels), 1));
SELECT pg_catalog.setval('public.finance_credit_customers_id_seq', COALESCE((SELECT MAX(id) FROM public.finance_credit_customers), 1));
SELECT pg_catalog.setval('public.finance_bad_debt_rates_id_seq', COALESCE((SELECT MAX(id) FROM public.finance_bad_debt_rates), 1));
SELECT pg_catalog.setval('public.finance_param_audits_id_seq',  COALESCE((SELECT MAX(id) FROM public.finance_param_audits), 1));
