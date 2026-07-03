import json
import os
import subprocess
import sys
from datetime import datetime
from html import escape

import streamlit as st

# Add the root directory of the project to the system path
root_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.services import state as sm
from app.utils import utils

st.set_page_config(
    page_title="生成历史 - 混剪智能体",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        :root {
            --mpt-bg: #f3f7fb;
            --mpt-bg-soft: #f8fbff;
            --mpt-surface: rgba(255, 255, 255, 0.82);
            --mpt-surface-strong: rgba(255, 255, 255, 0.94);
            --mpt-border: rgba(148, 163, 184, 0.18);
            --mpt-border-strong: rgba(14, 165, 233, 0.26);
            --mpt-ink: #0f172a;
            --mpt-ink-soft: #334155;
            --mpt-muted: #64748b;
            --mpt-cyan: #0ea5e9;
            --mpt-teal: #14b8a6;
            --mpt-indigo: #4f46e5;
            --mpt-success-bg: rgba(16, 185, 129, 0.14);
            --mpt-success-text: #047857;
            --mpt-warning-bg: rgba(245, 158, 11, 0.16);
            --mpt-warning-text: #b45309;
            --mpt-danger-bg: rgba(239, 68, 68, 0.14);
            --mpt-danger-text: #b91c1c;
            --mpt-shadow-sm: 0 8px 24px rgba(15, 23, 42, 0.06);
            --mpt-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
            --mpt-radius-sm: 12px;
            --mpt-radius: 18px;
            --mpt-radius-lg: 24px;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(900px 420px at 0% -12%, rgba(14, 165, 233, 0.14), transparent 58%),
                radial-gradient(760px 360px at 100% -10%, rgba(79, 70, 229, 0.10), transparent 56%),
                linear-gradient(180deg, var(--mpt-bg-soft) 0%, var(--mpt-bg) 100%);
            color: var(--mpt-ink);
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        #MainMenu,
        footer {
            display: none !important;
        }

        .block-container {
            max-width: 1320px;
            padding-top: 1.2rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            color: var(--mpt-ink);
            letter-spacing: 0;
        }

        h1 {
            font-size: 2rem !important;
            line-height: 1.1 !important;
            margin-bottom: 0 !important;
        }

        h3 {
            font-size: 1.12rem !important;
            margin-bottom: 0.9rem !important;
        }

        [data-testid="stMetric"] {
            border: 1px solid var(--mpt-border);
            border-radius: var(--mpt-radius);
            padding: 16px 18px;
            background: var(--mpt-surface);
            backdrop-filter: blur(14px);
            box-shadow: var(--mpt-shadow-sm);
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid var(--mpt-border) !important;
            border-radius: var(--mpt-radius) !important;
            background: rgba(255, 255, 255, 0.9) !important;
            box-shadow: var(--mpt-shadow-sm) !important;
        }

        [data-testid="stMetricLabel"] {
            color: var(--mpt-muted);
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            color: var(--mpt-ink);
            font-weight: 700;
        }

        [data-testid="stTextArea"] textarea {
            min-height: 180px;
            border-radius: 14px !important;
            border: 1px solid var(--mpt-border) !important;
            background: rgba(255, 255, 255, 0.9) !important;
            color: var(--mpt-ink-soft) !important;
            line-height: 1.65 !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
        }

        .stButton > button {
            min-height: 42px;
            border-radius: 12px;
            border: 1px solid var(--mpt-border);
            background: linear-gradient(180deg, #ffffff, #f8fbff);
            color: var(--mpt-ink);
            font-weight: 600;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        }

        .stButton > button:hover {
            border-color: var(--mpt-border-strong);
            color: #0369a1;
            box-shadow: 0 10px 24px rgba(14, 165, 233, 0.12);
        }

        .mpt-history-shell {
            display: flex;
            flex-direction: column;
            gap: 18px;
        }

        .mpt-history-hero {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.55);
            border-radius: var(--mpt-radius-lg);
            padding: 24px 28px 22px;
            background:
                radial-gradient(560px 180px at 0% 0%, rgba(14, 165, 233, 0.12), transparent 72%),
                radial-gradient(480px 200px at 100% 0%, rgba(79, 70, 229, 0.11), transparent 72%),
                var(--mpt-surface-strong);
            backdrop-filter: blur(18px);
            box-shadow: var(--mpt-shadow);
        }

        .mpt-history-hero::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(90deg, rgba(14, 165, 233, 0.08), transparent 25%, transparent 75%, rgba(79, 70, 229, 0.08)),
                linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
                linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
            background-size: auto, 22px 22px, 22px 22px;
            pointer-events: none;
        }

        .mpt-history-toolbar {
            position: relative;
            z-index: 1;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 18px;
        }

        .mpt-history-back-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            min-height: 42px;
            padding: 0 16px;
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: rgba(255, 255, 255, 0.84);
            color: var(--mpt-ink);
            text-decoration: none;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.06);
            transition: all 0.2s ease;
            text-decoration: none !important;
        }

        .mpt-history-back-link:hover,
        .mpt-history-back-link:visited,
        .mpt-history-back-link:focus,
        .mpt-history-back-link:active {
            border-color: rgba(14, 165, 233, 0.34);
            color: #0369a1;
            transform: translateY(-1px);
            text-decoration: none !important;
        }

        .mpt-history-eyebrow {
            position: relative;
            z-index: 1;
            color: var(--mpt-cyan);
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
        }

        .mpt-history-heading {
            position: relative;
            z-index: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .mpt-history-heading p {
            margin: 0;
            color: var(--mpt-muted);
            font-size: 0.96rem;
            max-width: 720px;
            line-height: 1.6;
        }

        .mpt-history-card {
            border: 1px solid var(--mpt-border);
            border-radius: var(--mpt-radius);
            padding: 20px 22px;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(14px);
            box-shadow: var(--mpt-shadow-sm);
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }

        .mpt-history-card:hover {
            transform: translateY(-2px);
            border-color: rgba(14, 165, 233, 0.22);
            box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
        }

        .mpt-history-card-title {
            font-size: 1.08rem;
            font-weight: 700;
            color: var(--mpt-ink);
            margin-bottom: 10px;
            line-height: 1.45;
            word-break: break-word;
        }

        .mpt-history-meta-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px 18px;
            margin-bottom: 14px;
        }

        .mpt-history-meta-item {
            display: flex;
            flex-direction: column;
            gap: 4px;
            min-width: 0;
        }

        .mpt-history-meta-label {
            font-size: 0.76rem;
            color: var(--mpt-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 700;
        }

        .mpt-history-meta-value {
            font-size: 0.95rem;
            color: var(--mpt-ink-soft);
            line-height: 1.45;
            word-break: break-all;
        }

        .mpt-history-card-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            margin-top: 12px;
        }

        .mpt-history-card-footer .stButton {
            width: 100%;
        }

        .mpt-history-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            min-height: 34px;
            padding: 0 14px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 700;
            white-space: nowrap;
        }

        .mpt-history-status::before {
            content: "";
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: currentColor;
            opacity: 0.75;
        }

        .mpt-status-completed {
            background: var(--mpt-success-bg);
            color: var(--mpt-success-text);
        }

        .mpt-status-processing {
            background: var(--mpt-warning-bg);
            color: var(--mpt-warning-text);
        }

        .mpt-status-failed {
            background: var(--mpt-danger-bg);
            color: var(--mpt-danger-text);
        }

        .mpt-section-card {
            border: 1px solid var(--mpt-border);
            border-radius: var(--mpt-radius);
            padding: 20px 22px;
            background: rgba(255, 255, 255, 0.9);
            box-shadow: var(--mpt-shadow-sm);
            margin-bottom: 1rem;
        }

        .mpt-section-heading {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 14px;
            color: var(--mpt-ink);
            font-size: 1.02rem;
            font-weight: 700;
        }

        .mpt-section-heading::before {
            content: "";
            width: 5px;
            height: 20px;
            border-radius: 999px;
            background: linear-gradient(180deg, var(--mpt-cyan), var(--mpt-indigo));
        }

        .mpt-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .mpt-chip {
            display: inline-flex;
            align-items: center;
            min-height: 30px;
            padding: 0 12px;
            border-radius: 999px;
            border: 1px solid rgba(14, 165, 233, 0.16);
            background: rgba(14, 165, 233, 0.08);
            color: #0f4c81;
            font-size: 0.84rem;
            font-weight: 600;
        }

        .mpt-detail-title {
            font-size: 1.26rem;
            font-weight: 700;
            color: var(--mpt-ink);
            line-height: 1.45;
            margin-bottom: 6px;
            word-break: break-word;
        }

        .mpt-detail-subtitle {
            color: var(--mpt-muted);
            font-size: 0.92rem;
            line-height: 1.55;
            word-break: break-all;
        }

        .mpt-video-card [data-testid="stVideo"] {
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12);
        }

        .mpt-history-video-caption {
            text-align: center;
            color: var(--mpt-muted);
            font-size: 12px;
            margin-top: 10px;
            font-weight: 600;
        }

        .mpt-empty-state {
            border: 1px dashed rgba(148, 163, 184, 0.28);
            border-radius: var(--mpt-radius-lg);
            padding: 72px 24px;
            background: rgba(255, 255, 255, 0.72);
            text-align: center;
            color: var(--mpt-muted);
        }

        .mpt-empty-icon {
            font-size: 52px;
            margin-bottom: 14px;
        }

        .mpt-pagination {
            text-align: center;
            color: var(--mpt-muted);
            font-size: 0.92rem;
            font-weight: 600;
            padding-top: 10px;
        }

        @media (max-width: 900px) {
            .mpt-history-meta-grid {
                grid-template-columns: 1fr;
            }

            .mpt-history-card-footer {
                flex-direction: column;
                align-items: stretch;
            }
        }

        @media (max-width: 680px) {
            .block-container {
                padding-top: 0.8rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .mpt-history-hero {
                padding: 20px 18px 18px;
            }

            .mpt-history-toolbar {
                flex-direction: column;
                align-items: flex-start;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


STATUS_MAP = {
    0: ("排队中", "mpt-status-processing"),
    1: ("处理中", "mpt-status-processing"),
    2: ("已完成", "mpt-status-completed"),
    3: ("失败", "mpt-status-failed"),
}


def format_timestamp(timestamp):
    if not timestamp:
        return "未知时间"

    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        else:
            normalized = str(timestamp).replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(timestamp)


def get_task_status_display(state):
    return STATUS_MAP.get(state, ("未知", "mpt-status-processing"))


def open_path_in_file_manager(path: str) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)
        return

    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
        return

    subprocess.run(["xdg-open", path], check=False)


def load_task_details(task_id):
    try:
        task_dir = utils.task_dir(task_id)
        details = {"script": "", "terms": [], "videos": []}

        script_file = os.path.join(task_dir, "script.json")
        if os.path.exists(script_file):
            with open(script_file, "r", encoding="utf-8") as file:
                script_data = json.load(file)
            details["script"] = script_data.get("script", "")
            details["terms"] = script_data.get("terms", [])

        for index in range(1, 11):
            video_path = os.path.join(task_dir, f"final-{index}.mp4")
            if os.path.exists(video_path):
                details["videos"].append(video_path)

        return details
    except Exception as exc:
        st.error(f"加载任务详情失败: {exc}")
        return None


def build_task_meta(task, task_id):
    create_time = task.get("create_time", "")
    if not create_time and task_id:
        try:
            timestamp_part = task_id.split("-")[0]
            if len(timestamp_part) >= 10:
                create_time = int(timestamp_part)
        except Exception:
            pass

    if not create_time and task_id:
        task_dir = utils.task_dir(task_id)
        if os.path.isdir(task_dir):
            try:
                create_time = int(os.path.getmtime(task_dir))
            except OSError:
                pass
    return create_time


def render_history_hero(title, subtitle):
    st.markdown(
        f"""
        <div class="mpt-history-hero">
            <div class="mpt-history-toolbar">
                <a class="mpt-history-back-link" href="/" target="_self">← 返回主页</a>
            </div>
            <div class="mpt-history-eyebrow">History Center</div>
            <div class="mpt-history-heading">
                <h1>{escape(title)}</h1>
                <p>{escape(subtitle)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_task_card(task):
    task_id = task.get("task_id", "")
    state = task.get("state", 0)
    progress = int(task.get("progress", 0) or 0)
    create_time = build_task_meta(task, task_id)
    status_text, status_class = get_task_status_display(state)
    video_subject = task.get("video_subject") or "未命名任务"

    with st.container(border=True):
        info_col, action_col = st.columns([2.8, 1])
        with info_col:
            st.markdown(
                f'<div class="mpt-history-card-title">{escape(video_subject)}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <div class="mpt-history-meta-grid">
                    <div class="mpt-history-meta-item">
                        <div class="mpt-history-meta-label">任务 ID</div>
                        <div class="mpt-history-meta-value">{escape(task_id)}</div>
                    </div>
                    <div class="mpt-history-meta-item">
                        <div class="mpt-history-meta-label">创建时间</div>
                        <div class="mpt-history-meta-value">{escape(format_timestamp(create_time))}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with action_col:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("查看详情", key=f"view_{task_id}", use_container_width=True):
                st.session_state["selected_task_id"] = task_id
                st.rerun()


def render_script_section(task_id, script_text):
    with st.container(border=True):
        st.markdown(
            '<div class="mpt-section-heading">生成文案</div>',
            unsafe_allow_html=True,
        )
        st.text_area(
            "文案内容",
            value=script_text,
            height=220,
            key=f"script_{task_id}",
            disabled=True,
            label_visibility="collapsed",
        )


def render_terms_section(terms):
    with st.container(border=True):
        st.markdown(
            '<div class="mpt-section-heading">关键词</div>',
            unsafe_allow_html=True,
        )
        chips = "".join(
            f'<span class="mpt-chip">{escape(str(term))}</span>'
            for term in terms
            if str(term).strip()
        )
        st.markdown(f'<div class="mpt-chip-row">{chips}</div>', unsafe_allow_html=True)


def render_video_section(videos):
    with st.container(border=True):
        st.markdown(
            '<div class="mpt-section-heading">生成视频</div>',
            unsafe_allow_html=True,
        )

        video_count = len(videos)
        if video_count == 1:
            video_cols = [st.columns([1, 1.2, 1])[1]]
            video_width = 360
        elif video_count == 2:
            video_cols = st.columns(2)
            video_width = 320
        else:
            video_cols = st.columns(3)
            video_width = 300

        for index, video_path in enumerate(videos):
            with video_cols[index % len(video_cols)]:
                st.markdown('<div class="mpt-video-card">', unsafe_allow_html=True)
                st.video(video_path, width=video_width)
                st.markdown(
                    f'<div class="mpt-history-video-caption">视频 {index + 1}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)


def render_task_detail(task_id):
    task = sm.state.get_task(task_id)
    if not task:
        st.error("任务不存在或已被删除")
        return

    details = load_task_details(task_id)
    if not details:
        return

    create_time = build_task_meta(task, task_id)
    status_text, status_class = get_task_status_display(task.get("state", 0))
    video_subject = task.get("video_subject") or "未命名任务"

    with st.container(border=True):
        title_col, status_col = st.columns([3.2, 1.2])
        with title_col:
            st.markdown(
                f'<div class="mpt-detail-title">{escape(video_subject)}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="mpt-detail-subtitle">任务 ID：{escape(task_id)}</div>',
                unsafe_allow_html=True,
            )
        with status_col:
            st.markdown(
                f'<div style="padding-top: 6px;"><span class="mpt-history-status {status_class}">{escape(status_text)}</span></div>',
                unsafe_allow_html=True,
            )

    top_action_cols = st.columns([1, 5])
    with top_action_cols[0]:
        if st.button("← 返回列表", key="back_to_list", use_container_width=True):
            st.session_state.pop("selected_task_id", None)
            st.rerun()

    if details.get("script"):
        render_script_section(task_id, details["script"])

    if details.get("terms"):
        render_terms_section(details["terms"])

    if details.get("videos"):
        render_video_section(details["videos"])

    with st.container(border=True):
        st.markdown(
            '<div class="mpt-section-heading">操作</div>',
            unsafe_allow_html=True,
        )
        action_cols = st.columns([1, 1, 3])

        with action_cols[0]:
            if st.button(
                "打开文件夹",
                key=f"open_folder_{task_id}",
                use_container_width=True,
            ):
                task_folder = utils.task_dir(task_id)
                if os.path.exists(task_folder):
                    open_path_in_file_manager(task_folder)
                else:
                    st.error("任务文件夹不存在")

        with action_cols[1]:
            if st.button(
                "删除任务",
                key=f"delete_{task_id}",
                use_container_width=True,
            ):
                if st.session_state.get(f"confirm_delete_{task_id}", False):
                    sm.state.delete_task(task_id)
                    st.success("任务已删除")
                    st.session_state.pop("selected_task_id", None)
                    st.session_state.pop(f"confirm_delete_{task_id}", None)
                    st.rerun()
                else:
                    st.session_state[f"confirm_delete_{task_id}"] = True
                    st.warning("再次点击确认删除")


def render_empty_state():
    st.markdown(
        """
        <div class="mpt-empty-state">
            <div class="mpt-empty-icon">📭</div>
            <div style="font-size: 1.08rem; font-weight: 700; color: #0f172a; margin-bottom: 6px;">
                还没有生成历史
            </div>
            <div style="font-size: 0.94rem;">
                回到主页开始生成第一个视频，结果会自动出现在这里。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_history_hero(
    title="生成历史",
    subtitle="集中查看每次生成任务的状态、文案、素材结果和视频产物。这里更像你的创作归档区，而不是一张简单的任务表。",
)

selected_task_id = st.session_state.get("selected_task_id")
if selected_task_id:
    render_task_detail(selected_task_id)
else:
    if "history_page" not in st.session_state:
        st.session_state["history_page"] = 1

    page_size = 10
    current_page = st.session_state["history_page"]
    tasks, total = sm.state.get_all_tasks(current_page, page_size)

    if not tasks:
        render_empty_state()
    else:
        tasks_sorted = sorted(
            tasks,
            key=lambda task: task.get("create_time", 0) or 0,
            reverse=True,
        )

        summary_cols = st.columns(3)
        summary_cols[0].metric("当前页任务", len(tasks_sorted))
        summary_cols[1].metric("历史总数", total)
        summary_cols[2].metric("当前页码", current_page)

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        for task in tasks_sorted:
            render_task_card(task)

        total_pages = (total + page_size - 1) // page_size
        if total_pages > 1:
            with st.container(border=True):
                page_cols = st.columns([1, 2.5, 1])
                with page_cols[0]:
                    if st.button(
                        "← 上一页",
                        disabled=current_page <= 1,
                        use_container_width=True,
                    ):
                        st.session_state["history_page"] = max(1, current_page - 1)
                        st.rerun()

                with page_cols[1]:
                    st.markdown(
                        f'<div class="mpt-pagination">第 {current_page} 页 / 共 {total_pages} 页 · 共 {total} 个任务</div>',
                        unsafe_allow_html=True,
                    )

                with page_cols[2]:
                    if st.button(
                        "下一页 →",
                        disabled=current_page >= total_pages,
                        use_container_width=True,
                    ):
                        st.session_state["history_page"] = min(
                            total_pages, current_page + 1
                        )
                        st.rerun()
