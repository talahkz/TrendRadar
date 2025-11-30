"""
参数验证工具

提供统一的参数验证功能。
"""

from datetime import datetime
from typing import List, Optional
import os
import yaml

from .errors import InvalidParameterError
from .date_parser import DateParser


def get_supported_platforms() -> List[str]:
    """
    Dynamically get list of supported platforms from config.yaml

    Returns:
        List of platform IDs

    Note:
        - Returns empty list on failure, allowing all platforms (graceful degradation)
        - Platform list comes from config/config.yaml platforms and external_platforms
    """
    try:
        # Get config.yaml path (relative to current file)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, "..", "..", "config", "config.yaml")
        config_path = os.path.normpath(config_path)

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

            # Get newsnow platforms
            platforms = config.get('platforms', [])
            platform_ids = [p['id'] for p in platforms if 'id' in p]

            # Get external platforms (e.g., Reddit)
            external_platforms = config.get('external_platforms', {})
            for platform_id, platform_config in external_platforms.items():
                if platform_config.get('enabled', False):
                    platform_ids.append(platform_id)

            return platform_ids
    except Exception as e:
        # Graceful degradation: return empty list, allow all platforms
        print(f"Warning: Could not load platform config ({config_path}): {e}")
        return []


def validate_platforms(platforms: Optional[List[str]]) -> List[str]:
    """
    Validate platform list

    Args:
        platforms: List of platform IDs, None means use all platforms from config.yaml

    Returns:
        Validated platform list

    Raises:
        InvalidParameterError: Platform not supported

    Note:
        - When platforms=None, returns platform list from config.yaml
        - Validates platform IDs against config.yaml platforms configuration
        - On config load failure, allows all platforms (graceful degradation)
    """
    supported_platforms = get_supported_platforms()

    if platforms is None:
        # Return platform list from config file (user's default config)
        return supported_platforms if supported_platforms else []

    if not isinstance(platforms, list):
        raise InvalidParameterError("platforms parameter must be a list")

    if not platforms:
        # Empty list: return platform list from config file
        return supported_platforms if supported_platforms else []

    # If config load failed (supported_platforms is empty), allow all platforms
    if not supported_platforms:
        print("Warning: Platform config not loaded, skipping platform validation")
        return platforms

    # Validate each platform is in config
    invalid_platforms = [p for p in platforms if p not in supported_platforms]
    if invalid_platforms:
        raise InvalidParameterError(
            f"Unsupported platform(s): {', '.join(invalid_platforms)}",
            suggestion=f"Supported platforms (from config.yaml): {', '.join(supported_platforms)}"
        )

    return platforms


def validate_limit(limit: Optional[int], default: int = 20, max_limit: int = 1000) -> int:
    """
    验证数量限制参数

    Args:
        limit: 限制数量
        default: 默认值
        max_limit: 最大限制

    Returns:
        验证后的限制值

    Raises:
        InvalidParameterError: 参数无效
    """
    if limit is None:
        return default

    if not isinstance(limit, int):
        raise InvalidParameterError("limit 参数必须是整数类型")

    if limit <= 0:
        raise InvalidParameterError("limit 必须大于0")

    if limit > max_limit:
        raise InvalidParameterError(
            f"limit 不能超过 {max_limit}",
            suggestion=f"请使用分页或降低limit值"
        )

    return limit


def validate_date(date_str: str) -> datetime:
    """
    验证日期格式

    Args:
        date_str: 日期字符串 (YYYY-MM-DD)

    Returns:
        datetime对象

    Raises:
        InvalidParameterError: 日期格式错误
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise InvalidParameterError(
            f"日期格式错误: {date_str}",
            suggestion="请使用 YYYY-MM-DD 格式，例如: 2025-10-11"
        )


def validate_date_range(date_range: Optional[dict]) -> Optional[tuple]:
    """
    验证日期范围

    Args:
        date_range: 日期范围字典 {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}

    Returns:
        (start_date, end_date) 元组，或 None

    Raises:
        InvalidParameterError: 日期范围无效
    """
    if date_range is None:
        return None

    if not isinstance(date_range, dict):
        raise InvalidParameterError("date_range 必须是字典类型")

    start_str = date_range.get("start")
    end_str = date_range.get("end")

    if not start_str or not end_str:
        raise InvalidParameterError(
            "date_range 必须包含 start 和 end 字段",
            suggestion='例如: {"start": "2025-10-01", "end": "2025-10-11"}'
        )

    start_date = validate_date(start_str)
    end_date = validate_date(end_str)

    if start_date > end_date:
        raise InvalidParameterError(
            "开始日期不能晚于结束日期",
            suggestion=f"start: {start_str}, end: {end_str}"
        )

    # 检查日期是否在未来
    today = datetime.now().date()
    if start_date.date() > today or end_date.date() > today:
        # 获取可用日期范围提示
        try:
            from ..services.data_service import DataService
            data_service = DataService()
            earliest, latest = data_service.get_available_date_range()

            if earliest and latest:
                available_range = f"{earliest.strftime('%Y-%m-%d')} 至 {latest.strftime('%Y-%m-%d')}"
            else:
                available_range = "无可用数据"
        except Exception:
            available_range = "未知（请检查 output 目录）"

        future_dates = []
        if start_date.date() > today:
            future_dates.append(start_str)
        if end_date.date() > today and end_str != start_str:
            future_dates.append(end_str)

        raise InvalidParameterError(
            f"不允许查询未来日期: {', '.join(future_dates)}（当前日期: {today.strftime('%Y-%m-%d')}）",
            suggestion=f"当前可用数据范围: {available_range}"
        )

    return (start_date, end_date)


def validate_keyword(keyword: str) -> str:
    """
    验证关键词

    Args:
        keyword: 搜索关键词

    Returns:
        处理后的关键词

    Raises:
        InvalidParameterError: 关键词无效
    """
    if not keyword:
        raise InvalidParameterError("keyword 不能为空")

    if not isinstance(keyword, str):
        raise InvalidParameterError("keyword 必须是字符串类型")

    keyword = keyword.strip()

    if not keyword:
        raise InvalidParameterError("keyword 不能为空白字符")

    if len(keyword) > 100:
        raise InvalidParameterError(
            "keyword 长度不能超过100个字符",
            suggestion="请使用更简洁的关键词"
        )

    return keyword


def validate_top_n(top_n: Optional[int], default: int = 10) -> int:
    """
    验证TOP N参数

    Args:
        top_n: TOP N数量
        default: 默认值

    Returns:
        验证后的值

    Raises:
        InvalidParameterError: 参数无效
    """
    return validate_limit(top_n, default=default, max_limit=100)


def validate_mode(mode: Optional[str], valid_modes: List[str], default: str) -> str:
    """
    验证模式参数

    Args:
        mode: 模式字符串
        valid_modes: 有效模式列表
        default: 默认模式

    Returns:
        验证后的模式

    Raises:
        InvalidParameterError: 模式无效
    """
    if mode is None:
        return default

    if not isinstance(mode, str):
        raise InvalidParameterError("mode 必须是字符串类型")

    if mode not in valid_modes:
        raise InvalidParameterError(
            f"无效的模式: {mode}",
            suggestion=f"支持的模式: {', '.join(valid_modes)}"
        )

    return mode


def validate_config_section(section: Optional[str]) -> str:
    """
    验证配置节参数

    Args:
        section: 配置节名称

    Returns:
        验证后的配置节

    Raises:
        InvalidParameterError: 配置节无效
    """
    valid_sections = ["all", "crawler", "push", "keywords", "weights"]
    return validate_mode(section, valid_sections, "all")


def validate_date_query(
    date_query: str,
    allow_future: bool = False,
    max_days_ago: int = 365
) -> datetime:
    """
    验证并解析日期查询字符串

    Args:
        date_query: 日期查询字符串
        allow_future: 是否允许未来日期
        max_days_ago: 允许查询的最大天数

    Returns:
        解析后的datetime对象

    Raises:
        InvalidParameterError: 日期查询无效

    Examples:
        >>> validate_date_query("昨天")
        datetime(2025, 10, 10)
        >>> validate_date_query("2025-10-10")
        datetime(2025, 10, 10)
    """
    if not date_query:
        raise InvalidParameterError(
            "日期查询字符串不能为空",
            suggestion="请提供日期查询，如：今天、昨天、2025-10-10"
        )

    # 使用DateParser解析日期
    parsed_date = DateParser.parse_date_query(date_query)

    # 验证日期不在未来
    if not allow_future:
        DateParser.validate_date_not_future(parsed_date)

    # 验证日期不太久远
    DateParser.validate_date_not_too_old(parsed_date, max_days=max_days_ago)

    return parsed_date

