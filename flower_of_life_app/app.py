import os
import sys
import tempfile
from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from ali_api import analyze_image
from pdf import generate_pdf_from_txt
import uuid
from PIL import Image
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'flower-of-life-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 最大16MB文件

# 确保output目录存在
if not os.path.exists('output'):
    os.makedirs('output')

# 存储分析任务的状态
analysis_tasks = {}

def compress_image_if_needed(image_path, max_size_bytes=10 * 1024 * 1024):
    """
    如果图片超过指定大小，则进行压缩
    """
    if not os.path.exists(image_path):
        return image_path
    
    # 检查文件大小
    file_size = os.path.getsize(image_path)
    if file_size <= max_size_bytes:
        return image_path  # 文件大小已经在限制内
    
    try:
        # 打开图片
        with Image.open(image_path) as img:
            # 转换为RGB模式（如果需要）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # 计算压缩比例
            # 我们需要将文件大小压缩到max_size_bytes以下
            # 这里使用一个简化的计算方法
            quality = 85
            while quality > 10:
                # 保存到内存缓冲区
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                size = buffer.tell()
                
                if size <= max_size_bytes:
                    # 保存压缩后的图片
                    compressed_path = image_path.replace('.', '_compressed.')
                    with open(compressed_path, 'wb') as f:
                        f.write(buffer.getvalue())
                    return compressed_path
                else:
                    quality -= 5  # 降低质量继续尝试
            
            # 如果即使质量降到10 still太大，强制调整尺寸
            width, height = img.size
            ratio = (max_size_bytes / file_size) ** 0.5 * 0.9  # 留一些余量
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            # 重采样图片
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 保存压缩后的图片
            compressed_path = image_path.replace('.', '_compressed.')
            img_resized.save(compressed_path, 'JPEG', quality=70, optimize=True)
            return compressed_path
                
    except Exception as e:
        print(f"图片压缩失败: {e}")
        return image_path  # 返回原始路径，让后续处理决定

# 添加 favicon 路由
@app.route('/favicon.ico')
def favicon():
    return '', 204  # 返回空响应，避免404错误

@app.route('/')
def index():
    """主页 - Web界面"""
    return render_template('index.html')

@app.route('/docs')
def docs():
    """API文档页面"""
    return render_template('docs.html')

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """
    分析生命之花图片
    ---
    tags:
      - 分析接口
    description:
      上传生命之花图片并生成分析报告
    parameters:
      - name: image_url
        in: formData
        type: string
        description: 网络图片URL（与image_file二选一）
      - name: image_file
        in: formData
        type: file
        description: 上传本地图片文件（与image_url二选一）
      - name: name
        in: formData
        type: string
        required: true
        description: 用户姓名
    responses:
      200:
        description: 分析成功，返回报告文件信息
        schema:
          id: AnalysisResult
          properties:
            task_id:
              type: string
              description: 任务ID
            status:
              type: string
              description: 任务状态
            message:
              type: string
              description: 状态信息
      400:
        description: 请求参数错误
      500:
        description: 服务器内部错误
    """
    name = request.form.get('name')
    if not name:
        return jsonify({
            "error": "缺少必要参数",
            "message": "必须提供用户姓名"
        }), 400
    #读取可选提示词
    prompt_override = request.form.get('prompt', '').strip() or None
    # # 调用时传入
    # txt_file_path, error = analyze_image(image_path, name, prompt_override)

    # 处理图片输入
    image_path = None
    if 'image_url' in request.form and request.form['image_url']:
        image_path = request.form['image_url']
    elif 'image_file' in request.files and request.files['image_file'].filename != '':
        # 处理上传的文件
        file = request.files['image_file']
        if file:
            # 保存上传的文件到临时位置
            filename = secure_filename(file.filename)
            # 确保扩展名是正确的格式
            base_name, ext = os.path.splitext(filename)
            if ext and ext.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                image_path = os.path.join('output', f"{uuid.uuid4()}{ext.lower()}")
                file.save(image_path)
            else:
                if not ext:
                    temp_filename = f"{uuid.uuid4()}_temp"
                    file_path = os.path.join('output', temp_filename)
                    file.save(file_path)
                    try:
                        with Image.open(file_path) as img:
                            detected_type = img.format.lower()
                    except Exception:
                        detected_type = None
                    if detected_type and detected_type in ['png', 'jpeg', 'gif', 'bmp']:
                        correct_ext = '.' + detected_type if detected_type != 'jpeg' else '.jpg'
                        final_path = file_path + correct_ext
                        os.rename(file_path, final_path)
                        image_path = final_path
                    else:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        return jsonify({"success": False,"error_message": "不支持的图片格式，只支持 PNG, JPG, JPEG, BMP, GIF 格式"})
                else:
                    return jsonify({"error": "参数错误","message": "不支持的图片格式，只支持 PNG, JPG, JPEG, BMP, GIF 格式"}), 400
    else:
        return jsonify({"error": "参数错误","message": "必须提供图片URL或上传图片文件"}), 400
    
    # 压缩图片（如果需要）
    if image_path and os.path.exists(image_path):
        original_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
        image_path = compress_image_if_needed(image_path, max_size_bytes=10 * 1024 * 1024)  # 10MB限制
        if os.path.exists(image_path):
            compressed_size = os.path.getsize(image_path)
            print(f"图片压缩: {original_size} bytes -> {compressed_size} bytes")
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    analysis_tasks[task_id] = {
        "status": "processing",
        "message": "正在处理图片分析"
    }
    
    try:
        # 仅调用一次，并且把可选提示词传递进去  —— FIX: 去重
        # txt_file_path, error = analyze_image(image_path, name)  # (旧) 多余调用
        txt_file_path, error = analyze_image(image_path, name, prompt_override)

        if error:
            analysis_tasks[task_id] = {"status": "failed","message": f"分析失败: {error}"}
            return jsonify({"task_id": task_id,"status": "failed","message": f"分析失败: {error}"}), 500
        
        pdf_file_path = generate_pdf_from_txt(txt_file_path, image_path, name)
        txt_filename = os.path.basename(txt_file_path)
        pdf_filename = os.path.basename(pdf_file_path)
        
        analysis_tasks[task_id] = {
            "status": "completed","message": "分析完成",
            "txt_filename": txt_filename,"pdf_filename": pdf_filename
        }
        return jsonify({
            "task_id": task_id,"status": "completed","message": "分析完成",
            "result": {"txt_file": txt_filename,"pdf_file": pdf_filename}
        })
        
    except Exception as e:
        analysis_tasks[task_id] = {
            "status": "failed",
            "message": f"处理过程中出错: {str(e)}"
        }
        return jsonify({
            "task_id": task_id,
            "status": "failed",
            "message": f"处理过程中出错: {str(e)}"
        }), 500

@app.route('/api/task/<task_id>')
def get_task_status(task_id):
    """
    获取任务状态
    ---
    tags:
      - 任务接口
    description:
      根据任务ID获取分析任务的状态
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: 任务ID
    responses:
      200:
        description: 返回任务状态信息
        schema:
          id: TaskStatus
          properties:
            task_id:
              type: string
            status:
              type: string
            message:
              type: string
            result:
              type: object
              properties:
                txt_file:
                  type: string
                pdf_file:
                  type: string
      404:
        description: 任务不存在
    """
    if task_id not in analysis_tasks:
        return jsonify({
            "error": "任务不存在",
            "message": f"未找到任务ID: {task_id}"
        }), 404
    
    task_info = analysis_tasks[task_id].copy()
    task_info["task_id"] = task_id
    return jsonify(task_info)

@app.route('/api/download/<filename>')
def download_file(filename):
    """
    下载报告文件
    ---
    tags:
      - 文件接口
    description:
      下载生成的TXT或PDF报告文件
    parameters:
      - name: filename
        in: path
        type: string
        required: true
        description: 文件名
    responses:
      200:
        description: 文件下载
      404:
        description: 文件不存在
    """
    try:
        file_path = os.path.join('output', filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({
                "error": "文件不存在",
                "message": f"未找到文件: {filename}"
            }), 404
    except Exception as e:
        return jsonify({
            "error": "下载失败",
            "message": f"下载文件时出错: {str(e)}"
        }), 500

# Web界面路由
@app.route('/web/analyze', methods=['POST'])
def web_analyze():
    user_name = request.form.get('name', '未知用户')
    
    image_path = None
    if request.form.get('image_option') == 'url':
        image_path = request.form.get('image_url')
        if not image_path:
            return jsonify({"success": False, "error_message": "请输入图片URL"})
    else:
        if 'image_file' not in request.files:
            return jsonify({"success": False, "error_message": "请选择图片文件"})
        file = request.files['image_file']
        if file.filename == '':
            return jsonify({"success": False, "error_message": "请选择图片文件"})
        if file:
            filename = secure_filename(file.filename)
            base_name, ext = os.path.splitext(filename)   # <-- 修正：不要用 name 覆盖
            if ext and ext.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                image_path = os.path.join('output', f"{uuid.uuid4()}{ext.lower()}")
                file.save(image_path)
            else:
                if not ext:
                    temp_filename = f"{uuid.uuid4()}_temp"
                    file_path = os.path.join('output', temp_filename)
                    file.save(file_path)
                    try:
                        with Image.open(file_path) as img:
                            detected_type = img.format.lower()
                    except Exception:
                        detected_type = None
                    if detected_type and detected_type in ['png', 'jpeg', 'gif', 'bmp']:
                        correct_ext = '.' + detected_type if detected_type != 'jpeg' else '.jpg'
                        final_path = file_path + correct_ext
                        os.rename(file_path, final_path)
                        image_path = final_path
                    else:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        return jsonify({"success": False,"error_message": "不支持的图片格式，只支持 PNG, JPG, JPEG, BMP, GIF 格式"})
                else:
                    return jsonify({"success": False, "error_message": "不支持的图片格式，只支持 PNG, JPG, JPEG, BMP, GIF 格式"})
    
    if image_path and os.path.exists(image_path):
        original_size = os.path.getsize(image_path)
        image_path = compress_image_if_needed(image_path, max_size_bytes=10 * 1024 * 1024)
        if os.path.exists(image_path):
            compressed_size = os.path.getsize(image_path)
            print(f"图片压缩: {original_size} bytes -> {compressed_size} bytes")
    
    # 读取可选提示词，并只调用一次 analyze_image —— FIX: 去重
    prompt_override = (request.form.get('prompt') or '').strip() or None
    # txt_file_path, error = analyze_image(image_path, user_name)  # (旧) 多余调用
    txt_file_path, error = analyze_image(image_path, user_name, prompt_override)

    if error:
        return jsonify({"success": False, "error_message": error})
    
    try:
        pdf_file_path = generate_pdf_from_txt(txt_file_path, image_path, user_name)
        txt_filename = os.path.basename(txt_file_path)
        pdf_filename = os.path.basename(pdf_file_path)
        return jsonify({"success": True, "txt_filename": txt_filename, "pdf_filename": pdf_filename})
    except Exception as e:
        return jsonify({"success": False, "error_message": f"生成PDF时出错: {str(e)}"})

@app.route('/web/download/<filename>')
def web_download_file(filename):
    """Web界面文件下载"""
    try:
        file_path = os.path.join('output', filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return "文件不存在", 404
    except Exception as e:
        return f"下载文件时出错: {str(e)}", 500

# API文档路由
@app.route('/swagger.json')
def swagger_json():
    """Swagger API文档JSON"""
    return jsonify({
        "swagger": "2.0",
        "info": {
            "title": "生命之花分析API",
            "description": "生命之花图片分析服务API接口文档",
            "version": "1.0.0"
        },
        "host": request.host,
        "basePath": "/api",
        "schemes": ["http"],
        "tags": [
            {
                "name": "分析接口",
                "description": "图片分析相关接口"
            },
            {
                "name": "任务接口",
                "description": "任务状态查询接口"
            },
            {
                "name": "文件接口",
                "description": "文件下载接口"
            }
        ],
        "paths": {
            "/analyze": {
                "post": {
                    "tags": ["分析接口"],
                    "summary": "分析生命之花图片",
                    "description": "上传生命之花图片并生成分析报告",
                    "consumes": ["multipart/form-data"],
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "name": "image_url",
                            "in": "formData",
                            "type": "string",
                            "description": "网络图片URL（与image_file二选一）"
                        },
                        {
                            "name": "image_file",
                            "in": "formData",
                            "type": "file",
                            "description": "上传本地图片文件（与image_url二选一）"
                        },
                        {
                            "name": "name",
                            "in": "formData",
                            "type": "string",
                            "required": True,
                            "description": "用户姓名"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "分析成功，返回报告文件信息",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "task_id": {"type": "string"},
                                    "status": {"type": "string"},
                                    "message": {"type": "string"},
                                    "result": {
                                        "type": "object",
                                        "properties": {
                                            "txt_file": {"type": "string"},
                                            "pdf_file": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "请求参数错误"
                        },
                        "500": {
                            "description": "服务器内部错误"
                        }
                    }
                }
            },
            "/task/{task_id}": {
                "get": {
                    "tags": ["任务接口"],
                    "summary": "获取任务状态",
                    "description": "根据任务ID获取分析任务的状态",
                    "parameters": [
                        {
                            "name": "task_id",
                            "in": "path",
                            "type": "string",
                            "required": True,
                            "description": "任务ID"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "返回任务状态信息",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "task_id": {"type": "string"},
                                    "status": {"type": "string"},
                                    "message": {"type": "string"},
                                    "result": {
                                        "type": "object",
                                        "properties": {
                                            "txt_file": {"type": "string"},
                                            "pdf_file": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "任务不存在"
                        }
                    }
                }
            },
            "/download/{filename}": {
                "get": {
                    "tags": ["文件接口"],
                    "summary": "下载报告文件",
                    "description": "下载生成的TXT或PDF报告文件",
                    "parameters": [
                        {
                            "name": "filename",
                            "in": "path",
                            "type": "string",
                            "required": True,
                            "description": "文件名"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "文件下载"
                        },
                        "404": {
                            "description": "文件不存在"
                        }
                    }
                }
            }
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)