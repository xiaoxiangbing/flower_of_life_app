import os
import base64
import re
import requests
from openai import OpenAI
from datetime import datetime

# 初始化OpenAI客户端
client = OpenAI(
    api_key="sk-005adc9aad0245a78164ba3d3e066bd2",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MAX_IMAGE_SIZE = 19_000_000  # 字节，略小于接口最大限制

def get_image_url_or_base64(image_path):
    # 网络图片直接返回链接
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return {"url": image_path}
    # 本地图片转base64
    if not os.path.isfile(image_path):
        print("本地图片文件不存在，请检查路径。")
        return None
    with open(image_path, "rb") as img_file:
        img_bytes = img_file.read()
    if len(img_bytes) > MAX_IMAGE_SIZE:
        print(f"图片太大（{len(img_bytes)//1024//1024}MB），请上传小于 19MB 的图片。")
        return None
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    return {"url": f"data:image/jpeg;base64,{img_base64}"}

def clean_content(content):
    """清理内容中的多余字符"""
    # 移除#、*、等不需要的字符
    content = re.sub(r'[#*]', '', content)
    # 移除多余的空格
    content = re.sub(r' +', ' ', content)
    # 移除多余的空行
    content = re.sub(r'\n\s*\n', '\n\n', content)
    return content.strip()

def save_txt_report(content, name, image_path=None):
    # 针对表格行进行处理
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        # 跳过表头和分隔线
        if line.strip() in ["| 颜色 | 象征意义 |", "|------|----------|"]:
            continue
        # 去除所有"|"字符
        if "|" in line:
            new_lines.append(line.replace("|", "").strip())
        else:
            new_lines.append(line)
    cleaned_content = "\n".join(new_lines)
    
    # 确保 output 目录存在
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 保存为txt到 output 文件夹
    output_txt = os.path.join(output_dir, f"生命之花分析报告-{name}{datetime.now().strftime('%m.%d')}.txt")
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(f"生命之花分析报告\n姓名：{name}\n日期：{datetime.now().strftime('%Y-%m-%d')}\n")
        # 如果有图片路径，也保存到文件中
        if image_path:
            f.write(f"图片路径：{image_path}\n")
        f.write("\n")
        f.write(cleaned_content)
    print(f"文本报告已保存至: {os.path.abspath(output_txt)}")
    return output_txt

def analyze_image(image_path, name):
    """分析图片并生成报告"""
    image_url_obj = get_image_url_or_base64(image_path)
    if not image_url_obj:
        return None, "图片加载失败"
    
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant."}],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": image_url_obj,
                },
                {"type": "text", "text": "请你用以第二人称为这个名为\"生命之花\"的图片做一个完整的解析：1 . 图案结构解读 2 . 颜色能量解读 3 . 绘画表现方式 4 . 性格与核心天赋 5 . 荣格原型分析 6 . 职业与发展方向 7 . 成长与建议 8 . 总结金句？请回答具有逻辑，每个一级标题下的内容再分点回答。不要以表格的形式出现。不要出现敏感词：灵性"},
            ],
        },
    ]
    #提示词设计：请你以第二人称为这个名为\"生命之花\"的图片做一个完整的解析：1 . 图案结构解读 2 . 颜色能量解读 3 . 绘画表现方式 4 . 性格与核心天赋 5 . 荣格原型分析 
    # 6 . 职业与发展方向 7 . 成长与建议 8 . 总结金句？请回答具有逻辑，适当分点分行回答。不要以表格的形式出现，不要回答得太泛。不要出现敏感词：灵性

    try:
        completion = client.chat.completions.create(
            model="qwen-vl-max-latest",  # 支持图片输入的模型
            messages=messages,
        )
        analysis_result = completion.choices[0].message.content
        txt_file_path = save_txt_report(analysis_result, name, image_path)
        return txt_file_path, None
    except Exception as e:
        return None, str(e)