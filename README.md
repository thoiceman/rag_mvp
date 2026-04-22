# RAG_MVP

一个模块化、可扩展的检索增强生成（RAG）平台，基于 **React + FastAPI** 的前后端分离架构。项目已按照 FastAPI 行业标准结构进行全面重构，核心能力由 LangChain 1.x、LangGraph、Chroma 和 DashScope 驱动。

## 🎯 项目概述

RAG_MVP 采用 **Agentic Workflow** 实现了工具调用（Tool Calling）与知识库检索的深度融合，并引入了**长对话记忆（Memory Service）**与**自动摘要**功能。

本次重构重点：
- **统一配置管理**：基于 `Pydantic Settings` 的配置系统，支持环境变量覆盖。
- **标准化目录结构**：清晰的代码分层（API, Services, Repositories, Models, Schemas）。
- **自动化测试**：建立了基于 `pytest` 的单元测试与集成测试框架。
- **容器化支持**：优化的 `Dockerfile` 与 `docker-compose.yml`，支持健康检查与服务编排。

## 🏗️ 架构设计

本项目采用标准 FastAPI 生产级目录结构：

1.  **API 接入层 ([app/api](file:///Users/thomas/Desktop/rag_mvp/app/api))**
    - 采用版本化路由 (`v1`)，将不同领域拆分为独立的端点模块。
2.  **核心配置层 ([app/core](file:///Users/thomas/Desktop/rag_mvp/app/core))**
    - `config.py`: 统一配置管理。
    - `database.py`: 数据库连接与初始化。
3.  **业务逻辑层 ([app/services](file:///Users/thomas/Desktop/rag_mvp/app/services))**
    - 处理 Agent 编排、流式对话控制、异步记忆处理等。
4.  **仓储层 ([app/repositories](file:///Users/thomas/Desktop/rag_mvp/app/repositories))**
    - 封装底层 **SQLModel** CRUD 操作。
5.  **数据验证层 ([app/schemas](file:///Users/thomas/Desktop/rag_mvp/app/schemas))**
    - 统一管理 Pydantic 模型。
6.  **数据模型层 ([app/models](file:///Users/thomas/Desktop/rag_mvp/app/models))**
    - 数据库实体模型及大模型初始化工厂。
7.  **知识库与工具 ([app/rag](file:///Users/thomas/Desktop/rag_mvp/app/rag) & [app/tools](file:///Users/thomas/Desktop/rag_mvp/app/tools))**
    - 封装 RAG 核心链路及 Agent 扩展工具。

## 🛠️ 技术选型

### 前端技术栈 (web/)
- React 19, TypeScript, Vite, Tailwind CSS

### 后端技术栈 (app/)
- FastAPI, Uvicorn, SQLModel, LangChain 1.x, LangGraph, Chroma, DashScope

## 🚀 快速开始

### 1. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入 DASHSCOPE_API_KEY
```

### 2. 环境准备 (Conda)
```bash
conda env update -n rag_mvp -f environment.yml
conda activate rag_mvp
```

### 3. 运行项目
- **后端**: `python -m app.main` 或 `uvicorn app.main:app --reload`
- **前端**: `cd web && npm install && npm run dev`

### 4. 运行测试
```bash
pytest
```

## 🐳 Docker 部署
```bash
docker-compose up -d --build
```

## 🧩 项目结构
```text
rag_mvp/
├── app/                   # 后端源码
│   ├── api/               # 路由层
│   ├── core/              # 核心配置 (config, database)
│   ├── models/            # 数据库模型
│   ├── schemas/           # Pydantic 模型
│   ├── repositories/      # 仓储层
│   ├── services/          # 业务逻辑
│   ├── rag/               # RAG 逻辑
│   └── main.py            # 入口文件
├── tests/                 # 测试目录
├── web/                   # 前端源码
├── data/                  # 持久化数据
├── Dockerfile.backend     # 后端镜像
└── docker-compose.yml     # 编排文件
```

```bash
docker compose up -d --build
```
数据将持久化在宿主机的 `./data` 目录下。访问 `http://localhost` 即可使用。
