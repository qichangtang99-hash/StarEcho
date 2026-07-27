# -*- coding: utf-8 -*-
"""
响星 - 主入口
"""

from modules.input_parser import parse_input, UserInput
from modules.theme_analyzer import choose_inspiration_mode
from modules.storyboard import create_storyboard
from modules.prompt_writer import write_prompts
from modules.edit_advisor import generate_edit_advice
from modules.memory import save_planning, ask_pitfall_feedback


def main():
    # ========== ① 解析输入 ==========
    user_input = parse_input()
    target_audience = f"{user_input.target_gender}，{user_input.target_age}"

    # ========== ② 主题分析 + ④ 灵感生成 ==========
    inspiration_results = choose_inspiration_mode(
        theme=user_input.theme,
        ai_play=user_input.ai_play,
        target_audience=target_audience
    )

    # 灵感已由各模式直接输出，取第一条作为默认选中
    selected = inspiration_results[0] if inspiration_results else "默认方向"

    # ========== ⑤ 分镜表制作 ==========
    storyboard = create_storyboard(
        inspiration=selected,
        ai_play=user_input.ai_play
    )

    # ========== ⑥ 提示词撰写 ==========
    prompts = write_prompts(
        storyboard=storyboard,
        template_name=user_input.prompt_template,
        theme=user_input.theme
    )

    # ========== ⑦ 剪辑建议 ==========
    edit_advice = generate_edit_advice(
        storyboard=storyboard,
        ai_play=user_input.ai_play
    )

    # ========== ⑧ 输出完整策划方案 + 归档 ==========
    print("\n" + "=" * 60)
    print("  策划方案生成完毕！")
    print("=" * 60)

    save_planning(user_input, selected, storyboard, prompts, edit_advice)

    # 询问暗礁反馈
    ask_pitfall_feedback()

    print("\n感谢使用响星！下次见 ✨")


if __name__ == "__main__":
    main()
