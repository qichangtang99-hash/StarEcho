# -*- coding: utf-8 -*-
"""
响星 - 网页版主入口（星海主题）
运行方式：streamlit run app.py
"""

import streamlit as st
import json
import os
import random
from datetime import datetime

import config
from modules import llm_client
from modules.memory import (
    save_planning, update_dimension_usage, update_template_usage, add_pitfall,
    load_history_index, rebuild_index, index_exists,
    rename_in_index, delete_record, load_record_file,
    save_record_content, update_index_after_edit
)
from modules.theme_analyzer import (
    load_star_map, get_dimensions_for_theme, get_cold_dimensions,
    get_random_dimensions, update_dimension_usage as update_dim
)
from modules.storyboard import generate_storyboard as llm_generate_storyboard
from modules.prompt_writer import fill_template_smart, fill_template_simple, check_pitfall

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="响星 · AI彩铃策划",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 步骤快照 & 渲染辅助函数
# ============================================================

def save_step(step_key, label, data):
    """保存当前步骤快照到 session_state.session_steps"""
    if "session_steps" not in st.session_state:
        st.session_state.session_steps = []
    st.session_state.session_steps = [
        s for s in st.session_state.session_steps if s["step_key"] != step_key
    ]
    st.session_state.session_steps.append({
        "step_key": step_key,
        "label": label,
        "data": data,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


def build_synthetic_steps(record):
    """从旧格式记录（无 steps 字段）构建步骤列表"""
    steps = []
    if record.get("主题"):
        steps.append({
            "step_key": "input", "label": "输入需求",
            "data": {
                "theme": record.get("主题", ""),
                "ai_play": record.get("AI玩法", ""),
                "target": record.get("目标人群", ""),
                "template": record.get("提示词模版", ""),
                "input_type": "文字", "video_format": "视频"
            }
        })
    if record.get("模式"):
        steps.append({
            "step_key": "mode", "label": "选择灵感模式",
            "data": {"mode": record.get("模式", "未知")}
        })
    if record.get("灵感"):
        steps.append({
            "step_key": "inspiration", "label": "灵感结果",
            "data": {"inspiration_result": record.get("灵感", ""), "mode": record.get("模式", "未知")}
        })
    if record.get("分镜表"):
        steps.append({
            "step_key": "storyboard", "label": "分镜表",
            "data": {"storyboard": record.get("分镜表", []), "template_choice": "未知"}
        })
    if record.get("提示词"):
        steps.append({
            "step_key": "prompts", "label": "提示词与剪辑",
            "data": {"prompts": record.get("提示词", []), "edit_advice": record.get("剪辑建议", {})}
        })
    return steps


def render_step_indicator(steps, current_idx):
    """渲染步骤进度指示器"""
    items = []
    for i, s in enumerate(steps):
        if i == current_idx:
            items.append(f'<span style="color:#90b8f8;font-weight:bold;">● {s["label"]}</span>')
        else:
            items.append(f'<span style="color:#5a6a8a;">○ {s["label"]}</span>')
    html = " → ".join(items)
    st.markdown(f'<div style="text-align:center;font-size:0.85rem;margin:0.5rem 0 1rem;">{html}</div>',
                unsafe_allow_html=True)


def render_step_content(step_key, data):
    """渲染某个步骤的内容（历史查看用，只读）"""
    if step_key == "input":
        st.markdown("#### 📥 输入需求")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**主题**：{data.get('theme', '')}")
            st.markdown(f"**输入类型**：{data.get('input_type', '文字')}")
            st.markdown(f"**视频形态**：{data.get('video_format', '视频')}")
            st.markdown(f"**提示词模版**：{data.get('template', data.get('prompt_template', ''))}")
        with c2:
            st.markdown(f"**AI玩法**：{data.get('ai_play', '')}")
            st.markdown(f"**目标人群**：{data.get('target', '')}")

    elif step_key == "mode":
        mode = data.get("mode", "未知")
        mode_icons = {"引星": "🎯", "星图": "🗺️", "流星": "☄️"}
        st.markdown(f"#### {mode_icons.get(mode, '')} 选择灵感模式：**{mode}**")
        if mode == "流星" and data.get("starfire"):
            sf = data["starfire"]
            st.markdown(f"**星火种子**：🌤 {sf.get('weather', '')} · 💭 {sf.get('mood', '')} · 🌲 {sf.get('place', '')} · 🎲 {sf.get('random_word', '')}")
        elif mode == "引星" and data.get("member_framework"):
            st.markdown(f"**联想框架**：{data['member_framework']}")

    elif step_key == "inspiration":
        st.markdown("#### 💡 灵感结果")
        mode = data.get("mode", "")
        if mode:
            mode_icons = {"引星": "🎯", "星图": "🗺️", "流星": "☄️"}
            st.caption(f"{mode_icons.get(mode, '')} 模式：**{mode}**")
        st.markdown(f'<div class="result-box">{data.get("inspiration_result", "")}</div>', unsafe_allow_html=True)

    elif step_key == "storyboard":
        st.markdown("#### 🎬 分镜表")
        tc = data.get("template_choice", "")
        if tc:
            st.caption(f"分镜结构：**{tc}**")
        for shot in data.get("storyboard", []):
            col_num, col_func, col_time, col_desc, col_sub = st.columns([0.5, 1.2, 0.6, 3, 2])
            with col_num:
                st.markdown(f"**#{shot.get('镜头编号', '')}**")
            with col_func:
                st.caption(shot.get("功能", ""))
            with col_time:
                st.text(shot.get("时长", ""))
            with col_desc:
                st.text(shot.get("画面描述", ""))
            with col_sub:
                st.text(shot.get("文字字幕", ""))

    elif step_key == "prompts":
        st.markdown("#### 📝 提示词")
        for p in data.get("prompts", []):
            st.markdown(f"**镜头 {p.get('镜头', '')}**")
            st.code(p.get("提示词", ""), language=None)
        edit_advice = data.get("edit_advice", {})
        if edit_advice:
            st.markdown("---")
            st.markdown("#### ✂️ 剪辑建议")
            col_trans, col_sub = st.columns(2)
            with col_trans:
                st.markdown("**转场推荐**")
                for t in edit_advice.get("转场推荐", []):
                    st.markdown(f"- **{t['名称']}**（{t.get('风格', '')}） — `{t.get('剪映路径', '')}`")
            with col_sub:
                st.markdown("**字幕推荐**")
                for s in edit_advice.get("字幕推荐", []):
                    st.markdown(f"- **{s['名称']}**（{s.get('风格', '')}） — `{s.get('剪映路径', '')}`")
    else:
        st.json(data)


# ============================================================
# 星空水彩主题样式
# ============================================================
import base64 as _b64

def _load_bg_css():
    bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "bg.png")
    if os.path.exists(bg_path):
        with open(bg_path, "rb") as f:
            bg_data = _b64.b64encode(f.read()).decode()
        bg_url = f"data:image/png;base64,{bg_data}"
    else:
        bg_url = "linear-gradient(160deg, #eef3fc, #f5f8ff, #edf2fa)"
    return bg_url

_bg_url = _load_bg_css()

st.markdown(f"""
<style>
    /* ========== 顶部工具栏：高度归零但保留侧边栏开关 ========== */
    header[data-testid="stHeader"] {{
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        overflow: visible !important;
    }}
    header[data-testid="stHeader"] button[kind="header"] {{
        position: fixed !important;
        top: 8px !important;
        left: 8px !important;
        z-index: 9999 !important;
        background: rgba(15, 25, 55, 0.70) !important;
        border: 1px solid rgba(120, 160, 220, 0.30) !important;
        border-radius: 8px !important;
        color: #c8d8f8 !important;
    }}
    .block-container {{
        padding-top: 2rem !important;
    }}

    /* ========== 全局背景：星空图 + 半透明遮罩 ========== */
    .stApp {{
        background-image: url('{_bg_url}') !important;
        background-size: cover !important;
        background-position: center top !important;
        background-attachment: fixed !important;
        background-repeat: no-repeat !important;
        color: #e8f0ff;
    }}
    .stApp::before {{
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(8, 16, 40, 0.55);
        pointer-events: none;
        z-index: 0;
    }}
    .stApp > * {{ position: relative; z-index: 1; }}

    /* ========== 侧边栏 ========== */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, rgba(10, 20, 50, 0.88) 0%, rgba(15, 30, 60, 0.85) 50%, rgba(8, 18, 45, 0.90) 100%) !important;
        border-right: 1px solid rgba(120, 160, 220, 0.15) !important;
        backdrop-filter: blur(12px);
    }}
    section[data-testid="stSidebar"] * {{ color: #c8d8f8 !important; }}
    section[data-testid="stSidebar"] .stButton > button {{
        background: rgba(100, 150, 220, 0.15);
        border: 1px solid rgba(120, 160, 220, 0.25);
        color: #a0c0f0 !important;
        border-radius: 8px;
    }}
    section[data-testid="stSidebar"] .stButton > button:hover {{
        background: rgba(100, 150, 220, 0.30);
        border-color: rgba(120, 160, 220, 0.50);
    }}

    /* ========== 文字 ========== */
    h1, h2, h3, h4, h5, h6, .main-title {{ color: #e8f0ff !important; }}
    p, span, label, .stMarkdown {{ color: #c8d8f0 !important; }}
    .stCaption {{ color: #8898b8 !important; }}

    /* ========== 主标题 ========== */
    .hero-title {{
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #90b8f8 0%, #c8d8ff 40%, #f0d0e8 80%, #90b8f8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.2rem;
        letter-spacing: 2px;
    }}
    .hero-sub {{
        text-align: center;
        color: #8898c0 !important;
        font-size: 1rem;
        margin-bottom: 2rem;
        letter-spacing: 4px;
    }}

    /* ========== 步骤徽章 ========== */
    .step-badge {{
        display: inline-block;
        background: linear-gradient(135deg, #5880c8, #78a8e8);
        color: white !important;
        border-radius: 50%;
        width: 28px;
        height: 28px;
        text-align: center;
        line-height: 28px;
        font-weight: bold;
        margin-right: 8px;
        font-size: 0.85rem;
    }}

    /* ========== 卡片 ========== */
    .mode-card {{
        background: linear-gradient(135deg, rgba(20, 35, 70, 0.70), rgba(30, 50, 90, 0.50));
        border: 1px solid rgba(120, 160, 220, 0.20);
        border-radius: 16px;
        padding: 1.8rem 1.2rem;
        text-align: center;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }}
    .mode-card:hover {{
        border-color: rgba(120, 160, 220, 0.45);
        transform: translateY(-2px);
        box-shadow: 0 6px 24px rgba(80, 130, 220, 0.15);
    }}
    .mode-icon {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
    .mode-title {{ font-size: 1.4rem; font-weight: 700; color: #c8d8f8 !important; margin-bottom: 0.3rem; }}
    .mode-desc {{ font-size: 0.85rem; color: #8898b8 !important; margin-bottom: 1rem; }}
    .mode-tag {{
        display: inline-block;
        background: rgba(100, 150, 220, 0.12);
        border: 1px solid rgba(120, 160, 220, 0.22);
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.75rem;
        color: #a0c0f0 !important;
    }}

    /* ========== 结果框 ========== */
    .result-box {{
        background: linear-gradient(135deg, rgba(20, 35, 70, 0.55), rgba(30, 50, 90, 0.40));
        border: 1px solid rgba(120, 160, 220, 0.18);
        border-left: 4px solid #6a9ae0;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        color: #c8d8f0;
        line-height: 1.8;
        white-space: pre-wrap;
    }}

    /* ========== 输入框 ========== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {{
        background: rgba(15, 25, 55, 0.60) !important;
        border: 1px solid rgba(120, 160, 220, 0.25) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: rgba(120, 160, 220, 0.50) !important;
        box-shadow: 0 0 0 2px rgba(100, 150, 220, 0.15) !important;
    }}
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {{ color: #7a8ab0 !important; }}
    .stSelectbox div[data-baseweb="select"] > div {{
        background: rgba(15, 25, 55, 0.60) !important;
        color: #ffffff !important;
        border: 1px solid rgba(120, 160, 220, 0.25) !important;
        border-radius: 8px !important;
    }}
    .stRadio label, .stRadio label div {{ color: #c8d8f0 !important; }}

    /* ========== 按钮 ========== */
    .stButton > button {{
        background: linear-gradient(135deg, #5080c0, #6aa0e0) !important;
        border: none !important;
        color: white !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }}
    .stButton > button:hover {{
        background: linear-gradient(135deg, #6a9ae0, #88b8f8) !important;
        box-shadow: 0 4px 16px rgba(80, 130, 220, 0.30);
    }}
    [data-testid="stSidebar"] .stButton > button {{
        background: rgba(100, 150, 220, 0.15) !important;
        border: 1px solid rgba(120, 160, 220, 0.25) !important;
        color: #a0c0f0 !important;
    }}

    /* ========== 分隔线/代码/Alert ========== */
    hr {{ border-color: rgba(120, 160, 220, 0.15) !important; }}
    code {{
        background: rgba(15, 25, 55, 0.60) !important;
        border: 1px solid rgba(120, 160, 220, 0.15) !important;
        color: #c8d8f0 !important;
        border-radius: 6px !important;
    }}
    pre {{
        background: rgba(10, 20, 50, 0.70) !important;
        border: 1px solid rgba(120, 160, 220, 0.15) !important;
        border-radius: 8px !important;
        color: #c8d8f0 !important;
    }}
    .stAlert {{
        background: rgba(15, 25, 55, 0.50) !important;
        border: 1px solid rgba(120, 160, 220, 0.20) !important;
    }}

    /* ========== 侧边栏记录列表 ========== */
    .rec-item {{
        background: rgba(15, 25, 55, 0.40);
        border: 1px solid rgba(120, 160, 220, 0.15);
        border-radius: 8px;
        padding: 0.5rem 0.8rem;
        margin: 0.3rem 0;
        cursor: pointer;
        transition: all 0.2s;
    }}
    .rec-item:hover {{
        border-color: rgba(120, 160, 220, 0.40);
        background: rgba(15, 25, 55, 0.60);
    }}
    .rec-name {{ font-size: 0.9rem; color: #c8d8f0; font-weight: 600; }}
    .rec-meta {{ font-size: 0.75rem; color: #6a7a9a; }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# Session State 初始化
# ============================================================
if "step" not in st.session_state:
    st.session_state.step = 1
if "user_input" not in st.session_state:
    st.session_state.user_input = {}
if "inspiration_result" not in st.session_state:
    st.session_state.inspiration_result = ""
if "storyboard" not in st.session_state:
    st.session_state.storyboard = []
if "prompts" not in st.session_state:
    st.session_state.prompts = []
if "session_steps" not in st.session_state:
    st.session_state.session_steps = []
if "viewing_record" not in st.session_state:
    st.session_state.viewing_record = None
if "viewing_step_idx" not in st.session_state:
    st.session_state.viewing_step_idx = 0
if "renaming_id" not in st.session_state:
    st.session_state.renaming_id = None
if "deleting_id" not in st.session_state:
    st.session_state.deleting_id = None

# ============================================================
# 侧边栏
# ============================================================
with st.sidebar:
    st.markdown("### 🌟 响星")
    st.caption("AI彩铃策划Agent")
    st.divider()
    st.markdown("**响星导航，星盘指路**")
    st.markdown("- 🎯 引星自定")
    st.markdown("- 🗺 星图不迷")
    st.markdown("- ☄️ 流星天降")
    st.markdown("- 🪨 暗礁不触")
    st.markdown("- 🔥 星火点亮")
    st.divider()
    st.caption("MVP v0.1 · DeepSeek")
    if st.button("🔄 重新开始", use_container_width=True):
        st.session_state.step = 1
        st.session_state.user_input = {}
        st.session_state.inspiration_result = ""
        st.session_state.storyboard = []
        st.session_state.prompts = []
        st.session_state.session_steps = []
        st.session_state.viewing_record = None
        st.session_state.viewing_step_idx = 0
        st.session_state.renaming_id = None
        st.session_state.deleting_id = None
        st.rerun()

    # ---- 生成记录 ----
    st.divider()
    st.markdown("#### 📋 生成记录")

    _history_index = load_history_index()
    if not _history_index and not index_exists():
        _cnt = rebuild_index()
        if _cnt > 0:
            _history_index = load_history_index()

    if not _history_index:
        st.caption("暂无记录")
    else:
        _records_rev = list(reversed(_history_index))
        _ids = [r["id"] for r in _records_rev]
        _labels = [f"{r['name']}（{r['mode']}）" for r in _records_rev]

        def _on_record_change():
            """radio 选中变化时自动进入查看模式"""
            st.session_state.viewing_record = _ids[st.session_state.history_radio]
            st.session_state.viewing_step_idx = 999
            st.session_state.step = "view_record"

        _sel = st.radio(
            "选择记录",
            range(len(_ids)),
            format_func=lambda x: _labels[x],
            key="history_radio",
            label_visibility="collapsed",
            on_change=_on_record_change
        )

        _selected_id = _ids[_sel]
        _selected = next((r for r in _history_index if r["id"] == _selected_id), {})

        # 改名
        bc1, _ = st.columns(2)
        with bc1:
            if st.button("✏️ 改名", key="btn_rename_rec", use_container_width=True):
                st.session_state.renaming_id = _selected_id
                st.session_state.deleting_id = None
        with _:
            pass  # 删除按钮移至记录查看页

        if st.session_state.get("renaming_id") == _selected_id:
            _new_name = st.text_input("新名称", value=_selected.get("name", ""), key="rename_input")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("✅ 确认", key="confirm_rename", use_container_width=True):
                    rename_in_index(_selected_id, _new_name)
                    st.session_state.renaming_id = None
                    st.rerun()
            with rc2:
                if st.button("取消", key="cancel_rename", use_container_width=True):
                    st.session_state.renaming_id = None
                    st.rerun()

        # 删除确认
        if st.session_state.get("deleting_id") == _selected_id:
            st.warning("确认删除此记录？")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("确认删除", key="confirm_del", use_container_width=True):
                    delete_record(_selected_id)
                    st.session_state.deleting_id = None
                    st.rerun()
            with dc2:
                if st.button("取消", key="cancel_del", use_container_width=True):
                    st.session_state.deleting_id = None
                    st.rerun()

# ============================================================
# Step 1: 输入需求
# ============================================================
if st.session_state.step == 1:
    st.markdown('<p class="hero-title">🌟 响星</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-sub">A I 彩 铃 策 划 · 响 星 导 航 · 星 盘 指 路</p>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### <span class='step-badge'>1</span> 输入本期需求", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        theme = st.text_input("🎯 主题", placeholder="如：心情、节日、悦己")
        input_type = st.selectbox("📥 输入类型", ["文字", "图片", "文字+图片"])
        video_format = st.selectbox("🎬 视频形态", ["视频", "图片"])
        prompt_template = st.selectbox("📝 提示词模版", ["中间型", "高随机性", "高还原度"],
                                       index=0,
                                       help="高随机性：创意导向，结果差异大\n高还原度：精确还原，结果稳定\n中间型：平衡两者")

    with col2:
        ai_play = st.text_area("🎨 AI玩法", placeholder="客户具体要求、风格描述等\n如：文生视频，治愈系文字独白，心情感受，整体风格文艺治愈",
                                height=150)
        target_gender = st.selectbox("👤 目标性别", ["不限", "女性", "男性"])
        target_age = st.text_input("🎂 目标年龄段", placeholder="如：20-30岁", value="20-30岁")

    image_path = None
    if input_type in ["图片", "文字+图片"]:
        image_path = st.text_input("🖼 参考图片路径", placeholder="粘贴图片的完整路径")

    st.markdown("---")
    if st.button("✅ 确认需求，开始策划", type="primary", use_container_width=True):
        if not theme:
            st.error("请至少填写主题！")
        elif not ai_play:
            st.error("请填写AI玩法描述！")
        else:
            st.session_state.user_input = {
                "theme": theme,
                "input_type": input_type,
                "video_format": video_format,
                "ai_play": ai_play,
                "target_gender": target_gender,
                "target_age": target_age,
                "prompt_template": prompt_template,
                "image_path": image_path
            }
            # 保存步骤快照
            save_step("input", "输入需求", dict(st.session_state.user_input))
            st.session_state.session_steps = [st.session_state.session_steps[-1]]  # 只保留当前步骤
            st.session_state.step = 2
            st.rerun()

# ============================================================
# Step 2: 选择灵感模式
# ============================================================
elif st.session_state.step == 2:
    ui = st.session_state.user_input
    st.markdown(f"### <span class='step-badge'>2</span> 选择灵感模式", unsafe_allow_html=True)
    st.caption(f"当前主题：**{ui['theme']}** · 目标人群：**{ui['target_gender']}，{ui['target_age']}**")

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="mode-card">
            <div class="mode-icon">🎯</div>
            <div class="mode-title">引星</div>
            <div class="mode-desc">你引一颗星来引路</div>
            <div class="mode-tag">成员参与度最高</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
        st.caption("成员自己定方向，LLM填充文化知识")
        if st.button("选择引星 →", key="btn_yinxing", use_container_width=True):
            st.session_state.mode = "引星"
            save_step("mode", "选择灵感模式", {"mode": "引星"})
            st.session_state.step = "yinxing_input"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="mode-card">
            <div class="mode-icon">🗺️</div>
            <div class="mode-title">星图</div>
            <div class="mode-desc">按图导航，全维度覆盖</div>
            <div class="mode-tag">覆盖面最全</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
        st.caption("维度框架知识库驱动，全维度发散")
        if st.button("选择星图 →", key="btn_xingtu", use_container_width=True):
            st.session_state.mode = "星图"
            save_step("mode", "选择灵感模式", {"mode": "星图"})
            st.session_state.step = "generating"
            st.rerun()

    with col3:
        st.markdown("""
        <div class="mode-card">
            <div class="mode-icon">☄️</div>
            <div class="mode-title">流星🎲</div>
            <div class="mode-desc">天降惊喜，不可预测</div>
            <div class="mode-tag">独特性最强</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
        st.caption("星火种子+随机维度，每次都不同")
        if st.button("选择流星 →", key="btn_liuxing", use_container_width=True):
            st.session_state.mode = "流星"
            save_step("mode", "选择灵感模式", {"mode": "流星"})
            st.session_state.step = "liuxing_input"
            st.rerun()

# ============================================================
# 引星模式：成员输入框架
# ============================================================
elif st.session_state.step == "yinxing_input":
    ui = st.session_state.user_input
    st.markdown("### 🎯 引星 — 你引一颗星来引路")
    st.markdown("---")

    st.info("请按以下格式输入你的联想链：", icon="📝")
    st.markdown("**格式**：（主题）——（联想主题）——（作品名称）")
    st.markdown("**示例**：`节日 —— 团圆 —— 灯火可亲`  *(示例与当前主题无关，仅展示格式)*")
    st.markdown("---")

    framework = st.text_input(
        f"请输入你的联想链（以「{ui['theme']}」为起点）：",
        placeholder=f"{ui['theme']} —— （你的联想方向） —— （你的作品名称）"
    )

    st.markdown("---")
    col_back, col_go = st.columns(2)
    with col_back:
        if st.button("← 返回选择模式", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col_go:
        if st.button("生成灵感 ✨", type="primary", use_container_width=True):
            if not framework.strip():
                st.error("请输入你的联想链！")
            else:
                st.session_state.member_framework = framework
                # 补充模式步骤数据
                save_step("mode", "选择灵感模式", {"mode": "引星", "member_framework": framework})
                st.session_state.step = "generating"
                st.rerun()

# ============================================================
# 流星模式：收集星火
# ============================================================
elif st.session_state.step == "liuxing_input":
    st.markdown("### ☄️ 流星🎲 — 天降惊喜，不可预测")
    st.markdown("---")
    st.info("先收集一些星火（灵感种子），这些信息会渗透进生成但不直接出现", icon="🔥")

    col1, col2 = st.columns(2)
    with col1:
        weather = st.text_input("🌤 今天天气怎么样？", placeholder="晴天/下雨/多云...")
        mood = st.text_input("💭 现在心情如何？", placeholder="开心/平静/焦虑/期待...")
    with col2:
        place = st.text_input("🌲 森林还是海边？", placeholder="森林/海边/沙漠/城市...")
        random_word = st.text_input("🎲 随便说一个词", placeholder="随便什么都行...")

    st.markdown("---")
    col_back, col_go = st.columns(2)
    with col_back:
        if st.button("← 返回选择模式", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col_go:
        if st.button("播星火，生成灵感 ✨", type="primary", use_container_width=True):
            st.session_state.starfire = {
                "weather": weather or "晴天",
                "mood": mood or "平静",
                "place": place or "森林",
                "random_word": random_word or "蒲公英"
            }
            # 补充模式步骤数据
            save_step("mode", "选择灵感模式", {"mode": "流星", "starfire": dict(st.session_state.starfire)})
            st.session_state.step = "generating"
            st.rerun()

# ============================================================
# 生成中（三种模式共用）
# ============================================================
elif st.session_state.step == "generating":
    ui = st.session_state.user_input
    mode = st.session_state.mode
    target_audience = f"{ui['target_gender']}，{ui['target_age']}"

    with st.spinner("🌌 响星正在为你生成灵感..."):
        image_context = ""
        if ui.get("image_path") and ui["image_path"].strip():
            with st.spinner("🖼 正在理解参考图片..."):
                image_desc = llm_client.understand_image(ui["image_path"])
                if not image_desc.startswith("["):
                    image_context = f"\n\n【参考图片分析】{image_desc}"
                    st.session_state.image_description = image_desc
                else:
                    st.warning(f"图片理解失败：{image_desc}")

        enhanced_ai_play = ui["ai_play"] + image_context

        if mode == "引星":
            result = llm_client.chat_free_creation(
                theme=ui["theme"],
                member_framework=st.session_state.member_framework,
                ai_play=enhanced_ai_play,
                target_audience=target_audience
            )
        elif mode == "星图":
            dimensions = get_dimensions_for_theme(ui["theme"])
            dim_names = [d["维度名"] for d in dimensions]
            st.info(f"当前可用维度：{', '.join(dim_names)}", icon="🗺️")
            result = llm_client.chat_with_dimensions(
                theme=ui["theme"],
                dimensions=dim_names,
                ai_play=enhanced_ai_play,
                target_audience=target_audience
            )
            update_dim(dim_names)
        elif mode == "流星":
            sf = st.session_state.starfire
            today = datetime.now().strftime("%Y年%m月%d日")
            seed_context = f"天气：{sf['weather']}，心情：{sf['mood']}，场景：{sf['place']}，随机词：{sf['random_word']}，日期：{today}"

            dimensions = get_dimensions_for_theme(ui["theme"])
            random_dims = get_random_dimensions(dimensions, n=3)
            cold_dims = get_cold_dimensions(dimensions, top_n=1)
            all_dims = list(dict.fromkeys(random_dims + cold_dims))

            st.info(f"随机维度：{', '.join(random_dims)} · 冷门维度：{', '.join(cold_dims)} · +1条自由发散", icon="☄️")

            result = llm_client.chat_meteor(
                theme=ui["theme"],
                dimensions=all_dims,
                seed_context=seed_context,
                ai_play=enhanced_ai_play,
                target_audience=target_audience
            )
            update_dim(all_dims)

    st.session_state.inspiration_result = result
    # 保存灵感步骤快照
    save_step("inspiration", "灵感结果", {"inspiration_result": result, "mode": mode})
    st.session_state.step = 3
    st.rerun()

# ============================================================
# Step 3: 灵感结果 + 进入分镜
# ============================================================
elif st.session_state.step == 3:
    st.markdown("### <span class='step-badge'>3</span> 灵感结果", unsafe_allow_html=True)

    mode_icons = {"引星": "🎯", "星图": "🗺️", "流星": "☄️"}
    st.caption(f"{mode_icons.get(st.session_state.mode, '')} 模式：**{st.session_state.mode}**")

    st.markdown("---")
    st.markdown(f'<div class="result-box">{st.session_state.inspiration_result}</div>', unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("**选择分镜结构：**")
        template_choice = st.radio(
            "镜头数",
            ["3镜头版", "5镜头版", "7镜头版"],
            index=1,
            horizontal=True,
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("")
        st.markdown("")
        if st.button("生成分镜表 →", type="primary", use_container_width=True):
            st.session_state.template_choice = template_choice
            st.session_state.step = 4
            st.rerun()

# ============================================================
# Step 4: 分镜表（可修改确认）
# ============================================================
elif st.session_state.step == 4:
    st.markdown("### <span class='step-badge'>4</span> 分镜表", unsafe_allow_html=True)

    path = os.path.join(config.KNOWLEDGE_BASE_DIR, "storyboard_templates.json")
    with open(path, "r", encoding="utf-8") as f:
        templates_data = json.load(f)
    templates = templates_data.get("模版列表", [])

    template = next((t for t in templates if t["名称"] == st.session_state.template_choice), templates[0])
    ui = st.session_state.user_input
    target_audience = f"{ui['target_gender']}，{ui['target_age']}"

    if not st.session_state.storyboard:
        with st.spinner("🎬 响星正在生成分镜表..."):
            storyboard_data = llm_generate_storyboard(
                inspiration=st.session_state.inspiration_result,
                template=template,
                ai_play=ui["ai_play"],
                target_audience=target_audience
            )
            st.session_state.storyboard = storyboard_data
            # 保存分镜步骤快照
            save_step("storyboard", "分镜表", {
                "storyboard": storyboard_data,
                "template_choice": st.session_state.template_choice
            })

    st.caption(f"分镜结构：**{template['名称']}**（{template['适用场景']}）")
    st.markdown("---")

    updated_storyboard = []
    for i, shot in enumerate(st.session_state.storyboard):
        col_num, col_func, col_time, col_desc, col_sub = st.columns([0.5, 1.2, 0.6, 3, 2])

        with col_num:
            st.markdown(f"**#{shot['镜头编号']}**")
        with col_func:
            st.caption(shot["功能"])
        with col_time:
            st.text(shot["时长"])
        with col_desc:
            new_desc = st.text_input("画面描述", value=shot["画面描述"],
                                      key=f"desc_{i}", label_visibility="collapsed")
            shot["画面描述"] = new_desc
        with col_sub:
            new_sub = st.text_input("字幕", value=shot["文字字幕"],
                                     key=f"sub_{i}", label_visibility="collapsed",
                                     placeholder="输入字幕文字...")
            shot["文字字幕"] = new_sub

        updated_storyboard.append(shot)

    st.session_state.storyboard = updated_storyboard

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 返回修改灵感", use_container_width=True):
            st.session_state.step = 3
            st.session_state.storyboard = []
            st.rerun()
    with col2:
        if st.button("确认分镜，生成提示词 →", type="primary", use_container_width=True):
            # 更新分镜步骤（用户可能修改过）
            save_step("storyboard", "分镜表", {
                "storyboard": st.session_state.storyboard,
                "template_choice": st.session_state.template_choice
            })
            st.session_state.step = 5
            st.rerun()

# ============================================================
# Step 5: 提示词 + 剪辑建议 + 完成
# ============================================================
elif st.session_state.step == 5:
    st.markdown("### <span class='step-badge'>5</span> 提示词", unsafe_allow_html=True)

    ui = st.session_state.user_input
    template_name = ui["prompt_template"]

    path = os.path.join(config.KNOWLEDGE_BASE_DIR, "prompt_templates.json")
    with open(path, "r", encoding="utf-8") as f:
        templates_data = json.load(f)
    template = next((t for t in templates_data["模版列表"] if t["名称"] == template_name), templates_data["模版列表"][0])

    st.caption(f"模版：**{template_name}** · 格式：`{template['模版']}`")
    st.markdown("---")

    prompts_output = []
    for shot in st.session_state.storyboard:
        prompt_text, used_llm = fill_template_smart(
            template=template,
            shot=shot,
            ai_play=ui["ai_play"]
        )
        fill_method = "LLM智能填充" if used_llm else "规则填充（降级）"

        warnings = check_pitfall(prompt_text, ui["theme"])

        st.markdown(f"**镜头 {shot['镜头编号']}**（{shot['功能']}）`{fill_method}`")
        st.code(prompt_text, language=None)
        for w in warnings:
            st.warning(f"⚠ {w}")

        prompts_output.append({"镜头": shot["镜头编号"], "提示词": prompt_text})

    st.markdown("---")

    st.markdown("### <span class='step-badge'>6</span> 剪辑建议", unsafe_allow_html=True)

    jianying_path = os.path.join(config.KNOWLEDGE_BASE_DIR, "jianying_assets.json")
    with open(jianying_path, "r", encoding="utf-8") as f:
        jianying = json.load(f)

    edit_advice = {"转场推荐": jianying.get("转场效果", [])[:4], "字幕推荐": jianying.get("字幕样式", [])[:4]}

    col_trans, col_sub = st.columns(2)
    with col_trans:
        st.markdown("**转场推荐**")
        for t in edit_advice["转场推荐"]:
            st.markdown(f"- **{t['名称']}**（{t['风格']}） — `{t['剪映路径']}`")
    with col_sub:
        st.markdown("**字幕推荐**")
        for s in edit_advice["字幕推荐"]:
            st.markdown(f"- **{s['名称']}**（{s['风格']}） — `{s['剪映路径']}`")

    st.info("以上所有推荐均为剪映免费可商用素材", icon="✅")

    st.markdown("---")

    # 保存提示词步骤快照
    save_step("prompts", "提示词与剪辑", {"prompts": prompts_output, "edit_advice": edit_advice})

    save_planning(
        user_input=type('obj', (object,), ui)(),
        inspiration=st.session_state.inspiration_result,
        storyboard=st.session_state.storyboard,
        prompts=prompts_output,
        edit_advice=edit_advice,
        mode=st.session_state.mode,
        steps=st.session_state.session_steps
    )

    st.markdown("### 🪨 暗礁反馈")
    pitfall_feedback = st.text_input("如审核不通过，请输入反馈原文（留空跳过）：", placeholder="如：不允许出现外语")
    if pitfall_feedback:
        add_pitfall(theme=ui["theme"], feedback=pitfall_feedback, category="内容违规", member="匿名")
        st.success("暗礁已记录！")

    st.markdown("---")
    st.markdown("### 🌟 策划方案生成完毕！")
    st.balloons()

    if st.button("🔄 开始新一期策划", type="primary", use_container_width=True):
        st.session_state.step = 1
        st.session_state.user_input = {}
        st.session_state.inspiration_result = ""
        st.session_state.storyboard = []
        st.session_state.prompts = []
        st.session_state.session_steps = []
        st.session_state.viewing_record = None
        st.session_state.viewing_step_idx = 0
        st.session_state.renaming_id = None
        st.session_state.deleting_id = None
        st.rerun()

# ============================================================
# 查看历史记录（步骤回退/前进）
# ============================================================
elif st.session_state.step == "view_record":
    _record_id = st.session_state.get("viewing_record")
    if not _record_id:
        st.session_state.step = 1
        st.rerun()

    _record = load_record_file(_record_id)
    if not _record:
        st.error("记录文件不存在或已损坏")
        if st.button("← 返回主界面"):
            st.session_state.step = 1
            st.session_state.viewing_record = None
            st.rerun()
    else:
        _idx = load_history_index()
        _entry = next((r for r in _idx if r["id"] == _record_id), {})
        _rec_name = _entry.get("name", "未命名")

        # 获取步骤列表（优先用 steps 字段，否则合成）
        _steps = _record.get("steps", [])
        if not _steps:
            _steps = build_synthetic_steps(_record)

        _total = len(_steps)
        if _total == 0:
            st.warning("该记录无步骤数据")
            if st.button("← 返回主界面"):
                st.session_state.step = 1
                st.session_state.viewing_record = None
                st.rerun()
            st.stop()

        # 当前查看的步骤索引
        _step_idx = st.session_state.get("viewing_step_idx", 0)
        # 999 表示"最后一步"
        if _step_idx >= _total:
            _step_idx = _total - 1
        st.session_state.viewing_step_idx = _step_idx

        # ---- 页头 ----
        st.markdown(f"### 📋 {_rec_name}")
        st.caption(f"{_record.get('日期', '')} · {_record.get('模式', '未知')}")

        # ---- 步骤进度指示器 ----
        render_step_indicator(_steps, _step_idx)

        st.markdown("---")

        # ---- 渲染当前步骤内容 ----
        _current = _steps[_step_idx]
        render_step_content(_current.get("step_key", ""), _current.get("data", {}))

        st.markdown("---")

        # ---- 步骤导航 ----
        nav1, nav2, nav3 = st.columns([1, 2, 1])
        with nav1:
            if _step_idx > 0:
                if st.button("◀ 上一步", key="prev_step", use_container_width=True):
                    st.session_state.viewing_step_idx = _step_idx - 1
                    st.rerun()
        with nav2:
            st.caption(f"第 {_step_idx + 1} 步 / 共 {_total} 步")
        with nav3:
            if _step_idx < _total - 1:
                if st.button("下一步 ▶", key="next_step", use_container_width=True):
                    st.session_state.viewing_step_idx = _step_idx + 1
                    st.rerun()

        st.markdown("---")
        nav1, nav2, nav3 = st.columns([1, 1, 1])
        with nav1:
            if st.button("← 返回主界面", use_container_width=True):
                st.session_state.step = 1
                st.session_state.viewing_record = None
                st.session_state.viewing_step_idx = 0
                st.session_state.confirm_delete = False
                st.rerun()
        with nav3:
            if st.button("🗑 删除此记录", key="btn_del_viewing", use_container_width=True):
                st.session_state.confirm_delete = True

        if st.session_state.get("confirm_delete", False):
            st.warning("⚠️ 您是否要删除此记录？删除后无法恢复。")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("确认删除", key="confirm_del_viewing", type="primary", use_container_width=True):
                    delete_record(_record_id)
                    st.session_state.confirm_delete = False
                    st.session_state.viewing_record = None
                    st.session_state.viewing_step_idx = 0
                    st.session_state.step = 1
                    st.success("✅ 记录已删除")
                    st.rerun()
            with dc2:
                if st.button("取消", key="cancel_del_viewing", use_container_width=True):
                    st.session_state.confirm_delete = False
                    st.rerun()
