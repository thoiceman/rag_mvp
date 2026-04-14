import ast
import operator as op

from langchain_core.tools import tool
from pydantic import BaseModel, Field

class CalculateInput(BaseModel):
    expression: str = Field(description="一个数学表达式字符串，例如 '123 * 45' 或 '(10 + 20) / 2'")


_ALLOWED_BINARY_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.FloorDiv: op.floordiv,
}

_ALLOWED_UNARY_OPS = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}


def _safe_eval_math(expression: str) -> float | int:
    """仅支持数学表达式，禁止变量、函数调用、属性访问等危险语法。"""
    tree = ast.parse(expression, mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINARY_OPS:
            return _ALLOWED_BINARY_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPS:
            return _ALLOWED_UNARY_OPS[type(node.op)](_eval(node.operand))
        raise ValueError("仅支持数字与 + - * / % // ** () 运算")

    return _eval(tree)


@tool(args_schema=CalculateInput)
def calculate(expression: str) -> str:
    """
    用于执行精确的数学计算。
    当你需要进行加、减、乘、除、求余等数学运算时，必须调用此工具，不要自己猜测结果。
    """
    try:
        result = _safe_eval_math(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {str(e)}"
