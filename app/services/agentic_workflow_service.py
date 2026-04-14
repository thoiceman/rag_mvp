from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage
import re

from app.models.factory import get_chat_model
from app.tools.calculator_tool import calculate
from app.tools.weather_tool import get_current_weather
from app.utils.logger import get_logger
from app.rag.rag_service import RagService
from pydantic import BaseModel, Field

logger = get_logger("AgenticWorkflowService")


class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(description='你要检索的关键词或完整问题，例如"公司报销额度是多少？"')

class AgenticWorkflowService:
    def __init__(self):
        self.llm = get_chat_model()
        self.rag_service = RagService()
        self._last_references = []
        self._last_hit_count = 0

        system_msg = '''你是一个智能助理。你的核心任务是决定是否需要使用外部工具来完成任务。
你可以使用的工具包括：
1. get_current_weather: 用于查询指定城市的实时天气。
2. calculate: 用于执行精确的数学计算。
3. search_knowledge_base: 用于检索专属的内部知识库。

【严格规则】：
- 如果用户问天气，必须调用 get_current_weather。
- 如果用户要求计算，必须调用 calculate。
- 如果用户询问专有知识或历史人物（如某人是谁），必须调用 search_knowledge_base。
- 输出工具参数时，必须生成合法的 JSON 格式。
'''
        self.system_msg = system_msg
        self._known_cities = ["北京", "上海", "杭州", "深圳"]

    def _extract_cities(self, text: str) -> list[str]:
        """按出现顺序提取问题中的城市，去重后返回。"""
        hits: list[tuple[int, str]] = []
        for city in self._known_cities:
            idx = text.find(city)
            if idx != -1:
                hits.append((idx, city))
        hits.sort(key=lambda x: x[0])
        seen = set()
        ordered = []
        for _, city in hits:
            if city not in seen:
                seen.add(city)
                ordered.append(city)
        return ordered

    def _build_tools(self, db, agent_id: str):
        def _search_knowledge_base(query: str) -> str:
            try:
                logger.info(f"触发知识库检索工具，检索关键词: {query}")
                result = self.rag_service.ask(db, agent_id=agent_id, question=query)
                # 使用 extend 原地更新列表内容，而不是重新赋值引用
                self._last_references.clear()
                self._last_references.extend(result.get("references", []))
                self._last_hit_count = result.get("hit_count", 0)
                
                # 为了防止 Agent 收到太长的回复后直接原封不动地复读，
                # 我们可以在这里指示大模型进行提炼，而不是直接把原文扔回去。
                ans = result["answer"]
                return f"【知识库检索结果】\n{ans}\n\n请根据上述信息，用你自己的话向用户进行自然流畅的回复，不要直接复制粘贴上文。"
            except Exception as e:
                logger.error(f"检索知识库失败: {e}")
                return f"检索知识库失败: {str(e)}"

        kb_tool = StructuredTool.from_function(
            func=_search_knowledge_base,
            name="search_knowledge_base",
            description="检索专属内部知识库，适用于人物、制度、业务资料问答",
            args_schema=SearchKnowledgeBaseInput,
        )
        return [calculate, get_current_weather, kb_tool]

    def run_agent(self, db, agent_id: str, question: str, history: list = None) -> str:
        """
        运行完整的 Agentic Workflow
        """
        logger.info(f"启动 Agentic Workflow 解决问题: {question}")
        self._last_references = []
        self._last_hit_count = 0

        # 先做确定性路由，避免模型在复合意图下漏掉工具调用
        direct_answer = self._direct_tool_route(question)
        if direct_answer:
            return direct_answer

        tools = self._build_tools(db, agent_id)
        agent_executor = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=self.system_msg,
        )

        chat_history = []
        if history:
            for msg in history[-5:]:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    chat_history.append(HumanMessage(content=content))
                elif role == "assistant":
                    chat_history.append(AIMessage(content=content))

        chat_history.append(HumanMessage(content=question))

        try:
            response = agent_executor.invoke({"messages": chat_history})
            return response["messages"][-1].content
        except Exception as e:
            err = str(e)
            logger.error(f"Agentic Workflow 执行失败: {e}")
            # Qwen 在 Function Calling 参数格式异常时，降级到直接 RAG，保证可用性
            if "function.arguments" in err and "JSON format" in err:
                logger.warning("触发 Function Calling 降级：改走直接 RAG 问答")
                rag_result = self.rag_service.ask(db, agent_id=agent_id, question=question, history=history or [])
                self._last_references.clear()
                self._last_references.extend(rag_result.get("references", []))
                self._last_hit_count = rag_result.get("hit_count", 0)
                return rag_result["answer"]
            if "'name'" in err:
                logger.warning("触发消息格式降级：忽略历史消息重试一次")
                try:
                    retry_response = agent_executor.invoke({"messages": [HumanMessage(content=question)]})
                    return retry_response["messages"][-1].content
                except Exception as retry_e:
                    logger.error(f"重试仍失败，降级到 RAG: {retry_e}")
                    rag_result = self.rag_service.ask(db, agent_id=agent_id, question=question, history=[])
                    self._last_references.clear()
                    self._last_references.extend(rag_result.get("references", []))
                    self._last_hit_count = rag_result.get("hit_count", 0)
                    return rag_result["answer"]
            return f"任务执行出错: {err}"

    async def run_agent_stream(self, db, agent_id: str, question: str, history: list = None):
        """
        运行完整的 Agentic Workflow 并返回异步流
        """
        logger.info(f"启动 Agentic Workflow 流式解决问题: {question}")
        self._last_references = []
        self._last_hit_count = 0

        # 先做确定性路由，避免模型在复合意图下漏掉工具调用
        direct_answer = self._direct_tool_route(question)
        if direct_answer:
            # 如果是确定性路由，直接生成一个模拟的异步流
            async def direct_stream():
                chunk_size = 2
                for i in range(0, len(direct_answer), chunk_size):
                    yield direct_answer[i:i+chunk_size]
            return direct_stream()

        tools = self._build_tools(db, agent_id)
        agent_executor = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=self.system_msg,
        )

        chat_history = []
        if history:
            for msg in history[-5:]:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    chat_history.append(HumanMessage(content=content))
                elif role == "assistant":
                    chat_history.append(AIMessage(content=content))

        chat_history.append(HumanMessage(content=question))

        async def generate_stream():
            try:
                # 使用 astream_events 获取底层的流式事件
                # version="v2" 是 LangChain 推荐的事件版本
                # 追踪是否已经产生了任何输出
                has_output = False
                
                # 记录已经输出的内容，防止极短时间内的重复片段（针对某些模型的重复输出特性）
                yielded_content = ""
                
                # 我们需要缓存当前阶段的大模型输出
                # 如果这个输出最后触发了工具调用，我们就把它当成“思考过程”丢弃掉。
                # 只有在确信没有工具调用时（大模型真正返回最终结果），我们才把这部分输出给前端。
                # 但流式要求实时性，所以我们不能一直等，这是一个折中：
                # 我们先存下流，如果在某个时间点发现了 tool_calls，我们通过抛出一个特殊字符（或者前端过滤）来清理，
                # 但这里更优雅的做法是：一旦模型在调用工具之前输出了内容，在工具调用之后它会再次生成一段最终回复。
                # 由于这会导致前端看到两段重复，我们在发送给前端的文本流中，加上基于事件边界的控制。
                
                # 标记当前是否处于最后一步（非工具调用的一步）
                # 在 react agent 中，只有工具调用结束后，或者不需要工具调用时，才会产生最终的 agent 节点事件
                current_run_id = None
                
                async for event in agent_executor.astream_events(
                    {"messages": chat_history}, 
                    version="v2"
                ):
                    # 【核心修复】只处理来自顶层 agent 节点的流式事件
                    # 这样可以完全屏蔽掉工具内部（如 RAG 链）产生的任何流式输出
                    if event.get("metadata", {}).get("langgraph_node") != "agent":
                        continue

                    # 优先捕捉大模型的流式输出事件
                    if event["event"] in ["on_chat_model_stream", "on_llm_stream"]:
                        # 检查 tags 中是否有 'langsmith:hidden'，如果有说明是内部步骤，不应该输出
                        tags = event.get("tags", [])
                        if "langsmith:hidden" in tags:
                            continue
                            
                        chunk = event["data"].get("chunk")
                        if chunk:
                            # 判断是否带有 tool_calls 或 tool_call_chunks
                            has_tool_calls = False
                            if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                                has_tool_calls = True
                            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                                has_tool_calls = True
                            if isinstance(chunk, dict) and (chunk.get("tool_call_chunks") or chunk.get("tool_calls")):
                                has_tool_calls = True
                                
                            # 带有工具调用的流是思考过程，拦截之
                            if has_tool_calls:
                                continue
                                
                            # 提取内容
                            if hasattr(chunk, "content"):
                                content = chunk.content
                            elif isinstance(chunk, dict):
                                content = chunk.get("content", "")
                            else:
                                content = str(chunk)
                                
                            if content:
                                has_output = True
                                yielded_content += content
                                yield content
                
                # 如果整个流程结束都没有任何流式输出，尝试获取最后的消息内容作为兜底
                if not has_output:
                    logger.warning("流式输出为空，尝试获取最终 invoke 结果")
                    rag_result = self.rag_service.ask(db, agent_id=agent_id, question=question, history=history or [])
                    self._last_references.clear()
                    self._last_references.extend(rag_result.get("references", []))
                    self._last_hit_count = rag_result.get("hit_count", 0)
                    yield rag_result["answer"]
                            
            except Exception as e:
                err = str(e)
                logger.error(f"Agentic Workflow 流式执行失败: {e}")
                # 降级处理：退回到 RAG
                yield f"\n[系统提示：Agent 执行异常，降级为普通问答 ({err})]\n"
                
                try:
                    # 获取 RAG 结果
                    rag_result = self.rag_service.ask(db, agent_id=agent_id, question=question, history=history or [])
                    self._last_references.clear()
                    self._last_references.extend(rag_result.get("references", []))
                    self._last_hit_count = rag_result.get("hit_count", 0)
                    yield rag_result["answer"]
                except Exception as rag_err:
                    yield f"降级问答也失败了: {str(rag_err)}"

        return generate_stream()

    def _direct_tool_route(self, question: str) -> str | None:
        q = question.strip()
        need_weather = any(k in q for k in ["天气", "气温", "温度", "下雨", "晴", "阴"])
        need_calc = any(k in q for k in ["计算", "乘以", "乘", "加", "减", "除以", "*", "+", "-", "/"])

        if not need_weather and not need_calc:
            return None

        parts = []

        if need_weather:
            locations = self._extract_cities(q) or ["北京"]
            for location in locations:
                try:
                    weather = get_current_weather.invoke({"location": location})
                    parts.append(f"{location}天气：{weather}")
                except Exception as e:
                    logger.warning(f"天气工具调用失败({location}): {e}")

        if need_calc:
            expr = self._extract_expression(q)
            if expr:
                try:
                    calc_result = calculate.invoke({"expression": expr})
                    parts.append(f"计算结果（{expr}）：{calc_result}")
                except Exception as e:
                    logger.warning(f"计算工具调用失败: {e}")

        if parts:
            logger.info("命中确定性路由，已直接调用工具")
            return "\n".join(parts)
        return None

    def _extract_expression(self, text: str) -> str | None:
        normalized = text.replace("×", "*").replace("x", "*").replace("X", "*")
        m = re.search(r"(\d+(?:\.\d+)?)\s*(乘以|乘|\*)\s*(\d+(?:\.\d+)?)", normalized)
        if m:
            return f"{m.group(1)}*{m.group(3)}"
        m = re.search(r"(\d+(?:\.\d+)?)\s*(加|\+)\s*(\d+(?:\.\d+)?)", normalized)
        if m:
            return f"{m.group(1)}+{m.group(3)}"
        m = re.search(r"(\d+(?:\.\d+)?)\s*(减|-)\s*(\d+(?:\.\d+)?)", normalized)
        if m:
            return f"{m.group(1)}-{m.group(3)}"
        m = re.search(r"(\d+(?:\.\d+)?)\s*(除以|/)\s*(\d+(?:\.\d+)?)", normalized)
        if m:
            return f"{m.group(1)}/{m.group(3)}"
        return None

    def ask(self, db, agent_id: str, question: str, history: list = None, session_id: str = None) -> dict:
        answer = self.run_agent(db, agent_id, question, history)
        return {
            "answer": answer,
            "references": self._last_references,
            "hit_count": self._last_hit_count,
        }

    async def ask_stream(self, db, agent_id: str, question: str, history: list = None, session_id: str = None) -> dict:
        stream_generator = await self.run_agent_stream(db, agent_id, question, history)

        return {
            # 因为流是异步生成的，所以这里无法提前知道完整的 answer
            "answer": "",
            "references": self._last_references,
            "hit_count": self._last_hit_count,
            "stream": stream_generator
        }
