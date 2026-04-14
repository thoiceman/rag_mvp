# RAG_MVP

一个模块化、可扩展的检索增强生成（RAG）平台，基于 **React + FastAPI** 的前后端分离架构。项目已按照 FastAPI 生产级标准重构，核心能力由 LangChain 1.x、LangGraph、Chroma 和 DashScope 驱动，旨在提供一个将检索（RAG）与推理（Agent）相结合的统一系统。

## 🎯 项目概述

RAG_MVP 展示了如何构建一个具备领域知识的智能问答助手。项目通过 **Agentic Workflow** 实现了工具调用（Tool Calling）与知识库检索的深度融合，并引入了**长对话记忆（Memory Service）**与**自动摘要**功能。

本项目的核心目标是：提供一个标准、易读、可扩展的 FastAPI 参考实现，展示如何通过 **Repository 模式** 与 **依赖注入** 实现复杂的 RAG 业务链路。

## 🏗️ 架构设计

本项目采用标准 FastAPI 生产级目录结构，主要包含以下层级：

1.  **API 接入层 (app/api)**
    - 采用版本化路由 (`v1`)，将不同领域（Agents, Files, Chat, Sessions）拆分为独立的端点模块。
2.  **业务逻辑层 (app/services)**
    - 核心业务中枢，处理 Agent 编排、流式对话控制、异步记忆处理等复杂逻辑。
3.  **仓储层 (app/repositories)**
    - 引入 Repository 模式，封装底层 **SQLModel** CRUD 操作，实现业务与数据库的解耦。
4.  **数据验证层 (app/schemas)**
    - 统一管理 Pydantic 模型，负责 API 的入参验证与出参格式化。
5.  **核心配置层 (app/core)**
    - 集中管理数据库连接（同步 Session 池）、应用生命周期（Lifespan）及全局设置。
6.  **数据模型层 (app/models)**
    - 定义数据库实体模型及大模型初始化工厂。
7.  **知识库与工具 (app/rag & app/tools)**
    - 封装 RAG 核心链路（切分、向量化、检索）及 Agent 可用的扩展工具（计算器、天气等）。

## 🛠️ 技术选型

### 前端技术栈 (web/)
- **框架**：React 19, TypeScript, Vite
- **样式**：Tailwind CSS
- **请求库**：Axios, SSE (Server-Sent Events)

### 后端技术栈 (app/)
- **核心框架**：Python 3.11, FastAPI, Uvicorn
- **ORM**：SQLModel (基于 SQLAlchemy)
- **Agent 框架**：LangChain 1.x, LangGraph
- **向量数据库**：Chroma
- **大模型层**：DashScope (通义千问)

## 🖥️ 核心功能模块

1.  **标准 FastAPI 架构**：代码结构清晰，易于维护和二次开发。
2.  **Agent 智能推理**：基于 LangGraph 实现，具备自动判断是否需要调用知识库、计算器或天气工具的能力。
3.  **流式溯源问答**：支持 Server-Sent Events 流式输出，且回答实时附带**参考资料来源**。
4.  **长对话记忆系统**：
    - **向量化记忆**：自动将历史对话向量化并存储，实现跨时空的上下文检索。
    - **自动滚动摘要**：定期对长对话进行摘要压缩，节省 Token 并保持核心语境。
5.  **手动索引控制**：支持文件上传与向量化解耦，用户可自主决定何时构建知识库索引。

## 🚀 快速开始

### 1. 配置环境变量
在根目录下配置 `.env` 文件：
```bash
cp .env.example .env
# 编辑 .env 文件，填入 DASHSCOPE_API_KEY
```

### 2. 启动后端 (Conda)
```bash
conda env update -n rag_mvp -f environment.yml
conda activate rag_mvp

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 启动前端
```bash
cd web
npm install
npm run dev
```

## 🧩 项目结构说明

```text
rag_mvp/
├── app/                   # 后端 Python 源码 (FastAPI)
│   ├── api/               # API 路由层 (v1/endpoints)
│   ├── core/              # 核心配置 (数据库、配置加载)
│   ├── models/            # 数据库模型与模型工厂
│   ├── schemas/           # Pydantic 数据验证模型
│   ├── repositories/      # 仓储层 (CRUD 操作)
│   ├── services/          # 业务逻辑服务层
│   ├── rag/               # RAG 核心逻辑
│   ├── storage/           # 本地持久化抽象
│   └── main.py            # 应用唯一入口
├── web/                   # 前端 React 源码
├── data/                  # 本地持久化数据 (DB, 向量库, 上传文件)
├── docker-compose.yml     # Docker 一键部署配置
└── requirements.txt       # 后端依赖列表
```

## 🐳 Docker 部署

```bash
docker compose up -d --build
```
数据将持久化在宿主机的 `./data` 目录下。访问 `http://localhost` 即可使用。
