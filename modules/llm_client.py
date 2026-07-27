# -*- coding: utf-8 -*-
"""
响星 - LLM API调用模块
通过DeepSeek API与LLM交互
"""

import json
from openai import OpenAI
import config


def get_client():
    """获取OpenAI兼容客户端（DeepSeek）"""
    return OpenAI(
        api_key=config.API_KEY,
        base_url=config.API_BASE
    )


def chat(prompt: str, system_prompt: str = "") -> str:
    """
    调用LLM生成回复

    Args:
        prompt: 用户输入的prompt
        system_prompt: 系统提示词（可选）

    Returns:
        LLM生成的文本
    """
    client = get_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=messages,
            temperature=0.8,  # 偏高温度保证创意性
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[API调用失败] {str(e)}"


def chat_with_dimensions(theme: str, dimensions: list, ai_play: str,
                         target_audience: str, anti_anchor_hint: str = "") -> str:
    """
    星图模式专用：按维度生成联想链

    Args:
        theme: 主题（如"心情"）
        dimensions: 维度列表
        ai_play: AI玩法描述
        target_audience: 目标人群
        anti_anchor_hint: 反锚定提示（如AI玩法中的举例仅为风格参考）

    Returns:
        LLM生成的联想链文本
    """
    dimension_text = "\n".join([f"- {d}" for d in dimensions])

    prompt = f"""请围绕【{theme}】主题，从以下维度各生成一条联想链。

可用维度：
{dimension_text}

AI玩法：{ai_play}
目标人群：{target_audience}

要求：
1. 每个维度独立发散，不要互相重复
2. {anti_anchor_hint if anti_anchor_hint else "AI玩法中的举例仅为风格参考，请勿围绕该举例发散"}
3. 联想链格式：主题 → 中间关键词 → 具体意象/表达
4. 每条联想链方向尽量差异明显

请按以下格式输出每个维度的联想链："""

    system_prompt = "你是一个AI彩铃策划助手，擅长从多元文化维度发散联想。你的联想必须具体、有画面感、可转化为视觉表达。"

    return chat(prompt, system_prompt)


def chat_free_creation(theme: str, member_framework: str, ai_play: str,
                       target_audience: str) -> str:
    """
    引星模式专用：按成员提供的框架填充文化知识

    Args:
        theme: 主题
        member_framework: 成员输入的联想框架
        ai_play: AI玩法描述
        target_audience: 目标人群

    Returns:
        LLM填充后的联想链
    """
    prompt = f"""团队成员提供了以下联想框架，请根据这个框架填充具体的文化知识和意象。

主题：{theme}
成员框架：{member_framework}
AI玩法：{ai_play}
目标人群：{target_audience}

要求：
1. 严格按照成员的框架方向填充，不改变框架方向
2. 填充的内容要具体、有画面感
3. 可以引用相关的诗词、典故、哲学观点等文化知识
4. 最终输出格式：主题 → 中间关键词 → 具体意象/表达"""

    system_prompt = "你是一个AI彩铃策划助手，擅长根据成员提供的框架填充文化知识。你尊重成员的创作方向，只补充不改变。"

    return chat(prompt, system_prompt)


def chat_meteor(theme: str, dimensions: list, seed_context: str,
                ai_play: str, target_audience: str) -> str:
    """
    流星模式专用：星火种子+随机维度+自由发散

    Args:
        theme: 主题
        dimensions: 随机抽取的维度列表（含冷门维度）
        seed_context: 星火上下文（天气/心情/森林or海边/随机词/日期）
        ai_play: AI玩法描述
        target_audience: 目标人群

    Returns:
        LLM生成的联想链
    """
    dimension_text = "\n".join([f"- {d}" for d in dimensions])

    prompt = f"""请围绕【{theme}】主题，从以下维度生成联想链，同时让灵感种子的氛围自然渗透进联想方向。

灵感种子（当前氛围）：{seed_context}

可用维度：
{dimension_text}

AI玩法：{ai_play}
目标人群：{target_audience}

要求：
1. 每个维度独立发散，方向尽量差异明显
2. 灵感种子的信息不要直接出现在结果中，而是转化为意境和氛围
3. 联想链格式：主题 → 中间关键词 → 具体意象/表达

请先按以上维度各生成一条联想链，最后额外生成一条完全自由的联想链（不限定任何维度，自由发散）。"""

    system_prompt = "你是一个AI彩铃策划助手，擅长在氛围引导下自由联想。你的联想有画面感、有意境、可转化为视觉表达。"

    return chat(prompt, system_prompt)


def chat_storyboard(inspiration: str, template_structure: list,
                     ai_play: str, target_audience: str) -> str:
    """
    根据灵感结果和分镜结构，调用LLM为每个镜头生成画面描述和字幕

    Args:
        inspiration: 灵感结果文本
        template_structure: 分镜结构列表，每项包含"镜头编号"、"功能"、"时长"
        ai_play: AI玩法描述
        target_audience: 目标人群

    Returns:
        LLM生成的分镜描述（JSON格式字符串）
    """
    shot_list = "\n".join([
        f"  镜头{s['镜头编号']}：{s['功能']}，时长{s['时长']}"
        for s in template_structure
    ])

    prompt = f"""请根据以下灵感和分镜结构，为每个镜头生成具体的画面描述和文字字幕。

【灵感方向】
{inspiration}

【AI玩法】
{ai_play}

【目标人群】
{target_audience}

【分镜结构】
{shot_list}

要求：
1. 画面描述要具体、有画面感，可直接用于AI视频生成提示词
2. 文字字幕要简短有感染力（5-12字），与画面配合
3. 各镜头之间要有叙事递进关系，不是独立片段
4. 画面风格与AI玩法描述一致
5. 画面描述控制在30字以内，字幕控制在12字以内

请严格按照以下JSON格式输出（不要加任何其他文字）：
[
  {{"镜头编号": 1, "画面描述": "xxx", "文字字幕": "xxx"}},
  {{"镜头编号": 2, "画面描述": "xxx", "文字字幕": "xxx"}}
]"""

    system_prompt = "你是一个AI彩铃分镜师，擅长将抽象灵感转化为具体的视觉画面和文字表达。输出必须是纯JSON格式。"

    return chat(prompt, system_prompt)


def chat_prompt_decompose(shot_desc: str, shot_subtitle: str,
                          template_str: str, ai_play: str) -> str:
    """
    将镜头画面描述智能拆解为提示词模版各占位符的内容

    Args:
        shot_desc: 镜头画面描述
        shot_subtitle: 镜头文字字幕
        template_str: 提示词模版字符串（含[占位符]）
        ai_play: AI玩法描述

    Returns:
        LLM生成的占位符键值对（JSON格式字符串）
    """
    # 提取所有占位符
    import re
    placeholders = re.findall(r'\[([^\]]+)\]', template_str)

    if not placeholders:
        return "{}"

    placeholder_list = "\n".join([f"  - [{p}]" for p in placeholders])

    prompt = f"""请将以下画面描述和字幕，拆解填入提示词模版的各个占位符。

【画面描述】{shot_desc}
【文字字幕】{shot_subtitle}
【AI玩法/风格要求】{ai_play}

【模版占位符列表】
{placeholder_list}

要求：
1. 每个占位符填写具体、精炼的内容（不要笼统模糊的描述）
2. 内容要与画面描述和AI玩法风格一致
3. [画面比例]固定填写"9:16竖屏"
4. [风格描述]和[精确风格]填写整体风格关键词（如"文艺治愈风""水墨淡雅风"）
5. [主体内容]和[主体动作与姿态]填写具体人物/物体的动作姿态描述
6. [氛围关键词]和[氛围与色彩]填写氛围和色调关键词
7. [具体场景与构图]填写构图方式和场景空间
8. [色彩与光影]填写色调和光线描述

请严格按照以下JSON格式输出（不要加任何其他文字）：
{{"占位符名": "填写内容", ...}}"""

    system_prompt = "你是一个AI视频提示词工程师，擅长将画面描述精准拆解为结构化的提示词字段。输出必须是纯JSON格式。"

    return chat(prompt, system_prompt)


def understand_image(image_path: str, question: str = "请描述这张图片的风格、人物特征、色调和氛围，用于AI彩铃制作参考。") -> str:
    """
    图片理解：使用多模态API分析参考图片

    Args:
        image_path: 图片文件路径
        question: 对图片的提问

    Returns:
        LLM对图片的理解描述
    """
    import base64

    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return f"[图片读取失败] {str(e)}"

    # 判断图片格式
    ext = image_path.lower().split(".")[-1]
    mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}
    mime_type = mime_map.get(ext, "jpeg")

    client = get_client()
    try:
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{mime_type};base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[图片理解失败，该模型可能不支持图片输入] {str(e)}"
