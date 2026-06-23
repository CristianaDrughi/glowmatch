"""Autentificare admin folosind Flask-Login.

Parola este verificata cu werkzeug (PBKDF2). Hash-urile sunt stocate in
tabela admin_users, generate de seed_db.py la initializare.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import UserMixin, login_user, logout_user, login_required
from werkzeug.security import check_password_hash

from db import get_db

auth_bp = Blueprint('auth', __name__)


class AdminUser(UserMixin):
    def __init__(self, row):
        self.id = str(row['id'])
        self.username = row['username']
        self.rol = row['rol']


def load_user(user_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM admin_users WHERE id = ?", (user_id,)
        ).fetchone()
    return AdminUser(row) if row else None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM admin_users WHERE username = ?", (username,)
            ).fetchone()
        if row and check_password_hash(row['password_hash'], password):
            login_user(AdminUser(row))
            return redirect(url_for('admin.products'))
        flash('Username sau parola incorecta', 'error')
    return render_template('admin/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Te-ai delogat cu succes', 'success')
    return redirect(url_for('auth.login'))
