-- SPDX-License-Identifier: Apache-2.0
-- 四角色默认权限矩阵（与 src/infra/rbac_catalog.py DEFAULT_* 对齐）
-- 幂等：先清系统角色绑定再写入

DELETE FROM role_permissions
WHERE role_id IN (SELECT id FROM roles WHERE code IN ('admin', 'gm', 'rm', 'fd'));

-- admin：全部权限
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'admin';

-- gm：除用户/RBAC 菜单外的全部菜单 + 经营操作
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON (
    (p.kind = 'menu' AND p.code NOT IN ('menu.system.users', 'menu.system.rbac'))
    OR p.code IN (
        'action.orders.write',
        'action.rooms.status',
        'action.rooms.lock_ooo_price',
        'action.rooms.master_write',
        'action.hk.dispatch',
        'action.pricing.accept',
        'action.finance.night_audit',
        'action.finance.refund',
        'action.mkt.coupon_grant',
        'action.pii.reveal'
    )
)
WHERE r.code = 'gm';

-- rm：收益相关
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN (
    'menu.overview.dashboard',
    'menu.overview.pricing',
    'menu.overview.forecast',
    'menu.rooms.inventory',
    'menu.analytics.insights',
    'menu.analytics.profit',
    'menu.analytics.ai',
    'action.pricing.accept'
)
WHERE r.code = 'rm';

-- fd：前台日常
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN (
    'menu.orders.center',
    'menu.orders.booking',
    'menu.orders.assign',
    'menu.orders.checkout',
    'menu.rooms.board',
    'menu.rooms.hk',
    'menu.rooms.assets',
    'menu.crm.directory',
    'menu.crm.cohort',
    'menu.crm.vip',
    'action.orders.write',
    'action.rooms.status'
)
WHERE r.code = 'fd';
