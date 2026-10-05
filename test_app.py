"""管理后台自动化测试 —— 运行方式：python -m pytest test_app.py -v"""
import os, io
import pytest
import app as app_module
import db as db_module
from db import get_db


@pytest.fixture
def client():
    app_module.app.config['TESTING'] = True
    # 用独立测试库，不污染正式数据
    test_db = os.path.join(os.path.dirname(__file__), 'test.db')
    if os.path.exists(test_db):
        os.remove(test_db)
    db_module.DB_PATH = test_db
    db_module.init_db()
    with app_module.app.test_client() as client:
        yield client


def login(client, username='admin', password='123456'):
    return client.post('/login', data={'username': username, 'password': password},
                       follow_redirects=False)


# ---------- 认证 ----------
def test_redirect_to_login_when_not_logged_in(client):
    r = client.get('/')
    assert r.status_code == 302
    assert '/login' in r.headers['Location']

def test_login_wrong_password(client):
    r = client.post('/login', data={'username': 'admin', 'password': 'wrong'})
    assert b'\xe7\x94\xa8\xe6\x88\xb7\xe5\x90\x8d\xe6\x88\x96\xe5\xaf\x86\xe7\xa0\x81\xe9\x94\x99\xe8\xaf\xaf' in r.data

def test_login_success(client):
    r = login(client)
    assert r.status_code == 302
    assert '/' in r.headers['Location']

def test_demo_cannot_access_users(client):
    login(client, 'demo', 'demo')
    r = client.get('/users')
    assert r.status_code == 403

def test_admin_can_access_users(client):
    login(client)
    r = client.get('/users')
    assert r.status_code == 200
    assert 'admin'.encode() in r.data

# ---------- 看板 ----------
def test_dashboard_shows_cards(client):
    login(client)
    r = client.get('/')
    assert r.status_code == 200
    assert b'\xe6\x95\xb0\xe6\x8d\xae\xe7\x9c\x8b\xe6\x9d\xbf' in r.data  # 数据看板

def test_api_sales_returns_json(client):
    login(client)
    r = client.get('/api/sales')
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list) and len(data) >= 3
    assert 'month' in data[0] and 'amount' in data[0]

# ---------- 员工 ----------
def test_employee_list(client):
    login(client)
    r = client.get('/employees')
    assert r.status_code == 200
    assert b'\xe5\x91\x98\xe5\xb7\xa5\xe7\xae\xa1\xe7\x90\x86' in r.data  # 员工管理

def test_employee_search(client):
    login(client)
    r = client.get('/employees?kw=%E5%BC%A0')  # 张
    assert r.status_code == 200
    assert b'\xe5\xbc\xa0\xe4\xb8\x89' in r.data   # 张三
    assert b'\xe6\x9d\x8e\xe5\x9b\x9b' not in r.data  # 李四

def test_add_and_delete_employee(client):
    login(client)
    r = client.post('/employees/add', data={
        'name': '测试员', 'department': '测试部', 'position': '测试',
        'salary': 10000, 'email': 't@t.com'
    }, follow_redirects=False)
    assert r.status_code == 302
    r = client.get('/employees?kw=%E6%B5%8B%E8%AF%95%E5%91%98')  # 测试员
    assert '测试员'.encode() in r.data
    # 查出来拿 id 删掉
    conn = get_db()
    eid = conn.execute("SELECT id FROM employees WHERE name='测试员'").fetchone()[0]
    conn.close()
    client.post(f'/employees/{eid}/delete')
    conn = get_db()
    row = conn.execute("SELECT id FROM employees WHERE name='测试员'").fetchone()
    conn.close()
    assert row is None

def test_export_excel(client):
    login(client)
    r = client.get('/employees/export')
    assert r.status_code == 200
    assert r.data[:2] == b'PK'  # xlsx 是 zip
    assert 'spreadsheetml' in r.content_type

# ---------- 订单 ----------
def test_order_list(client):
    login(client)
    r = client.get('/orders')
    assert r.status_code == 200
    assert b'\xe8\xae\xa2\xe5\x8d\x95\xe7\xae\xa1\xe7\x90\x86' in r.data  # 订单管理

def test_add_order(client):
    login(client)
    client.post('/orders/add', data={'customer': '客户X', 'product': '测试商品',
                                     'amount': 999, 'status': '待付款'})
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE customer='客户X'").fetchone()
    conn.close()
    assert row is not None
    assert row['order_no'].startswith('ORD')

def test_change_order_status(client):
    login(client)
    conn = get_db()
    oid = conn.execute("SELECT id FROM orders LIMIT 1").fetchone()[0]
    conn.close()
    client.post(f'/orders/{oid}/status', data={'status': '已完成'})
    conn = get_db()
    s = conn.execute("SELECT status FROM orders WHERE id=?", (oid,)).fetchone()[0]
    conn.close()
    assert s == '已完成'
