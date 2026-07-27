# -*- coding: utf-8 -*-
"""
响星 - 记忆模块
历史策划归档、使用统计、暗礁库管理
"""

import json
import os
from datetime import datetime
import config


# ============================================================
# 历史策划归档
# ============================================================

def save_planning(user_input, inspiration, storyboard, prompts, edit_advice, mode="未知", steps=None):
    """保存一次完整策划到历史归档，同时更新索引"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    filename = f"{now.strftime('%Y-%m-%d_%H%M%S')}_{user_input.theme}.json"
    filepath = os.path.join(config.HISTORY_DIR, filename)

    record = {
        "日期": date_str,
        "主题": user_input.theme,
        "AI玩法": user_input.ai_play,
        "目标人群": f"{user_input.target_gender}，{user_input.target_age}",
        "提示词模版": user_input.prompt_template,
        "模式": mode,
        "灵感": inspiration,
        "分镜表": storyboard,
        "提示词": prompts,
        "剪辑建议": edit_advice,
        "steps": steps or []
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    # 同时更新历史索引
    record_id = now.strftime("%Y-%m-%d_%H%M%S")
    input_summary = f"{user_input.theme} | {user_input.ai_play[:20]}..." if len(user_input.ai_play) > 20 else f"{user_input.theme} | {user_input.ai_play}"
    output_summary = (inspiration[:40] + "...") if len(inspiration) > 40 else inspiration

    add_to_index(
        record_id=record_id,
        name=f"{user_input.theme}_{now.strftime('%m%d')}",
        filename=filename,
        date=date_str,
        theme=user_input.theme,
        mode=mode,
        input_summary=input_summary,
        output_summary=output_summary,
        shot_count=len(storyboard)
    )

    print(f"\n  策划已归档：{filename}")


# ============================================================
# 使用统计
# ============================================================

def update_dimension_usage(used_dimensions: list):
    """更新维度使用频次统计"""
    filepath = os.path.join(config.STATS_DIR, "dimension_usage.json")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            stats = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        stats = {}

    for dim in used_dimensions:
        stats[dim] = stats.get(dim, 0) + 1

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def update_template_usage(template_name: str):
    """更新模版使用频次统计"""
    filepath = os.path.join(config.STATS_DIR, "template_usage.json")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            stats = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        stats = {}

    stats[template_name] = stats.get(template_name, 0) + 1

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def update_member_activity(member_name: str, theme: str):
    """更新成员活动记录"""
    filepath = os.path.join(config.STATS_DIR, "member_activity.json")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            stats = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        stats = {}

    if member_name not in stats:
        stats[member_name] = []

    stats[member_name].append({
        "主题": theme,
        "日期": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


# ============================================================
# 暗礁库管理
# ============================================================

def add_pitfall(theme: str, feedback: str, category: str, member: str):
    """添加一条暗礁规则"""
    pitfall_path = os.path.join(config.KNOWLEDGE_BASE_DIR, "pitfall_rules.json")

    with open(pitfall_path, "r", encoding="utf-8") as f:
        pitfall_data = json.load(f)

    new_rule = {
        "主题": theme,
        "审核反馈": feedback,
        "归类": category,
        "来源成员": member,
        "日期": datetime.now().strftime("%Y-%m-%d"),
        "关键词": feedback.split()  # 简单按空格拆分作为匹配关键词
    }

    pitfall_data["规则列表"].append(new_rule)

    with open(pitfall_path, "w", encoding="utf-8") as f:
        json.dump(pitfall_data, f, ensure_ascii=False, indent=2)

    print(f"\n  已添加暗礁规则：{feedback}")


def ask_pitfall_feedback():
    """询问成员是否有审核反馈需要记录"""
    print("\n是否有审核反馈需要记录到暗礁库？（y/n）[n]：")
    choice = input().strip().lower()

    if choice == "y":
        theme = input("  关联主题：").strip()
        feedback = input("  审核反馈原文：").strip()
        category = input("  归类（内容违规/风格不符/格式问题）：").strip() or "内容违规"
        member = input("  你的名字：").strip() or "匿名"
        add_pitfall(theme, feedback, category, member)


# ============================================================
# 历史记录索引管理
# ============================================================

HISTORY_INDEX_PATH = os.path.join(config.HISTORY_DIR, "index.json")


def index_exists():
    """检查索引文件是否存在"""
    return os.path.exists(HISTORY_INDEX_PATH)


def load_history_index():
    """加载历史记录索引"""
    try:
        with open(HISTORY_INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history_index(index):
    """保存历史记录索引"""
    with open(HISTORY_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def add_to_index(record_id, name, filename, date, theme, mode, input_summary, output_summary, shot_count):
    """添加一条记录到索引"""
    index = load_history_index()
    index.append({
        "id": record_id,
        "name": name,
        "filename": filename,
        "date": date,
        "theme": theme,
        "mode": mode,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "shot_count": shot_count
    })
    save_history_index(index)


def rename_in_index(record_id, new_name):
    """重命名一条记录"""
    index = load_history_index()
    for entry in index:
        if entry["id"] == record_id:
            entry["name"] = new_name
            break
    save_history_index(index)


def delete_record(record_id):
    """删除一条记录（索引+文件）"""
    index = load_history_index()
    filename = None
    for entry in index:
        if entry["id"] == record_id:
            filename = entry.get("filename")
            break
    if filename:
        filepath = os.path.join(config.HISTORY_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    index = [e for e in index if e["id"] != record_id]
    save_history_index(index)


def load_record_file(record_id):
    """加载一条完整记录"""
    index = load_history_index()
    entry = next((e for e in index if e["id"] == record_id), None)
    if not entry:
        return None
    filepath = os.path.join(config.HISTORY_DIR, entry["filename"])
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_record_content(record_id, record_data):
    """保存记录内容修改"""
    index = load_history_index()
    entry = next((e for e in index if e["id"] == record_id), None)
    if not entry:
        return False
    filepath = os.path.join(config.HISTORY_DIR, entry["filename"])
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record_data, f, ensure_ascii=False, indent=2)
    return True


def update_index_after_edit(record_id, record_data):
    """编辑记录后更新索引中的摘要"""
    index = load_history_index()
    for entry in index:
        if entry["id"] == record_id:
            theme = record_data.get("主题", "")
            ai_play = record_data.get("AI玩法", "")
            entry["input_summary"] = f"{theme} | {ai_play[:20]}..." if len(ai_play) > 20 else f"{theme} | {ai_play}"
            inspiration = record_data.get("灵感", "")
            entry["output_summary"] = (inspiration[:40] + "...") if len(inspiration) > 40 else inspiration
            entry["theme"] = theme
            break
    save_history_index(index)


def rebuild_index():
    """从history目录中的JSON文件重建索引（首次使用或迁移）"""
    index = []
    for fname in sorted(os.listdir(config.HISTORY_DIR)):
        if not fname.endswith(".json") or fname == "index.json":
            continue
        filepath = os.path.join(config.HISTORY_DIR, fname)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                record = json.load(f)
            parts = fname.replace(".json", "").split("_", 2)
            record_id = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else fname
            theme = record.get("主题", "未知")
            ai_play = record.get("AI玩法", "")
            input_summary = f"{theme} | {ai_play[:20]}..." if len(ai_play) > 20 else f"{theme} | {ai_play}"
            inspiration = record.get("灵感", "")
            output_summary = (inspiration[:40] + "...") if len(inspiration) > 40 else inspiration
            date = record.get("日期", "")
            name = f"{theme}_{date[5:10].replace('-', '')}" if date else fname
            mode = record.get("模式", "未知")
            storyboard = record.get("分镜表", [])
            index.append({
                "id": record_id,
                "name": name,
                "filename": fname,
                "date": date,
                "theme": theme,
                "mode": mode,
                "input_summary": input_summary,
                "output_summary": output_summary,
                "shot_count": len(storyboard)
            })
        except (json.JSONDecodeError, KeyError):
            continue
    save_history_index(index)
    return len(index)
