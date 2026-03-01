import random
from frappe import whitelist
import frappe
import subprocess
import os
import base64

@whitelist()
def get_random_seal_params():
    return {
        "rotation_angle": random.uniform(-7, 7),
        "random_top": random.uniform(-10, -5),
        "random_left": random.uniform(17, 23),
        "opacity": random.uniform(0.59, 0.79)
    }

@whitelist(allow_guest=False)
def export_print_to_image(doctype, name, print_format):
    # 获取打印格式的HTML
    html = frappe.get_print(doctype, name, print_format=print_format)
    
    # 定义临时文件路径
    temp_img_path = frappe.get_site_path("private", "files", f"{name}_contract.png")
    
    # 调用 Node.js 脚本
    script_path = frappe.get_app_path("erpnext_printing", "node_scripts", "html_to_image.js")
    try:
        subprocess.run([
            "node", 
            script_path, 
            html, 
            temp_img_path
        ], check=True, timeout=30)  # 设置超时防止挂起
    except subprocess.CalledProcessError as e:
        frappe.throw(f"生成图片失败: {str(e)}")
    
    # 读取生成的图片
    if not os.path.exists(temp_img_path):
        frappe.throw("图片生成失败，未找到文件")
    
    with open(temp_img_path, "rb") as f:
        img_content = f.read()
    
    # 保存到 ERPNext 文件系统
    file_name = f"{name}_contract.png"
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "is_private": 1,
        "content": img_content
    })
    file_doc.save()
    
    # 删除临时文件
    os.remove(temp_img_path)
    
    return file_doc.file_url