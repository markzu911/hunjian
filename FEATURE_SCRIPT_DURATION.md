# 功能说明：根据视频时长生成文案

## 功能描述

当用户上传本地视频素材并设置每段视频的时长时，系统现在会自动计算总时长，并生成与之匹配的文案。

### 示例场景

- 用户上传了 **4 个视频**
- 每段设置为 **6 秒**
- 系统会自动计算：`4 × 6 = 24 秒`
- AI 生成的文案时长将控制在约 24 秒左右

## 技术实现

### 1. 修改 `app/services/llm.py`

#### 1.1 更新 `build_script_prompt` 函数

添加了 `target_duration` 参数（默认为 0，表示无时长约束）：

```python
def build_script_prompt(
    video_subject: str,
    language: str = "",
    paragraph_number: int = 1,
    video_script_prompt: str = "",
    custom_system_prompt: str = "",
    target_duration: float = 0,  # 新增参数
) -> str:
```

当 `target_duration > 0` 时，会在 AI 提示词中添加：

```
## Duration Constraint:
The script MUST be suitable for a video of approximately 24.0 seconds duration.
Please generate content that can be naturally narrated within this time frame.
For reference: typical narration speed is about 150-180 words per minute for English, 
or 4-5 Chinese characters per second.
```

#### 1.2 更新 `generate_script` 函数

同样添加 `target_duration` 参数并传递给 `build_script_prompt`：

```python
def generate_script(
    video_subject: str,
    language: str = "",
    paragraph_number: int = 1,
    video_script_prompt: str = "",
    custom_system_prompt: str = "",
    target_duration: float = 0,  # 新增参数
) -> str:
```

### 2. 修改 `app/services/task.py`

在 `generate_script` 函数中添加本地素材时长计算逻辑：

```python
def generate_script(task_id, params):
    logger.info("\n\n## generating video script")
    video_script = params.video_script.strip()
    if not video_script:
        # 计算目标时长：如果用户上传了本地素材，根据素材数量和每段时长计算
        target_duration = 0
        if params.video_source == "local" and params.video_materials:
            material_count = len(params.video_materials)
            clip_duration = params.video_clip_duration or 5
            target_duration = material_count * clip_duration
            logger.info(
                f"calculated target script duration from local materials: "
                f"{material_count} materials × {clip_duration}s = {target_duration}s"
            )

        video_script = llm.generate_script(
            video_subject=params.video_subject,
            language=params.video_language,
            paragraph_number=params.paragraph_number,
            video_script_prompt=params.video_script_prompt,
            custom_system_prompt=params.custom_system_prompt,
            target_duration=target_duration,  # 传递计算的目标时长
        )
```

## 工作流程

1. **用户操作**：
   - 在 WebUI 中选择"本地文件"作为素材来源
   - 上传 N 个视频文件
   - 设置"视频片段时长"为 T 秒

2. **系统计算**：
   ```
   target_duration = N × T
   ```

3. **AI 生成**：
   - 系统将目标时长信息发送给 AI
   - AI 根据时长约束生成合适长度的文案
   - 对于中文：按 4-5 字/秒的朗读速度
   - 对于英文：按 150-180 词/分钟的朗读速度

4. **配音合成**：
   - 使用生成的文案进行 TTS 语音合成
   - 最终音频时长应该接近目标时长

## 注意事项

### 1. 时长精确性

- AI 生成的文案是**估算**，实际朗读时长可能有 ±10% 的偏差
- 不同 TTS 服务的朗读速度略有差异
- 建议为视频素材留有一定余量

### 2. 适用场景

此功能**仅在以下条件下生效**：

- ✅ `video_source = "local"`（本地素材）
- ✅ `video_materials` 不为空（已上传素材）
- ✅ 未手动填写文案（`video_script` 为空）

### 3. 其他素材来源

对于在线素材（Pexels、Pixabay、Coverr），系统会：
1. 先生成文案
2. 根据文案时长下载匹配的素材
3. 因此不需要预先约束文案时长

## 使用示例

### WebUI 操作流程

1. 打开 MoneyPrinterTurbo WebUI
2. 在"素材来源"中选择"本地文件"
3. 上传 4 个视频文件
4. 将"视频片段时长"设置为 6 秒
5. 填写视频主题（如"金钱的作用"）
6. 点击"生成文案"

**预期结果**：
- 日志中显示：`calculated target script duration from local materials: 4 materials × 6s = 24s`
- AI 生成约 24 秒时长的文案（中文约 96-120 字）

### API 调用示例

```python
from app.models.schema import VideoParams, MaterialInfo

# 准备本地素材
materials = [
    MaterialInfo(provider="local", url="/path/to/video1.mp4", duration=0),
    MaterialInfo(provider="local", url="/path/to/video2.mp4", duration=0),
    MaterialInfo(provider="local", url="/path/to/video3.mp4", duration=0),
    MaterialInfo(provider="local", url="/path/to/video4.mp4", duration=0),
]

# 创建任务参数
params = VideoParams(
    video_subject="金钱的作用",
    video_source="local",
    video_materials=materials,
    video_clip_duration=6,  # 每段 6 秒
    # 不填写 video_script，让 AI 自动生成
)

# 系统会自动计算：4 × 6 = 24 秒，并生成匹配时长的文案
```

## 日志输出

启用该功能后，你会在日志中看到：

```
## generating video script
calculated target script duration from local materials: 4 materials × 6s = 24s
generating video script: subject=金钱的作用, paragraph_number=1, target_duration=24.0s, ...
```

## 后续优化建议

1. **自适应调整**：如果 TTS 生成的音频时长与目标差距过大，可以考虑：
   - 自动重新生成文案
   - 调整语音速率（`voice_rate`）

2. **用户反馈**：在 WebUI 中显示预计时长和实际时长的对比

3. **多语言优化**：针对不同语言添加更精确的语速参考值

## 版本信息

- **修改日期**：2026-07-03
- **影响文件**：
  - `app/services/llm.py`
  - `app/services/task.py`
- **向后兼容**：✅ 是（新参数为可选，默认值为 0）
