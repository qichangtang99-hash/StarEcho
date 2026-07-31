# -*- coding: utf-8 -*-
"""
响星 - 剪辑建议模块
查剪映素材知识库，推荐转场和字幕
"""

import json
import os
import config


def load_jianying_assets() -> dict:
    """加载剪映素材知识库"""
    path = os.path.join(config.KNOWLEDGE_BASE_DIR, "jianying_assets.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recommend_transitions(style: str = "") -> list:
    """根据视频风格推荐转场效果"""
    assets = load_jianying_assets()
    transitions = assets.get("转场效果", [])

    # 简单匹配：所有素材都是免费可商用的，直接返回
    # 后续可根据style做更智能的匹配
    return [t for t in transitions if t.get("免费可商用")]


def recommend_subtitles(style: str = "") -> list:
    """根据文字内容推荐字幕样式"""
    assets = load_jianying_assets()
    subtitles = assets.get("字幕样式", [])

    return [s for s in subtitles if s.get("免费可商用")]


def generate_edit_advice(storyboard: list, ai_play: str) -> dict:
    """生成剪辑建议"""
    transitions = recommend_transitions()
    subtitles = recommend_subtitles()

    print("\n" + "=" * 60)
    print("  剪辑建议")
    print("=" * 60)

    print("\n推荐转场效果：")
    for t in transitions[:3]:  # 推荐3个
        print(f"  · {t['名称']}（{t['风格']}）- 剪映路径：{t['剪映路径']}")

    print("\n推荐字幕样式：")
    for s in subtitles[:3]:  # 推荐3个
        print(f"  · {s['名称']}（{s['风格']}）- 剪映路径：{s['剪映路径']}")

    print("\n  ⚠ 所有推荐均为剪映免费可商用素材")

    return {
        "转场推荐": transitions[:3],
        "字幕推荐": subtitles[:3]
    }
