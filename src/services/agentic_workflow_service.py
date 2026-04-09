from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage
import re

from src.model.factory import get_chat_model
from src.tools.calculator_tool import calculate
from src.tools.weather_tool import get_current_weather
from src.utils.logger import get_logger
from src.rag.rag_service import RagService
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

    def _build_tools(self, agent_id: str):
        def _search_knowledge_base(query: str) -> str:
            try:
                logger.info(f"触发知识库检索工具，检索关键词: {query}")
                result = self.rag_service.ask(agent_id=agent_id, question=query)
                self._last_references = result.get("references", [])
                self._last_hit_count = result.get("hit_count", 0)
                return result["answer"]
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

    def run_agent(self, agent_id: str, question: str, history: list = None) -> str:
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

        tools = self._build_tools(agent_id)
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
                rag_result = self.rag_service.ask(agent_id=agent_id, question=question, history=history or [])
                self._last_references = rag_result.get("references", [])
                self._last_hit_count = rag_result.get("hit_count", 0)
                return rag_result["answer"]
            if "'name'" in err:
                logger.warning("触发消息格式降级：忽略历史消息重试一次")
                try:
                    retry_response = agent_executor.invoke({"messages": [HumanMessage(content=question)]})
                    return retry_response["messages"][-1].content
                except Exception as retry_e:
                    logger.error(f"重试仍失败，降级到 RAG: {retry_e}")
                    rag_result = self.rag_service.ask(agent_id=agent_id, question=question, history=[])
                    self._last_references = rag_result.get("references", [])
                    self._last_hit_count = rag_result.get("hit_count", 0)
                    return rag_result["answer"]
            return f"任务执行出错: {err}"

    def _direct_tool_route(self, question: str) -> str | None:
        q = question.strip()
        need_weather = any(k in q for k in ["天气", "气温", "温度", "下雨", "晴", "阴"])
        need_calc = any(k in q for k in ["计算", "乘以", "乘", "加", "减", "除以", "*", "+", "-", "/"])

        if not need_weather and not need_calc:
            return None

        parts = []

        if need_weather:
            location = next((city for city in self._known_cities if city in q), "北京")
            try:
                weather = get_current_weather.invoke({"location": location})
                parts.append(f"{location}天气：{weather}")
            except Exception as e:
                logger.warning(f"天气工具调用失败: {e}")

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

    def ask(self, agent_id: str, question: str, history: list = None, session_id: str = None) -> dict:
        answer = self.run_agent(agent_id, question, history)
        return {
            "answer": answer,
            "references": self._last_references,
            "hit_count": self._last_hit_count,
        }

    def ask_stream(self, agent_id: str, question: str, history: list = None, session_id: str = None) -> dict:
        answer = self.run_agent(agent_id, question, history)

        def stream_generator():
            import time
            chunk_size = 2
            for i in range(0, len(answer), chunk_size):
                yield answer[i:i+chunk_size]
                time.sleep(0.01)

        return {
            "answer": answer,
            "references": self._last_references,
            "hit_count": self._last_hit_count,
            "stream": stream_generator()
        }
