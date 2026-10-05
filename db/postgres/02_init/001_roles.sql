-- SPDX-License-Identifier: Apache-2.0
-- 系统角色（无酒店业务数据）
INSERT INTO roles (code, name, description, is_system)
VALUES
    ('admin', '系统管理员', '全权限；用户与角色配置', TRUE),
    ('gm', '店长', '单店经营与审批；可进系统配置（不含用户/RBAC）', TRUE),
    ('rm', '收益经理', '定价、收益与洞察', TRUE),
    ('fd', '前台', '订单、房态与日常接待', TRUE)
ON CONFLICT (code) DO UPDATE
SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    is_system = TRUE;
