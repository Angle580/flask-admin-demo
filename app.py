from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from db import init_db, get_db
from functools import wraps
from datetime import datetime
import os, uuid, io
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = 'admin-demo-secret'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
PAGE_SIZE = 5

init_db()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            return '403 无权限', 403
        return f(*args, **kwargs)
    return wrapper

# ---------- 认证 ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                            (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        flash('用户名或密码错误')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------- 看板 ----------
@app.route('/')
@login_required
def dashboard():
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()['c']
    total_emps = conn.execute("SELECT COUNT(*) c FROM employees").fetchone()['c']
    total_salary = conn.execute("SELECT COALESCE(SUM(salary),0) s FROM employees").fetchone()['s']
    total_orders = conn.execute("SELECT COUNT(*) c FROM orders").fetchone()['c']
    sales = conn.execute("SELECT month, amount FROM sales ORDER BY month").fetchall()
    conn.close()
    return render_template('dashboard.html',
                           total_users=total_users, total_emps=total_emps,
                           total_salary=int(total_salary), total_orders=total_orders,
                           sales=[dict(s) for s in sales])

# ---------- 用户管理 ----------
@app.route('/users')
@login_required
@admin_required
def users():
    conn = get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    conn.close()
    return render_template('users.html', users=rows)

@app.route('/users/add', methods=['POST'])
@login_required
@admin_required
def user_add():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username,password,role,created_at) VALUES (?,?,?,?)",
                     (request.form['username'], request.form['password'],
                      request.form.get('role', 'user'), now))
        conn.commit()
    except Exception:
        flash('添加失败：用户名已存在')
    conn.close()
    return redirect(url_for('users'))

@app.route('/users/<int:uid>/delete', methods=['POST'])
@login_required
@admin_required
def user_delete(uid):
    if uid == session['user_id']:
        flash('不能删除自己')
    else:
        conn = get_db()
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
        conn.close()
    return redirect(url_for('users'))

# ---------- 员工管理（搜索 + 分页 + 编辑 + 头像 + 导出） ----------
@app.route('/employees')
@login_required
def employees():
    page = max(1, request.args.get('page', 1, type=int))
    kw = request.args.get('kw', '').strip()
    dept = request.args.get('dept', '')
    where, params = [], []
    if kw:
        where.append("name LIKE ?"); params.append(f"%{kw}%")
    if dept:
        where.append("department = ?"); params.append(dept)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) c FROM employees {where_sql}", params).fetchone()['c']
    rows = conn.execute(
        f"SELECT * FROM employees {where_sql} ORDER BY id LIMIT ? OFFSET ?",
        params + [PAGE_SIZE, (page-1)*PAGE_SIZE]).fetchall()
    depts = [r['department'] for r in conn.execute("SELECT DISTINCT department FROM employees").fetchall()]
    conn.close()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return render_template('employees.html', emps=rows, depts=depts, cur_dept=dept,
                           kw=kw, page=page, total_pages=total_pages, total=total)

@app.route('/employees/add', methods=['POST'])
@login_required
def emp_add():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    avatar = None
    f = request.files.get('avatar')
    if f and f.filename:
        ext = os.path.splitext(f.filename)[1]
        fname = uuid.uuid4().hex + ext
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        avatar = fname
    conn = get_db()
    conn.execute("INSERT INTO employees (name,department,position,salary,email,avatar,created_at) VALUES (?,?,?,?,?,?,?)",
                 (request.form['name'], request.form['department'], request.form['position'],
                  float(request.form['salary']), request.form.get('email', ''), avatar, now))
    conn.commit()
    conn.close()
    return redirect(url_for('employees'))

@app.route('/employees/<int:eid>/edit', methods=['GET', 'POST'])
@login_required
def emp_edit(eid):
    conn = get_db()
    if request.method == 'POST':
        avatar = request.form.get('old_avatar')
        f = request.files.get('avatar')
        if f and f.filename:
            ext = os.path.splitext(f.filename)[1]
            fname = uuid.uuid4().hex + ext
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            avatar = fname
        conn.execute("UPDATE employees SET name=?,department=?,position=?,salary=?,email=?,avatar=? WHERE id=?",
                     (request.form['name'], request.form['department'], request.form['position'],
                      float(request.form['salary']), request.form.get('email', ''), avatar, eid))
        conn.commit()
        conn.close()
        return redirect(url_for('employees'))
    emp = conn.execute("SELECT * FROM employees WHERE id=?", (eid,)).fetchone()
    conn.close()
    return render_template('emp_edit.html', emp=emp)

@app.route('/employees/<int:eid>/delete', methods=['POST'])
@login_required
def emp_delete(eid):
    conn = get_db()
    conn.execute("DELETE FROM employees WHERE id=?", (eid,))
    conn.commit()
    conn.close()
    return redirect(url_for('employees'))

@app.route('/employees/export')
@login_required
def emp_export():
    conn = get_db()
    rows = conn.execute("SELECT name,department,position,salary,email,created_at FROM employees ORDER BY id").fetchall()
    conn.close()
    wb = Workbook()
    ws = wb.active
    ws.title = '员工列表'
    ws.append(['姓名', '部门', '职位', '薪资', '邮箱', '入职时间'])
    for r in rows:
        ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='employees.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ---------- 订单模块 ----------
@app.route('/orders')
@login_required
def orders():
    page = max(1, request.args.get('page', 1, type=int))
    status = request.args.get('status', '')
    where, params = "", []
    if status:
        where = "WHERE status=?"; params.append(status)
    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) c FROM orders {where}", params).fetchone()['c']
    rows = conn.execute(f"SELECT * FROM orders {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                        params + [PAGE_SIZE, (page-1)*PAGE_SIZE]).fetchall()
    statuses = [r['status'] for r in conn.execute("SELECT DISTINCT status FROM orders").fetchall()]
    conn.close()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return render_template('orders.html', orders=rows, statuses=statuses,
                           cur_status=status, page=page, total_pages=total_pages)

@app.route('/orders/add', methods=['POST'])
@login_required
def order_add():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    order_no = 'ORD' + datetime.now().strftime('%Y%m%d%H%M%S')
    conn = get_db()
    conn.execute("INSERT INTO orders (order_no,customer,product,amount,status,created_at) VALUES (?,?,?,?,?,?)",
                 (order_no, request.form['customer'], request.form['product'],
                  float(request.form['amount']), request.form.get('status', '待付款'), now))
    conn.commit()
    conn.close()
    return redirect(url_for('orders'))

@app.route('/orders/<int:oid>/status', methods=['POST'])
@login_required
def order_status(oid):
    conn = get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (request.form['status'], oid))
    conn.commit()
    conn.close()
    return redirect(url_for('orders'))

@app.route('/orders/<int:oid>/delete', methods=['POST'])
@login_required
def order_delete(oid):
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    return redirect(url_for('orders'))

# ---------- API ----------
@app.route('/api/sales')
@login_required
def api_sales():
    conn = get_db()
    rows = conn.execute("SELECT month, amount FROM sales ORDER BY month").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
