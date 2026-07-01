import os
import re
import sys
import webbrowser
from datetime import datetime
from html import escape
from uuid import UUID, uuid4

import requests
import pandas as pd
import streamlit as st
from loguru import logger

# Add the root directory of the project to the system path to allow importing modules from the project
root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)
    print("******** sys.path ********")
    print(sys.path)
    print("")

from app.config import config
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services import llm, voice
from app.services import task as tm
from app.utils import utils

st.set_page_config(
    page_title="混剪智能体",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        "Report a bug": "https://github.com/harry0703/MoneyPrinterTurbo/issues",
        "About": "# 混剪智能体\nSimply provide a topic or keyword for a video, and it will "
        "automatically generate the video copy, video materials, video subtitles, "
        "and video background music before synthesizing a high-definition short "
        "video.\n\nhttps://github.com/harry0703/MoneyPrinterTurbo",
    },
)


streamlit_style = """
<style>
    :root {
        --mpt-bg: #f7f8f4;
        --mpt-bg-warm: #fbfaf5;
        --mpt-surface: #ffffff;
        --mpt-surface-soft: #fbfcf8;
        --mpt-surface-strong: #f3f7f3;
        --mpt-ink: #17212b;
        --mpt-muted: #607086;
        --mpt-soft-muted: #8794a5;
        --mpt-border: #dbe5de;
        --mpt-border-strong: #bdcec5;
        --mpt-teal: #0f766e;
        --mpt-teal-dark: #115e59;
        --mpt-teal-soft: #e5f5f2;
        --mpt-amber: #b7791f;
        --mpt-indigo: #315f88;
        --mpt-focus: rgba(15, 118, 110, 0.24);
        --mpt-shadow-sm: 0 8px 18px rgba(23, 33, 43, 0.06);
        --mpt-shadow: 0 18px 42px rgba(23, 33, 43, 0.10);
        --mpt-shadow-lg: 0 28px 70px rgba(23, 33, 43, 0.16);
    }

    html, body, [data-testid="stAppViewContainer"] {
        background:
            linear-gradient(90deg, rgba(15, 118, 110, 0.035) 1px, transparent 1px),
            linear-gradient(180deg, rgba(49, 95, 136, 0.035) 1px, transparent 1px),
            linear-gradient(180deg, var(--mpt-bg-warm) 0%, var(--mpt-bg) 42%, #f2f4ef 100%);
        background-size: 44px 44px, 44px 44px, auto;
        color: var(--mpt-ink);
    }

    [data-testid="stHeader"] {
        display: none !important;
    }

    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .stDeployButton,
    #MainMenu,
    footer {
        display: none !important;
    }

    .block-container {
        max-width: 1440px;
        padding-top: 0.65rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        letter-spacing: 0;
        color: var(--mpt-ink);
    }

    h1 {
        padding-top: 0 !important;
        margin-bottom: 0 !important;
        font-size: 2rem !important;
        line-height: 1.1 !important;
    }

    p, label, span, div {
        letter-spacing: 0;
    }

    .mpt-sticky-shell {
        min-height: 10.9rem;
        margin-bottom: 1.15rem;
    }

    .mpt-sticky-summary {
        position: fixed;
        top: 0;
        left: 50%;
        width: min(1440px, calc(100% - 10rem));
        transform: translateX(-50%);
        z-index: 50;
        margin: 0;
        padding: 0.35rem 0 1rem;
        background: linear-gradient(
            180deg,
            rgba(251, 250, 245, 0.98) 0%,
            rgba(251, 250, 245, 0.94) 82%,
            rgba(251, 250, 245, 0) 100%
        );
        backdrop-filter: blur(16px);
    }

    .mpt-topbar {
        display: flex;
        align-items: center;
        gap: 14px;
        min-height: 52px;
        margin-bottom: 0.75rem;
    }

    .mpt-mark {
        width: 44px;
        height: 44px;
        display: grid;
        place-items: center;
        border-radius: 8px;
        background: linear-gradient(135deg, var(--mpt-teal), var(--mpt-indigo));
        color: #ffffff;
        font-weight: 800;
        box-shadow: 0 14px 30px rgba(15, 118, 110, 0.24);
        flex: 0 0 auto;
    }

    .mpt-title {
        font-size: 2.05rem;
        line-height: 1.12;
        font-weight: 800;
        color: var(--mpt-ink);
    }

    .mpt-version {
        color: var(--mpt-muted);
        font-weight: 600;
        font-size: 0.92rem;
        margin-top: 2px;
    }

    .mpt-status-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 0.25rem 0 1.1rem;
    }

    .mpt-sticky-summary .mpt-status-grid {
        margin-bottom: 0;
    }

    [data-testid="stElementContainer"]:has(#mpt-settings-popover-marker) {
        position: fixed;
        top: 0.4rem;
        right: max(1.5rem, calc((100% - 1440px) / 2 + 1rem));
        z-index: 90;
        width: auto !important;
    }

    [data-testid="stElementContainer"]:has(#mpt-settings-popover-marker) [data-testid="stMarkdownContainer"] {
        display: none;
    }

    [data-testid="stElementContainer"]:has(#mpt-settings-popover-marker) + div {
        position: fixed;
        top: 0.4rem;
        right: max(1.5rem, calc((100% - 1440px) / 2 + 1rem));
        z-index: 91;
        width: auto !important;
    }

    [data-testid="stElementContainer"]:has(#mpt-settings-popover-marker) + div button {
        min-height: 40px;
        border-radius: 8px;
        border-color: var(--mpt-border);
        background: rgba(255, 255, 255, 0.92);
        box-shadow: var(--mpt-shadow-sm);
        font-weight: 760;
    }

    [data-testid="stPopoverBody"] {
        width: min(920px, calc(100vw - 32px)) !important;
        max-width: min(920px, calc(100vw - 32px)) !important;
        min-width: min(760px, calc(100vw - 32px)) !important;
        max-height: calc(100vh - 128px);
        overflow-y: auto;
        padding: 1.15rem 1.25rem 1.3rem;
        border: 1px solid var(--mpt-border);
        border-radius: 8px;
        box-shadow: var(--mpt-shadow-lg);
    }

    [data-testid="stPopoverBody"] h3 {
        font-size: 1.12rem;
        line-height: 1.25;
        margin: 0.25rem 0 0.65rem;
    }

    [data-testid="stPopoverBody"] [data-testid="stTabs"] button {
        min-height: 40px;
        font-weight: 720;
    }

    [data-testid="stPopoverBody"] [data-testid="stCodeBlock"] {
        border-radius: 8px;
        overflow: hidden;
    }

    .mpt-wizard {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 0 0 1.1rem;
    }

    .mpt-wizard-step {
        position: relative;
        min-height: 64px;
        border: 1px solid var(--mpt-border);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.78);
        padding: 12px 14px 12px 54px;
        box-shadow: var(--mpt-shadow-sm);
        overflow: hidden;
        transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
    }

    .mpt-wizard-step::before {
        content: attr(data-step);
        position: absolute;
        left: 14px;
        top: 50%;
        width: 28px;
        height: 28px;
        display: grid;
        place-items: center;
        transform: translateY(-50%);
        border-radius: 999px;
        border: 1px solid var(--mpt-border);
        background: var(--mpt-surface);
        color: var(--mpt-muted);
        font-size: 0.78rem;
        font-weight: 800;
    }

    .mpt-wizard-step.done {
        border-color: rgba(15, 118, 110, 0.28);
        background: rgba(245, 251, 248, 0.9);
    }

    .mpt-wizard-step.done::before {
        content: "✓";
        border-color: rgba(15, 118, 110, 0.35);
        background: var(--mpt-teal-soft);
        color: var(--mpt-teal-dark);
    }

    .mpt-wizard-step.active {
        border-color: rgba(15, 118, 110, 0.64);
        background: linear-gradient(180deg, rgba(240, 253, 250, 0.98), rgba(255, 255, 255, 0.94));
        box-shadow: 0 18px 36px rgba(15, 118, 110, 0.14);
    }

    .mpt-wizard-step.active::before {
        border-color: transparent;
        background: linear-gradient(135deg, var(--mpt-teal), var(--mpt-indigo));
        color: #ffffff;
        box-shadow: 0 8px 18px rgba(15, 118, 110, 0.24);
    }

    .mpt-wizard-index {
        color: var(--mpt-soft-muted);
        font-size: 0.76rem;
        font-weight: 760;
        margin-bottom: 4px;
    }

    .mpt-wizard-title {
        color: var(--mpt-ink);
        font-size: 0.95rem;
        font-weight: 780;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .mpt-status-card {
        position: relative;
        min-height: 76px;
        border: 1px solid var(--mpt-border);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.84);
        box-shadow: var(--mpt-shadow-sm);
        padding: 14px 16px;
        overflow: hidden;
    }

    .mpt-status-card::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 3px;
        background: linear-gradient(180deg, var(--mpt-teal), var(--mpt-amber));
        opacity: 0.72;
    }

    .mpt-status-label {
        color: var(--mpt-muted);
        font-size: 0.78rem;
        font-weight: 760;
        margin-bottom: 7px;
    }

    .mpt-status-value {
        color: var(--mpt-ink);
        font-size: 1rem;
        font-weight: 800;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .mpt-section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--mpt-ink);
        font-size: 1.02rem;
        font-weight: 760;
        margin: 0 0 0.85rem;
    }

    .mpt-section-title::before {
        content: "";
        width: 8px;
        height: 24px;
        border-radius: 8px;
        background: linear-gradient(180deg, var(--mpt-teal), var(--mpt-amber));
        flex: 0 0 auto;
    }

    .mpt-generating-overlay {
        position: fixed;
        inset: 0;
        z-index: 1000;
        display: grid;
        place-items: center;
        padding: 1rem;
        background: rgba(249, 250, 246, 0.78);
        backdrop-filter: blur(12px);
    }

    .mpt-generating-dialog {
        width: min(420px, calc(100vw - 32px));
        border: 1px solid var(--mpt-border);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.96);
        box-shadow: 0 28px 70px rgba(31, 41, 51, 0.20);
        padding: 28px 28px 26px;
        text-align: center;
    }

    .mpt-generating-spinner {
        width: 58px;
        height: 58px;
        margin: 0 auto 18px;
        border: 4px solid #dce6e1;
        border-top-color: var(--mpt-teal);
        border-right-color: var(--mpt-amber);
        border-radius: 999px;
        animation: mpt-spin 900ms linear infinite;
    }

    .mpt-generating-title {
        color: var(--mpt-ink);
        font-size: 1.08rem;
        line-height: 1.35;
        font-weight: 780;
        margin-bottom: 8px;
    }

    .mpt-generating-copy {
        color: var(--mpt-muted);
        font-size: 0.92rem;
        line-height: 1.55;
        margin-bottom: 18px;
    }

    .mpt-generating-progress {
        position: relative;
        height: 6px;
        overflow: hidden;
        border-radius: 999px;
        background: #e5ebe8;
    }

    .mpt-generating-progress::before {
        content: "";
        position: absolute;
        top: 0;
        bottom: 0;
        left: 0;
        width: 42%;
        border-radius: inherit;
        background: linear-gradient(90deg, var(--mpt-teal), var(--mpt-amber));
        animation: mpt-progress 1.25s ease-in-out infinite;
    }

    @keyframes mpt-spin {
        to {
            transform: rotate(360deg);
        }
    }

    @keyframes mpt-progress {
        0% {
            transform: translateX(-110%);
        }
        100% {
            transform: translateX(260%);
        }
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid var(--mpt-border);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.9);
        box-shadow: var(--mpt-shadow);
        padding: 1.15rem 1.15rem 1.25rem;
        transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
    }

    [data-testid="stVerticalBlockBorderWrapper"]:focus-within {
        border-color: rgba(15, 118, 110, 0.42);
        box-shadow: 0 20px 42px rgba(15, 118, 110, 0.12);
    }

    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > p:first-child {
        color: var(--mpt-ink);
        font-size: 1.04rem;
        font-weight: 800;
        margin-bottom: 0.75rem;
    }

    div[data-testid="stExpander"] {
        border: 1px solid var(--mpt-border);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.78);
        box-shadow: var(--mpt-shadow-sm);
    }

    div[data-testid="stExpander"] summary {
        min-height: 46px;
        color: var(--mpt-ink);
        font-weight: 720;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-baseweb="select"] > div,
    [data-testid="stFileUploader"] section {
        border-color: var(--mpt-border) !important;
        border-radius: 8px !important;
        background-color: var(--mpt-surface-soft) !important;
    }

    [data-testid="stTextInput"] input,
    [data-baseweb="select"] > div {
        min-height: 44px;
    }

    [data-testid="stFileUploader"] section {
        border-style: dashed !important;
        border-width: 1.5px !important;
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(245, 250, 248, 0.88)) !important;
    }

    [data-testid="stFileUploader"] section:hover {
        border-color: rgba(15, 118, 110, 0.48) !important;
        background-color: #f4fbf8 !important;
    }

    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus,
    [data-baseweb="select"] > div:focus-within {
        border-color: var(--mpt-teal) !important;
        box-shadow: 0 0 0 3px var(--mpt-focus) !important;
    }

    [data-testid="stTextArea"] textarea {
        line-height: 1.58;
    }

    .stButton > button {
        min-height: 44px;
        border-radius: 8px;
        border: 1px solid var(--mpt-border);
        font-weight: 760;
        transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease, background 120ms ease;
        touch-action: manipulation;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        border-color: var(--mpt-teal);
        box-shadow: 0 12px 22px rgba(23, 33, 43, 0.10);
    }

    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 6px 14px rgba(23, 33, 43, 0.09);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--mpt-teal), var(--mpt-indigo));
        border-color: transparent;
        color: #ffffff;
        box-shadow: 0 16px 30px rgba(15, 118, 110, 0.26);
    }

    [data-testid="stCheckbox"] label {
        min-height: 32px;
    }

    [data-testid="stSlider"] [role="slider"] {
        box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.12);
    }

    [data-testid="stVideo"] {
        overflow: hidden;
        border: 1px solid var(--mpt-border);
        border-radius: 8px;
        background: #0f172a;
        box-shadow: var(--mpt-shadow);
    }

    [data-testid="stAlert"] {
        border-radius: 8px;
        border: 1px solid var(--mpt-border);
    }

    [data-testid="stTabs"] button {
        min-height: 42px;
        font-weight: 720;
    }

    @media (max-width: 900px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .mpt-status-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .mpt-sticky-shell {
            min-height: 14.6rem;
        }

        .mpt-sticky-summary {
            width: calc(100% - 2rem);
        }

        [data-testid="stElementContainer"]:has(#mpt-settings-popover-marker),
        [data-testid="stElementContainer"]:has(#mpt-settings-popover-marker) + div {
            right: 1rem;
        }
    }

    @media (max-width: 640px) {
        h1 {
            font-size: 1.55rem !important;
        }

        .mpt-title {
            font-size: 1.55rem;
        }

        .mpt-topbar {
            align-items: flex-start;
        }

        .mpt-status-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
        }

        .mpt-status-card {
            min-height: 68px;
            padding: 11px 12px;
        }

        .mpt-status-label {
            font-size: 0.72rem;
            margin-bottom: 5px;
        }

        .mpt-status-value {
            font-size: 0.92rem;
        }

        .mpt-sticky-shell {
            min-height: 16.2rem;
        }

        .mpt-sticky-summary {
            top: 0;
            padding-bottom: 0.7rem;
        }

        [data-testid="stElementContainer"]:has(#mpt-settings-popover-marker),
        [data-testid="stElementContainer"]:has(#mpt-settings-popover-marker) + div {
            top: 0.4rem;
        }

        .mpt-wizard {
            grid-template-columns: 1fr;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .mpt-generating-spinner,
        .mpt-generating-progress::before {
            animation-duration: 2.4s;
        }
    }
</style>
"""
st.markdown(streamlit_style, unsafe_allow_html=True)

# 定义资源目录
font_dir = os.path.join(root_dir, "resource", "fonts")
song_dir = os.path.join(root_dir, "resource", "songs")
i18n_dir = os.path.join(root_dir, "webui", "i18n")
config_file = os.path.join(root_dir, "webui", ".streamlit", "webui.toml")
system_locale = utils.get_system_locale()
DEFAULT_CHATTERBOX_BASE_URL = "http://127.0.0.1:4123/v1"
DEFAULT_CHATTERBOX_MODEL = "chatterbox"
DEFAULT_CHATTERBOX_VOICES = ["default-Female"]
LOCAL_MATERIAL_FILE_TYPES = [
    "mp4",
    "mov",
    "avi",
    "flv",
    "mkv",
    "jpg",
    "jpeg",
    "png",
]
LOCAL_MATERIAL_LIBRARY_SUBDIR = os.path.join("local_videos", "library")


def _parse_chatterbox_voices(voices):
    # Chatterbox 是自托管服务，音色列表由用户在 WebUI 中手动输入。
    # 这里统一兼容 TOML 数组和输入框里的逗号分隔字符串，避免下拉框、
    # 试听按钮和后续生成流程使用不同格式导致状态不一致。
    if isinstance(voices, str):
        return [v.strip() for v in voices.split(",") if v.strip()]
    return [str(v).strip() for v in voices or [] if str(v).strip()]


def _sync_chatterbox_config_from_session_state():
    # Streamlit 的按钮会触发整页 rerun，而 Chatterbox 配置输入框位于
    # “试听语音合成”按钮之后。如果试听时只读取 config.chatterbox，可能拿不到
    # 用户刚在输入框里填入的 base_url/model/voices。先从 session_state 同步一次，
    # 可以保证按钮逻辑和输入框显示逻辑使用同一份最新配置。
    config.chatterbox["base_url"] = (
        st.session_state.get(
            "chatterbox_base_url_input",
            config.chatterbox.get("base_url") or DEFAULT_CHATTERBOX_BASE_URL,
        )
        or ""
    ).strip()
    config.chatterbox["api_key"] = st.session_state.get(
        "chatterbox_api_key_input", config.chatterbox.get("api_key", "")
    )
    config.chatterbox["model_id"] = (
        st.session_state.get(
            "chatterbox_model_input",
            config.chatterbox.get("model_id") or DEFAULT_CHATTERBOX_MODEL,
        )
        or DEFAULT_CHATTERBOX_MODEL
    ).strip()
    config.chatterbox["voices"] = _parse_chatterbox_voices(
        st.session_state.get(
            "chatterbox_voices_input",
            config.chatterbox.get("voices") or DEFAULT_CHATTERBOX_VOICES,
        )
    )


def _detect_audio_mime(audio_file: str, audio_bytes: bytes) -> str:
    # 有些 OpenAI-compatible TTS 服务，例如 travisvn/chatterbox-tts-api，
    # 即使请求 response_format=mp3，也会返回 WAV 内容。WebUI 试听如果固定
    # 使用 audio/mp3，浏览器可能无法播放，因此这里按文件头识别真实格式。
    header = audio_bytes[:12]
    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "audio/wav"
    if header.startswith(b"ID3") or header[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mp3"
    if header.startswith(b"OggS"):
        return "audio/ogg"
    ext = os.path.splitext(audio_file)[1].lower()
    return {
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
    }.get(ext, "audio/mp3")


if "video_subject" not in st.session_state:
    st.session_state["video_subject"] = ""
if "video_script" not in st.session_state:
    st.session_state["video_script"] = ""
if "video_terms" not in st.session_state:
    st.session_state["video_terms"] = ""
if "video_source" not in st.session_state:
    saved_video_source = config.app.get("video_source", "pexels")
    if saved_video_source not in [
        "pexels",
        "pixabay",
        "coverr",
        "local",
        "local_library",
    ]:
        saved_video_source = "pexels"
    st.session_state["video_source"] = saved_video_source
config.app["video_source"] = st.session_state["video_source"]
if "wizard_step" not in st.session_state:
    st.session_state["wizard_step"] = "media"
if "generated_video_files" not in st.session_state:
    st.session_state["generated_video_files"] = []
if "last_task_id" not in st.session_state:
    st.session_state["last_task_id"] = ""
if "custom_audio_file_path" not in st.session_state:
    st.session_state["custom_audio_file_path"] = ""
if st.session_state.get("wizard_order_version") != "media_first_v1":
    if st.session_state.get("wizard_step") == "script":
        st.session_state["wizard_step"] = "media"
    st.session_state["wizard_order_version"] = "media_first_v1"
if "video_script_prompt" not in st.session_state:
    st.session_state["video_script_prompt"] = ""
if "custom_system_prompt" not in st.session_state:
    st.session_state["custom_system_prompt"] = llm.DEFAULT_SCRIPT_SYSTEM_PROMPT
if "use_custom_system_prompt" not in st.session_state:
    st.session_state["use_custom_system_prompt"] = False
if "match_materials_to_script" not in st.session_state:
    st.session_state["match_materials_to_script"] = bool(
        config.app.get("match_materials_to_script", False)
    )
st.session_state["ui_language"] = "zh"
config.ui["language"] = "zh"
if "local_video_materials" not in st.session_state:
    # 记住用户最近一次已经落盘的本地素材，避免仅修改文案后二次生成时丢失素材列表。
    st.session_state["local_video_materials"] = []
if "local_library_video_materials" not in st.session_state:
    st.session_state["local_library_video_materials"] = []

# 加载语言文件
locales = utils.load_locales(i18n_dir)

# 创建一个顶部栏，包含标题和语言选择
title_col = st.container()

with title_col:
    llm_provider_labels = {
        "openai": "OpenAI",
        "claude": "Claude",
        "moonshot": "Kimi",
        "qwen": "Qwen",
        "deepseek": "DeepSeek",
        "glm": "GLM",
        "gemini": "Gemini",
    }
    video_source_labels = {
        "pexels": "Pexels 素材库",
        "pixabay": "Pixabay 素材库",
        "coverr": "Coverr 素材库",
        "local": "本地文件",
        "local_library": "本地素材库",
    }
    tts_server_labels = {
        voice.NO_VOICE_NAME: "无配音",
        "azure-tts-v1": "微软语音 V1",
        "azure-tts-v2": "微软语音 V2",
        "siliconflow": "硅基流动语音",
        "gemini-tts": "Gemini 语音",
        "mimo-tts": "小米 MiMo 语音",
        "elevenlabs": "ElevenLabs 语音",
        "chatterbox": "自托管 Chatterbox",
    }
    current_llm_key = str(config.app.get("llm_provider", "openai")).lower()
    current_source_key = str(config.app.get("video_source", "pexels")).lower()
    current_tts_key = str(config.ui.get("tts_server", "azure-tts-v1"))
    current_llm = escape(llm_provider_labels.get(current_llm_key, current_llm_key))
    current_source = escape(
        video_source_labels.get(current_source_key, current_source_key)
    )
    current_tts = escape(tts_server_labels.get(current_tts_key, current_tts_key))
    st.markdown(
        f"""
        <div class="mpt-sticky-shell">
        <div class="mpt-sticky-summary">
        <div class="mpt-topbar">
            <div class="mpt-mark">创</div>
            <div>
                <div class="mpt-title">混剪智能体</div>
                <div class="mpt-version">v{escape(str(config.project_version))}</div>
            </div>
        </div>
        <div class="mpt-status-grid">
            <div class="mpt-status-card">
                <div class="mpt-status-label">模型服务</div>
                <div class="mpt-status-value">{current_llm}</div>
            </div>
            <div class="mpt-status-card">
                <div class="mpt-status-label">素材来源</div>
                <div class="mpt-status-value">{current_source}</div>
            </div>
            <div class="mpt-status-card">
                <div class="mpt-status-label">配音服务</div>
                <div class="mpt-status-value">{current_tts}</div>
            </div>
            <div class="mpt-status-card">
                <div class="mpt-status-label">画布比例</div>
                <div class="mpt-status-value">9:16</div>
            </div>
        </div>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if False:
    display_languages = []
    selected_index = 0
    for i, code in enumerate(locales.keys()):
        display_languages.append(f"{code} - {locales[code].get('Language')}")
        if code == st.session_state.get("ui_language", ""):
            selected_index = i

    selected_language = st.selectbox(
        "Language / 语言",
        options=display_languages,
        index=selected_index,
        key="top_language_selector",
        label_visibility="collapsed",
    )
    if selected_language:
        code = selected_language.split(" - ")[0].strip()
        st.session_state["ui_language"] = code
        config.ui["language"] = code

support_locales = [
    "zh-CN",
    "zh-HK",
    "zh-TW",
    "de-DE",
    "en-US",
    "fr-FR",
    "ru-RU",
    "vi-VN",
    "th-TH",
    "tr-TR",
]


def get_all_fonts():
    fonts = []
    for root, dirs, files in os.walk(font_dir):
        for file in files:
            if file.endswith(".ttf") or file.endswith(".ttc"):
                fonts.append(file)
    fonts.sort()
    return fonts


FONT_DISPLAY_NAMES = {
    "MicrosoftYaHeiBold.ttc": "微软雅黑 粗体",
    "MicrosoftYaHeiNormal.ttc": "微软雅黑",
    "msyh.ttc": "微软雅黑",
    "msyhbd.ttc": "微软雅黑 粗体",
    "msyhl.ttc": "微软雅黑 Light",
    "simhei.ttf": "黑体",
    "simsun.ttc": "宋体 / 新宋体",
    "simsunb.ttf": "宋体 粗体",
    "simkai.ttf": "楷体",
    "Deng.ttf": "等线",
    "Dengb.ttf": "等线 粗体",
    "Dengl.ttf": "等线 Light",
    "STHeitiLight.ttc": "华文黑体 Light",
    "STHeitiMedium.ttc": "华文黑体 Medium",
}


def format_font_name(font_name):
    display_name = FONT_DISPLAY_NAMES.get(font_name)
    if display_name:
        return f"{display_name}（{font_name}）"
    return font_name


def get_all_songs():
    songs = []
    for root, dirs, files in os.walk(song_dir):
        for file in files:
            if file.endswith(".mp3"):
                songs.append(file)
    return songs


def get_local_material_library_dir(create=True):
    return utils.storage_dir(LOCAL_MATERIAL_LIBRARY_SUBDIR, create=create)


def sanitize_material_filename(filename):
    basename = os.path.basename(str(filename or "")).strip()
    if not basename:
        basename = f"material-{uuid4()}.mp4"
    name, ext = os.path.splitext(basename)
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" ._")
    safe_ext = re.sub(r"[^A-Za-z0-9.]", "", ext).lower()
    if not safe_name:
        safe_name = f"material-{uuid4()}"
    if not safe_ext:
        safe_ext = ".mp4"
    return f"{safe_name[:120]}{safe_ext}"


def material_display_name(file_path):
    filename = os.path.basename(str(file_path or ""))
    prefix, separator, original_name = filename.partition("_")
    if separator and original_name and len(prefix) >= 8:
        return original_name
    return filename


def list_local_material_library():
    library_dir = get_local_material_library_dir(create=True)
    materials = []
    allowed_exts = {f".{ext.lower()}" for ext in LOCAL_MATERIAL_FILE_TYPES}
    for root, _, files in os.walk(library_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            if os.path.splitext(filename)[1].lower() in allowed_exts:
                materials.append(file_path)
    return sorted(
        materials,
        key=lambda file_path: os.path.getmtime(file_path),
        reverse=True,
    )


def save_uploaded_materials_to_library(uploaded_materials):
    if not uploaded_materials:
        return []
    library_dir = get_local_material_library_dir(create=True)
    saved_files = []
    for uploaded_file in uploaded_materials:
        safe_filename = sanitize_material_filename(uploaded_file.name)
        file_id = getattr(uploaded_file, "file_id", str(uuid4()))
        save_path = os.path.join(library_dir, f"{file_id}_{safe_filename}")
        if not os.path.exists(save_path):
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        saved_files.append(save_path)
    return saved_files


def material_paths_to_session_materials(material_paths):
    materials = []
    for file_path in material_paths or []:
        if not file_path or not os.path.exists(file_path):
            continue
        materials.append(
            {
                "provider": "local",
                "url": file_path,
                "duration": 0,
            }
        )
    return materials


def is_local_material_library_path(file_path):
    if not file_path:
        return False
    library_dir = os.path.abspath(get_local_material_library_dir(create=True))
    material_path = os.path.abspath(str(file_path))
    try:
        return os.path.commonpath([library_dir, material_path]) == library_dir
    except ValueError:
        return False


def get_material_kind(file_path):
    ext = os.path.splitext(str(file_path or ""))[1].lower().lstrip(".")
    if ext in {"jpg", "jpeg", "png"}:
        return "图片"
    return "视频"


def format_material_file_size(size_bytes):
    size = float(size_bytes or 0)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def get_material_modified_time(file_path):
    try:
        return datetime.fromtimestamp(os.path.getmtime(file_path)).strftime(
            "%Y-%m-%d %H:%M"
        )
    except OSError:
        return "-"


def rename_local_material(file_path, new_name):
    if not is_local_material_library_path(file_path) or not os.path.isfile(file_path):
        raise ValueError("素材不存在")

    basename = os.path.basename(str(new_name or "")).strip()
    name, ext = os.path.splitext(basename)
    if not name.strip():
        raise ValueError("请输入素材名称")

    current_ext = os.path.splitext(file_path)[1].lower()
    allowed_exts = {f".{ext.lower()}" for ext in LOCAL_MATERIAL_FILE_TYPES}
    if not ext:
        ext = current_ext
    ext = ext.lower()
    if ext not in allowed_exts:
        raise ValueError("不支持的素材格式")

    safe_filename = sanitize_material_filename(f"{name}{ext}")
    target_path = os.path.join(os.path.dirname(file_path), safe_filename)
    if os.path.abspath(target_path) == os.path.abspath(file_path):
        return file_path
    if os.path.exists(target_path):
        raise ValueError("同名素材已存在")

    os.rename(file_path, target_path)
    return target_path


def delete_local_material(file_path):
    if not is_local_material_library_path(file_path) or not os.path.isfile(file_path):
        raise ValueError("素材不存在")
    os.remove(file_path)


def sync_selected_library_material(old_path=None, new_path=None):
    selected_materials = st.session_state.get("local_library_video_materials", [])
    synced_materials = []
    for material in selected_materials:
        material_url = material.get("url")
        if old_path and material_url == old_path:
            if new_path:
                material = {**material, "url": new_path}
            else:
                continue
        synced_materials.append(material)
    st.session_state["local_library_video_materials"] = synced_materials

    for state_key, state_value in list(st.session_state.items()):
        if not state_key.endswith("_selected_paths") or not isinstance(state_value, list):
            continue
        synced_paths = []
        for material_path in state_value:
            if old_path and material_path == old_path:
                if new_path:
                    synced_paths.append(new_path)
                continue
            synced_paths.append(material_path)
        st.session_state[state_key] = synced_paths


def render_local_material_selection_list(all_materials, visible_materials, key_prefix):
    selected_key = f"{key_prefix}_selected_paths"
    valid_paths = set(all_materials)
    if selected_key in st.session_state:
        selected_paths = [
            material_path
            for material_path in st.session_state.get(selected_key, [])
            if material_path in valid_paths
        ]
    else:
        selected_paths = [
            material["url"]
            for material in st.session_state.get("local_library_video_materials", [])
            if material.get("url") in valid_paths
        ]
        if not selected_paths:
            selected_paths = list(all_materials)

    existing_visible_materials = [
        material_path for material_path in visible_materials if os.path.exists(material_path)
    ]
    selected_set = set(selected_paths)
    action_cols = st.columns([0.75, 0.75, 2.5])
    if action_cols[0].button(
        "全选",
        key=f"{key_prefix}_select_visible",
        use_container_width=True,
    ):
        selected_set.update(existing_visible_materials)
        st.session_state[selected_key] = list(selected_set)
        st.rerun()
    if action_cols[1].button(
        "清空",
        key=f"{key_prefix}_clear_visible",
        use_container_width=True,
    ):
        selected_set.difference_update(existing_visible_materials)
        st.session_state[selected_key] = list(selected_set)
        st.rerun()
    selected_visible_count = sum(
        1 for material_path in existing_visible_materials if material_path in selected_set
    )
    action_cols[2].caption(
        f"当前列表 {len(existing_visible_materials)} 个，已选择 {selected_visible_count} 个"
    )

    if not existing_visible_materials:
        st.warning("没有匹配的素材")
        st.session_state[selected_key] = list(selected_set)
        return [material_path for material_path in all_materials if material_path in selected_set]

    material_rows = [
        {
            "选择": file_path in selected_set,
            "素材名称": material_display_name(file_path),
            "类型": get_material_kind(file_path),
            "大小": format_material_file_size(os.path.getsize(file_path)),
        }
        for file_path in existing_visible_materials
    ]
    visible_row_count = min(len(material_rows), 5)
    editor_height = 42 + max(1, visible_row_count) * 34
    edited_materials = st.data_editor(
        pd.DataFrame(material_rows),
        hide_index=True,
        use_container_width=True,
        height=editor_height,
        row_height=34,
        disabled=["素材名称", "类型", "大小"],
        column_order=["选择", "素材名称", "类型", "大小"],
        column_config={
            "选择": st.column_config.CheckboxColumn(
                "选择",
                default=False,
                width="small",
            ),
            "素材名称": st.column_config.TextColumn("素材名称", width="medium"),
            "类型": st.column_config.TextColumn("类型", width="small"),
            "大小": st.column_config.TextColumn("大小", width="small"),
        },
        key=f"{key_prefix}_selection_table",
    )

    updated_selected = {
        material_path for material_path in selected_set if material_path not in existing_visible_materials
    }
    for row_index, checked in enumerate(edited_materials["选择"].tolist()):
        if row_index >= len(existing_visible_materials):
            continue
        if checked:
            updated_selected.add(existing_visible_materials[row_index])
    st.session_state[selected_key] = [
        material_path for material_path in all_materials if material_path in updated_selected
    ]
    return st.session_state[selected_key]


def render_local_material_library_manager(
    key_prefix,
    compact=False,
    show_upload=True,
    show_stats=True,
):
    if show_upload:
        upload_label = "添加素材"
        uploaded_materials = st.file_uploader(
            upload_label,
            type=LOCAL_MATERIAL_FILE_TYPES
            + [file_type.upper() for file_type in LOCAL_MATERIAL_FILE_TYPES],
            accept_multiple_files=True,
            key=f"{key_prefix}_uploader",
        )
        saved_materials = save_uploaded_materials_to_library(uploaded_materials)
        if saved_materials:
            st.success(f"已添加 {len(saved_materials)} 个素材")

    library_materials = list_local_material_library()
    if show_stats:
        video_count = sum(1 for file_path in library_materials if get_material_kind(file_path) == "视频")
        image_count = len(library_materials) - video_count
        total_size = sum(
            os.path.getsize(file_path)
            for file_path in library_materials
            if os.path.exists(file_path)
        )

        stat_cols = st.columns(4)
        stat_cols[0].metric("全部素材", len(library_materials))
        stat_cols[1].metric("视频", video_count)
        stat_cols[2].metric("图片", image_count)
        stat_cols[3].metric("占用空间", format_material_file_size(total_size))

    if not library_materials:
        st.info("本地素材库暂无素材")
        return []

    search_keyword = st.text_input(
        "搜索素材",
        key=f"{key_prefix}_search",
        placeholder="输入文件名关键词",
    ).strip()
    filtered_materials = [
        file_path
        for file_path in library_materials
        if not search_keyword
        or search_keyword.lower() in material_display_name(file_path).lower()
    ]

    if not filtered_materials:
        st.warning("没有匹配的素材")
        return [] if compact else library_materials

    if compact:
        return filtered_materials

    material_rows = [
        {
            "名称": material_display_name(file_path),
            "类型": get_material_kind(file_path),
            "大小": format_material_file_size(os.path.getsize(file_path)),
            "修改时间": get_material_modified_time(file_path),
        }
        for file_path in filtered_materials
        if os.path.exists(file_path)
    ]
    st.dataframe(material_rows, hide_index=True, use_container_width=True)

    selected_key = f"{key_prefix}_selected"
    if st.session_state.get(selected_key) not in filtered_materials:
        st.session_state.pop(selected_key, None)

    selected_material = st.selectbox(
        "查看素材",
        options=filtered_materials,
        format_func=material_display_name,
        key=selected_key,
    )
    if not selected_material:
        return library_materials

    preview_col, edit_col = st.columns([1.1, 1])
    with preview_col:
        with st.container(border=True):
            st.caption(
                f"{get_material_kind(selected_material)} · "
                f"{format_material_file_size(os.path.getsize(selected_material))} · "
                f"{get_material_modified_time(selected_material)}"
            )
            if get_material_kind(selected_material) == "图片":
                st.image(selected_material, use_container_width=True)
            else:
                st.video(selected_material)

    with edit_col:
        with st.container(border=True):
            new_name = st.text_input(
                "素材名称",
                value=material_display_name(selected_material),
                key=f"{key_prefix}_rename",
            )
            rename_col, delete_col = st.columns(2)
            if rename_col.button("保存名称", key=f"{key_prefix}_rename_btn"):
                try:
                    renamed_path = rename_local_material(selected_material, new_name)
                    sync_selected_library_material(selected_material, renamed_path)
                    st.session_state[selected_key] = renamed_path
                    st.success("已保存名称")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

            confirm_delete = st.checkbox(
                "确认删除当前素材",
                key=f"{key_prefix}_confirm_delete",
            )
            if delete_col.button(
                "删除素材",
                key=f"{key_prefix}_delete_btn",
                disabled=not confirm_delete,
            ):
                try:
                    delete_local_material(selected_material)
                    sync_selected_library_material(selected_material, None)
                    st.session_state.pop(selected_key, None)
                    st.success("已删除素材")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    return list_local_material_library()


def open_task_folder(task_id):
    try:
        # task_id 应始终是服务端生成的 UUID。这里先做格式校验，避免异常值
        # 通过路径拼接访问任务目录之外的位置，也避免后续打开目录时触发
        # 平台 shell 对特殊字符的解释。
        normalized_task_id = str(UUID(str(task_id)))
        tasks_root = os.path.abspath(os.path.join(root_dir, "storage", "tasks"))
        path = os.path.abspath(os.path.join(tasks_root, normalized_task_id))

        # 即使 UUID 校验通过，也再次确认最终路径仍在任务根目录内，避免
        # 未来调用方调整 task_id 来源时引入路径穿越风险。
        if not path.startswith(tasks_root + os.sep):
            logger.warning(f"invalid task folder path: {path}")
            return

        if os.path.isdir(path):
            webbrowser.open(f"file://{path}")
    except Exception as e:
        logger.error(e)


def scroll_to_bottom():
    js = """
    <script>
        console.log("scroll_to_bottom");
        function scroll(dummy_var_to_force_repeat_execution){
            var sections = parent.document.querySelectorAll('section.main');
            console.log(sections);
            for(let index = 0; index<sections.length; index++) {
                sections[index].scrollTop = sections[index].scrollHeight;
            }
        }
        scroll(1);
    </script>
    """
    st.components.v1.html(js, height=0, width=0)


def show_generating_overlay(container):
    container.markdown(
        """
        <div class="mpt-generating-overlay" role="status" aria-live="polite">
            <div class="mpt-generating-dialog">
                <div class="mpt-generating-spinner"></div>
                <div class="mpt-generating-title">正在生成视频</div>
                <div class="mpt-generating-copy">
                    系统正在匹配素材、合成配音和字幕，请保持当前页面打开。
                </div>
                <div class="mpt-generating-progress"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def init_log():
    logger.remove()
    _lvl = "DEBUG"

    def format_record(record):
        # 获取日志记录中的文件全路径
        file_path = record["file"].path
        # 将绝对路径转换为相对于项目根目录的路径
        relative_path = os.path.relpath(file_path, root_dir)
        # 更新记录中的文件路径
        record["file"].path = f"./{relative_path}"
        # 返回修改后的格式字符串
        # 您可以根据需要调整这里的格式
        record["message"] = record["message"].replace(root_dir, ".")

        _format = (
            "<green>{time:%Y-%m-%d %H:%M:%S}</> | "
            + "<level>{level}</> | "
            + '"{file.path}:{line}":<blue> {function}</> '
            + "- <level>{message}</>"
            + "\n"
        )
        return _format

    logger.add(
        sys.stdout,
        level=_lvl,
        format=format_record,
        colorize=True,
    )


init_log()

locales = utils.load_locales(i18n_dir)


def tr(key):
    loc = locales.get(st.session_state["ui_language"], {})
    return loc.get("Translation", {}).get(key, key)

@st.cache_data(ttl=300, show_spinner=False)
def get_groq_model_ids(api_key: str, base_url: str) -> list[str]:
    if not api_key:
        return []

    normalized_base_url = (base_url or "https://api.groq.com/openai/v1").strip().rstrip("/")
    models_url = f"{normalized_base_url}/models"

    try:
        response = requests.get(
            models_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])

        model_ids = []
        for item in data:
            if isinstance(item, dict):
                model_id = item.get("id")
                if isinstance(model_id, str) and model_id.strip():
                    model_ids.append(model_id.strip())

        return sorted(set(model_ids))
    except Exception as e:
        logger.warning(f"failed to fetch groq models: {e}")
        return []


def render_video_api_key_manager():
    st.subheader("API Key 管理")

    provider_settings = [
        ("pexels_api_keys", "Pexels"),
        ("pixabay_api_keys", "Pixabay"),
        ("coverr_api_keys", "Coverr"),
    ]

    def normalize_keys(cfg_key):
        api_keys = config.app.get(cfg_key, [])
        if isinstance(api_keys, str):
            api_keys = [api_keys] if api_keys else []
        api_keys = [str(key).strip() for key in api_keys or [] if str(key).strip()]
        config.app[cfg_key] = api_keys
        return api_keys

    def mask_api_key(api_key):
        api_key = str(api_key or "")
        if len(api_key) <= 12:
            return api_key
        return f"{api_key[:6]}...{api_key[-6:]}"

    tabs = st.tabs([provider_name for _, provider_name in provider_settings])
    for tab, (cfg_key, provider_name) in zip(tabs, provider_settings):
        with tab:
            api_keys = normalize_keys(cfg_key)
            st.write(f"{provider_name} API Keys")

            if api_keys:
                st.caption(f"当前已配置 {len(api_keys)} 个 Key")
                for key in api_keys:
                    st.code(mask_api_key(key))
            else:
                st.info(f"当前没有 {provider_name} API Key")

            new_key = st.text_input(
                f"新增 {provider_name} API Key",
                key=f"{cfg_key}_new_key",
            ).strip()
            if st.button(
                f"新增 {provider_name} API Key",
                key=f"{cfg_key}_add_button",
            ):
                if new_key and new_key not in api_keys:
                    config.app[cfg_key].append(new_key)
                    config.save_config()
                    st.success(f"{provider_name} API Key 已新增")
                elif new_key in api_keys:
                    st.warning("这个 API Key 已存在")
                else:
                    st.error("请输入有效的 API Key")

            api_keys = normalize_keys(cfg_key)
            if api_keys:
                delete_key = st.selectbox(
                    f"选择要删除的 {provider_name} API Key",
                    api_keys,
                    format_func=mask_api_key,
                    key=f"{cfg_key}_delete_key",
                )
                if st.button(
                    f"删除选定的 {provider_name} API Key",
                    key=f"{cfg_key}_delete_button",
                ):
                    config.app[cfg_key].remove(delete_key)
                    config.save_config()
                    st.success(f"{provider_name} API Key 已删除")


def render_wizard_progress(current_step):
    steps = [
        ("media", "视频与音频"),
        ("script", "文案与字幕"),
        ("result", "生成结果"),
    ]
    items = []
    current_index = next(
        (i for i, (step_key, _) in enumerate(steps) if step_key == current_step),
        0,
    )
    for index, (step_key, label) in enumerate(steps, start=1):
        step_position = index - 1
        state_class = " active" if step_key == current_step else ""
        if step_position < current_index:
            state_class += " done"
        items.append(
            f'<div class="mpt-wizard-step{state_class}" data-step="{index}">'
            f'<div class="mpt-wizard-index">STEP {index}</div>'
            f'<div class="mpt-wizard-title">{label}</div>'
            "</div>"
        )
    st.markdown(
        f'<div class="mpt-wizard">{"".join(items)}</div>',
        unsafe_allow_html=True,
    )


def hydrate_params_from_saved_state(params):
    params.video_subject = st.session_state.get("video_subject", "").strip()
    params.video_script = st.session_state.get("video_script", "")
    params.video_terms = (
        ""
        if params.video_source in ["local", "local_library"]
        else st.session_state.get("video_terms", "")
    )
    params.video_language = st.session_state.get("video_language_value", "")
    params.paragraph_number = st.session_state.get("paragraph_number_input", 1)
    params.video_script_prompt = st.session_state.get(
        "video_script_prompt", ""
    ).strip()
    params.custom_system_prompt = (
        st.session_state.get("custom_system_prompt", "").strip()
        if st.session_state.get("use_custom_system_prompt", False)
        else ""
    )

    params.subtitle_enabled = bool(config.ui.get("subtitle_enabled", True))
    params.subtitle_position = config.ui.get("subtitle_position", "bottom")
    params.custom_position = float(config.ui.get("custom_position", 70.0))
    params.font_name = config.ui.get("font_name", "MicrosoftYaHeiBold.ttc")
    params.text_fore_color = config.ui.get("text_fore_color", "#FFFFFF")
    params.font_size = int(config.ui.get("font_size", 60))
    params.stroke_color = config.ui.get("stroke_color", "#000000")
    params.stroke_width = float(config.ui.get("stroke_width", 1.5))
    subtitle_background_enabled = bool(
        config.ui.get("subtitle_background_enabled", True)
    )
    params.text_background_color = (
        config.ui.get("subtitle_background_color", "#000000")
        if subtitle_background_enabled
        else False
    )
    params.rounded_subtitle_background = bool(
        config.ui.get("rounded_subtitle_background", False)
    )

    try:
        params.video_concat_mode = VideoConcatMode(
            st.session_state.get("video_concat_mode", VideoConcatMode.random.value)
        )
    except ValueError:
        params.video_concat_mode = VideoConcatMode.random

    try:
        params.video_transition_mode = VideoTransitionMode(
            st.session_state.get(
                "video_transition_mode", VideoTransitionMode.none.value
            )
        )
    except ValueError:
        params.video_transition_mode = VideoTransitionMode.none

    default_aspect_value = (
        VideoAspect.landscape.value
        if params.video_source == "coverr"
        else VideoAspect.portrait.value
    )
    saved_aspect_value = st.session_state.get(
        f"video_aspect_value_for_{params.video_source}", default_aspect_value
    )
    try:
        params.video_aspect = VideoAspect(saved_aspect_value)
    except ValueError:
        params.video_aspect = VideoAspect(default_aspect_value)

    params.video_clip_duration = int(st.session_state.get("video_clip_duration", 3))
    params.video_count = int(st.session_state.get("video_count", 1))
    params.match_materials_to_script = bool(
        st.session_state.get(
            "match_materials_to_script",
            config.app.get("match_materials_to_script", False),
        )
    )
    params.voice_name = config.ui.get("voice_name", "")
    params.voice_volume = float(st.session_state.get("voice_volume", 1.0))
    params.voice_rate = float(st.session_state.get("voice_rate", 1.0))
    params.bgm_type = st.session_state.get("bgm_type", "random")
    params.bgm_file = st.session_state.get(
        "bgm_file", st.session_state.get("custom_bgm_file_input", "")
    )
    params.bgm_volume = float(st.session_state.get("bgm_volume", 0.2))
    custom_audio_file_path = st.session_state.get("custom_audio_file_path", "")
    if custom_audio_file_path and os.path.exists(custom_audio_file_path):
        params.custom_audio_file = custom_audio_file_path
    return params


# 创建顶部设置入口
config.app["hide_config"] = False
config.ui["hide_log"] = False
st.markdown('<span id="mpt-settings-popover-marker"></span>', unsafe_allow_html=True)
with st.popover("设置", key="top_settings_popover"):
    middle_config_panel, right_config_panel, api_key_panel, material_library_panel = st.tabs(
        ["大模型", "视频源", "Key 管理", "素材库"]
    )

    # 左侧面板 - 大模型设置

    with middle_config_panel:
        st.subheader("大模型设置")
        # 下拉框需要展示“AIHubMix（推荐）”这类面向用户的文案，
        # 但配置文件和后端逻辑必须继续使用稳定的小写 provider id。
        # 因此这里显式维护 display label 和 provider id 的映射，避免
        # UI 文案变化污染 `config.app["llm_provider"]`。
        llm_provider_options = [
            ("DeepSeek", "deepseek"),
            ("OpenAI", "openai"),
            ("Claude", "claude"),
            ("Kimi", "moonshot"),
            ("Qwen", "qwen"),
            ("GLM", "glm"),
            ("Gemini", "gemini"),
        ]
        llm_provider_ids = [provider_id for _, provider_id in llm_provider_options]
        llm_provider_labels = {
            provider_id: label for label, provider_id in llm_provider_options
        }
        saved_llm_provider = config.app.get("llm_provider", "openai").lower()
        if saved_llm_provider not in llm_provider_ids:
            saved_llm_provider = "openai"

        # Streamlit 会把没有 key 的 selectbox 视为一个由 label/options/index
        # 共同决定的临时控件。如果每次选择后都根据 config.app 重新计算 index，
        # 用户第一次切换 provider 后控件可能被重建，表现为“必须选择两次才生效”。
        # 这里用稳定的 provider id 作为真实选项，并给控件固定 key；展示文案只
        # 通过 format_func 转换，避免 UI 文案变化影响状态。
        if st.session_state.get("llm_provider_select") not in (
            None,
            *llm_provider_ids,
        ):
            del st.session_state["llm_provider_select"]

        llm_provider = st.selectbox(
            tr("LLM Provider"),
            options=llm_provider_ids,
            index=llm_provider_ids.index(saved_llm_provider),
            format_func=lambda provider_id: llm_provider_labels[provider_id],
            key="llm_provider_select",
        )
        llm_helper = st.container()
        config.app["llm_provider"] = llm_provider

        llm_api_key = config.app.get(f"{llm_provider}_api_key", "")
        llm_secret_key = config.app.get(
            f"{llm_provider}_secret_key", ""
        )  # only for baidu ernie
        llm_base_url = config.app.get(f"{llm_provider}_base_url", "")
        llm_model_name = config.app.get(f"{llm_provider}_model_name", "")
        llm_account_id = config.app.get(f"{llm_provider}_account_id", "")

        tips = ""
        if llm_provider == "ollama":
            if not llm_model_name:
                llm_model_name = "qwen:7b"
            if not llm_base_url:
                llm_base_url = config.get_default_ollama_base_url()

            with llm_helper:
                docker_hint = ""
                if config.is_running_in_container():
                    docker_hint = "\n                            > 检测到容器环境，未配置 Base Url 时会默认使用 `http://host.docker.internal:11434/v1`\n"
                tips = f"""
                        ##### Ollama配置说明
                        - **API Key**: 随便填写，比如 123
                        - **Base Url**: 一般为 http://localhost:11434/v1
                            - 如果 `MoneyPrinterTurbo` 和 `Ollama` **不在同一台机器上**，需要填写 `Ollama` 机器的IP地址
                            - 如果 `MoneyPrinterTurbo` 是 `Docker` 部署，建议填写 `http://host.docker.internal:11434/v1`{docker_hint}
                        - **Model Name**: 使用 `ollama list` 查看，比如 `qwen:7b`
                        """

        if llm_provider == "openai":
            if not llm_model_name:
                llm_model_name = "gpt-3.5-turbo"
            with llm_helper:
                tips = """
                        ##### OpenAI 配置说明
                        > 需要VPN开启全局流量模式
                        - **API Key**: [点击到官网申请](https://platform.openai.com/api-keys)
                        - **Base Url**: 官方 OpenAI 可留空；如果使用 OpenAI 兼容供应商（例如 OpenRouter），请填写对应的兼容接口地址
                        - **Model Name**: 填写**有权限**的模型；如果使用兼容供应商，请填写该平台支持的模型 ID
                        """

        if llm_provider == "claude":
            if not llm_model_name:
                llm_model_name = "claude-3-5-sonnet-latest"
            if not llm_base_url:
                llm_base_url = "https://api.anthropic.com/v1"
            with llm_helper:
                tips = """
                        ##### Claude 配置说明
                        - **API Key**: 填写 Anthropic 控制台创建的 API Key
                        - **Base Url**: 默认 https://api.anthropic.com/v1
                        - **Model Name**: 例如 claude-3-5-sonnet-latest，也可以填写你账号可用的 Claude 模型名
                        """

        if llm_provider == "aihubmix":
            if not llm_model_name:
                llm_model_name = "gpt-5.4-mini"
            if not llm_base_url:
                llm_base_url = "https://aihubmix.com/v1"
            with llm_helper:
                tips = """
                        ##### AIHubMix 配置说明
                        - **注册链接**: [点击注册 AIHubMix](https://aihubmix.com/?aff=CEve)
                        - **Base Url**: 预填 https://aihubmix.com/v1
                        - **推荐模型**: 默认 gpt-5.4-mini，也可以填写 AIHubMix 支持的免费模型或其它模型 ID

                        推荐理由：
                        - **模型全**: Claude、GPT、Gemini、Grok、DeepSeek、通义等 700+ 模型一站覆盖
                        - **稳定**: 无限并发，永远在线，集群部署于谷歌云，长期为众多知名应用提供高并发服务
                        - **能力完整**: 文本、图片生成、视频生成、TTS、STT、向量嵌入、Rerank，多模态场景全搞定
                        - **计费透明**: 按量付费，无会员无包月，免费模型可使用
                        """

        if llm_provider == "aimlapi":
            if not llm_model_name:
                llm_model_name = "openai/gpt-4o-mini"
            if not llm_base_url:
                llm_base_url = "https://api.aimlapi.com/v1"
            with llm_helper:
                tips = """
                        ##### AIML API Configuration
                        - **API Key**: create one at https://aimlapi.com/app/keys
                        - **Base Url**: https://api.aimlapi.com/v1
                        - **Model Name**: for example `openai/gpt-4o-mini`, `openai/gpt-4o`, `anthropic/claude-sonnet-4.5`, or `google/gemini-3-flash-preview`
                        """

        if llm_provider == "evolink":
            if not llm_model_name:
                llm_model_name = "gpt-5.5"
            if not llm_base_url:
                llm_base_url = "https://direct.evolink.ai/v1"
            with llm_helper:
                tips = """
                        ##### EvoLink 配置说明
                        - **API Key**: [点击到官网申请](https://evolink.ai/dashboard/keys)
                        - **Base Url**: 默认 https://direct.evolink.ai/v1
                        - **Model Name**: 默认 gpt-5.5，也可以填写 EvoLink 支持的其它模型 ID
                        """

        if llm_provider == "moonshot":
            if not llm_model_name:
                llm_model_name = "moonshot-v1-8k"
            with llm_helper:
                tips = """
                        ##### Moonshot 配置说明
                        - **API Key**: [点击到官网申请](https://platform.moonshot.cn/console/api-keys)
                        - **Base Url**: 固定为 https://api.moonshot.cn/v1
                        - **Model Name**: 比如 moonshot-v1-8k，[点击查看模型列表](https://platform.moonshot.cn/docs/intro#%E6%A8%A1%E5%9E%8B%E5%88%97%E8%A1%A8)
                        """
        if llm_provider == "oneapi":
            if not llm_model_name:
                llm_model_name = (
                    "claude-3-5-sonnet-20240620"  # 默认模型，可以根据需要调整
                )
            with llm_helper:
                tips = """
                    ##### OneAPI 配置说明
                    - **API Key**: 填写您的 OneAPI 密钥
                    - **Base Url**: 填写 OneAPI 的基础 URL
                    - **Model Name**: 填写您要使用的模型名称，例如 claude-3-5-sonnet-20240620
                    """

        if llm_provider == "qwen":
            if not llm_model_name:
                llm_model_name = "qwen-max"
            with llm_helper:
                tips = """
                        ##### 通义千问Qwen 配置说明
                        - **API Key**: [点击到官网申请](https://dashscope.console.aliyun.com/apiKey)
                        - **Base Url**: 留空
                        - **Model Name**: 比如 qwen-max，[点击查看模型列表](https://help.aliyun.com/zh/dashscope/developer-reference/model-introduction#3ef6d0bcf91wy)
                        """

        if llm_provider == "g4f":
            if not llm_model_name:
                llm_model_name = "gpt-3.5-turbo"
            with llm_helper:
                tips = """
                        ##### gpt4free 配置说明
                        > [GitHub开源项目](https://github.com/xtekky/gpt4free)，可以免费使用GPT模型，但是**稳定性较差**
                        - **API Key**: 随便填写，比如 123
                        - **Base Url**: 留空
                        - **Model Name**: 比如 gpt-3.5-turbo，[点击查看模型列表](https://github.com/xtekky/gpt4free/blob/main/g4f/models.py#L308)
                        """
        if llm_provider == "azure":
            with llm_helper:
                tips = """
                        ##### Azure 配置说明
                        > [点击查看如何部署模型](https://learn.microsoft.com/zh-cn/azure/ai-services/openai/how-to/create-resource)
                        - **API Key**: [点击到Azure后台创建](https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/OpenAI)
                        - **Base Url**: 留空
                        - **Model Name**: 填写你实际的部署名
                        """

        if llm_provider == "gemini":
            if not llm_model_name:
                llm_model_name = "gemini-2.5-flash"

            with llm_helper:
                tips = """
                        ##### Gemini 配置说明
                        > 需要VPN开启全局流量模式
                        - **API Key**: [点击到官网申请](https://ai.google.dev/)
                        - **Base Url**: 留空
                        - **Model Name**: 比如 gemini-2.5-flash
                        """

        if llm_provider == "grok":
            if not llm_model_name:
                llm_model_name = "grok-4.3"
            if not llm_base_url:
                llm_base_url = "https://api.x.ai/v1"

            with llm_helper:
                tips = """
                        ##### Grok 配置说明
                        - **API Key**: 填写您的 GrokAPI 密钥
                        - **Base Url**: 填写 GrokAPI 的基础 URL
                        - **Model Name**: 比如 grok-4.3
                        """

        if llm_provider == "groq":
            if not llm_model_name:
                llm_model_name = "llama-3.3-70b-versatile"
            if not llm_base_url:
                llm_base_url = "https://api.groq.com/openai/v1"

            with llm_helper:
                tips = """
                        ##### Groq 配置说明
                        - **API Key**: [点击到官网申请](https://console.groq.com/keys)
                        - **Base Url**: 固定为 https://api.groq.com/openai/v1
                        - **Model Name**: 比如 llama-3.3-70b-versatile
                        """

        if llm_provider == "deepseek":
            if not llm_model_name:
                llm_model_name = "deepseek-chat"
            if not llm_base_url:
                llm_base_url = "https://api.deepseek.com"
            with llm_helper:
                tips = """
                        ##### DeepSeek 配置说明
                        - **API Key**: [点击到官网申请](https://platform.deepseek.com/api_keys)
                        - **Base Url**: 固定为 https://api.deepseek.com
                        - **Model Name**: 固定为 deepseek-chat
                        """

        if llm_provider == "glm":
            if not llm_model_name:
                llm_model_name = "glm-4-flash"
            if not llm_base_url:
                llm_base_url = "https://open.bigmodel.cn/api/paas/v4"
            with llm_helper:
                tips = """
                        ##### GLM 配置说明
                        - **API Key**: 填写智谱开放平台创建的 API Key
                        - **Base Url**: 默认 https://open.bigmodel.cn/api/paas/v4
                        - **Model Name**: 例如 glm-4-flash，也可以填写你账号可用的 GLM 模型名
                        """

        if llm_provider == "mimo":
            if not llm_model_name:
                llm_model_name = "mimo-v2.5-pro"
            if not llm_base_url:
                llm_base_url = "https://api.xiaomimimo.com/v1"
            with llm_helper:
                tips = """
                        ##### Xiaomi MiMo 配置说明
                        - **API Key**: [点击到官网申请](https://platform.xiaomimimo.com/docs/zh-CN/quick-start/first-api-call)
                        - **Base Url**: 固定为 https://api.xiaomimimo.com/v1
                        - **Model Name**: 默认 mimo-v2.5-pro，也可以按官方文档填写其它可用模型
                        """

        if llm_provider == "modelscope":
            if not llm_model_name:
                llm_model_name = "Qwen/Qwen3-32B"
            if not llm_base_url:
                llm_base_url = "https://api-inference.modelscope.cn/v1/"
            with llm_helper:
                tips = """
                        ##### ModelScope 配置说明
                        - **API Key**: [点击到官网申请](https://modelscope.cn/docs/model-service/API-Inference/intro)
                        - **Base Url**: 固定为 https://api-inference.modelscope.cn/v1/
                        - **Model Name**: 比如 Qwen/Qwen3-32B，[点击查看模型列表](https://modelscope.cn/models?filter=inference_type&page=1)
                        """

        if llm_provider == "ernie":
            with llm_helper:
                tips = """
                        ##### 百度文心一言 配置说明
                        - **API Key**: [点击到官网申请](https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application)
                        - **Secret Key**: [点击到官网申请](https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application)
                        - **Base Url**: 填写 **请求地址** [点击查看文档](https://cloud.baidu.com/doc/WENXINWORKSHOP/s/jlil56u11#%E8%AF%B7%E6%B1%82%E8%AF%B4%E6%98%8E)
                        """

        if llm_provider == "pollinations":
            if not llm_model_name:
                llm_model_name = "default"
            with llm_helper:
                tips = """
                        ##### Pollinations AI Configuration
                        - **API Key**: Optional - Leave empty for public access
                        - **Base Url**: Default is https://text.pollinations.ai/openai
                        - **Model Name**: Use 'openai-fast' or specify a model name
                        """

        if llm_provider == "litellm":
            if not llm_model_name:
                llm_model_name = "openai/gpt-4o-mini"
            with llm_helper:
                tips = """
                        ##### LiteLLM Configuration
                        > [LiteLLM](https://github.com/BerriAI/litellm) routes to 100+ LLM providers via a unified interface.
                        > Set your provider's API key as an env var: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `AWS_ACCESS_KEY_ID`, etc.
                        - **Model Name**: LiteLLM format — `openai/gpt-4o`, `anthropic/claude-sonnet-4-20250514`, `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0`, `gemini/gemini-2.5-flash`. See [full provider list](https://docs.litellm.ai/docs/providers)
                        """

        if tips and config.ui["language"] == "zh":
            with st.expander("配置说明", expanded=False):
                st.markdown(tips)

        st_llm_api_key = st.text_input(
            tr("API Key"), value=llm_api_key, type="password"
        )
        st_llm_base_url = st.text_input(tr("Base Url"), value=llm_base_url)
        st_llm_model_name = ""
        if llm_provider != "ernie":
            if llm_provider == "groq":
                effective_api_key = st_llm_api_key or llm_api_key
                effective_base_url = st_llm_base_url or llm_base_url
                groq_models = get_groq_model_ids(
                    api_key=effective_api_key,
                    base_url=effective_base_url,
                )

                if groq_models:
                    selected_index = 0
                    if llm_model_name in groq_models:
                        selected_index = groq_models.index(llm_model_name)

                    st_llm_model_name = st.selectbox(
                        tr("Model Name"),
                        options=groq_models,
                        index=selected_index,
                        key="groq_model_name_select",
                    )
                else:
                    st_llm_model_name = st.text_input(
                        tr("Model Name"),
                        value=llm_model_name,
                        key="groq_model_name_input",
                    )
                    if effective_api_key:
                        st.caption(
                            "Unable to load Groq model list right now. You can still enter a model name manually — note it won't be validated until generation."
                        )
                    else:
                        st.caption(
                            "Add a Groq API key to load available models automatically."
                        )
            else:
                st_llm_model_name = st.text_input(
                    tr("Model Name"),
                    value=llm_model_name,
                    key=f"{llm_provider}_model_name_input",
                )
            if st_llm_model_name:
                config.app[f"{llm_provider}_model_name"] = st_llm_model_name
        else:
            st_llm_model_name = None

        if st_llm_api_key:
            config.app[f"{llm_provider}_api_key"] = st_llm_api_key
        if st_llm_base_url:
            config.app[f"{llm_provider}_base_url"] = st_llm_base_url
        if st_llm_model_name:
            config.app[f"{llm_provider}_model_name"] = st_llm_model_name
        if llm_provider == "ernie":
            st_llm_secret_key = st.text_input(
                tr("Secret Key"), value=llm_secret_key, type="password"
            )
            config.app[f"{llm_provider}_secret_key"] = st_llm_secret_key

        if llm_provider == "cloudflare":
            st_llm_account_id = st.text_input(
                tr("Account ID"), value=llm_account_id
            )
            if st_llm_account_id:
                config.app[f"{llm_provider}_account_id"] = st_llm_account_id

    # 右侧面板 - API 密钥设置
    with right_config_panel:

        def get_keys_from_config(cfg_key):
            api_keys = config.app.get(cfg_key, [])
            if isinstance(api_keys, str):
                api_keys = [api_keys]
            api_key = ", ".join(api_keys)
            return api_key

        def save_keys_to_config(cfg_key, value):
            value = value.replace(" ", "")
            if value:
                config.app[cfg_key] = value.split(",")

        st.subheader("视频源设置")

        pexels_api_key = get_keys_from_config("pexels_api_keys")
        pexels_api_key = st.text_input(
            tr("Pexels API Key"), value=pexels_api_key, type="password"
        )
        save_keys_to_config("pexels_api_keys", pexels_api_key)

        pixabay_api_key = get_keys_from_config("pixabay_api_keys")
        pixabay_api_key = st.text_input(
            tr("Pixabay API Key"), value=pixabay_api_key, type="password"
        )
        save_keys_to_config("pixabay_api_keys", pixabay_api_key)

        coverr_api_key = get_keys_from_config("coverr_api_keys")
        coverr_api_key = st.text_input(
            tr("Coverr API Key"), value=coverr_api_key, type="password"
        )
        save_keys_to_config("coverr_api_keys", coverr_api_key)

    with api_key_panel:
        render_video_api_key_manager()

    with material_library_panel:
        st.subheader("本地素材库")
        render_local_material_library_manager(
            key_prefix="settings_material_library",
            compact=False,
        )

llm_provider = config.app.get("llm_provider", "").lower()
valid_wizard_steps = {"script", "media", "result"}
if st.session_state.get("wizard_step") not in valid_wizard_steps:
    st.session_state["wizard_step"] = "media"
wizard_step = st.session_state["wizard_step"]
render_script_step = wizard_step == "script"
render_media_step = wizard_step == "media"
render_result_step = wizard_step == "result"

params = VideoParams(video_subject="")
params.video_source = st.session_state.get(
    "video_source", config.app.get("video_source", "pexels")
)
params.match_materials_to_script = bool(
    st.session_state.get("match_materials_to_script", False)
)
uploaded_files = []
uploaded_audio_file = None
is_local_video_source = params.video_source in ["local", "local_library"]
params = hydrate_params_from_saved_state(params)

st.markdown('<div class="mpt-section-title">创作工作台</div>', unsafe_allow_html=True)
render_wizard_progress(wizard_step)

if render_script_step:
    step_panels = st.columns(2)
    left_panel = step_panels[0]
    right_panel = step_panels[1]
elif render_media_step:
    media_panels = st.columns([1.2, 0.8], gap="large")
    middle_panel = media_panels[0]
    audio_panel = media_panels[1]
else:
    result_panel = st.container()

if render_script_step:
    with left_panel:
        with st.container(border=True):
            st.write(tr("Video Script Settings"))
            params.video_subject = st.text_input(
                tr("Video Subject"),
                key="video_subject",
            ).strip()

            video_languages = [
                (tr("Auto Detect"), ""),
            ]
            for code in support_locales:
                video_languages.append((code, code))

            selected_index = st.selectbox(
                tr("Script Language"),
                index=0,
                options=range(
                    len(video_languages)
                ),  # Use the index as the internal option value
                format_func=lambda x: video_languages[x][
                    0
                ],  # The label is displayed to the user
            )
            params.video_language = video_languages[selected_index][1]
            st.session_state["video_language_value"] = params.video_language

            with st.expander(tr("Advanced Script Settings"), expanded=False):
                params.paragraph_number = st.slider(
                    tr("Script Paragraph Number"),
                    min_value=llm.MIN_SCRIPT_PARAGRAPH_NUMBER,
                    max_value=llm.MAX_SCRIPT_PARAGRAPH_NUMBER,
                    value=st.session_state.get("paragraph_number_input", 1),
                    key="paragraph_number_input",
                )
                params.video_script_prompt = st.text_area(
                    tr("Custom Script Requirements"),
                    height=100,
                    max_chars=llm.MAX_SCRIPT_PROMPT_LENGTH,
                    placeholder=tr("Custom Script Requirements Placeholder"),
                    key="video_script_prompt",
                ).strip()

                use_custom_system_prompt = st.checkbox(
                    tr("Use Custom System Prompt"),
                    help=tr("Use Custom System Prompt Help"),
                    key="use_custom_system_prompt",
                )

                if use_custom_system_prompt:
                    custom_system_prompt = st.text_area(
                        tr("Custom System Prompt"),
                        height=240,
                        max_chars=llm.MAX_SCRIPT_SYSTEM_PROMPT_LENGTH,
                        key="custom_system_prompt",
                    ).strip()
                    params.custom_system_prompt = custom_system_prompt
                else:
                    params.custom_system_prompt = ""

            script_button_label = (
                "生成视频文案"
                if is_local_video_source
                else tr("Generate Video Script and Keywords")
            )
            if st.button(script_button_label, key="auto_generate_script"):
                spinner_label = (
                    "正在生成视频文案"
                    if is_local_video_source
                    else tr("Generating Video Script and Keywords")
                )
                with st.spinner(spinner_label):
                    script = llm.generate_script(
                        video_subject=params.video_subject,
                        language=params.video_language,
                        paragraph_number=params.paragraph_number,
                        video_script_prompt=params.video_script_prompt,
                        custom_system_prompt=params.custom_system_prompt,
                    )
                    if "Error: " in script:
                        st.error(tr(script))
                    elif is_local_video_source:
                        st.session_state["video_script"] = script
                        st.session_state["video_terms"] = ""
                    else:
                        terms = llm.generate_terms(
                            params.video_subject,
                            script,
                            amount=8 if params.match_materials_to_script else 5,
                            match_script_order=params.match_materials_to_script,
                        )
                        if "Error: " in terms:
                            st.error(tr(terms))
                            st.stop()
                        st.session_state["video_script"] = script
                        st.session_state["video_terms"] = ", ".join(terms)
            params.video_script = st.text_area(
                tr("Video Script"), value=st.session_state["video_script"], height=280
            )
            if is_local_video_source:
                params.video_terms = ""
                st.session_state["video_terms"] = ""
            else:
                if st.button(tr("Generate Video Keywords"), key="auto_generate_terms"):
                    if not params.video_script:
                        st.error(tr("Please Enter the Video Subject"))
                        st.stop()

                    with st.spinner(tr("Generating Video Keywords")):
                        terms = llm.generate_terms(
                            params.video_subject,
                            params.video_script,
                            amount=8 if params.match_materials_to_script else 5,
                            match_script_order=params.match_materials_to_script,
                        )
                        if "Error: " in terms:
                            st.error(tr(terms))
                        else:
                            st.session_state["video_terms"] = ", ".join(terms)

                params.video_terms = st.text_area(
                    tr("Video Keywords"), value=st.session_state["video_terms"]
                )
                st.caption(
                    "想让画面和主题更一致，可以手动填写更具体的英文关键词。"
                    "例如草莓主题可填写：strawberry, fresh strawberries, strawberry close up。"
                    "需要跟随文案顺序时，可在高级视频设置中开启“按文案顺序匹配素材”。"
                )

if render_media_step:
    with middle_panel:
        with st.container(border=True):
            st.write(tr("Video Settings"))
            video_concat_modes = [
                (tr("Sequential"), "sequential"),
                (tr("Random"), "random"),
            ]
            video_sources = [
                (tr("Pexels"), "pexels"),
                (tr("Pixabay"), "pixabay"),
                (tr("Coverr"), "coverr"),
                (tr("Local file"), "local"),
                ("本地素材库", "local_library"),
            ]

            video_source_labels = {value: label for label, value in video_sources}
            video_source_values = [value for _, value in video_sources]
            saved_video_source_name = st.session_state.get(
                "video_source", config.app.get("video_source", "pexels")
            )
            if saved_video_source_name not in video_source_values:
                saved_video_source_name = "pexels"
                st.session_state["video_source"] = saved_video_source_name
            saved_video_source_index = video_source_values.index(saved_video_source_name)

            params.video_source = st.selectbox(
                tr("Video Source"),
                options=video_source_values,
                format_func=lambda value: video_source_labels[value],
                index=saved_video_source_index,
                key="video_source",
            )
            config.app["video_source"] = params.video_source

            if params.video_source == "local":
                # Streamlit 的文件类型校验对扩展名大小写敏感，这里同时放行大小写两种形式。
                uploaded_files = st.file_uploader(
                    tr("Upload Local Files"),
                    type=LOCAL_MATERIAL_FILE_TYPES
                    + [file_type.upper() for file_type in LOCAL_MATERIAL_FILE_TYPES],
                    accept_multiple_files=True,
                )
                st.caption(
                    "支持一次选择多个视频或图片文件；当前不支持直接上传文件夹。"
                    "文件数量不做硬性限制，单文件默认约 200MB，实际可上传数量取决于浏览器、内存、磁盘空间和后续合成性能。"
                    "为了让系统更准确地按文案自动排序，请用能描述画面的文件名，"
                    "例如 01_草莓特写.mp4、02_清洗草莓.mp4、03_草莓甜品.mp4。"
                )
                if uploaded_files:
                    local_videos_dir = utils.storage_dir("local_videos", create=True)
                    persisted_local_materials = []
                    for file in uploaded_files:
                        file_path = os.path.join(
                            local_videos_dir, f"{file.file_id}_{file.name}"
                        )
                        if not os.path.exists(file_path):
                            with open(file_path, "wb") as f:
                                f.write(file.getbuffer())
                        persisted_local_materials.append(
                            {
                                "provider": "local",
                                "url": file_path,
                                "duration": 0,
                            }
                        )
                    st.session_state["local_video_materials"] = (
                        persisted_local_materials
                    )

            if params.video_source == "local_library":
                visible_library_materials = render_local_material_library_manager(
                    key_prefix="video_source_library",
                    compact=True,
                    show_upload=False,
                    show_stats=False,
                )
                library_materials = list_local_material_library()
                if not library_materials:
                    st.info("本地素材库暂无素材，请到顶部设置中的素材库添加素材。")
                    st.session_state["local_library_video_materials"] = []
                else:
                    st.markdown("##### 选择本次使用的素材")
                    selected_library_materials = render_local_material_selection_list(
                        all_materials=library_materials,
                        visible_materials=visible_library_materials,
                        key_prefix="local_library",
                    )
                    st.caption(
                        f"素材库共 {len(library_materials)} 个素材，当前列表 {len(visible_library_materials)} 个，本次将使用 {len(selected_library_materials)} 个。"
                    )
                    st.session_state["local_library_video_materials"] = (
                        material_paths_to_session_materials(selected_library_materials)
                    )

            saved_concat_value = st.session_state.get(
                "video_concat_mode", VideoConcatMode.random.value
            )
            saved_concat_index = 1
            for i, (_, mode_value) in enumerate(video_concat_modes):
                if mode_value == saved_concat_value:
                    saved_concat_index = i
                    break
            selected_index = st.selectbox(
                tr("Video Concat Mode"),
                index=saved_concat_index,
                options=range(
                    len(video_concat_modes)
                ),  # Use the index as the internal option value
                format_func=lambda x: video_concat_modes[x][
                    0
                ],  # The label is displayed to the user
            )
            params.video_concat_mode = VideoConcatMode(
                video_concat_modes[selected_index][1]
            )
            st.session_state["video_concat_mode"] = params.video_concat_mode.value

            # 视频转场模式
            video_transition_modes = [
                (tr("None"), VideoTransitionMode.none.value),
                (tr("Shuffle"), VideoTransitionMode.shuffle.value),
                (tr("FadeIn"), VideoTransitionMode.fade_in.value),
                (tr("FadeOut"), VideoTransitionMode.fade_out.value),
                (tr("SlideIn"), VideoTransitionMode.slide_in.value),
                (tr("SlideOut"), VideoTransitionMode.slide_out.value),
            ]
            saved_transition_value = st.session_state.get(
                "video_transition_mode", VideoTransitionMode.none.value
            )
            saved_transition_index = 0
            for i, (_, mode_value) in enumerate(video_transition_modes):
                if mode_value == saved_transition_value:
                    saved_transition_index = i
                    break
            selected_index = st.selectbox(
                tr("Video Transition Mode"),
                options=range(len(video_transition_modes)),
                format_func=lambda x: video_transition_modes[x][0],
                index=saved_transition_index,
            )
            params.video_transition_mode = VideoTransitionMode(
                video_transition_modes[selected_index][1]
            )
            st.session_state["video_transition_mode"] = (
                params.video_transition_mode.value
            )

            video_aspect_ratios = [
                (tr("Portrait"), VideoAspect.portrait.value),
                (tr("Landscape"), VideoAspect.landscape.value),
            ]
            # Coverr 库 99% 是 16:9 横屏,默认竖屏会让画面被大量黑边包围。
            # 用 source-specific widget key 让每个 source 各自记忆 aspect 选择:
            #   - 首次切到 coverr → 默认 Landscape(index=1)
            #   - 其他 source 沿用 Portrait(index=0)
            #   - 用户在某 source 下手动改过 aspect,session_state 会记住,
            #     下次回到同一 source 时尊重用户选择,不会再被强制覆盖。
            default_aspect_index = 1 if params.video_source == "coverr" else 0
            saved_aspect_value = st.session_state.get(
                f"video_aspect_value_for_{params.video_source}"
            )
            if saved_aspect_value:
                aspect_values = [value for _, value in video_aspect_ratios]
                if saved_aspect_value in aspect_values:
                    default_aspect_index = aspect_values.index(saved_aspect_value)
            selected_index = st.selectbox(
                tr("Video Ratio"),
                options=range(
                    len(video_aspect_ratios)
                ),  # Use the index as the internal option value
                format_func=lambda x: video_aspect_ratios[x][
                    0
                ],  # The label is displayed to the user
                index=default_aspect_index,
                key=f"video_aspect_for_{params.video_source}",
            )
            params.video_aspect = VideoAspect(video_aspect_ratios[selected_index][1])
            st.session_state[f"video_aspect_value_for_{params.video_source}"] = (
                params.video_aspect.value
            )

            clip_duration_options = [2, 3, 4, 5, 6, 7, 8, 9, 10]
            saved_clip_duration = int(st.session_state.get("video_clip_duration", 3))
            clip_duration_index = (
                clip_duration_options.index(saved_clip_duration)
                if saved_clip_duration in clip_duration_options
                else 1
            )
            params.video_clip_duration = st.selectbox(
                tr("Clip Duration"),
                options=clip_duration_options,
                index=clip_duration_index,
                key="video_clip_duration",
            )
            video_count_options = [1, 2, 3, 4, 5]
            saved_video_count = int(st.session_state.get("video_count", 1))
            video_count_index = (
                video_count_options.index(saved_video_count)
                if saved_video_count in video_count_options
                else 0
            )
            params.video_count = st.selectbox(
                tr("Number of Videos Generated Simultaneously"),
                options=video_count_options,
                index=video_count_index,
                key="video_count",
            )

            with st.expander(tr("Advanced Video Settings"), expanded=False):
                # 默认关闭，避免影响老用户的随机素材体验。开启后只改变关键词和素材
                # 下载/拼接顺序，用于改善画面主题早于或晚于旁白的问题。
                params.match_materials_to_script = st.checkbox(
                    tr("Match Materials to Script Order"),
                    help=tr("Match Materials to Script Order Help"),
                    key="match_materials_to_script",
                )
                if params.match_materials_to_script and params.video_source in [
                    "local",
                    "local_library",
                ]:
                    st.caption(
                        "本地素材模式下，该选项会根据文案和素材文件名自动选择素材顺序，"
                        "再按排序结果拼接成片。请尽量使用能描述画面的文件名；"
                        "如果文件名无法判断内容，会保留原始顺序。"
                    )
                elif params.match_materials_to_script:
                    st.caption(
                        "在线素材模式下，该选项会让关键词生成、素材下载和视频拼接尽量跟随文案顺序。"
                    )
                config.app["match_materials_to_script"] = params.match_materials_to_script

                video_codec_options = [
                    ("libx264 (CPU)", "libx264"),
                    ("NVIDIA NVENC (h264_nvenc)", "h264_nvenc"),
                    ("AMD AMF (h264_amf)", "h264_amf"),
                    ("Intel QSV (h264_qsv)", "h264_qsv"),
                    ("Windows MediaFoundation (h264_mf)", "h264_mf"),
                    ("macOS VideoToolbox (h264_videotoolbox)", "h264_videotoolbox"),
                ]
                saved_video_codec = config.app.get("video_codec", "libx264")
                saved_video_codec_values = [item[1] for item in video_codec_options]
                if saved_video_codec not in saved_video_codec_values:
                    saved_video_codec = "libx264"
                selected_codec_index = saved_video_codec_values.index(saved_video_codec)
                selected_codec_index = st.selectbox(
                    tr("Video Encoder"),
                    options=range(len(video_codec_options)),
                    index=selected_codec_index,
                    format_func=lambda x: video_codec_options[x][0],
                    help=tr("Video Encoder Help"),
                )
                config.app["video_codec"] = video_codec_options[selected_codec_index][1]
    with audio_panel:
        with st.container(border=True):
            st.write(tr("Audio Settings"))

            # 添加TTS服务器选择下拉框
            tts_servers = [
                (voice.NO_VOICE_NAME, tr("No Voice")),
                ("azure-tts-v1", "微软语音 V1"),
                ("azure-tts-v2", "微软语音 V2"),
                ("siliconflow", "硅基流动语音"),
                ("gemini-tts", "Gemini 语音"),
                ("mimo-tts", "小米 MiMo 语音"),
                ("elevenlabs", "ElevenLabs 语音"),
                ("chatterbox", "自托管 Chatterbox"),
            ]

            # 获取保存的TTS服务器，默认为v1
            saved_tts_server = config.ui.get("tts_server", "azure-tts-v1")
            saved_tts_server_index = 0
            for i, (server_value, _) in enumerate(tts_servers):
                if server_value == saved_tts_server:
                    saved_tts_server_index = i
                    break

            selected_tts_server_index = st.selectbox(
                "语音合成服务",
                options=range(len(tts_servers)),
                format_func=lambda x: tts_servers[x][1],
                index=saved_tts_server_index,
            )

            selected_tts_server = tts_servers[selected_tts_server_index][0]
            config.ui["tts_server"] = selected_tts_server

            # 根据选择的TTS服务器获取声音列表
            filtered_voices = []

            if selected_tts_server == voice.NO_VOICE_NAME:
                # 无配音是显式模式，只提供一个稳定 sentinel。这样普通 TTS 的空配置
                # 不会被误判为静音，后端也能继续通过同一条音频/字幕流程生成视频。
                filtered_voices = [voice.NO_VOICE_NAME]
            elif selected_tts_server == "siliconflow":
                # 获取硅基流动的声音列表
                filtered_voices = voice.get_siliconflow_voices()
            elif selected_tts_server == "gemini-tts":
                # 获取Gemini TTS的声音列表
                filtered_voices = voice.get_gemini_voices()
            elif selected_tts_server == "mimo-tts":
                # 获取 Xiaomi MiMo TTS 的预置音色列表
                filtered_voices = voice.get_mimo_voices()
            elif selected_tts_server == "elevenlabs":
                # Read from session_state first so the API key is available before
                # the Play Voice button runs (which is earlier in the script than
                # the API key text_input widget).
                saved_elevenlabs_api_key = st.session_state.get(
                    "elevenlabs_api_key_input",
                    config.elevenlabs.get("api_key", ""),
                )
                if saved_elevenlabs_api_key:
                    config.elevenlabs["api_key"] = saved_elevenlabs_api_key
                cache_key = f"elevenlabs_voices_{saved_elevenlabs_api_key}"
                if cache_key not in st.session_state:
                    st.session_state[cache_key] = voice.get_elevenlabs_voices(
                        saved_elevenlabs_api_key
                    )
                filtered_voices = st.session_state[cache_key]
            elif selected_tts_server == "chatterbox":
                # 自托管 Chatterbox 服务的预置音色（来自 [chatterbox] voices 配置）
                _sync_chatterbox_config_from_session_state()
                filtered_voices = voice.get_chatterbox_voices()
            else:
                # 获取Azure的声音列表
                all_voices = voice.get_all_azure_voices(filter_locals=None)

                # 根据选择的TTS服务器筛选声音
                for v in all_voices:
                    if selected_tts_server == "azure-tts-v2":
                        # V2版本的声音名称中包含"v2"
                        if "V2" in v:
                            filtered_voices.append(v)
                    else:
                        # V1版本的声音名称中不包含"v2"
                        if "V2" not in v:
                            filtered_voices.append(v)

            if selected_tts_server == voice.NO_VOICE_NAME:
                friendly_names = {voice.NO_VOICE_NAME: tr("No Voice")}
            else:
                def _friendly(v):
                    if voice.is_elevenlabs_voice(v):
                        parts = v.split(":", 2)
                        return parts[2] if len(parts) >= 3 else v
                    if voice.is_chatterbox_voice(v):
                        name = v.split(":", 1)[1] if ":" in v else v
                        return name.replace("-Female", "").replace("-Male", "")
                    return (
                        v.replace("Female", tr("Female"))
                        .replace("Male", tr("Male"))
                        .replace("Neural", "")
                    )
                friendly_names = {v: _friendly(v) for v in filtered_voices}

            saved_voice_name = config.ui.get("voice_name", "")
            saved_voice_name_index = 0

            # 检查保存的声音是否在当前筛选的声音列表中
            if saved_voice_name in friendly_names:
                saved_voice_name_index = list(friendly_names.keys()).index(saved_voice_name)
            else:
                # 如果不在，则根据当前UI语言选择一个默认声音
                for i, v in enumerate(filtered_voices):
                    if v.lower().startswith(st.session_state["ui_language"].lower()):
                        saved_voice_name_index = i
                        break

            # 如果没有找到匹配的声音，使用第一个声音
            if saved_voice_name_index >= len(friendly_names) and friendly_names:
                saved_voice_name_index = 0

            # 确保有声音可选
            if friendly_names:
                selected_friendly_name = st.selectbox(
                    tr("Speech Synthesis"),
                    options=list(friendly_names.values()),
                    index=min(saved_voice_name_index, len(friendly_names) - 1)
                    if friendly_names
                    else 0,
                )

                voice_name = list(friendly_names.keys())[
                    list(friendly_names.values()).index(selected_friendly_name)
                ]
                params.voice_name = voice_name
                config.ui["voice_name"] = voice_name
            else:
                # 如果没有声音可选，显示提示信息
                st.warning(
                    tr(
                        "No voices available for the selected TTS server. Please select another server."
                    )
                )
                voice_name = ""
                params.voice_name = ""
                config.ui["voice_name"] = ""

            # 无配音模式会生成静音占位音频，不展示试听按钮，避免用户误以为需要测试声音。
            if (
                friendly_names
                and selected_tts_server != voice.NO_VOICE_NAME
                and st.button(tr("Play Voice"))
            ):
                if selected_tts_server == "chatterbox":
                    _sync_chatterbox_config_from_session_state()
                play_content = params.video_subject
                if not play_content:
                    play_content = params.video_script
                if not play_content:
                    # For ElevenLabs voices, detect language from the display name
                    # so the test text matches the voice's language.
                    if voice.is_elevenlabs_voice(voice_name):
                        parts = voice_name.split(":", 2)
                        display = parts[2] if len(parts) >= 3 else ""
                        _vi_chars = set("àáâãèéêìíòóôõùúýăđơưÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐƠƯ")
                        if any(c in _vi_chars for c in display):
                            play_content = "Xin chào, đây là đoạn âm thanh thử nghiệm giọng nói."
                        else:
                            play_content = tr("Voice Example")
                    else:
                        play_content = tr("Voice Example")
                with st.spinner(tr("Synthesizing Voice")):
                    temp_dir = utils.storage_dir("temp", create=True)
                    audio_file = os.path.join(temp_dir, f"tmp-voice-{str(uuid4())}.mp3")
                    sub_maker = voice.tts(
                        text=play_content,
                        voice_name=voice_name,
                        voice_rate=params.voice_rate,
                        voice_file=audio_file,
                        voice_volume=params.voice_volume,
                    )
                    # if the voice file generation failed, try again with a default content.
                    if not sub_maker:
                        play_content = "This is a example voice. if you hear this, the voice synthesis failed with the original content."
                        sub_maker = voice.tts(
                            text=play_content,
                            voice_name=voice_name,
                            voice_rate=params.voice_rate,
                            voice_file=audio_file,
                            voice_volume=params.voice_volume,
                        )

                    if sub_maker and os.path.exists(audio_file):
                        with open(audio_file, "rb") as f:
                            audio_bytes = f.read()
                        if audio_bytes:
                            st.audio(
                                audio_bytes,
                                format=_detect_audio_mime(audio_file, audio_bytes),
                            )
                        else:
                            logger.error(f"voice preview audio file is empty: {audio_file}")
                        if os.path.exists(audio_file):
                            os.remove(audio_file)

            # 当选择V2版本或者声音是V2声音时，显示服务区域和API key输入框
            if selected_tts_server == "azure-tts-v2" or (
                voice_name and voice.is_azure_v2_voice(voice_name)
            ):
                saved_azure_speech_region = config.azure.get("speech_region", "")
                saved_azure_speech_key = config.azure.get("speech_key", "")
                azure_speech_region = st.text_input(
                    tr("Speech Region"),
                    value=saved_azure_speech_region,
                    key="azure_speech_region_input",
                )
                azure_speech_key = st.text_input(
                    tr("Speech Key"),
                    value=saved_azure_speech_key,
                    type="password",
                    key="azure_speech_key_input",
                )
                config.azure["speech_region"] = azure_speech_region
                config.azure["speech_key"] = azure_speech_key

            # 当选择硅基流动时，显示API key输入框和说明信息
            if selected_tts_server == "siliconflow" or (
                voice_name and voice.is_siliconflow_voice(voice_name)
            ):
                saved_siliconflow_api_key = config.siliconflow.get("api_key", "")

                siliconflow_api_key = st.text_input(
                    tr("SiliconFlow API Key"),
                    value=saved_siliconflow_api_key,
                    type="password",
                    key="siliconflow_api_key_input",
                )

                # 显示硅基流动的说明信息
                st.info(
                    tr("SiliconFlow TTS Settings")
                    + ":\n"
                    + "- "
                    + tr("Speed: Range [0.25, 4.0], default is 1.0")
                    + "\n"
                    + "- "
                    + tr("Volume: Uses Speech Volume setting, default 1.0 maps to gain 0")
                )

                config.siliconflow["api_key"] = siliconflow_api_key

            # 当选择 Xiaomi MiMo TTS 时，复用 MiMo LLM provider 的 API Key。
            # 这样用户如果同时使用 MiMo 生成文案和语音，只需要维护一份密钥。
            if selected_tts_server == "mimo-tts" or (
                voice_name and voice.is_mimo_voice(voice_name)
            ):
                saved_mimo_api_key = config.app.get("mimo_api_key", "")

                mimo_api_key = st.text_input(
                    tr("MiMo API Key"),
                    value=saved_mimo_api_key,
                    type="password",
                    key="mimo_tts_api_key_input",
                )

                st.info(
                    tr("MiMo TTS Settings")
                    + ":\n"
                    + "- "
                    + tr("Uses Xiaomi MiMo V2.5 TTS preset voices")
                    + "\n"
                    + "- "
                    + tr("Speed and volume are currently handled by the provider defaults")
                )

                config.app["mimo_api_key"] = mimo_api_key

            # ElevenLabs API key section
            if selected_tts_server == "elevenlabs" or (
                voice_name and voice.is_elevenlabs_voice(voice_name)
            ):
                saved_elevenlabs_api_key = config.elevenlabs.get("api_key", "")

                elevenlabs_api_key = st.text_input(
                    tr("ElevenLabs API Key"),
                    value=saved_elevenlabs_api_key,
                    type="password",
                    key="elevenlabs_api_key_input",
                )

                _elevenlabs_models = [
                    "eleven_multilingual_v2",
                    "eleven_flash_v2_5",
                    "eleven_v3",
                ]
                saved_elevenlabs_model = config.elevenlabs.get(
                    "model_id", "eleven_multilingual_v2"
                )
                if saved_elevenlabs_model not in _elevenlabs_models:
                    saved_elevenlabs_model = "eleven_multilingual_v2"
                elevenlabs_model = st.selectbox(
                    tr("ElevenLabs Model"),
                    options=_elevenlabs_models,
                    index=_elevenlabs_models.index(saved_elevenlabs_model),
                    key="elevenlabs_model_select",
                )
                config.elevenlabs["model_id"] = elevenlabs_model

                st.info(
                    "ElevenLabs 语音设置：\n"
                    "- 请在 https://elevenlabs.io/app/settings/api-keys 获取 API Key\n"
                    "- 在 ElevenLabs 音色库中把需要的音色标记为 Favorite 后，这里才会显示"
                )

                if elevenlabs_api_key != saved_elevenlabs_api_key:
                    for k in list(st.session_state.keys()):
                        if k.startswith("elevenlabs_voices_"):
                            del st.session_state[k]

                config.elevenlabs["api_key"] = elevenlabs_api_key

            # Chatterbox API settings section (self-hosted, OpenAI-compatible)
            if selected_tts_server == "chatterbox" or (
                voice_name and voice.is_chatterbox_voice(voice_name)
            ):
                chatterbox_base_url = st.text_input(
                    "Chatterbox 服务地址",
                    value=config.chatterbox.get("base_url") or DEFAULT_CHATTERBOX_BASE_URL,
                    key="chatterbox_base_url_input",
                    placeholder="http://localhost:4123/v1",
                )
                config.chatterbox["base_url"] = (chatterbox_base_url or "").strip()

                chatterbox_api_key = st.text_input(
                    "Chatterbox API Key",
                    value=config.chatterbox.get("api_key", ""),
                    type="password",
                    key="chatterbox_api_key_input",
                )
                config.chatterbox["api_key"] = chatterbox_api_key

                chatterbox_model = st.text_input(
                    "Chatterbox 模型",
                    value=config.chatterbox.get("model_id") or DEFAULT_CHATTERBOX_MODEL,
                    key="chatterbox_model_input",
                )
                config.chatterbox["model_id"] = (
                    chatterbox_model or DEFAULT_CHATTERBOX_MODEL
                ).strip()

                _saved_chatterbox_voices = (
                    _parse_chatterbox_voices(config.chatterbox.get("voices"))
                    or DEFAULT_CHATTERBOX_VOICES
                )
                if isinstance(_saved_chatterbox_voices, list):
                    _saved_chatterbox_voices = ", ".join(_saved_chatterbox_voices)
                chatterbox_voices = st.text_input(
                    "Chatterbox 音色列表",
                    value=str(_saved_chatterbox_voices or ""),
                    key="chatterbox_voices_input",
                    placeholder="default-Female, narrator-Male",
                )
                config.chatterbox["voices"] = _parse_chatterbox_voices(chatterbox_voices)

                st.info(
                    "Chatterbox 语音设置（自托管）：\n"
                    "- 请先运行兼容 OpenAI 接口的 Chatterbox 服务，并把服务地址填写为 /v1 端点\n"
                    "- 音色列表用英文逗号分隔；-Female 或 -Male 只是用于在下拉框中标记性别\n"
                    "- Chatterbox 不支持这里的朗读音量参数，请优先使用朗读速度调整效果"
                )

            voice_volume_options = [0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0, 5.0]
            saved_voice_volume = float(st.session_state.get("voice_volume", 1.0))
            voice_volume_index = (
                voice_volume_options.index(saved_voice_volume)
                if saved_voice_volume in voice_volume_options
                else 2
            )
            params.voice_volume = st.selectbox(
                tr("Speech Volume"),
                options=voice_volume_options,
                index=voice_volume_index,
                key="voice_volume",
            )

            voice_rate_options = [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0]
            saved_voice_rate = float(st.session_state.get("voice_rate", 1.0))
            voice_rate_index = (
                voice_rate_options.index(saved_voice_rate)
                if saved_voice_rate in voice_rate_options
                else 2
            )
            params.voice_rate = st.selectbox(
                tr("Speech Rate"),
                options=voice_rate_options,
                index=voice_rate_index,
                key="voice_rate",
            )

            custom_audio_file_types = ["mp3", "wav", "m4a", "aac", "flac", "ogg"]
            uploaded_audio_file = st.file_uploader(
                tr("Custom Audio File"),
                type=custom_audio_file_types
                + [file_type.upper() for file_type in custom_audio_file_types],
                accept_multiple_files=False,
                key="custom_audio_file_uploader",
            )
            if uploaded_audio_file:
                temp_dir = utils.storage_dir("temp", create=True)
                _, audio_ext = os.path.splitext(
                    os.path.basename(uploaded_audio_file.name)
                )
                audio_ext = audio_ext.lower() or ".mp3"
                custom_audio_path = os.path.join(
                    temp_dir, f"custom-audio-{uploaded_audio_file.file_id}{audio_ext}"
                )
                with open(custom_audio_path, "wb") as f:
                    f.write(uploaded_audio_file.getbuffer())
                st.session_state["custom_audio_file_path"] = custom_audio_path
                params.custom_audio_file = custom_audio_path
                st.audio(uploaded_audio_file, format="audio/mp3")
                st.info(
                    tr(
                        "Custom audio will be used directly. TTS synthesis will be skipped for this task."
                    )
                )

            bgm_options = [
                (tr("No Background Music"), ""),
                (tr("Random Background Music"), "random"),
                (tr("Custom Background Music"), "custom"),
            ]
            saved_bgm_type = st.session_state.get("bgm_type", "random")
            bgm_values = [value for _, value in bgm_options]
            selected_bgm_index = (
                bgm_values.index(saved_bgm_type) if saved_bgm_type in bgm_values else 1
            )
            selected_index = st.selectbox(
                tr("Background Music"),
                index=selected_bgm_index,
                options=range(
                    len(bgm_options)
                ),  # Use the index as the internal option value
                format_func=lambda x: bgm_options[x][
                    0
                ],  # The label is displayed to the user
            )
            # Get the selected background music type
            params.bgm_type = bgm_options[selected_index][1]
            st.session_state["bgm_type"] = params.bgm_type

            # Show or hide components based on the selection
            if params.bgm_type == "custom":
                custom_bgm_file = st.text_input(
                    tr("Custom Background Music File"), key="custom_bgm_file_input"
                )
                if custom_bgm_file:
                    # 这里不直接用 os.path.exists 判断，因为用户常见输入是
                    # output000.mp3，这个文件名需要由服务层映射到 resource/songs
                    # 目录后再校验。服务层会统一限制目录和文件类型，避免任意路径读取。
                    params.bgm_file = custom_bgm_file.strip()
                    st.session_state["bgm_file"] = params.bgm_file
                    # st.write(f":red[已选择自定义背景音乐]：**{custom_bgm_file}**")
            bgm_volume_options = [
                0.0,
                0.1,
                0.2,
                0.3,
                0.4,
                0.5,
                0.6,
                0.7,
                0.8,
                0.9,
                1.0,
            ]
            saved_bgm_volume = float(st.session_state.get("bgm_volume", 0.2))
            bgm_volume_index = (
                bgm_volume_options.index(saved_bgm_volume)
                if saved_bgm_volume in bgm_volume_options
                else 2
            )
            params.bgm_volume = st.selectbox(
                tr("Background Music Volume"),
                options=bgm_volume_options,
                index=bgm_volume_index,
                key="bgm_volume",
            )

if render_script_step:
    with right_panel:
        with st.container(border=True):
            st.write(tr("Subtitle Settings"))
            params.subtitle_enabled = st.checkbox(
                tr("Enable Subtitles"),
                value=bool(config.ui.get("subtitle_enabled", True)),
                key="subtitle_enabled",
            )
            config.ui["subtitle_enabled"] = params.subtitle_enabled
            font_names = get_all_fonts()
            saved_font_name = config.ui.get("font_name", "MicrosoftYaHeiBold.ttc")
            saved_font_name_index = 0
            if saved_font_name in font_names:
                saved_font_name_index = font_names.index(saved_font_name)
            params.font_name = st.selectbox(
                tr("Font"),
                font_names,
                index=saved_font_name_index,
                format_func=format_font_name,
            )
            config.ui["font_name"] = params.font_name

            subtitle_positions = [
                (tr("Top"), "top"),
                (tr("Center"), "center"),
                (tr("Bottom"), "bottom"),
                (tr("Custom"), "custom"),
            ]
            saved_subtitle_position = config.ui.get("subtitle_position", "bottom")
            saved_position_index = 2
            for i, (_, pos_value) in enumerate(subtitle_positions):
                if pos_value == saved_subtitle_position:
                    saved_position_index = i
                    break
            selected_index = st.selectbox(
                tr("Position"),
                index=saved_position_index,
                options=range(len(subtitle_positions)),
                format_func=lambda x: subtitle_positions[x][0],
            )
            params.subtitle_position = subtitle_positions[selected_index][1]
            config.ui["subtitle_position"] = params.subtitle_position

            if params.subtitle_position == "custom":
                saved_custom_position = config.ui.get("custom_position", 70.0)
                custom_position = st.text_input(
                    tr("Custom Position (% from top)"),
                    value=str(saved_custom_position),
                    key="custom_position_input",
                )
                try:
                    params.custom_position = float(custom_position)
                    if params.custom_position < 0 or params.custom_position > 100:
                        st.error(tr("Please enter a value between 0 and 100"))
                    else:
                        config.ui["custom_position"] = params.custom_position
                except ValueError:
                    st.error(tr("Please enter a valid number"))

            font_cols = st.columns([0.3, 0.7])
            with font_cols[0]:
                saved_text_fore_color = config.ui.get("text_fore_color", "#FFFFFF")
                params.text_fore_color = st.color_picker(
                    tr("Font Color"), saved_text_fore_color
                )
                config.ui["text_fore_color"] = params.text_fore_color

            with font_cols[1]:
                saved_font_size = config.ui.get("font_size", 60)
                params.font_size = st.slider(tr("Font Size"), 30, 100, saved_font_size)
                config.ui["font_size"] = params.font_size

        stroke_cols = st.columns([0.3, 0.7])
        with stroke_cols[0]:
            params.stroke_color = st.color_picker(
                tr("Stroke Color"),
                config.ui.get("stroke_color", "#000000"),
                key="stroke_color",
            )
            config.ui["stroke_color"] = params.stroke_color
        with stroke_cols[1]:
            params.stroke_width = st.slider(
                tr("Stroke Width"),
                0.0,
                10.0,
                float(config.ui.get("stroke_width", 1.5)),
                key="stroke_width",
            )
            config.ui["stroke_width"] = params.stroke_width

            subtitle_bg_cols = st.columns([0.4, 0.6])
            saved_subtitle_background_enabled = config.ui.get(
                "subtitle_background_enabled", True
            )
            with subtitle_bg_cols[0]:
                subtitle_background_enabled = st.checkbox(
                    tr("Enable Subtitle Background"),
                    value=saved_subtitle_background_enabled,
                )
            config.ui["subtitle_background_enabled"] = subtitle_background_enabled
            if subtitle_background_enabled:
                with subtitle_bg_cols[1]:
                    saved_subtitle_background_color = config.ui.get(
                        "subtitle_background_color", "#000000"
                    )
                    params.text_background_color = st.color_picker(
                        tr("Subtitle Background Color"),
                        saved_subtitle_background_color,
                    )
                    config.ui["subtitle_background_color"] = params.text_background_color
            else:
                params.text_background_color = False

            saved_rounded_subtitle_background = config.ui.get(
                "rounded_subtitle_background", False
            )
            # 背景关闭时，圆角背景没有可渲染的底色。这里禁用控件并保留原配置，
            # 用户下次重新开启字幕背景后，可以继续使用之前保存的圆角偏好。
            params.rounded_subtitle_background = st.checkbox(
                tr("Rounded Subtitle Background"),
                value=(
                    saved_rounded_subtitle_background
                    if subtitle_background_enabled
                    else False
                ),
                help=tr("Rounded Subtitle Background Help"),
                disabled=not subtitle_background_enabled,
            )
        if subtitle_background_enabled:
            config.ui["rounded_subtitle_background"] = (
                params.rounded_subtitle_background
            )

if render_media_step:
    nav_cols = st.columns([1, 1.4, 1])
    with nav_cols[1]:
        if st.button("下一步：文案和字幕设置", use_container_width=True, type="primary"):
            config.save_config()
            st.session_state["wizard_step"] = "script"
            st.rerun()

if render_script_step:
    st.markdown('<div class="mpt-section-title">生成视频</div>', unsafe_allow_html=True)
    nav_cols = st.columns([0.8, 1, 1, 0.8])
    with nav_cols[1]:
        if st.button("上一步：视频和音频设置", use_container_width=True):
            config.save_config()
            st.session_state["wizard_step"] = "media"
            st.rerun()

    with nav_cols[2]:
        start_button = st.button(
            tr("Generate Video"),
            use_container_width=True,
            type="primary",
        )
else:
    start_button = False

if render_script_step and start_button:
    config.save_config()
    task_id = str(uuid4())
    if not params.video_subject and not params.video_script:
        st.error(tr("Video Script and Subject Cannot Both Be Empty"))
        scroll_to_bottom()
        st.stop()

    if params.video_source not in [
        "pexels",
        "pixabay",
        "coverr",
        "local",
        "local_library",
    ]:
        st.error(tr("Please Select a Valid Video Source"))
        scroll_to_bottom()
        st.stop()

    if params.video_source == "pexels" and not config.app.get("pexels_api_keys", ""):
        st.error(tr("Please Enter the Pexels API Key"))
        scroll_to_bottom()
        st.stop()

    if params.video_source == "pixabay" and not config.app.get("pixabay_api_keys", ""):
        st.error(tr("Please Enter the Pixabay API Key"))
        scroll_to_bottom()
        st.stop()

    if params.video_source == "coverr" and not config.app.get("coverr_api_keys", ""):
        st.error(tr("Please Enter the Coverr API Key"))
        scroll_to_bottom()
        st.stop()

    if uploaded_audio_file:
        task_dir = utils.task_dir(task_id)
        # 上传文件名来自浏览器，不能直接拼到磁盘路径里；这里只保留扩展名，
        # 并使用固定文件名保存到当前任务目录，避免路径穿越或特殊字符问题。
        _, audio_ext = os.path.splitext(os.path.basename(uploaded_audio_file.name))
        audio_ext = audio_ext.lower() or ".mp3"
        custom_audio_path = os.path.join(task_dir, f"custom-audio{audio_ext}")
        with open(custom_audio_path, "wb") as f:
            f.write(uploaded_audio_file.getbuffer())
        params.custom_audio_file = custom_audio_path

    if uploaded_files:
        local_videos_dir = utils.storage_dir("local_videos", create=True)
        # 每次重新上传时都以本次选择的素材为准，避免旧素材不断重复追加。
        params.video_materials = []
        persisted_local_materials = []
        for file in uploaded_files:
            file_path = os.path.join(local_videos_dir, f"{file.file_id}_{file.name}")
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
                m = MaterialInfo()
                m.provider = "local"
                m.url = file_path
                params.video_materials.append(m)
                persisted_local_materials.append(
                    {
                        "provider": m.provider,
                        "url": m.url,
                        "duration": m.duration,
                    }
                )
        # 将已上传并保存到本地的视频素材写入会话，供后续只改文案时直接复用。
        st.session_state["local_video_materials"] = persisted_local_materials
    elif params.video_source == "local" and st.session_state["local_video_materials"]:
        # 当用户没有重新上传文件时，复用最近一次已经保存到磁盘的本地素材列表。
        params.video_materials = []
        for material in st.session_state["local_video_materials"]:
            m = MaterialInfo()
            m.provider = material.get("provider", "local")
            m.url = material.get("url", "")
            m.duration = material.get("duration", 0)
            if m.url:
                params.video_materials.append(m)
    elif params.video_source == "local_library":
        library_materials = st.session_state.get("local_library_video_materials", [])
        params.video_materials = []
        for material in library_materials:
            m = MaterialInfo()
            m.provider = material.get("provider", "local")
            m.url = material.get("url", "")
            m.duration = material.get("duration", 0)
            if m.url:
                params.video_materials.append(m)

        if not params.video_materials:
            st.error("请先在本地素材库中添加并选择素材")
            scroll_to_bottom()
            st.stop()

        params.video_source = "local"

    generating_overlay = st.empty()
    show_generating_overlay(generating_overlay)
    logger.info(tr("Start Generating Video"))
    logger.info(utils.to_json(params))

    try:
        result = tm.start(task_id=task_id, params=params)
    except Exception as e:
        generating_overlay.empty()
        logger.exception(e)
        st.error(tr("Video Generation Failed"))
        scroll_to_bottom()
        st.stop()

    if not result or "videos" not in result:
        generating_overlay.empty()
        st.error(tr("Video Generation Failed"))
        logger.error(tr("Video Generation Failed"))
        scroll_to_bottom()
        st.stop()

    video_files = result.get("videos", [])
    st.session_state["generated_video_files"] = video_files
    st.session_state["last_task_id"] = task_id
    logger.info(tr("Video Generation Completed"))
    generating_overlay.empty()
    st.session_state["wizard_step"] = "result"
    st.rerun()

if render_result_step:
    with result_panel:
        st.markdown('<div class="mpt-section-title">生成结果</div>', unsafe_allow_html=True)
        video_files = st.session_state.get("generated_video_files", [])
        if video_files:
            player_cols = st.columns(len(video_files) * 2 + 1)
            for i, url in enumerate(video_files):
                player_cols[i * 2 + 1].video(url)
        else:
            st.info("还没有生成结果，请先完成前两步并点击生成。")

        result_nav_cols = st.columns([1, 1, 1])
        with result_nav_cols[0]:
            if st.button("返回视频和音频设置", use_container_width=True):
                st.session_state["wizard_step"] = "media"
                st.rerun()
        with result_nav_cols[1]:
            if st.button("返回文案和字幕设置", use_container_width=True):
                st.session_state["wizard_step"] = "script"
                st.rerun()
        with result_nav_cols[2]:
            if st.button("打开结果文件夹", use_container_width=True):
                if st.session_state.get("last_task_id"):
                    open_task_folder(st.session_state["last_task_id"])

config.save_config()
