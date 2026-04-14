# 技能匹配度评估与项目优化路线图 (Skill Evaluation & Optimization Roadmap)

## 一、 项目现有技术栈与业务模块梳理

### 1. 技术栈全景
- **后端开发**：Python 3.11, FastAPI, Uvicorn
- **AI 与大模型**：LangChain 生态 (Core/Community/Chroma), LangGraph, DashScope (通义千问)
- **数据与存储**：ChromaDB (向量库), 基于本地文件的 JSON 存储 (`JsonStore`), PyMuPDF/python-docx
- **前端交互**：React 19, Vite, TypeScript, Tailwind CSS v4, Axios
- **环境与部署**：Docker, Docker Compose, Nginx (按规范将引入 Conda)

### 2. 核心业务模块
- **Agent 管理**：动态创建、更新带有系统提示词的 Agent。
- **知识库构建**：文档解析、基于 Markdown 标题和字符的双重切片、向量化存储。
- **Agentic Workflow**：支持计算器、天气查询、知识库检索的 ReAct 编排与混合长记忆 RAG。

---

## 二、 技能匹配度评估与缺口分析

基于代码库现状，团队具备快速搭建 LLM 原型应用的能力，但在迈向生产级架构时存在以下**技能缺口**与**技术债务**：

1. **FastAPI 异步编程与契约规范** (缺口)
   - **现象**：`main_api.py` 中遗留了大量 Streamlit 的同步文件代理对象 (`UploadFileProxy`)；接口参数过度依赖 `Form(...)` 和 `dict`，缺少 Pydantic 模型。
   - **风险**：同步操作可能阻塞 FastAPI 的异步事件循环；缺少参数校验会导致运行时错误。
2. **流式输出与并发处理** (缺口)
   - **现象**：`agentic_workflow_service.py` 中使用 `time.sleep(0.01)` 模拟伪流式输出；`index_service.py` 采用 `threading.Thread` + `queue` 结合 `asyncio.sleep` 处理 SSE。
   - **风险**：极高的首字延迟 (TTFT)，以及高并发下的内存泄漏与死锁风险。
3. **持久化与并发事务** (缺口)
   - **现象**：业务数据依赖 `src/storage/json_store.py` 进行文件级原子重命名。
   - **风险**：多进程 (如多 Worker 部署) 下存在严重的数据竞态条件和读写冲突。
4. **Agent 路由编排** (缺口)
   - **现象**：`_direct_tool_route` 中通过硬编码 (`if "天气" in q`) 强制路由工具。
   - **风险**：破坏了 Agent 的泛化能力，后续扩展工具时维护成本极高。

---

## 三、 存在技术债务的优化点 (按优先级排序)

### P0: 移除 Streamlit 适配层与 API 规范化
- **具体技能**：FastAPI, Pydantic 数据建模
- **预期收益**：消除冗余代码，获得 OpenAPI 自动校验与文档支持。
- **风险**：前端可能需要同步调整参数传递方式。

### P1: 真实异步流式输出重构
- **具体技能**：Python Async Generators, LangChain `astream_events`
- **预期收益**：实现真正的 Token 级别流式响应，极大提升前端用户体验。
- **风险**：需要深入理解 LangChain 的异步回调机制。

### P2: 数据库持久化升级
- **具体技能**：SQLAlchemy / SQLModel, SQLite / PostgreSQL
- **预期收益**：彻底解决多线程读写 JSON 带来的数据一致性问题。
- **风险**：需开发数据迁移脚本以保留现有测试数据。

### P3: Agent 动态路由优化
- **具体技能**：LangGraph 状态图高级编排, Semantic Router
- **预期收益**：移除硬编码的 IF-ELSE 路由，实现基于语义的智能工具分发。
- **风险**：可能略微增加工具调用的延迟和 LLM 规划的不可控性。

---

## 四、 技能补强与项目优化路线图 (Actionable Roadmap)

### Phase 1: API 契约化与环境规范化 (优先执行)
- 使用 Conda 统一环境管理 (符合团队偏好)。
- 清理 `main_api.py` 中的 `UploadFileProxy`，直接处理字节流。
- 为 `/agents` 和 `/sessions` 接口引入 Pydantic BaseModel。
- **学习资源**：[FastAPI Pydantic 教程](https://fastapi.tiangolo.com/tutorial/body/)

### Phase 2: 异步重构与流式体验提升
- 重构 `index_service.py`，使用原生 `asyncio.Queue` 替换多线程队列。
- 重写 `agentic_workflow_service.py`，对接大模型的原生异步流 (Async Streaming)。
- **学习资源**：[LangChain Streaming Docs](https://python.langchain.com/docs/concepts/streaming/)

### Phase 3: 存储升级与架构解耦
- 引入 `SQLModel`，建立 Agent、Session 和 File 的关系型数据库表结构。
- 替换硬编码路由，探索 LangGraph 监督机制 (Supervisor) 或 Semantic Router。
- **学习资源**：[SQLModel 官方文档](https://sqlmodel.tiangolo.com/)