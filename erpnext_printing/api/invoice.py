import os
import xml.etree.ElementTree as ET

import frappe
from frappe import _


@frappe.whitelist()
def parse_invoice_xml(doc=None, method=None):
    if not doc:
        frappe.throw(_("缺少必需参数 'doc'"))

    try:
        if isinstance(doc, dict):
            file_url = doc.get("file_url")
            file_name = doc.get("file_name")
        else:
            file_url = doc.file_url
            file_name = doc.file_name

        if not file_url:
            frappe.throw(_("缺少文件路径 file_url"))

        file_path, is_private = _resolve_file_path(file_url)
        if not os.path.exists(file_path):
            frappe.log_error(f"文件未找到: {file_path}", "ERPNext Printing Invoice Parse")
            return {"status": "error", "message": "文件未找到"}

        tree = ET.parse(file_path)
        root = tree.getroot()

        namespace = {"ns0": "http://www.chinatax.gov.cn/"}
        invoice_data = {
            "invoice_code": _find_text(root, ".//ns0:fpdm", namespace),
            "invoice_number": _find_text(root, ".//ns0:fphm", namespace),
            "issue_date": _find_text(root, ".//ns0:kprq", namespace),
            "amount": _find_float(root, ".//ns0:hjje", namespace),
            "tax_amount": _find_float(root, ".//ns0:spse", namespace),
            "supplier": _find_text(root, ".//ns0:gfmc", namespace) or "未知供应商",
        }

        pi = create_purchase_invoice(invoice_data)
        _attach_file_to_document(
            file_url=file_url,
            file_name=file_name or os.path.basename(file_path),
            attached_to_doctype="Purchase Invoice",
            attached_to_name=pi.name,
            is_private=is_private,
        )

        frappe.msgprint(_("发票已解析并生成采购发票: {0}").format(pi.name))
        return {
            "status": "success",
            "message": "发票已解析并生成采购发票",
            "purchase_invoice": pi.name,
            "data": invoice_data,
        }

    except ET.ParseError as e:
        frappe.log_error(f"XML 解析错误: {str(e)}", "ERPNext Printing Invoice Parse")
        return {"status": "error", "message": f"XML 解析失败: {str(e)}"}
    except Exception as e:
        frappe.log_error(f"处理错误: {str(e)}", "ERPNext Printing Invoice Parse")
        return {"status": "error", "message": f"处理失败: {str(e)}"}


def create_purchase_invoice(invoice_data):
    try:
        supplier = frappe.db.get_value("Supplier", {"supplier_name": invoice_data["supplier"]}, "name")
        if not supplier:
            supplier_doc = frappe.get_doc(
                {
                    "doctype": "Supplier",
                    "supplier_name": invoice_data["supplier"],
                }
            )
            supplier_doc.insert(ignore_permissions=True)
            supplier = supplier_doc.name

        item_code = frappe.db.get_value("Item", {"item_name": "Default Item"}, "name")
        if not item_code:
            default_item = frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_name": "Default Item",
                    "item_group": "All Item Groups",
                }
            )
            default_item.insert(ignore_permissions=True)
            item_code = default_item.name

        pi = frappe.get_doc(
            {
                "doctype": "Purchase Invoice",
                "supplier": supplier,
                "posting_date": invoice_data["issue_date"],
                "items": [
                    {
                        "item_code": item_code,
                        "qty": 1,
                        "rate": invoice_data["amount"],
                        "amount": invoice_data["amount"],
                    }
                ],
            }
        )
        pi.insert(ignore_permissions=True)
        pi.submit()
        return pi
    except Exception as e:
        frappe.log_error(f"创建采购发票错误: {str(e)}", "ERPNext Printing Invoice Parse")
        frappe.throw(_("创建采购发票失败: {0}").format(str(e)))


def _attach_file_to_document(file_url, file_name, attached_to_doctype, attached_to_name, is_private=False):
    existing = frappe.db.exists(
        "File",
        {
            "file_url": file_url,
            "attached_to_doctype": attached_to_doctype,
            "attached_to_name": attached_to_name,
        },
    )
    if existing:
        return

    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_name,
            "file_url": file_url,
            "is_private": 1 if is_private else 0,
            "attached_to_doctype": attached_to_doctype,
            "attached_to_name": attached_to_name,
        }
    )
    file_doc.insert(ignore_permissions=True)


def _resolve_file_path(file_url):
    normalized = file_url.strip()
    if normalized.startswith("/private/files/"):
        filename = os.path.basename(normalized)
        return frappe.get_site_path("private", "files", filename), True

    if normalized.startswith("/files/"):
        filename = os.path.basename(normalized)
        return frappe.get_site_path("public", "files", filename), False

    filename = os.path.basename(normalized)
    return frappe.get_site_path("public", "files", filename), False


def _find_text(root, path, namespace):
    node = root.find(path, namespace)
    return node.text if node is not None else ""


def _find_float(root, path, namespace):
    value = _find_text(root, path, namespace)
    try:
        return float(value) if value else 0.0
    except ValueError:
        return 0.0
