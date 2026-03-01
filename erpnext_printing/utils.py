import os
import random
import subprocess
from decimal import Decimal, ROUND_HALF_UP

import frappe
from frappe import whitelist

CN_NUMBERS = "零壹贰叁肆伍陆柒捌玖"
CN_UNITS = ["", "拾", "佰", "仟"]
CN_SECTION_UNITS = ["", "万", "亿", "兆"]


@whitelist()
def get_random_seal_params():
    return {
        "rotation_angle": random.uniform(-7, 7),
        "random_top": random.uniform(-10, -5),
        "random_left": random.uniform(17, 23),
        "opacity": random.uniform(0.59, 0.79),
    }


def _section_to_cn(section):
    result = ""
    zero = False
    unit_pos = 0

    while section > 0:
        digit = section % 10
        if digit == 0:
            if not zero and result:
                result = CN_NUMBERS[0] + result
            zero = True
        else:
            result = CN_NUMBERS[digit] + CN_UNITS[unit_pos] + result
            zero = False
        unit_pos += 1
        section //= 10

    return result


def _integer_to_cn(integer_part):
    if integer_part == 0:
        return CN_NUMBERS[0]

    result = ""
    unit_pos = 0
    need_zero = False

    while integer_part > 0:
        section = integer_part % 10000

        if section == 0:
            if result and not result.startswith(CN_NUMBERS[0]):
                result = CN_NUMBERS[0] + result
        else:
            section_text = _section_to_cn(section) + CN_SECTION_UNITS[unit_pos]
            if need_zero and not section_text.startswith(CN_NUMBERS[0]):
                section_text = CN_NUMBERS[0] + section_text
            result = section_text + result
            need_zero = section < 1000

        integer_part //= 10000
        unit_pos += 1

    while "零零" in result:
        result = result.replace("零零", "零")
    return result.rstrip("零")


def amount_to_rmb_upper(amount):
    value = Decimal(str(amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    negative = value < 0
    value = abs(value)

    integer_part = int(value)
    decimal_part = int((value - integer_part) * 100)
    jiao = decimal_part // 10
    fen = decimal_part % 10

    result = _integer_to_cn(integer_part) + "元"
    if decimal_part == 0:
        result += "整"
    else:
        if jiao > 0:
            result += CN_NUMBERS[jiao] + "角"
        elif fen > 0:
            result += "零"

        if fen > 0:
            result += CN_NUMBERS[fen] + "分"

    if negative:
        result = "负" + result
    return result


@whitelist()
def rmb_upper(amount):
    return amount_to_rmb_upper(amount)


@whitelist(allow_guest=False)
def export_print_to_image(doctype, name, print_format):
    # 获取打印格式的HTML
    html = frappe.get_print(doctype, name, print_format=print_format)

    # 定义临时文件路径
    temp_img_path = frappe.get_site_path("private", "files", f"{name}_contract.png")

    # 调用 Node.js 脚本
    script_path = frappe.get_app_path("erpnext_printing", "node_scripts", "html_to_image.js")
    try:
        subprocess.run(
            [
                "node",
                script_path,
                html,
                temp_img_path,
            ],
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        frappe.throw(f"生成图片失败: {str(e)}")

    # 读取生成的图片
    if not os.path.exists(temp_img_path):
        frappe.throw("图片生成失败，未找到文件")

    with open(temp_img_path, "rb") as f:
        img_content = f.read()

    # 保存到 ERPNext 文件系统
    file_name = f"{name}_contract.png"
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_name,
            "is_private": 1,
            "content": img_content,
        }
    )
    file_doc.save()

    # 删除临时文件
    os.remove(temp_img_path)

    return file_doc.file_url