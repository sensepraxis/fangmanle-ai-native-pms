# 酒店生产版 · 离线部署

**内容：** PostgreSQL + DDL + 系统初始化数据（角色/权限/渠道）  
**不含：** 演示样例客人/订单等业务假数据  

适合发给酒店。服务器上不需要业务源码。

## 目录

```text
hotel/
  docker-compose.yml
  .env.example
  install.sh
  images/           ← pack 后生成 *.tar
  db/               ← pack 后复制 01_ddl + 02_init
  README.md
```

## 本机打包

```powershell
cd E:\Workspace\Ai-Native-PMS\fangmanle-demo
powershell -File deploy\offline\pack.ps1 -Edition hotel
```

产出：`deploy/offline-dist/hotel/`

## 服务器

```bash
cp .env.example .env   # 改密码
bash install.sh
# 或：docker load … && docker compose up -d
```

访问：`http://服务器IP:8000`
