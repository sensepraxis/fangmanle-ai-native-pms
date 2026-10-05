-- SPDX-License-Identifier: Apache-2.0
-- 渠道主数据目录（无酒店合同/订单）
-- type 取值须符合 channels.type CHECK：ota / douyin / xiaohongshu / direct / agreement / wechat

INSERT INTO channels (code, name, type, commission_rate, is_active) VALUES
    ('ctrip', '携程', 'ota', 0.1200, TRUE),
    ('meituan', '美团酒店', 'ota', 0.1000, TRUE),
    ('fliggy', '飞猪', 'ota', 0.1100, TRUE),
    ('douyin', '抖音团购', 'douyin', 0.0800, TRUE),
    ('xiaohongshu', '小红书', 'xiaohongshu', 0.0600, TRUE),
    ('direct', '散客直订', 'direct', 0.0000, TRUE),
    ('agreement', '协议客户', 'agreement', 0.0500, TRUE),
    ('wechat', '企微私域', 'wechat', 0.0300, TRUE)
ON CONFLICT (code) DO UPDATE
SET
    name = EXCLUDED.name,
    type = EXCLUDED.type,
    commission_rate = EXCLUDED.commission_rate,
    is_active = EXCLUDED.is_active;
