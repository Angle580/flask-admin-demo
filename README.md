# Flask 管理后台 Demo

一个用 Python + Flask + SQLite 写的轻量级管理后台，适合学习和练手。

## 功能

- 🔐 用户登录 / 退出，session 鉴权
- 👑 角色权限：admin 可进用户管理，普通 user 访问 `/users` 返回 403
- 📊 数据看板：用户/员工/工资/订单统计卡片 + 近 6 月销售折线图（Chart.js）
- 👥 员工管理：列表、按姓名搜索、按部门筛选、分页（每页 5 条）、新增、编辑、删除、头像上传、导出 Excel
- 📦 订单管理：列表、按状态筛选、分页、新增、修改状态、删除
- 🧪 自动化测试：pytest 覆盖 14 个用例

## 技术栈

- 后端：Flask 3
- 数据库：SQLite（零配置，首次运行自动建表）
- 前端：HTML + CSS + Chart.js
- 测试：pytest

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动
python app.py

# 3. 浏览器打开
# http://127.0.0.1:8080
```

默认账号：

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| 管理员 | admin | 123456 |
| 普通用户 | demo | demo |

## 跑测试

```bash
python -m pytest test_app.py -v
```

## 项目结构

```
admin-demo/
├── app.py              # 主程序 + 所有路由
├── db.py               # SQLite 初始化和连接
├── test_app.py         # pytest 测试用例
├── requirements.txt
├── templates/
│   ├── base.html       # 侧边栏布局
│   ├── login.html
│   ├── dashboard.html
│   ├── employees.html
│   ├── emp_edit.html
│   ├── orders.html
│   └── users.html
└── static/
    ├── style.css
    └── uploads/        # 头像上传目录
```

## 主要路由

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST | /login | 登录 |
| GET | / | 数据看板 |
| GET | /employees | 员工列表（支持 ?kw= &dept= &page=） |
| GET | /employees/export | 导出 Excel |
| GET/POST | /employees/<id>/edit | 编辑员工 |
| GET | /orders | 订单列表 |
| POST | /orders/<id>/status | 修改订单状态 |
| GET | /users | 用户管理（admin） |
| GET | /api/sales | 销售数据 JSON |
