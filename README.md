# RAG_MVP

一个模块化、可扩展的检索增强生成（RAG）平台，基于 **React + FastAPI** 的前后端分离架构，核心能力由 LangChain 1.x、Chroma 和 DashScope 驱动，旨在提供一个将检索（RAG）与推理（Agent）相结合的统一系统。

## 🎯 项目概述

RAG_MVP 是一个基于 LangChain 和 RAG（检索增强生成）技术构建的最小可行性产品（MVP）。它展示了如何将知识库检索与大模型推理相结合，构建一个具备领域知识的智能问答助手。

本项目的核心目标是：提供一个轻量、易读、可运行的参考实现，帮助开发者快速理解 RAG 的核心链路（包括文档加载、文本切分、向量化、检索和 Prompt 组装），以及如何实现多个智能 Agent 之间的知识库隔离与独立配置。

## 🏗️ 架构设计

本项目采用前后端分离架构，主要包含以下层级：

1. **前端交互层（React + Vite）**
   - 基于 React 19 和 Tailwind CSS 构建的现代 Web UI。
   - 负责 Agent 创建与管理、文件上传、手动触发向量化、会话管理以及流式问答聊天（展示参考资料）。
2. **API 接入层（FastAPI）**
   - 提供 RESTful API 和流式响应（Server-Sent Events）接口供前端调用。
3. **应用服务层（Service）**
   - 负责业务逻辑封装，如 Agent 管理 (`AgentService`)、文件管理 (`FileService`)、向量化流程 (`IndexService`)、检索问答调度 (`ChatService`) 以及会话状态管理 (`SessionService`)。
4. **模型适配层（Model）**
   - 通过统一工厂类对接大语言模型和向量模型，具备良好的扩展性。
5. **知识库层（RAG）**
   - 负责多种格式文档（TXT, PDF, DOCX 等）的加载、文本切分、基于 DashScope 的 Embedding 计算、以及基于 Chroma 向量库的存储与检索。
6. **数据持久化层（Storage）**
   - 负责 Agent 配置、Prompt、文件元数据、向量数据库及会话记录的本地保存（采用 JSON + 本地目录管理，方便快速迭代）。

## 🛠️ 技术选型

### 前端技术栈 (web/)
- **框架**：React 19, TypeScript
- **构建工具**：Vite
- **样式**：Tailwind CSS
- **请求库**：Axios
- **图标**：Lucide React

### 后端技术栈 (src/)
- **核心框架**：Python 3.11, FastAPI, Uvicorn
- **大模型框架**：LangChain 1.x
- **向量数据库**：Chroma (`chromadb`, `langchain-chroma`)
- **文档处理**：`langchain-text-splitters`, `pypdf`, `python-docx`
- **大模型层**：DashScope (阿里通义千问)
  - Embedding：`DashScopeEmbeddings`
  - Chat：`ChatTongyi`

## 🖥️ 核心功能模块

1. **Agent 管理**
   - 创建自定义 Agent，设定领域、描述及系统 Prompt。
   - 每个 Agent 的配置、知识库、对话会话相互隔离。
2. **知识库管理 (RAG)**
   - 支持 TXT、PDF 等格式的知识库文件上传。
   - **手动构建索引**：文件上传与自动向量化解耦，给予用户充分的控制权。随时可查看并管理已向量化的文档。
3. **智能聊天体验**
   - 支持多会话（Session）管理。
   - 采用流式输出（StreamingResponse），提供丝滑的打字机体验。
   - 问答结果附带**参考资料溯源**，增强大模型回答的可解释性和可信度。

## 🚀 快速开始

### 1. 克隆项目与环境准备
```bash
git clone <repository-url>
cd rag_mvp
```

### 2. 配置环境变量
在项目根目录下复制一份环境变量模板并配置您的 DashScope API Key：
```bash
cp .env.example .env
# 编辑 .env 文件，填入 DASHSCOPE_API_KEY
```

### 3. 启动后端 (FastAPI)
推荐使用 Conda 管理虚拟环境：
```bash
# 创建并激活 Conda 虚拟环境 (推荐 Python 3.11)
conda create -n rag_mvp python=3.11 -y
conda activate rag_mvp

# 安装后端依赖
pip install -r requirements.txt

# 启动 FastAPI 服务 (默认运行在 http://localhost:8000)
python -m src.main_api 或者 python -m uvicorn src.main_api:app --reload --host 0.0.0.0 --port 8000
```

### 4. 启动前端 (React)
打开一个新的终端窗口：
```bash
cd web

# 安装前端依赖
npm install

# 启动开发服务器 (默认运行在 http://localhost:5173)
npm run dev
```

在浏览器中访问 `http://localhost:5173` 即可体验平台。

## 🧩 项目结构说明

```text
rag_mvp/
├── data/                  # 本地数据存储 (Agent配置、日志、会话、文件、Chroma向量库)
├── src/                   # 后端 Python 源码
│   ├── config/            # 配置文件
│   ├── model/             # 模型初始化工厂
│   ├── prompts/           # 预设系统提示词
│   ├── rag/               # RAG核心逻辑 (文档加载、切分、向量化、检索)
│   ├── services/          # 业务逻辑服务层
│   ├── storage/           # 本地存储操作封装
│   ├── utils/             # 工具类 (日志、ID生成等)
│   └── main_api.py        # FastAPI 应用入口
├── web/                   # 前端 React 源码
│   ├── src/               # 前端组件、API调用与样式
│   ├── package.json       # 前端依赖配置
│   └── vite.config.ts     # Vite 构建配置
├── requirements.txt       # 后端依赖列表
└── README.md              # 项目文档
```
