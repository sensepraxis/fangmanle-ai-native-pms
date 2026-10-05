# 演示版 · 离线部署

**内容：** PostgreSQL + DDL + 系统初始化 + **丰满样例业务数据**（客人/订单/房态等）  
适合你自己部署在云服务器上给客户演示。

> Demo 样例数据 SQL 已随仓库提交（`db/postgres/03_demo/010_full_demo_data.sql`），无需导出。  
> 如需重新生成见 `db/postgres/03_demo/refresh_demo.sh`。

## 目录

```text
demo/
  docker-compose.yml
  .env.example
  install.sh
  images/
  db/               ← 含 01_ddl + 02_init + 03_demo
  README.md
```

## 本机打包

```powershell
cd E:\Workspace\Ai-Native-PMS\fangmanle-demo
powershell -File deploy\offline\pack.ps1 -Edition demo
```

产出：`deploy/offline-dist/demo/`

## 服务器

```bash
cp .env.example .env
bash install.sh
```

访问：`http://你的演示服务器IP:8000`
