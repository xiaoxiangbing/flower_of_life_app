# pdf.py
import re
from fpdf import FPDF
from datetime import datetime
import os

class FlowerOfLifeReportConverter:
    def __init__(self, image_path=None, user_name=None):
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=False)  # 禁用自动分页
        self.section_data = {}
        self.image_path = image_path  # 保存图片路径
        self.user_name = user_name    # 保存用户输入的姓名
        
        # 添加中文字体支持
        try:
            self.pdf.add_font("SimHei", style="", fname="fonts/simhei.ttf", uni=True)
            self.pdf.add_font("SimHei", style="B", fname="fonts/simhei.ttf", uni=True)
            self.pdf.add_font("SimHei", style="I", fname="fonts/simhei.ttf", uni=True)
            self.pdf.add_font("SimHei", style="BI", fname="fonts/simhei.ttf", uni=True)
            self.font_name = "SimHei"
        except Exception as e:
            print(f"警告: 未找到中文字体，使用默认字体可能显示异常: {e}")
            self.font_name = "Arial"

    def parse_text_file(self, file_path):
        """解析文本文件内容"""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # 提取姓名和日期
        name_match = re.search(r'姓名[:：]\s*(.+)', content)
        date_match = re.search(r'日期[:：]\s*(.+)', content)
        image_match = re.search(r'图片路径[:：]\s*(.+)', content)

        # 优先使用用户输入的姓名
        if self.user_name:
            self.section_data['name'] = self.user_name
        else:
            self.section_data['name'] = name_match.group(1).strip() if name_match else "未知"

        self.section_data['date'] = date_match.group(1).strip() if date_match else datetime.now().strftime("%Y-%m-%d")
        self.section_data['image_path'] = image_match.group(1).strip() if image_match else None

        # 如果类中没有设置图片路径但文件中有，则使用文件中的图片路径
        if not self.image_path and self.section_data['image_path']:
            self.image_path = self.section_data['image_path']

        # 清理内容
        cleaned_content = self._clean_content(content)

        # 分割章节 - 匹配格式如 "**1. 图案结构解读**"
        sections = re.split(r'(\*\*\d+\..+?\*\*)', cleaned_content)
        
        # 不再提取引言部分，直接处理章节
        # 处理章节
        for i in range(1, len(sections), 2):
            if i < len(sections) and i+1 < len(sections):
                section_title = sections[i].strip().replace('**', '')  # 移除标题中的 **
                section_content = sections[i+1].strip()
                # 清理内容中的多余符号
                section_content = self._clean_section_content(section_content)
                self.section_data[section_title] = section_content

    def _clean_content(self, content):
        """清理内容中的无关符号"""
        content = re.sub(r'^---$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^###$', '', content, flags=re.MULTILINE)
        # 移除开头的报告标题行
        content = re.sub(r'^生命之花分析报告\s*$', '', content, flags=re.MULTILINE)
        return content.strip()
    
    def _clean_section_content(self, content):
        """清理章节内容中的多余符号"""
        # 移除 > 符号
        content = re.sub(r'^>\s*', '', content, flags=re.MULTILINE)
        # 移除多余的 * 符号
        content = re.sub(r'\*+', '', content)
        # 移除多余的空白行
        content = re.sub(r'\n\s*\n', '\n\n', content)
        return content.strip()

    def create_pdf(self, output_path):
        """创建PDF文件"""
        # 封面页：只使用 fengmian.png
        self.pdf.add_page()
        self.pdf.image("fengmian.png", x=0, y=0, w=210, h=297)

        # 内容页：从第二页开始
        self._fill_text_on_new_pages()

        self.pdf.output(output_path)
        print(f"PDF已生成: {output_path}")
        return output_path

    def _fill_text_on_new_pages(self):
        """填充内容页"""
        # 第二页开始添加背景和头部
        self._add_page_with_background(True)

        # 不再添加引言部分，直接添加章节
        # 按顺序添加章节
        sections_order = [
            "1. 图案结构解读",
            "2. 颜色能量解读",
            "3. 绘画表现方式",
            "4. 性格与核心天赋",
            "5. 荣格原型分析",
            "6. 职业与发展方向",
            "7. 成长与建议",
            "8. 总结金句"
        ]

        for section_title in sections_order:
            if section_title in self.section_data:
                self._add_section(section_title, self.section_data[section_title])

    def _add_page_with_background(self, with_header=True):
        """添加新页面并铺满背景图"""
        self.pdf.add_page()
        self.pdf.image("background.png", x=0, y=0, w=210, h=297)
        self.pdf.ln(5)

        if with_header:
            # 标题
            self.pdf.set_font(self.font_name, 'B', 20)
            self.pdf.set_text_color(57, 96, 156)
            self.pdf.cell(0, 10, "生命之花分析报告", ln=True, align='C')
            self.pdf.ln(5)

            # 机构信息
            self.pdf.set_font(self.font_name, '', 12)
            self.pdf.set_text_color(100, 100, 100)
            self.pdf.cell(0, 8, "訫香方阁", ln=True, align='C')
            self.pdf.cell(0, 8, "AI解密人生～树洞计划～帮你读懂自己", ln=True, align='C')
            self.pdf.ln(10)

            # 绘制矩形框（居中）
            box_width = 150
            box_height = 50
            x_center = (210 - box_width) / 2
            y_pos = self.pdf.get_y()

            self.pdf.rect(x_center, y_pos, box_width, box_height)

            # 姓名和日期（在矩形框内垂直居中）
            self.pdf.set_font(self.font_name, 'B', 14)
            self.pdf.set_text_color(0, 0, 0)
            
            text_start_y = y_pos + (box_height - 16) / 2
            
            self.pdf.set_xy(x_center + 10, text_start_y)
            self.pdf.cell(80, 8, f"姓名：{self.section_data['name']}")
            self.pdf.set_xy(x_center + 10, text_start_y + 8)
            self.pdf.cell(80, 8, f"日期：{self.section_data['date']}")

            # 插入图片
            image_to_use = self.image_path if self.image_path and os.path.exists(self.image_path) else "flower.png"
            if os.path.exists(image_to_use):
                _, ext = os.path.splitext(image_to_use)
                if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    try:
                        img_size = 40
                        img_x = x_center + box_width - img_size - 10
                        img_y = y_pos + (box_height - img_size) / 2
                        self.pdf.image(image_to_use, x=img_x, y=img_y, w=img_size, h=img_size)
                    except Exception as e:
                        print(f"警告: 无法加载图片 {image_to_use}: {str(e)}")

            # 设置内容起始位置
            content_start_y = y_pos + box_height + 10
            self.pdf.set_y(content_start_y)
            self.pdf.ln(0)
        else:
            # 后续页面留空行避免遮挡logo
            for _ in range(4):
                self.pdf.ln(8)

    def _add_section(self, title, content):
        """添加一个章节"""
        # 设置标题样式
        self.pdf.set_font(self.font_name, 'B', 16)
        self.pdf.set_text_color(57, 96, 156)
        
        # 检查是否需要换页
        if self.pdf.get_y() > 250:
            self._add_page_with_background(False)

        # 添加标题
        self.pdf.cell(0, 10, title, ln=True)
        self.pdf.ln(2)

        # 设置正文样式
        self.pdf.set_font(self.font_name, '', 12)
        self.pdf.set_text_color(0, 0, 0)

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                self.pdf.ln(5)
                continue

            # 检查是否需要换页
            if self.pdf.get_y() > 250:
                self._add_page_with_background(False)

            if line.startswith('- '):
                self.pdf.set_x(20)
                self.pdf.cell(5, 8, "•", ln=0)
                self.pdf.set_x(25)
                self.pdf.multi_cell(0, 8, line[2:].strip())
            else:
                self.pdf.multi_cell(0, 8, line)
            self.pdf.ln(4)

        self.pdf.ln(8)


def generate_pdf_from_txt(input_txt_path, image_path=None, user_name=None):
    """从txt文件生成PDF"""
    converter = FlowerOfLifeReportConverter(image_path, user_name)
    converter.parse_text_file(input_txt_path)

    # 构造输出文件名
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