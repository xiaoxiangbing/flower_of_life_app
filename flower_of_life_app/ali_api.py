import os
import base64
from datetime import datetime
from openai import OpenAI

# ----------------------------
# 原有客户端初始化（保留）；建议使用环境变量传入 KEY
# ----------------------------
client = OpenAI(
    api_key="sk-005adc9aad0245a78164ba3d3e066bd2",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MAX_IMAGE_SIZE = 19_000_000  # 平台限制约 20MB

def get_image_url_or_base64(image_path: str):
    """保留原有：支持 http(s) URL 或本地文件转 base64。"""
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return {"url": image_path}
    with open(image_path, "rb") as f:
        data = f.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise ValueError("图片过大，请压缩后再试")
    b64 = base64.b64encode(data).decode("utf-8")
    return {"url": f"data:image/png;base64,{b64}"}

def ensure_output_dir() -> str:
    out = os.path.join(os.getcwd(), "output")
    os.makedirs(out, exist_ok=True)
    return out

def save_txt_report(text: str, name: str, image_path: str) -> str:
    """将结果落盘到 output 目录。"""
    out = ensure_output_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(image_path))[0] or "report"
    fname = f"{ts}_{name}_{base}.txt"
    path = os.path.join(out, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

# ----------------------------
# 默认提示词（保留）
# ----------------------------
DEFAULT_PROMPT = (
    '请你用以第二人称为这个名为"生命之花"的图片做一个完整的解析：'
    '1 . 图案结构解读 2 . 颜色能量解读 3 . 绘画表现方式 4 . 性格与核心天赋 '
    '5 . 荣格原型分析 6 . 职业与发展方向 7 . 成长与建议 8 . 总结金句？'
    '请回答具有逻辑，每个一级标题下的内容再分点回答。不要以表格的形式出现。'
    '不要出现敏感词：灵性'
)

def analyze_image(image_path: str, name: str, prompt_override: str | None = None):
    """
    新增：prompt_override 为可选提示词。
    - 当提供时：完全替换 DEFAULT_PROMPT；并在末尾自动追加“请不要以表格的形式出现回答”。
    - 未提供：继续使用 DEFAULT_PROMPT（保持原行为）。
    """
    image_url_obj = get_image_url_or_base64(image_path)

    # 处理可选提示词并自动追加“不要表格”
    if prompt_override and prompt_override.strip():
        user_prompt = prompt_override.strip()
        if "不要以表格的形式" not in user_prompt and "不要以表格的形式出现回答" not in user_prompt:
            user_prompt += "。请不要以表格的形式出现回答"
    else:
        user_prompt = DEFAULT_PROMPT

    messages = [
        {"role": "system", "content": [{"type": "text", "text": "You are a helpful assistant."}]},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": image_url_obj},
                {"type": "text", "text": user_prompt},
            ],
        },
    ]

    try:
        completion = client.chat.completions.create(
            model="qwen-vl-max-latest",
            messages=messages,
        )
        # DashScope 兼容模式 message.content 为纯文本
        analysis_result = completion.choices[0].message.content
        txt_file_path = save_txt_report(analysis_result, name, image_path)
        return txt_file_path, None
    except Exception as e:
        return None, str(e)
