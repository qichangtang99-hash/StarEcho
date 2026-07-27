# -*- coding: utf-8 -*-
"""
响星 - 输入解析模块
解析团队成员传入的结构化需求
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserInput:
    """成员输入的结构化需求"""
    theme: str = ""                        # 主题
    input_type: str = "文字"               # 输入类型：文字/图片/文字+图片
    video_format: str = "视频"             # 视频形态：图片/视频
    ai_play: str = ""                      # AI玩法描述
    target_gender: str = ""                # 目标性别
    target_age: str = ""                   # 目标年龄段
    prompt_template: str = "中间型"        # 提示词模版选择
    image_path: Optional[str] = None       # 参考图片路径（如有）
    image_description: Optional[str] = None  # 图片理解结果（后续填充）

    def summary(self) -> str:
        """返回结构化需求摘要"""
        lines = [
            f"主题：{self.theme}",
            f"输入类型：{self.input_type}",
            f"视频形态：{self.video_format}",
            f"AI玩法：{self.ai_play}",
            f"目标人群：{self.target_gender}，{self.target_age}",
            f"提示词模版：{self.prompt_template}",
        ]
        if self.image_description:
            lines.append(f"图片分析：{self.image_description}")
        return "\n".join(lines)


def parse_input() -> UserInput:
    """交互式收集成员输入"""
    user_input = UserInput()

    print("\n" + "=" * 50)
    print("  响星 - AI彩铃策划Agent")
    print("  响星导航，星盘指路")
    print("=" * 50)

    user_input.theme = input("\n请输入本期彩铃主题（如：心情、节日、悦己）：").strip()
    if not user_input.theme:
        user_input.theme = "心情"
        print(f"  → 默认主题：{user_input.theme}")

    user_input.input_type = input("请输入类型（文字/图片/文字+图片）[文字]：").strip() or "文字"

    if "图片" in user_input.input_type:
        user_input.image_path = input("请输入参考图片路径：").strip() or None

    user_input.video_format = input("视频形态（图片/视频）[视频]：").strip() or "视频"
    user_input.ai_play = input("请输入AI玩法描述（客户具体要求、风格描述等）：").strip()

    user_input.target_gender = input("目标人群性别（男/女/不限）：").strip() or "不限"
    user_input.target_age = input("目标人群年龄段（如：20-30岁）：").strip() or "不限"

    # 提示词模版选择
    print("\n请选择提示词模版：")
    print("  1. 高随机性 - 创意导向，每代结果差异大")
    print("  2. 高还原度 - 精确还原，结果稳定可控")
    print("  3. 中间型 - 平衡随机性与还原度")
    template_choice = input("请选择（1/2/3）[3]：").strip()
    template_map = {"1": "高随机性", "2": "高还原度", "3": "中间型"}
    user_input.prompt_template = template_map.get(template_choice, "中间型")

    # 确认
    print("\n--- 需求确认 ---")
    print(user_input.summary())
    confirm = input("\n确认以上信息无误？（y/n）[y]：").strip().lower()
    if confirm == "n":
        print("请重新输入：")
        return parse_input()

    return user_input
