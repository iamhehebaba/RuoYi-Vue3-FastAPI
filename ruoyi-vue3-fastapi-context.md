# RuoYi-Vue3-FastAPI 项目上下文（供 LLM 使用）

## 1. 概览
RuoYi-Vue3-FastAPI 是基于 Vue3 + Element Plus 前端与 FastAPI 后端的快速开发中后台框架，支持 RBAC 权限、代码生成、定时任务等特性，适合快速搭建管理系统。<mcreference link="https://deepwiki.com/insistence/RuoYi-Vue-FastAPI" index="0">0</mcreference> <mcreference link="https://github.com/insistence/RuoYi-Vue3-FastAPI" index="1">1</mcreference>

## 2. 技术栈（核心）
前端：Vue3、Element Plus；后端：FastAPI、SQLAlchemy；数据库：MySQL 或 PostgreSQL；缓存：Redis；认证：OAuth2 + JWT。<mcreference link="https://deepwiki.com/insistence/RuoYi-Vue-FastAPI" index="0">0</mcreference> <mcreference link="https://github.com/insistence/RuoYi-Vue3-FastAPI" index="1">1</mcreference>

## 3. 核心功能（摘要）
用户/角色/菜单/部门/岗位/字典/参数/公告；登录与操作日志；在线用户；定时任务；服务与缓存监控；在线构建器；接口文档；一键代码生成（后端/前端/SQL）。<mcreference link="https://github.com/insistence/RuoYi-Vue3-FastAPI" index="1">1</mcreference>

## 4. 架构要点
分层架构：前端（路由、状态、组件、API 客户端）与后端（控制器、服务、DAO、数据模型）解耦，数据库与 Redis 作为基础设施层支撑。<mcreference link="https://deepwiki.com/insistence/RuoYi-Vue-FastAPI" index="0">0</mcreference>
数据流：前端携带 JWT 发起请求 → 后端鉴权与执行业务 → 优先查 Redis 缓存 → 缓存未命中则查询数据库 → 返回 JSON 响应并按需回填缓存。<mcreference link="https://deepwiki.com/insistence/RuoYi-Vue-FastAPI" index="0">0</mcreference>

## 5. 认证与权限
采用 OAuth2 + JWT 做认证，结合 RBAC（基于角色的访问控制）与菜单/按钮粒度的权限标识，支持多终端访问控制与动态权限菜单。<mcreference link="https://deepwiki.com/insistence/RuoYi-Vue-FastAPI" index="0">0</mcreference> <mcreference link="https://github.com/insistence/RuoYi-Vue3-FastAPI" index="1">1</mcreference>

## 6. 任务调度与代码生成
任务调度：内置基于调度器的定时任务管理（新增/修改/删除/执行日志）。<mcreference link="https://deepwiki.com/insistence/RuoYi-Vue-FastAPI" index="0">0</mcreference>
代码生成：从库表配置生成后端（Python/SQL）与前端（Vue/JS）代码，支持下载，显著提升 CRUD 模块交付效率。<mcreference link="https://github.com/insistence/RuoYi-Vue3-FastAPI" index="1">1</mcreference>

## 7. API 文档
基于 FastAPI 的 OpenAPI 能力，自动生成 Swagger UI / ReDoc 接口文档，支持在线调试与对接。<mcreference link="https://deepwiki.com/insistence/RuoYi-Vue-FastAPI" index="0">0</mcreference>

## 8. 快速开始（摘要）
前端：进入 ruoyi-fastapi-frontend，安装依赖（npm/yarn，建议使用国内镜像），npm run dev 启动。<mcreference link="https://github.com/insistence/RuoYi-Vue3-FastAPI" index="1">1</mcreference>
后端：进入 ruoyi-fastapi-backend，按数据库类型安装 requirements（MySQL 或 PostgreSQL），在 .env.dev 配置数据库与 Redis，导入对应 SQL，执行 python3 app.py --env=dev。<mcreference link="https://github.com/insistence/RuoYi-Vue3-FastAPI" index="1">1</mcreference>
访问：默认账号：admin / 密码：admin123；本地访问 http://localhost:80。<mcreference link="https://github.com/insistence/RuoYi-Vue3-FastAPI" index="1">1</mcreference>

## 9. 部署与构建（摘要）
前端：yarn build:stage 或 build:prod 进行构建；后端：在 .env.prod 配置环境后，python3 app.py --env=prod 运行。<mcreference link="https://github.com/insistence/RuoYi-Vue3-FastAPI" index="1">1</mcreference>

## 10. 许可
项目以 MIT 许可开源，可自由用于个人与商业用途。<mcreference link="https://deepwiki.com/insistence/RuoYi-Vue-FastAPI" index="0">0</mcreference>

## 11. 本地项目结构（与本文档对应）
- 后端目录：/ruoyi-fastapi-backend（包含 app.py、config、module_admin、module_generator、utils、sql 等）
- 前端目录：/ruoyi-fastapi-frontend（包含 src、public、vite.config.js、package.json 等）
- SQL：/ruoyi-fastapi-backend/sql/ 下提供 MySQL 与 PostgreSQL 初始化脚本
- 环境文件：后端 .env.dev / .env.prod；前端 .env.development / .env.staging / .env.production

## 12. 常见约定与实践（便于二次开发）
- 权限标识通常与菜单/按钮绑定，前端路由与服务端接口权限需同步维护
- 新建业务模块优先使用代码生成器产出骨架，再做定制开发
- 长耗时与周期性任务纳入调度器统一管理，并落表记录执行日志
- 数据读性能敏感场景优先利用缓存（Redis）并设计合理失效与回填策略