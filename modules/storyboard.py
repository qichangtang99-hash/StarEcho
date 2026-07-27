# -*- coding: utf-8 -*-
"""
响星 - 分镜表制作模块
支持LLM自动生成画面描述和字幕
"""

import json
import os
import config
from modules import llm_client


def load_storyboard_templates() -> dict:
    """加载分镜结构模版"""
    path = os.path.join(config.KNOWLEDGE_BASE_DIR, "storyboard_templates.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_template() -> dict:
    """让成员选择分镜结构模版"""
    templates_data = load_storyboard_templates()
    templates = templates_data.get("模版列表", [])

    print("\n请选择分镜结构模版：")
    for i, t in enumerate(templates, 1):
        shot_count = len(t["结构"])
        print(f"  {i}. {t['名称']}（{shot_count}个镜头，适用：{t['适用场景']}）")

    choice = input(f"\n请选择（1-{len(templates)}）[1]：").strip()
    idx = int(choice) - 1 if choice.isdigit() and 0 < int(choice) <= len(templates) else 0

    return templates[idx]


def generate_storyboard(inspiration: str, template: dict, ai_play: str,
                        target_audience: str = "") -> list:
    """
    根据灵感和模版生成分镜表
    调用LLM自动为每个镜头生成画面描述和字幕
    """
    structure = template["结构"]

    # 调用LLM生成分镜描述
    llm_result = llm_client.chat_storyboard(
        inspiration=inspiration,
        template_structure=structure,
        ai_play=ai_play,
        target_audience=target_audience
    )

    # 解析LLM返回的JSON
    shot_descriptions = _parse_storyboard_json(llm_result)

    storyboard = []
    for i, shot in enumerate(structure):
        shot_num = shot["镜头编号"]
        # 从LLM结果中查找对应镜头编号的描述
        desc_data = next(
            (s for s in shot_descriptions if s.get("镜头编号") == shot_num),
            {}
        )

        shot_data = {
            "镜头编号": shot_num,
            "功能": shot["功能"],
            "时长": shot["时长"],
            "画面描述": desc_data.get("画面描述", f"基于灵感方向的{shot['功能']}"),
            "文字字幕": desc_data.get("文字字幕", ""),
        }
        storyboard.append(shot_data)

    return storyboard


def _parse_storyboard_json(llm_result: str) -> list:
    """解析LLM返回的分镜JSON，兼容各种格式"""
    # 尝试直接解析
    try:
        result = json.loads(llm_result)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # 尝试提取JSON块（可能被```json包裹）
    import re
    json_match = re.search(r'\[[\s\S]*\]', llm_result)
    if json_match:
        try:
            result = json.loads(json_match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # 解析失败，返回空列表（将使用默认占位符）
    return []


def display_storyboard(storyboard: list):
    """展示分镜表"""
    print("\n" + "=" * 60)
    print("  分镜表")
    print("=" * 60)
    for shot in storyboard:
        print(f"\n  镜头 {shot['镜头编号']}（{shot['功能']}）")
        print(f"    时长：{shot['时长']}")
        print(f"    画面：{shot['画面描述']}")
        print(f"    字幕：{shot['文字字幕']}")


def modify_storyboard(storyboard: list) -> list:
    """允许成员修改分镜表"""
    while True:
        display_storyboard(storyboard)

        print("\n是否需要修改？")
        print("  1. 修改某个镜头")
        print("  2. 确认分镜表")

        choice = input("请选择（1/2）[2]：").strip()

        if choice == "1":
            shot_num = input("请输入要修改的镜头编号：").strip()
            shot = next((s for s in storyboard if str(s["镜头编号"]) == shot_num), None)

            if shot:
                print(f"\n当前画面描述：{shot['画面描述']}")
                new_desc = input("新的画面描述（直接回车保留原内容）：").strip()
                if new_desc:
                    shot["画面描述"] = new_desc

                print(f"当前文字字幕：{shot['文字字幕']}")
                new_sub = input("新的文字字幕（直接回车保留原内容）：").strip()
                if new_sub:
                    shot["文字字幕"] = new_sub
            else:
                print("未找到该镜头编号。")
        else:
            print("\n分镜表已确认！")
            return storyboard


def create_storyboard(inspiration: str, ai_play: str, target_audience: str = "") -> list:
    """分镜表制作主流程"""
    template = select_template()
    storyboard = generate_storyboard(inspiration, template, ai_play, target_audience)
    storyboard = modify_storyboard(storyboard)
    return storyboard
