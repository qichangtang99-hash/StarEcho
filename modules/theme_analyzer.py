# -*- coding: utf-8 -*-
"""
响星 - 主题分析与灵感生成模块
三种灵感模式：引星 / 星图 / 流星🎲
"""

import json
import os
import random
from datetime import datetime
from modules import llm_client
import config


def load_star_map() -> dict:
    """加载星盘（维度框架知识库）"""
    path = os.path.join(config.KNOWLEDGE_BASE_DIR, "dimension_framework.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_dimensions_for_theme(theme: str) -> list:
    """根据主题获取可用维度列表"""
    star_map = load_star_map()
    all_dimensions = star_map.get("所有可用维度", [])
    theme_mapping = star_map.get("主题与维度映射", {})

    # 如果主题有专属映射，用映射；否则用全部维度
    if theme in theme_mapping:
        theme_dims = theme_mapping[theme]
        return [d for d in all_dimensions if d["维度名"] in theme_dims]
    else:
        return all_dimensions


def get_cold_dimensions(dimensions: list, top_n: int = 1) -> list:
    """获取冷门维度（使用频次最低的）"""
    sorted_dims = sorted(dimensions, key=lambda d: d.get("使用频次", 0))
    return [d["维度名"] for d in sorted_dims[:top_n]]


def get_random_dimensions(dimensions: list, n: int = 3) -> list:
    """随机抽取n个维度"""
    sample = random.sample(dimensions, min(n, len(dimensions)))
    return [d["维度名"] for d in sample]


def update_dimension_usage(used_dimensions: list):
    """更新维度使用频次"""
    star_map = load_star_map()
    all_dimensions = star_map.get("所有可用维度", [])

    for dim in all_dimensions:
        if dim["维度名"] in used_dimensions:
            dim["使用频次"] = dim.get("使用频次", 0) + 1

    path = os.path.join(config.KNOWLEDGE_BASE_DIR, "dimension_framework.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(star_map, f, ensure_ascii=False, indent=2)


# ============================================================
# 引星模式：成员自定框架，LLM填充知识
# ============================================================

def yinxing_mode(theme: str, ai_play: str, target_audience: str) -> list:
    """引星模式"""
    print("\n" + "-" * 40)
    print("  引星 — 你引一颗星来引路")
    print("-" * 40)
    print(f"""
请按以下格式输入你的联想链：
（主题）——（联想主题）——（作品名称）

示例：节日 —— 团圆 —— 灯火可亲

（示例与当前主题无关，仅展示格式）
""")

    member_framework = input(f"请输入你的联想链（以「{theme}」为起点）：").strip()
    if not member_framework:
        member_framework = f"{theme} —— （请补充） —— （请补充）"
        print(f"  → 使用默认框架：{member_framework}")

    print("\n正在按你的框架填充文化知识...")
    result = llm_client.chat_free_creation(
        theme=theme,
        member_framework=member_framework,
        ai_play=ai_play,
        target_audience=target_audience
    )

    print(f"\n引星结果：\n{result}")
    return [result]


# ============================================================
# 星图模式：维度框架全量发散
# ============================================================

def xingtu_mode(theme: str, ai_play: str, target_audience: str) -> list:
    """星图模式"""
    print("\n" + "-" * 40)
    print("  星图 — 按图导航，全维度覆盖")
    print("-" * 40)

    dimensions = get_dimensions_for_theme(theme)
    dim_names = [d["维度名"] for d in dimensions]

    print(f"\n当前主题「{theme}」可用维度：")
    for i, name in enumerate(dim_names, 1):
        print(f"  {i}. {name}")

    print(f"\n正在按全量维度生成联想链...")
    result = llm_client.chat_with_dimensions(
        theme=theme,
        dimensions=dim_names,
        ai_play=ai_play,
        target_audience=target_audience
    )

    # 更新维度使用频次
    update_dimension_usage(dim_names)

    print(f"\n星图结果：\n{result}")
    return [result]


# ============================================================
# 流星模式：星火种子+随机维度+自由发散
# ============================================================

def liuxing_mode(theme: str, ai_play: str, target_audience: str) -> list:
    """流星模式"""
    print("\n" + "-" * 40)
    print("  流星🎲 — 天降惊喜，不可预测")
    print("-" * 40)
    print("  先收集一些星火（灵感种子）...\n")

    # 快问快答收集星火
    weather = input("① 今天天气怎么样？：").strip() or "晴天"
    mood = input("② 现在心情如何？：").strip() or "平静"
    place = input("③ 森林还是海边？：").strip() or "森林"
    random_word = input("④ 随便说一个词：：").strip() or "蒲公英"
    today = datetime.now().strftime("%Y年%m月%d日")

    seed_context = f"天气：{weather}，心情：{mood}，场景：{place}，随机词：{random_word}，日期：{today}"
    print(f"\n星火已收集：{seed_context}")

    # 获取维度并随机抽取
    dimensions = get_dimensions_for_theme(theme)
    random_dims = get_random_dimensions(dimensions, n=3)
    cold_dims = get_cold_dimensions(dimensions, top_n=1)
    all_dims = random_dims + cold_dims

    # 去重
    all_dims = list(dict.fromkeys(all_dims))

    print(f"\n随机抽取的维度：{', '.join(random_dims)}")
    print(f"冷门维度：{', '.join(cold_dims)}")
    print(f"（加上1条LLM自由发散）")

    print(f"\n正在生成联想链...")
    result = llm_client.chat_meteor(
        theme=theme,
        dimensions=all_dims,
        seed_context=seed_context,
        ai_play=ai_play,
        target_audience=target_audience
    )

    # 更新维度使用频次
    update_dimension_usage(all_dims)

    print(f"\n流星结果：\n{result}")
    return [result]


# ============================================================
# 灵感模式选择器
# ============================================================

def choose_inspiration_mode(theme: str, ai_play: str, target_audience: str) -> list:
    """让成员选择灵感模式"""
    print("\n请选择灵感发散模式：")
    print("  1. 引星 — 你引一颗星来引路，自己定方向")
    print("  2. 星图 — 按图导航，全维度覆盖")
    print("  3. 流星🎲 — 天降惊喜，不可预测")

    choice = input("\n请选择（1/2/3）[2]：").strip()

    if choice == "1":
        return yinxing_mode(theme, ai_play, target_audience)
    elif choice == "3":
        return liuxing_mode(theme, ai_play, target_audience)
    else:
        return xingtu_mode(theme, ai_play, target_audience)
