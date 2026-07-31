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
    星图模式专用：从全部维度中挑选最匹配AI玩法的7个维度，生成7条联想链

    Args:
        theme: 主题（如"心情"）
        dimensions: 维度列表
        ai_play: AI玩法描述
        target_audience: 目标人群
        anti_anchor_hint: 反锚定提示

    Returns:
        LLM生成的联想链文本
    """
    dimension_text = "\n".join([f"- {d}" for d in dimensions])

    prompt = f"""请围绕【{theme}】主题，从以下维度中挑选**最匹配AI玩法需求的7个维度**，每个选定维度各生成一条联想链。

可用维度：
{dimension_text}

AI玩法：{ai_play}
目标人群：{target_audience}

要求：
1. **先从全部维度中选出7个与AI玩法风格最契合的维度**，再为这7个维度分别生成联想链
2. 选维度的标准：与AI玩法的风格方向最贴合、最能产出可视觉化画面的维度
3. 每个维度独立发散，不要互相重复
4. {anti_anchor_hint if anti_anchor_hint else "AI玩法中的举例仅为风格参考，请勿围绕该举例发散"}
5. 联想链格式：主题 → 中间关键词 → 具体意象/表达
6. 7条联想链方向尽量差异明显，覆盖不同风格和感受

【彩铃用户画像与风格边界（必须遵守）】
- 彩铃用户画像：爱音乐的人、喜欢可爱治愈风格、追求生活美好感。不是抖音吐槽党，不是丧文化受众。
- 彩铃本质：十几秒接电话前的休闲娱乐，来电时看到/听到的画面
- 联想方向必须是：积极向上、热爱生活、发现小美好、治愈暖心、可爱有趣、浪漫温馨、轻松幽默、正能量
- 坚决避免：吐槽生活、抱怨工作、消极摆烂、丧文化、躺平、社畜自嘲、职场怨气、人间不值得
- 即使主题带"热梗""表情包"等，也要往"生活里的可爱瞬间""发现身边的美好"方向联想，而非"打工人有多惨"方向
- 不适合恐怖/怪诞/颓废/压抑/冰冷风格

【输出格式（严格遵守）】
直接输出7条灵感，每条以编号开头，不要写前言、后记、维度说明、总结等额外内容。
格式如下：

1. 【维度名】主题 → 中间关键词 → 具体意象/表达（一段具体画面描述）
2. 【维度名】主题 → 中间关键词 → 具体意象/表达（一段具体画面描述）
3. 【维度名】主题 → 中间关键词 → 具体意象/表达（一段具体画面描述）
...（共7条）

只输出这7条，不要输出其他任何内容。"""

    system_prompt = "你是一个AI彩铃策划助手，擅长从多元文化维度发散联想。你必须先精准判断哪些维度最匹配用户需求，再针对这些维度生成联想。你的联想必须具体、有画面感、可转化为视觉表达。你深知彩铃用户是爱音乐、喜欢可爱治愈的人，所以联想方向永远是积极向上、热爱生活、发现美好、治愈暖心的，不会走向吐槽抱怨或丧文化。"

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
4. 最终输出格式：主题 → 中间关键词 → 具体意象/表达
5. 【彩铃用户画像与风格边界】彩铃用户是爱音乐、喜欢可爱治愈、追求生活美好感的人。联想方向必须是积极向上、热爱生活、发现小美好、治愈暖心、可爱有趣，坚决避免吐槽生活、抱怨工作、消极摆烂、丧文化。彩铃本质是十几秒接电话前的休闲娱乐，不适合恐怖/怪诞/颓废/压抑/冰冷风格。即使主题带"热梗""表情包"，也要往"生活里的可爱瞬间"方向联想，而非"打工人有多惨"。"""

    system_prompt = "你是一个AI彩铃策划助手，擅长根据成员提供的框架填充文化知识。你尊重成员的创作方向，只补充不改变。你深知彩铃用户是爱音乐、喜欢可爱治愈的人，所以填充的方向总是积极向上、热爱生活、发现美好的，不会走向吐槽抱怨或丧文化。"

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

请先按以上维度各生成一条联想链，最后额外生成一条完全自由的联想链（不限定任何维度，自由发散）。

**最重要**：在生成所有联想链之后，请根据「AI玩法」中用户描述的需求方向和风格偏好，从你生成的所有联想链中选出**最匹配用户需求的1条**，单独标注为【最终推荐】。只选1条，选择标准是：与AI玩法风格最契合、画面感最强、最可转化为视觉表达。

【彩铃用户画像与风格边界（必须遵守）】
- 彩铃用户画像：爱音乐的人、喜欢可爱治愈风格、追求生活美好感。不是抖音吐槽党，不是丧文化受众。
- 彩铃本质：十几秒接电话前的休闲娱乐
- 联想方向必须是：积极向上、热爱生活、发现小美好、治愈暖心、可爱有趣、浪漫温馨、轻松幽默、正能量
- 坚决避免：吐槽生活、抱怨工作、消极摆烂、丧文化、躺平、社畜自嘲、职场怨气、人间不值得
- 即使主题带"热梗""表情包"等，也要往"生活里的可爱瞬间""发现身边的美好"方向联想
- 不适合恐怖/怪诞/颓废/压抑/冰冷风格

【输出格式（严格遵守）】
直接按编号输出各维度的联想链，最后一条为【最终推荐】，不要写前言、后记、维度说明等额外内容。
格式如下：

1. 【维度名】主题 → 中间关键词 → 具体意象/表达（一段具体画面描述）
2. 【维度名】主题 → 中间关键词 → 具体意象/表达（一段具体画面描述）
...
5. 【自由发散】主题 → 中间关键词 → 具体意象/表达（一段具体画面描述）

【最终推荐】第X条：主题 → 中间关键词 → 具体意象/表达（一段具体画面描述）

只输出以上内容，不要输出其他任何内容。"""

    system_prompt = "你是一个AI彩铃策划助手，擅长在氛围引导下自由联想。你的联想有画面感、有意境、可转化为视觉表达。你深知彩铃用户是爱音乐、喜欢可爱治愈的人，所以联想永远是积极向上、热爱生活、发现美好、治愈暖心的，不会走向吐槽抱怨或丧文化。你会在所有联想中精准选出最匹配用户需求的那一条。"

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

    shot_count = len(template_structure)
    # 动态生成JSON示例，与实际镜头数一致
    json_example = ",\n  ".join([
        f'{{"镜头编号": {s["镜头编号"]}, "画面描述": "xxx", "文字字幕": "xxx"}}'
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
1. **严格基于【灵感方向】中的内容生成分镜**，不要脱离提供的灵感自创画面
2. 如果灵感方向包含多条灵感，请将不同镜头分别对应到不同灵感，每条灵感至少被一个镜头使用
3. 各镜头之间要有叙事递进关系，不是独立片段
4. 画面描述要具体、有画面感，可直接用于AI视频生成提示词
5. 画面风格与AI玩法描述一致
6. 文字字幕要简短有感染力（5-12字），与画面配合
7. 画面描述控制在30字以内，字幕控制在12字以内
8. 【彩铃风格边界】画面必须适合彩铃场景（十几秒接电话前的休闲娱乐），方向积极向上、热爱生活、发现美好、治愈暖心、可爱有趣，不要出现吐槽抱怨、消极摆烂、恐怖/怪诞/颓废/压抑/冰冷画面
9. **必须为所有{shot_count}个镜头都生成描述，不要遗漏任何一个镜头**

请严格按照以下JSON格式输出（不要加任何其他文字），必须包含全部{shot_count}个镜头：
[
  {json_example}
]"""

    system_prompt = "你是一个AI彩铃分镜师，擅长将抽象灵感转化为具体的视觉画面和文字表达。你必须严格基于用户提供的灵感方向来设计分镜，不得自由发挥或偏向某一条灵感。输出必须是纯JSON格式。"

    return chat(prompt, system_prompt)


def chat_prompt_decompose(shot_desc: str, shot_subtitle: str,
                          static_template_str: str, dynamic_template_str: str = "",
                          ai_play: str = "") -> str:
    """
    将镜头画面描述智能拆解为提示词模版各占位符的内容（双轨制）

    Args:
        shot_desc: 镜头画面描述
        shot_subtitle: 镜头文字字幕
        static_template_str: 静态图提示词模版字符串（含[占位符]）
        dynamic_template_str: 动态运镜提示词模版字符串（含[占位符]，可为空）
        ai_play: AI玩法描述

    Returns:
        LLM生成的占位符键值对（JSON格式字符串）
    """
    import re

    # 提取所有占位符
    static_placeholders = re.findall(r'\[([^\]]+)\]', static_template_str)
    dynamic_placeholders = re.findall(r'\[([^\]]+)\]', dynamic_template_str) if dynamic_template_str else []
    all_placeholders = static_placeholders + dynamic_placeholders

    if not all_placeholders:
        return "{}"

    # 构建占位符说明
    static_ph_list = "\n".join([f"  - [{p}]（静态）" for p in static_placeholders])
    dynamic_ph_list = "\n".join([f"  - [{p}]（动态）" for p in dynamic_placeholders]) if dynamic_placeholders else ""

    ph_section = "【静态模版占位符】\n" + static_ph_list
    if dynamic_ph_list:
        ph_section += "\n\n【动态模版占位符】\n" + dynamic_ph_list

    dynamic_instruction = ""
    if dynamic_template_str:
        dynamic_instruction = f"""
5. 动态模版的占位符填写运镜、动作、节奏相关内容：
   - [运镜方式]：镜头运动方式（如缓慢推进、环绕拍摄、固定机位等）
   - [人物微动作]/[微动作]/[人物动作]：人物的细微动作（如呼吸、眨眼、轻微转头等）
   - [环境动态]/[氛围动态]：环境中的自然动态（如风、光、雨等）
   - [首帧→尾帧过渡动作]：从首帧到尾帧的过渡描述
   - [一句话动作描述]：一句话概括动作
6. 静态和动态占位符的内容要互相配合，不要重复描述同一内容
"""

    prompt = f"""请将以下画面描述和字幕，拆解填入提示词模版的各个占位符。

【画面描述】{shot_desc}
【文字字幕】{shot_subtitle}
【AI玩法/风格要求】{ai_play}

{ph_section}

要求：
1. 每个占位符填写具体、精炼的内容（不要笼统模糊的描述）
2. 内容要与画面描述和AI玩法风格一致
3. 静态模版的占位符填写画面相关内容：
   - [风格基调]：整体风格关键词（如"文艺治愈风""梦幻科技风""水墨淡雅风"）
   - [景别构图]：景别+构图方式（如"中景平视构图""大全景俯拍"）
   - [主体描述]：具体人物/物体的外观动作描述
   - [环境氛围]：场景环境和氛围
   - [光影色彩]：色调和光线描述
   - [约束条件]：画面比例和技术约束（如"9:16竖屏""电影级质感"）
   - [情绪关键词]：画面传达的情绪（如"温暖治愈""静谧沉思"）
   - [首帧参考图描述]/[尾帧参考图描述]：参考图内容描述
   - [过渡场景描述]：两帧之间的场景过渡
   - [场景名称]/[画幅分辨率]/[画风描述]/[场景内容]/[参考图说明]：场景图定型专用
   - [一句话画面描述]：极简型的一句话画面
   - [画面风格]：必须包含风格+画风+色调+光线+构图（如"治愈系插画风格，清新粉彩色调，柔和侧光，中景平视居中构图"），不要只写笼统的风格词
   - [画面主体]：必须包含景别+机位+主体详细描述（外观、动作、表情、姿态等具体细节），不要只写笼统的主体词
   - [画面背景]：必须包含具体场景环境（家具摆设、空间结构、天气氛围）+字幕文字内容（用引号标注），不要只写"温馨氛围背景"{dynamic_instruction}
4. 【字数约束】所有提示词（静态+动态合并）总计不超过800字，精炼表达

请严格按照以下JSON格式输出（不要加任何其他文字）：
{{"占位符名": "填写内容", ...}}"""

    system_prompt = "你是一个AI视频提示词工程师，擅长将画面描述精准拆解为结构化的提示词字段。输出必须是纯JSON格式。你必须确保风格方向适合彩铃场景——积极向上、热爱生活、发现美好、治愈暖心、可爱有趣，不要出现吐槽抱怨、消极摆烂、恐怖/怪诞/颓废/压抑/冰冷方向。特别注意：画面风格要包含画风+色调+光线+构图，画面主体要具体到外观动作细节+景别+机位，画面背景要写具体场景+字幕文字内容。"

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
