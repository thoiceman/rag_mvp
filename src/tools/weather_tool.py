import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
    api_key = os.getenv("SENIVERSE_API_KEY")
    if not api_key:
        return "天气服务未配置：缺少 SENIVERSE_API_KEY"

    base_url = "https://api.seniverse.com/v3/weather/now.json"
    params = {
        "key": api_key,
        "location": location,
        "language": "zh-Hans",
        "unit": "c",
    }
    url = f"{base_url}?{urlencode(params)}"

    try:
        req = Request(url, headers={"User-Agent": "rag-mvp/1.0"})
        with urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        results = payload.get("results", [])
        if not results:
            return f"暂时无法获取 {location} 的实时天气数据，请稍后再试。"

        location_info = results[0].get("location", {})
        city = location_info.get("name", location)
        now = results[0].get("now", {})
        weather_text = now.get("text", "未知")
        temperature = now.get("temperature", "未知")

        parts = [f"{city}：{weather_text}", f"温度 {temperature}°C"]

        feels_like = now.get("feels_like")
        humidity = now.get("humidity")
        wind_direction = now.get("wind_direction")
        wind_scale = now.get("wind_scale")

        has_extra = False
        if feels_like not in (None, ""):
            parts.append(f"体感 {feels_like}°C")
            has_extra = True
        if humidity not in (None, ""):
            parts.append(f"湿度 {humidity}%")
            has_extra = True
        if wind_direction not in (None, "") or wind_scale not in (None, ""):
            direction = wind_direction or "未知风向"
            scale = f"{wind_scale} 级" if wind_scale not in (None, "") else "风力未知"
            parts.append(f"风向风力 {direction} {scale}")
            has_extra = True

        if not has_extra:
            parts.append("（当前天气接口套餐未返回体感/湿度/风向风力）")

        return "，".join(parts)
    except HTTPError as e:
        return f"天气服务请求失败（HTTP {e.code}）"
    except URLError:
        return "天气服务暂时不可用，请稍后再试。"
    except Exception as e:
        return f"天气服务异常：{str(e)}"
