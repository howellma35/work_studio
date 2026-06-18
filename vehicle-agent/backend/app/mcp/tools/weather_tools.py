"""
MCP 天气工具集
模拟天气查询 API
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("WeatherTools")

# 模拟天气数据库
_weather_db = {
    "上海": {"temp": 26, "condition": "多云", "humidity": 65, "wind": "东南风3级", "aqi": 45},
    "北京": {"temp": 22, "condition": "晴", "humidity": 40, "wind": "北风2级", "aqi": 55},
    "杭州": {"temp": 28, "condition": "小雨", "humidity": 78, "wind": "东风2级", "aqi": 38},
    "苏州": {"temp": 27, "condition": "阴", "humidity": 70, "wind": "东南风3级", "aqi": 42},
}


@mcp.tool()
def get_weather(city: str) -> dict:
    """
    获取指定城市当前天气

    Args:
        city: 城市名称（如"上海"、"北京"）

    Returns:
        天气信息（温度/天气状况/湿度/风力/AQI）
    """
    weather = _weather_db.get(city, {"temp": 25, "condition": "未知", "humidity": 60, "wind": "微风", "aqi": 50})
    return {
        "status": "ok",
        "city": city,
        "current": weather,
        "suggestion": _get_suggestion(weather),
    }


@mcp.tool()
def get_forecast(city: str, days: int = 3) -> dict:
    """
    获取未来几天天气预报

    Args:
        city: 城市名称
        days: 预报天数（1-7）

    Returns:
        多日天气预报
    """
    days = max(1, min(7, days))
    base = _weather_db.get(city, {"temp": 25, "condition": "多云", "humidity": 60, "wind": "微风", "aqi": 50})
    forecast = []
    for i in range(days):
        forecast.append({
            "day": f"第{i + 1}天",
            "temp_high": base["temp"] + (2 if i % 2 == 0 else 0),
            "temp_low": base["temp"] - 5,
            "condition": base["condition"],
            "rain_probability": 30 if "雨" not in base["condition"] else 70,
        })
    return {"status": "ok", "city": city, "days": days, "forecast": forecast}


def _get_suggestion(weather: dict) -> str:
    """根据天气生成出行建议"""
    if "雨" in weather["condition"]:
        return "今日有雨，建议携带雨具，注意行车安全，适当降低车速。"
    if weather["temp"] > 30:
        return "今日气温较高，建议提前开启空调降温，注意防暑。"
    if weather["temp"] < 10:
        return "今日气温较低，建议开启座椅加热和暖风，注意保暖。"
    return "今日天气适宜出行，祝您一路顺风。"
