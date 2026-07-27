# -*- coding: utf-8 -*-
"""
响星 - 提示词撰写模块
按预选模版格式填空生成提示词，支持LLM智能拆解
"""

import json
import os
import re
import config
from modules import llm_client
from modules import memory as mem


def load_prompt_templates() -> dict:
    """加载提示词模版库"""
    path = os.path.join(config.KNOWLEDGE_BASE_DIR, "prompt_templates.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_template(template_name: str) -> dict:
    """根据名称获取模版"""
    templates_data = load_prompt_templates()
    templates = templates_data.get("模版列表", [])

    for t in templates:
        if t["名称"] == template_name:
            return t

    # 找不到就返回第一个
    return templates[0] if templates else {}


def fill_template_smart(template: dict, shot: dict, ai_play: str) -> tuple:
    """
    智能填空：调用LLM将画面描述拆解为模版各占位符的具体内容
    返回 (填空后的提示词, 是否使用了LLM)
    """
    template_str = template.get("模版", "")
    placeholders = re.findall(r'\[([^\]]+)\]', template_str)

    if not placeholders:
        return template_str, False

    # 调用LLM拆解
    llm_result = llm_client.chat_prompt_decompose(
        shot_desc=shot.get("画面描述", ""),
        shot_subtitle=shot.get("文字字幕", ""),
        template_str=template_str,
        ai_play=ai_play
    )

    # 解析LLM返回的JSON
    field_values = _parse_decompose_json(llm_result)

    # 填充模版
    filled = template_str
    used_llm = False
    for ph in placeholders:
        if ph in field_values and field_values[ph].strip():
            filled = filled.replace(f"[{ph}]", field_values[ph])
            used_llm = True
        else:
            # LLM未能填充的占位符，用默认值
            filled = filled.replace(f"[{ph}]", _default_value(ph, shot))

    # 追加负面提示词
    negative = template.get("负面提示词位置", "")
    if negative:
        filled += "，" + negative.replace("末尾追加：", "")

    return filled, used_llm


def fill_template_simple(template: dict, shot: dict) -> str:
    """
    简单填空：不调用LLM，用规则匹配填充（降级方案）
    """
    template_str = template.get("模版", "")
    placeholders = re.findall(r'\[([^\]]+)\]', template_str)

    filled = template_str
    for ph in placeholders:
        filled = filled.replace(f"[{ph}]", _default_value(ph, shot))

    negative = template.get("负面提示词位置", "")
    if negative:
        filled += "，" + negative.replace("末尾追加：", "")

    return filled


def _default_value(placeholder: str, shot: dict) -> str:
    """占位符默认值映射"""
    defaults = {
        "风格描述": shot.get("画面描述", "")[:15],
        "精确风格": shot.get("画面描述", "")[:10],
        "主体内容": shot.get("画面描述", ""),
        "主体内容与动作": shot.get("画面描述", ""),
        "主体动作与姿态": shot.get("画面描述", ""),
        "具体场景与构图": "居中构图",
        "色彩与光影": "暖色调柔光",
        "氛围关键词": shot.get("文字字幕", "温暖治愈"),
        "氛围与色彩": shot.get("文字字幕", "温暖治愈"),
        "画面比例": "9:16竖屏",
    }
    return defaults.get(placeholder, shot.get("画面描述", ""))


def _parse_decompose_json(llm_result: str) -> dict:
    """解析LLM返回的占位符键值对JSON"""
    try:
        result = json.loads(llm_result)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # 尝试提取JSON块
    json_match = re.search(r'\{[\s\S]*\}', llm_result)
    if json_match:
        try:
            result = json.loads(json_match.group())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return {}


def check_pitfall(prompt: str, theme: str) -> list:
    """暗礁校验：检查提示词是否命中避雷规则"""
    warnings = []
    pitfall_path = os.path.join(config.KNOWLEDGE_BASE_DIR, "pitfall_rules.json")

    with open(pitfall_path, "r", encoding="utf-8") as f:
        pitfall_data = json.load(f)

    rules = pitfall_data.get("规则列表", [])
    for rule in rules:
        keywords = rule.get("关键词", [])
        for kw in keywords:
            if kw.lower() in prompt.lower():
                warnings.append(f"[暗礁警告] 该方向可能触发审核问题：{rule.get('审核反馈', '未知原因')}")

    return warnings


def write_prompts(storyboard: list, template_name: str, theme: str,
                  ai_play: str = "", use_smart_fill: bool = True) -> list:
    """为每个镜头生成提示词"""
    template = get_template(template_name)
    prompts = []

    print("\n" + "=" * 60)
    print("  提示词")
    print("=" * 60)

    for shot in storyboard:
        if use_smart_fill and ai_play:
            prompt, used_llm = fill_template_smart(template, shot, ai_play)
            method = "LLM智能填充" if used_llm else "规则填充（降级）"
        else:
            prompt = fill_template_simple(template, shot)
            method = "规则填充"

        warnings = check_pitfall(prompt, theme)

        print(f"\n  镜头 {shot['镜头编号']}（{method}）：")
        print(f"    {prompt}")
        if warnings:
            for w in warnings:
                print(f"    {w}")

        prompts.append({
            "镜头编号": shot["镜头编号"],
            "提示词": prompt,
            "暗礁警告": warnings
        })

    # 更新模版使用统计
    mem.update_template_usage(template_name)

    return prompts
