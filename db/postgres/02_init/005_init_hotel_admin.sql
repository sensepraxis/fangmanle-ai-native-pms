-- SPDX-License-Identifier: Apache-2.0
-- 005_init_hotel_admin.sql
-- 酒店模式（hotel）与演示模式（demo）共用的初始管理员数据。
--
-- 幂等设计：
--   · hotels 用 WHERE NOT EXISTS 防重复（主键 id=1 可能被 03_demo 覆盖，但本行是兜底）
--   · users 用 ON CONFLICT(username) DO NOTHING（demo 模式后续 03_demo 会插入同名 admin，
--     本行静默跳过；hotel 模式则由本行提供唯一的管理员入口）
--
-- 密码算法：SHA-256（与 infra.auth_local.hash_password 一致）
--   admin123 → 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9

-- ① 默认酒店（id=1，单酒店部署的"本店"）
INSERT INTO public.hotels (id, code, name, timezone, currency, star_rating, is_active)
SELECT 1, 'LOCAL', '本店（请在系统设置中完善酒店信息）', 'Asia/Shanghai', 'CNY', 4, TRUE
WHERE NOT EXISTS (SELECT 1 FROM public.hotels WHERE id = 1);

-- ② 管理员账号 admin / admin123
INSERT INTO public.users (hotel_id, role_id, username, password_hash, full_name, is_active)
SELECT
  1,
  (SELECT id FROM public.roles WHERE code = 'admin' LIMIT 1),
  'admin',
  '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
  '系统管理员',
  TRUE
ON CONFLICT (username) DO NOTHING;
