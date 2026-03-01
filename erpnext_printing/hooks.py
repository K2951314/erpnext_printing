import re
from pathlib import Path

app_name = "erpnext_printing"
app_title = "ERPNext Printing"
app_publisher = "舍满取半"
app_description = "Print formats and invoice import utilities for ERPNext"
app_email = "qdsmqb@163.com"
app_license = "mit"
app_version = "0.0.1"

app_include_js = ["/assets/erpnext_printing/js/html2canvas_loader.js"]

jinja = {
    "methods": ["erpnext_printing.utils.rmb_upper"],
}

print_format_files = {
    "Sales Order": ["erpnext_printing.print_formats.sales_contract"],
    "Delivery Note": [
        "erpnext_printing.print_formats.sales_delivery",
        "erpnext_printing.print_formats.sales_delivery_with_price",
    ],
}

doc_events = {
    "File": {
        "after_insert": "erpnext_printing.api.invoice.parse_invoice_xml"
    }
}

LEGACY_SEAL_CALL = "erpnext_math.utils.get_random_seal_params"
CURRENT_SEAL_CALL = "erpnext_printing.utils.get_random_seal_params"
CURRENT_MONEY_CALL = "{{ rmb_upper(doc.grand_total) }}"


def _load_print_format_html(filename):
    import frappe

    file_path = Path(frappe.get_app_path("erpnext_printing")) / "print_formats" / filename
    if not file_path.exists():
        frappe.throw(f"文件未找到: {file_path}")
    return file_path.read_text(encoding="utf-8")


def _upsert_print_format(name, doc_type, filename):
    import frappe

    html_content = _load_print_format_html(filename)
    existing_name = frappe.db.get_value("Print Format", {"name": name, "doc_type": doc_type})

    if existing_name:
        pf = frappe.get_doc("Print Format", existing_name)
        pf.print_format_type = "Jinja"
        pf.custom_format = 1
        pf.is_standard = "No"
        pf.html = html_content
        pf.save(ignore_permissions=True)
        return

    pf = frappe.get_doc(
        {
            "doctype": "Print Format",
            "name": name,
            "doc_type": doc_type,
            "print_format_type": "Jinja",
            "html": html_content,
            "custom_format": 1,
            "is_standard": "No",
        }
    )
    pf.insert(ignore_permissions=True)


def fix_legacy_print_format_calls():
    import frappe

    candidates = frappe.get_all(
        "Print Format",
        filters=[
            ["Print Format", "html", "like", f"%{LEGACY_SEAL_CALL}%"],
        ],
        pluck="name",
    )
    candidates += frappe.get_all(
        "Print Format",
        filters=[
            ["Print Format", "html", "like", "%money_in_words(doc.grand_total, \"CNY\")%"],
        ],
        pluck="name",
    )
    candidates += frappe.get_all(
        "Print Format",
        filters=[
            ["Print Format", "html", "like", "%erpnext_printing.utils.rmb_upper%"],
        ],
        pluck="name",
    )
    candidates = list(dict.fromkeys(candidates))

    money_patterns = [
        r"\{\{\s*frappe\.utils\.money_in_words\(doc\.grand_total,\s*\"CNY\"\)\s*\}\}",
        r"\{\{\s*frappe\.call\(\s*'erpnext_printing\.utils\.rmb_upper'\s*,\s*doc\.grand_total\s*\)\s*\}\}",
        r"\{\{\s*frappe\.call\(\s*'erpnext_printing\.utils\.rmb_upper'\s*,\s*amount\s*=\s*doc\.grand_total\s*\)\s*\}\}",
    ]

    for name in candidates:
        pf = frappe.get_doc("Print Format", name)
        html = (pf.html or "").replace(LEGACY_SEAL_CALL, CURRENT_SEAL_CALL)
        for pattern in money_patterns:
            html = re.sub(pattern, CURRENT_MONEY_CALL, html)
        pf.html = html
        pf.save(ignore_permissions=True)

    return {"updated": len(candidates), "names": candidates}


def after_install():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    _upsert_print_format("Sales Contract", "Sales Order", "sales_contract.html")
    _upsert_print_format("Sales Delivery", "Delivery Note", "sales_delivery.html")
    _upsert_print_format(
        "Sales Delivery with Price",
        "Delivery Note",
        "sales_delivery_with_price.html",
    )
    fix_legacy_print_format_calls()

    create_custom_fields(
        {
            "Item": [
                {
                    "fieldname": "custom_规格型号",
                    "fieldtype": "Data",
                    "label": "规格型号",
                    "insert_after": "item_name",
                }
            ]
        },
        update=True,
    )


def after_migrate():
    after_install()