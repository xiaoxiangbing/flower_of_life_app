# pdf.py
import re
from fpdf import FPDF
from datetime import datetime
import os

def asset_path(*parts: str) -> str:
    """
    先按当前工作目录解析相对路径；找不到再退回到模块目录拼接。
    不写死绝对路径，便于服务器部署。
    """
    p1 = os.path.join(*parts)
    if os.path.exists(p1):
        return p1
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, *parts)

def clean_noise(text: str) -> str:
    """清理 TXT 中不符合阅读习惯的杂质符号。"""
    if not text:
        return text

    # 统一换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 去掉 Markdown 强调标记：**粗体**、*斜体*、***加粗斜体***
    # 注意：仅去除星号，保留中间文字
    text = re.sub(r'\*{1,3}([^\n*]+?)\*{1,3}', r'\1', text)

    # 删除“整行的分隔线”，如 --- / ---- / —— 等（只在单独一行时删除）
    text = re.sub(r'^\s*[-_–—]{3,}\s*$', '', text, flags=re.MULTILINE)

    # 去掉每行尾部多余空格
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

    # 轻微整理项目符号：行首的 "• " -> "•"
    text = re.sub(r'^\s*•\s*', '•', text, flags=re.MULTILINE)

    # 折叠 3 个以上空行为 2 个
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text

class FlowerOfLifeReportConverter:
    def __init__(self, image_path=None, user_name=None):
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=False)  # 禁用自动分页
        self.section_data = {}
        self.image_path = image_path
        self.user_name = user_name

        # 中文字体（相对路径，兼容服务器部署）
        self.font_name = "SimHei"
        try:
            font_file = asset_path("fonts", "simhei.ttf")
            self.pdf.add_font(self.font_name, style="",  fname=font_file, uni=True)
            self.pdf.add_font(self.font_name, style="B", fname=font_file, uni=True)
            self.pdf.add_font(self.font_name, style="I", fname=font_file, uni=True)
            self.pdf.add_font(self.font_name, style="BI",fname=font_file, uni=True)
        except Exception as e:
            print(f"警告: 中文字体加载失败，将使用内置字体（中文可能显示为空白）: {e}")
            self.font_name = "Arial"

    def parse_text_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            raw = file.read()

        # 先做一次全局清洗（可去除文件头部中可能的 **、--- 等）
        raw = clean_noise(raw)

        # 提取头部信息
        name_match  = re.search(r'姓名[:：]\s*(.+)', raw)
        date_match  = re.search(r'日期[:：]\s*(.+)', raw)
        image_match = re.search(r'图片路径[:：]\s*(.+)', raw)

        self.section_data['name']  = self.user_name or (name_match.group(1).strip() if name_match else "未知")
        self.section_data['date']  = date_match.group(1).strip() if date_match else datetime.now().strftime("%Y-%m-%d")
        self.section_data['image_path'] = image_match.group(1).strip() if image_match else None

        if not self.image_path and self.section_data['image_path']:
            self.image_path = self.section_data['image_path']

        # 去掉单独的抬头行，保留正文
        content = re.sub(r'^生命之花分析报告\s*$', '', raw, flags=re.MULTILINE).strip()

        # ——仅识别“行首的 1. 标题”为章节，避免把 xxx.jpg、小数点当标题——
        title_pat = re.compile(r'^\s*\*{0,2}(\d+)\.\s*([^\n]+?)\s*\*{0,2}\s*$', re.MULTILINE)
        matches = list(title_pat.finditer(content))

        for i, m in enumerate(matches):
            start = m.end()
            end   = matches[i+1].start() if i+1 < len(matches) else len(content)
            key   = f"{m.group(1)}. {m.group(2).strip()}"  # 如：1. 图案结构解读
            value = content[start:end]
            # 每节正文做清洗，去 **、--- 等
            value = clean_noise(value)
            # 适度清理：去掉引用符、多余空行
            value = re.sub(r'^\s*>\s*', '', value, flags=re.MULTILINE)
            value = re.sub(r'\n\s*\n', '\n\n', value).strip()
            self.section_data[key] = value

    def create_pdf(self, output_path):
        # 封面
        self.pdf.add_page()
        self.pdf.image(asset_path("fengmian.png"), x=0, y=0, w=210, h=297)

        # 正文（从第二页开始）
        self._fill_text_on_new_pages()
        self.pdf.output(output_path)
        print(f"PDF已生成: {output_path}")
        return output_path

    def _fill_text_on_new_pages(self):
        # 第二页先铺背景并画出抬头/矩形框
        self._add_page_with_background(with_header=True)

        sections_order = [
            "1. 图案结构解读",
            "2. 颜色能量解读",
            "3. 绘画表现方式",
            "4. 性格与核心天赋",
            "5. 荣格原型分析",
            "6. 职业与发展方向",
            "7. 成长与建议",
            "8. 总结金句",
        ]
        for title in sections_order:
            content = self.section_data.get(title, "")
            if content:
                self._add_section(title, content)

    def _add_page_with_background(self, with_header=True):
        self.pdf.add_page()
        self.pdf.image(asset_path("background.png"), x=0, y=0, w=210, h=297)
        self.pdf.ln(5)

        if with_header:
            # 抬头
            self.pdf.set_font(self.font_name, 'B', 20)
            self.pdf.set_text_color(57, 96, 156)
            self.pdf.cell(0, 10, "生命之花分析报告", ln=True, align='C')
            self.pdf.ln(5)

            self.pdf.set_font(self.font_name, '', 12)
            self.pdf.set_text_color(100, 100, 100)
            self.pdf.cell(0, 8, "訫香方阁", ln=True, align='C')
            self.pdf.cell(0, 8, "AI解密人生～树洞计划～帮你读懂自己", ln=True, align='C')
            self.pdf.ln(10)

            # 信息矩形框
            box_width, box_height = 150, 50
            x_center = (210 - box_width) / 2
            y_pos = self.pdf.get_y()
            self.pdf.rect(x_center, y_pos, box_width, box_height)

            self.pdf.set_font(self.font_name, 'B', 14)
            self.pdf.set_text_color(0, 0, 0)
            text_start_y = y_pos + (box_height - 16) / 2
            self.pdf.set_xy(x_center + 10, text_start_y)
            self.pdf.cell(80, 8, f"姓名：{self.section_data.get('name','')}")
            self.pdf.set_xy(x_center + 10, text_start_y + 8)
            self.pdf.cell(80, 8, f"日期：{self.section_data.get('date','')}")

            # 右侧小图（用户图/备用图）
            image_to_use = None
            if self.image_path:
                if str(self.image_path).startswith("http"):
                    image_to_use = self.image_path
                elif os.path.exists(self.image_path):
                    image_to_use = self.image_path
            if not image_to_use and os.path.exists(asset_path("flower.png")):
                image_to_use = asset_path("flower.png")

            if image_to_use:
                try:
                    img_size = 40
                    img_x = x_center + box_width - img_size - 10
                    img_y = y_pos + (box_height - img_size) / 2
                    self.pdf.image(image_to_use, x=img_x, y=img_y, w=img_size, h=img_size)
                except Exception as e:
                    print(f"警告: 无法加载图片 {image_to_use}: {e}")

            # 正文起始位置：紧贴矩形框下方
            content_start_y = y_pos + box_height + 5
            self.pdf.set_y(content_start_y)
        else:
            # 非首节页（背景后直接拉开一些空行）
            for _ in range(4):
                self.pdf.ln(8)

    def _add_section(self, title, content):
        # 再保险：渲染前再清洗一次（避免外部调用绕过 parse_text_file）
        content = clean_noise(content)
        if not content.strip():
            return

        # 节标题
        self.pdf.set_font(self.font_name, 'B', 16)
        self.pdf.set_text_color(57, 96, 156)

        # 临近页尾则新开一页（只铺背景，不再画抬头盒）
        if self.pdf.get_y() > 250:
            self._add_page_with_background(False)

        self.pdf.cell(0, 10, title, ln=True)
        self.pdf.ln(2)

        # 正文
        self.pdf.set_font(self.font_name, '', 12)
        self.pdf.set_text_color(0, 0, 0)

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                self.pdf.ln(5)
                continue
            if self.pdf.get_y() > 250:
                self._add_page_with_background(False)
            if line.startswith('•'):
                # 项目符号：小圆点 + 内容
                self.pdf.set_x(20)
                self.pdf.cell(5, 8, "•", ln=0)
                self.pdf.set_x(25)
                self.pdf.multi_cell(0, 8, line[1:].lstrip())
            elif line.startswith('- '):
                self.pdf.set_x(20)
                self.pdf.cell(5, 8, "•", ln=0)
                self.pdf.set_x(25)
                self.pdf.multi_cell(0, 8, line[2:].strip())
            else:
                self.pdf.multi_cell(0, 8, line)
            self.pdf.ln(4)
        self.pdf.ln(8)

def generate_pdf_from_txt(input_txt_path, image_path=None, user_name=None):
    converter = FlowerOfLifeReportConverter(image_path, user_name)
    converter.parse_text_file(input_txt_path)

    name = converter.section_data.get('name', '未知')
    date_str = converter.section_data.get('date', datetime.now().strftime("%Y-%m-%d"))
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%m.%d")
    except ValueError:
        formatted_date = datetime.now().strftime("%m.%d")

    output_filename = f"生命之花分析报告-{name}{formatted_date}.pdf"
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file = os.path.join(output_dir, output_filename)
    return converter.create_pdf(output_file)
