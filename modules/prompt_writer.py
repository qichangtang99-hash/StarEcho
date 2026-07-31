# -*- coding: utf-8 -*-
"""
响星 - 提示词撰写模块
按预选模版格式填空生成提示词，支持双轨制（静态图prompt + 动态运镜prompt）
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


def get_all_template_names() -> list:
    """获取所有模版名称列表"""
    templates_data = load_prompt_templates()
    templates = templates_data.get("模版列表", [])
    return [t["名称"] for t in templates]


def get_template_description(template_name: str) -> str:
    """获取模版适用场景描述"""
    t = get_template(template_name)
    return t.get("适用场景", "")


def fill_template_smart(template: dict, shot: dict, ai_play: str) -> tuple:
    """
    智能填空：调用LLM将画面描述拆解为模版各占位符的具体内容
    返回 (填空结果dict, 是否使用了LLM)
    填空结果格式：{"静态": "填空后的静态prompt", "动态": "填空后的动态prompt"} 或 {"静态": "...", "动态": None}
    """
    static_template = template.get("静态模版", "")
    dynamic_template = template.get("动态模版")
    is_dual_track = template.get("双轨制", False)

    static_placeholders = re.findall(r'\[([^\]]+)\]', static_template)
    dynamic_placeholders = re.findall(r'\[([^\]]+)\]', dynamic_template) if dynamic_template else []

    all_placeholders = static_placeholders + dynamic_placeholders

    if not all_placeholders:
        # 无占位符，直接返回原始模版
        return {
            "静态": static_template,
            "动态": dynamic_template
        }, False

    # 调用LLM一次性拆解所有占位符（静态+动态）
    llm_result = llm_client.chat_prompt_decompose(
        shot_desc=shot.get("画面描述", ""),
        shot_subtitle=shot.get("文字字幕", ""),
        static_template_str=static_template,
        dynamic_template_str=dynamic_template or "",
        ai_play=ai_play
    )

    # 解析LLM返回的JSON
    field_values = _parse_decompose_json(llm_result)

    # 填充静态模版
    filled_static = static_template
    used_llm = False
    for ph in static_placeholders:
        if ph in field_values and field_values[ph].strip():
            filled_static = filled_static.replace(f"[{ph}]", field_values[ph])
            used_llm = True
        else:
            filled_static = filled_static.replace(f"[{ph}]", _default_value(ph, shot))

    # 追加负面提示词（段式模版不追加，因为末尾是【画面背景】内容）
    negative = template.get("负面提示词", "")
    if negative and "【" not in static_template:
        filled_static += "，" + negative

    # 填充动态模版（如果有）
    filled_dynamic = None
    if dynamic_template:
        filled_dynamic = dynamic_template
        for ph in dynamic_placeholders:
            if ph in field_values and field_values[ph].strip():
                filled_dynamic = filled_dynamic.replace(f"[{ph}]", field_values[ph])
                used_llm = True
            else:
                filled_dynamic = filled_dynamic.replace(f"[{ph}]", _default_value(ph, shot, is_dynamic=True))

    return {
        "静态": filled_static,
        "动态": filled_dynamic
    }, used_llm


def fill_template_simple(template: dict, shot: dict) -> dict:
    """
    简单填空：不调用LLM，用规则匹配填充（降级方案）
    返回格式同 fill_template_smart
    """
    static_template = template.get("静态模版", "")
    dynamic_template = template.get("动态模版")

    static_placeholders = re.findall(r'\[([^\]]+)\]', static_template)
    dynamic_placeholders = re.findall(r'\[([^\]]+)\]', dynamic_template) if dynamic_template else []

    filled_static = static_template
    for ph in static_placeholders:
        filled_static = filled_static.replace(f"[{ph}]", _default_value(ph, shot))

    negative = template.get("负面提示词", "")
    if negative and "【" not in static_template:
        filled_static += "，" + negative

    filled_dynamic = None
    if dynamic_template:
        filled_dynamic = dynamic_template
        for ph in dynamic_placeholders:
            filled_dynamic = filled_dynamic.replace(f"[{ph}]", _default_value(ph, shot, is_dynamic=True))

    return {
        "静态": filled_static,
        "动态": filled_dynamic
    }


def _default_value(placeholder: str, shot: dict, is_dynamic: bool = False) -> str:
    """占位符默认值映射"""
    # 静态占位符默认值
    static_defaults = {
        "风格基调": "治愈系风格，柔和暖色调，中景构图",
        "景别构图": "中景居中构图",
        "主体描述": shot.get("画面描述", "人物主体，具体外观动作细节"),
        "画面风格": "治愈系风格，柔和暖色调，侧光，中景构图",
        "画面主体": shot.get("画面描述", "人物主体，具体外观动作细节，景别中景，机位平视"),
        "画面背景": "具体场景环境，家具摆设，色调光影，配文字字幕内容",
        "环境氛围": "温馨氛围，具体场景描述",
        "光影色彩": "柔和暖色调",
        "约束条件": "9:16竖屏",
        "首帧参考图描述": "首帧场景描述",
        "尾帧参考图描述": "尾帧场景描述",
        "过渡场景描述": "场景之间自然过渡",
        "情绪关键词": "温暖治愈",
        "场景名称": "默认场景",
        "画幅分辨率": "9:16（1080×1920）",
        "画风描述": "写实风格",
        "场景内容": shot.get("画面描述", "场景描述"),
        "参考图说明": "参考图一",
        "一句话画面描述": shot.get("画面描述", "画面内容"),
    }

    # 动态占位符默认值
    dynamic_defaults = {
        "运镜方式": "缓慢推进",
        "人物微动作": "微微呼吸",
        "微动作": "微微呼吸",
        "人物动作": "轻微动作",
        "环境动态": "环境轻微流动",
        "氛围动态": "环境轻微流动",
        "首帧→尾帧过渡动作": "首帧到尾帧自然过渡",
        "一句话动作描述": "轻微动作",
    }

    defaults = dynamic_defaults if is_dynamic else static_defaults
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
                break  # 每条规则只警告一次

    return warnings


def _load_ringtone_boundary() -> dict:
    """加载彩铃风格边界规则"""
    pitfall_path = os.path.join(config.KNOWLEDGE_BASE_DIR, "pitfall_rules.json")
    with open(pitfall_path, "r", encoding="utf-8") as f:
        pitfall_data = json.load(f)
    return pitfall_data.get("彩铃风格边界", {})


def get_negative_style_hint(theme: str, ai_play: str) -> str:
    """
    根据主题和AI玩法，调用LLM生成负面风格约束提示。
    基于彩铃本质（十几秒接电话前的休闲娱乐），自动追加"不要xxx"风格。
    返回格式：如"不要恐怖风格、怪诞风格，要搞笑、幽默风格"
    """
    boundary = _load_ringtone_boundary()
    suitable = "、".join(boundary.get("适合", []))
    unsuitable = "、".join(boundary.get("不适合", []))
    boundary_note = boundary.get("说明", "")

    prompt = f"""请根据以下主题和AI玩法，判断需要追加的负面风格约束。

主题：{theme}
AI玩法：{ai_play}

彩铃用户画像：爱音乐的人、喜欢可爱治愈风格、追求生活美好感。不是抖音吐槽党，不是丧文化受众。

彩铃风格边界：
- 适合：{suitable}
- 不适合：{unsuitable}、吐槽抱怨、消极摆烂、丧文化、职场怨气
- 注意：{boundary_note}

请输出一条负面风格约束，格式示例：
"不要恐怖风格、怪诞风格、吐槽抱怨，要搞笑、幽默、热爱生活的可爱风格"

要求：
1. 根据主题判断哪些"不适合"的风格最容易被误触发，加入"不要"约束
2. 根据主题给出正向风格引导（"要xxx风格"），方向是积极向上、热爱生活、发现美好
3. 如果主题是轻松搞笑类（如热梗、表情包），特别强调"不要恐怖/怪诞/吐槽抱怨/丧文化，要发现生活可爱瞬间的幽默感"
4. 如果主题是治愈/温馨类，特别强调"不要压抑/冰冷，要温暖/治愈"
5. 输出一句话即可，不要加任何解释"""

    system_prompt = "你是一个AI彩铃风格把关专家。你深知彩铃用户是爱音乐、喜欢可爱治愈的人，彩铃方向永远是积极向上、热爱生活、发现美好，不会走向吐槽抱怨或丧文化。你输出的约束简洁精准。"

    result = llm_client.chat(prompt, system_prompt)
    # 清理可能的引号和多余换行
    result = result.strip().strip('"').strip("'").strip()
    return result


def write_prompts(storyboard: list, template_name: str, theme: str,
                   ai_play: str = "", use_smart_fill: bool = True) -> list:
    """为每个镜头生成提示词（双轨制），自动追加负面风格约束"""
    template = get_template(template_name)
    prompts = []

    is_dual_track = template.get("双轨制", False)

    print("\n" + "=" * 60)
    print("  提示词（双轨制）")
    print("=" * 60)

    # 获取负面风格约束（一次策划只调用一次LLM）
    negative_hint = ""
    if ai_play:
        try:
            negative_hint = get_negative_style_hint(theme, ai_play)
            print(f"\n  [彩铃风格边界] {negative_hint}")
        except Exception as e:
            print(f"\n  [负面风格约束获取失败] {e}")

    for shot in storyboard:
        if use_smart_fill and ai_play:
            result, used_llm = fill_template_smart(template, shot, ai_play)
            method = "LLM智能填充" if used_llm else "规则填充（降级）"
        else:
            result = fill_template_simple(template, shot)
            method = "规则填充"

        # 将负面风格约束追加到静态提示词中
        if negative_hint:
            # 判断是否有画面风格相关占位符被填充
            if any(kw in result["静态"] for kw in ["风格", "画风", "基调"]):
                # 在风格关键词后追加负面约束
                result["静态"] = _inject_negative_hint(result["静态"], negative_hint)
            else:
                # 末尾追加
                result["静态"] += "，" + negative_hint

        # 合并静态+动态用于暗礁校验
        combined_prompt = result["静态"]
        if result["动态"]:
            combined_prompt += " | " + result["动态"]

        warnings = check_pitfall(combined_prompt, theme)

        print(f"\n  镜头 {shot['镜头编号']}（{method}）：")
        print(f"    [静态] {result['静态']}")
        if result["动态"]:
            print(f"    [动态] {result['动态']}")
        if warnings:
            for w in warnings:
                print(f"    {w}")

        prompts.append({
            "镜头编号": shot["镜头编号"],
            "静态提示词": result["静态"],
            "动态提示词": result["动态"],
            "提示词": combined_prompt,  # 向后兼容
            "暗礁警告": warnings
        })

    # 更新模版使用统计
    mem.update_template_usage(template_name)

    return prompts


def _inject_negative_hint(static_prompt: str, negative_hint: str) -> str:
    """将负面风格约束注入到静态提示词的风格相关位置"""
    # 找到风格关键词所在位置，在其后追加
    style_keywords = ["风格", "画风", "基调", "风格基调", "画面风格"]
    for kw in style_keywords:
        # 尝试找到"xxx风格"的结尾位置
        idx = static_prompt.find(kw)
        if idx == -1:
            continue
        # 从kw位置往后找，定位到这个风格词组的末尾
        # 在风格描述段后面追加负面约束
        # 找到下一个标点或分隔符
        after = idx + len(kw)
        # 在整个风格短语后插入（找到下一个逗号、句号或段式标记【）
        insert_pos = len(static_prompt)
        for delim_pos in range(after, len(static_prompt)):
            if static_prompt[delim_pos] in "，。、；【\n":
                insert_pos = delim_pos
                break
        # 在insert_pos前插入
        result = static_prompt[:insert_pos] + "、" + negative_hint + static_prompt[insert_pos:]
        return result
    # 如果没找到风格关键词，末尾追加
    return static_prompt + "，" + negative_hint
