# -*- coding: utf-8 -*-
"""
响星 - 配置文件
API Key 优先从 Streamlit Secrets 读取，其次从环境变量读取
部署到 Streamlit Cloud 时，在 Settings → Secrets 中配置：
  DEEPSEEK_API_KEY = "sk-xxx"
"""

import os

# DeepSeek API配置（优先级：Streamlit Secrets > 环境变量 > 本地开发默认值）
try:
    import streamlit as st
    _secret_key = st.secrets.get("DEEPSEEK_API_KEY", None)
except Exception:
    _secret_key = None

API_KEY = _secret_key or os.environ.get("DEEPSEEK_API_KEY", "your-api-key-here")
API_BASE = "https://api.deepseek.com"
MODEL_NAME = "deepseek-v4-flash"
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_DIR = os.path.join(PROJECT_ROOT, "knowledge_base")
HISTORY_DIR = os.path.join(PROJECT_ROOT, "history")
STATS_DIR = os.path.join(PROJECT_ROOT, "stats")

# 确保目录存在
for d in [HISTORY_DIR, STATS_DIR]:
    os.makedirs(d, exist_ok=True)
