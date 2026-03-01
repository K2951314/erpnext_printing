# erpnext_printing

ERPNext 自定义应用，提供打印格式与发票导入能力。

## 简介
`erpnext_printing` 用于管理销售相关打印模板，并支持从 XML 发票自动创建采购发票。

## 安装步骤

```bash
# 克隆应用
bench get-app --branch version-16 erpnext_printing <your_git_url>

# 安装到站点
bench --site <site_name> install-app erpnext_printing

# 执行迁移与构建
bench --site <site_name> migrate
bench build --app erpnext_printing
bench restart
```
