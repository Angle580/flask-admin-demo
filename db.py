import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'admin.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _column_exists(conn, table, col):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return col in cols

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        position TEXT NOT NULL,
        salary REAL NOT NULL,
        email TEXT,
        avatar TEXT,
        created_at TEXT NOT NULL
    )''')
    # 老库补 avatar 列
    if not _column_exists(conn, 'employees', 'avatar'):
        c.execute("ALTER TABLE employees ADD COLUMN avatar TEXT")
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT UNIQUE NOT NULL,
        customer TEXT NOT NULL,
        product TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT '待付款',
        created_at TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,
        amount REAL NOT NULL
    )''')
    # 默认管理员
    c.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
    if c.fetchone()[0] == 0:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO users (username,password,role,created_at) VALUES (?,?,?,?)",
                  ('admin', '123456', 'admin', now))
        c.execute("INSERT INTO users (username,password,role,created_at) VALUES (?,?,?,?)",
                  ('demo', 'demo', 'user', now))
    # 示例员工
    c.execute("SELECT COUNT(*) FROM employees")
    if c.fetchone()[0] == 0:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        samples = [
            ('张三', '技术部', '后端工程师', 18000, 'zhangsan@x.com', None, now),
            ('李四', '技术部', '前端工程师', 16000, 'lisi@x.com', None, now),
            ('王五', '产品部', '产品经理', 20000, 'wangwu@x.com', None, now),
            ('赵六', '人事部', 'HR专员', 9000, 'zhaoliu@x.com', None, now),
            ('钱七', '财务部', '会计', 12000, 'qianqi@x.com', None, now),
        ]
        c.executemany("INSERT INTO employees (name,department,position,salary,email,avatar,created_at) VALUES (?,?,?,?,?,?,?)", samples)
    # 示例订单
    c.execute("SELECT COUNT(*) FROM orders")
    if c.fetchone()[0] == 0:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        orders = [
            ('ORD20261001001', '客户A', '企业版年费', 12000, '已完成', now),
            ('ORD20261002002', '客户B', '标准版年费', 6000, '已付款', now),
            ('ORD20261003003', '客户C', '定制开发', 50000, '待付款', now),
            ('ORD20261004004', '客户D', '企业版年费', 12000, '已取消', now),
            ('ORD20261005005', '客户E', '技术咨询', 3000, '已完成', now),
        ]
        c.executemany("INSERT INTO orders (order_no,customer,product,amount,status,created_at) VALUES (?,?,?,?,?,?)", orders)
    # 示例销售数据
    c.execute("SELECT COUNT(*) FROM sales")
    if c.fetchone()[0] == 0:
        sales = [('2026-05', 120), ('2026-06', 180), ('2026-07', 150),
                 ('2026-08', 220), ('2026-09', 260), ('2026-10', 300)]
        c.executemany("INSERT INTO sales (month,amount) VALUES (?,?)", sales)
    conn.commit()
    conn.close()
