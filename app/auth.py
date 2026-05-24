import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import User

auth = Blueprint('auth', __name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.habits'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        password_confirm = request.form.get('password_confirm') or ''

        errors = []
        if not EMAIL_RE.match(email):
            errors.append('Введите корректный email.')
        if not username:
            errors.append('Имя пользователя обязательно.')
        if len(password) < 6:
            errors.append('Пароль должен быть не короче 6 символов.')
        if password != password_confirm:
            errors.append('Пароли не совпадают.')
        if User.query.filter_by(email=email).first():
            errors.append('Пользователь с таким email уже зарегистрирован.')

        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template('register.html', email=email, username=username)

        user = User(email=email, username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('Регистрация прошла успешно!', 'success')
        return redirect(url_for('main.habits'))

    return render_template('register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.habits'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash('Неверный email или пароль.', 'error')
            return render_template('login.html', email=email)

        login_user(user, remember=remember)
        next_url = request.args.get('next')
        return redirect(next_url or url_for('main.habits'))

    return render_template('login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('auth.login'))
