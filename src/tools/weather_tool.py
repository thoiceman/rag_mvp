from langchain_core.tools import tool
from pydantic import BaseModel, Field

class GetCurrentWeatherInput(BaseModel):
    location: str = Field(description="城市名称，如 '北京'、'杭州'")

@tool(args_schema=GetCurrentWeatherInput)
def get_current_weather(location: str) -> str:
    """
    获取指定城市的当前实时天气。
    如果用户问到某地的实时天气、温度、气候，请调用此工具。
    """
    # 这是一个 Mock 数据，真实场景可以接入心知天气、和风天气等第三方 API
    mock_data = {
        "北京": "晴，22°C，微风，适合户外活动",
        "杭州": "多云，25°C，适合出行",
        "上海": "小雨，20°C，出门请带伞",
        "深圳": "阴，23°C，空气湿度大"
    }
    
    # 模糊匹配
    for city, weather in mock_data.items():
        if city in location:
            return weather
            
    return f"暂时无法获取 {location} 的实时天气数据，请稍后再试。"
