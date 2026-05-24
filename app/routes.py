from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Habit
from app.uploads import save_habit_icon, delete_habit_icon, is_allowed_image

main = Blueprint('main', __name__)

VALID_FREQUENCIES = ('daily', 'weekly')
VALID_DAYS = (1, 2, 3, 4, 5, 6, 7)  # 1=Пн ... 7=Вс


def _parse_form(form):
    title = (form.get('title') or '').strip()
    description = (form.get('description') or '').strip() or None
    frequency = (form.get('frequency') or '').strip()
    color = (form.get('color') or '#4CAF50').strip() or '#4CAF50'

    target_days_raw = form.getlist('target_days')
    target_days = [int(d) for d in target_days_raw if d.isdigit() and int(d) in VALID_DAYS]
    target_days = target_days or None

    reminder_raw = (form.get('reminder_time') or '').strip()
    reminder_time = None
    if reminder_raw:
        try:
            reminder_time = datetime.strptime(reminder_raw, '%H:%M').time()
        except ValueError:
            reminder_time = None

    errors = []
    if not title:
        errors.append('Название обязательно.')
    if frequency not in VALID_FREQUENCIES:
        errors.append('Выберите частоту: daily или weekly.')
    if frequency == 'weekly' and not target_days:
        errors.append('Для еженедельной привычки выберите хотя бы один день.')

    return {
        'title': title,
        'description': description,
        'frequency': frequency,
        'target_days': target_days,
        'reminder_time': reminder_time,
        'color': color,
    }, errors


def _validate_icon_upload(file_storage, errors):
    """Returns saved relative path or None. Appends to errors if invalid."""
    if not file_storage or not file_storage.filename:
        return None
    if not is_allowed_image(file_storage.filename):
        errors.append('Иконка: допустимы только PNG, JPG, JPEG, GIF, WEBP.')
        return None
    return file_storage  # defer saving until after validation passes


def _get_own_habit_or_404(habit_id: int) -> Habit:
    habit = Habit.query.get_or_404(habit_id)
    if habit.user_id != current_user.id:
        abort(403)
    return habit


@main.route('/')
@main.route('/habits')
@login_required
def habits():
    user_habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).order_by(Habit.created_at.desc()).all()
    return render_template('habits.html', habits=user_habits)


@main.route('/habits/new', methods=['GET', 'POST'])
@login_required
def habit_new():
    if request.method == 'POST':
        data, errors = _parse_form(request.form)
        icon_file = _validate_icon_upload(request.files.get('icon'), errors)

        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template('habit_form.html', mode='new', habit=data, form_action=url_for('main.habit_new'))

        icon_path = save_habit_icon(icon_file) if icon_file else None

        habit = Habit(user_id=current_user.id, icon=icon_path, **data)
        db.session.add(habit)
        db.session.commit()
        flash('Привычка создана.', 'success')
        return redirect(url_for('main.habits'))

    return render_template('habit_form.html', mode='new', habit=None, form_action=url_for('main.habit_new'))


@main.route('/habits/<int:habit_id>/edit', methods=['GET', 'POST'])
@login_required
def habit_edit(habit_id):
    habit = _get_own_habit_or_404(habit_id)

    if request.method == 'POST':
        data, errors = _parse_form(request.form)
        icon_file = _validate_icon_upload(request.files.get('icon'), errors)

        if errors:
            for err in errors:
                flash(err, 'error')
            # preserve existing icon when re-rendering on error
            preview = {**data, 'icon': habit.icon}
            return render_template('habit_form.html', mode='edit', habit=preview, form_action=url_for('main.habit_edit', habit_id=habit.id))

        for key, value in data.items():
            setattr(habit, key, value)

        if icon_file:
            old_icon = habit.icon
            habit.icon = save_habit_icon(icon_file)
            delete_habit_icon(old_icon)

        db.session.commit()
        flash('Изменения сохранены.', 'success')
        return redirect(url_for('main.habits'))

    return render_template('habit_form.html', mode='edit', habit=habit, form_action=url_for('main.habit_edit', habit_id=habit.id))


@main.route('/habits/<int:habit_id>/delete', methods=['POST'])
@login_required
def habit_delete(habit_id):
    habit = _get_own_habit_or_404(habit_id)
    old_icon = habit.icon
    db.session.delete(habit)
    db.session.commit()
    delete_habit_icon(old_icon)
    flash('Привычка удалена.', 'info')
    return redirect(url_for('main.habits'))
