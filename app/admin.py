import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from app.decorators import admin_required
from app.extensions import db
from app.models import User, Habit, HabitLog, Reward, WeeklyReward, UserReward, UserWeeklyReward, RecommendedHabit
from app.uploads import (
    save_reward_icon, delete_reward_icon, is_allowed_image,
    save_recommended_icon, delete_recommended_icon,
)

admin = Blueprint('admin', __name__, url_prefix='/admin')


@admin.route('/')
@admin_required
def dashboard():
    xp_rewards = Reward.query.order_by(Reward.required_xp).all()
    weekly_rewards = WeeklyReward.query.order_by(WeeklyReward.position).all()
    recommended = RecommendedHabit.query.order_by(RecommendedHabit.id).all()
    return render_template(
        'admin.html',
        xp_rewards=xp_rewards,
        weekly_rewards=weekly_rewards,
        recommended=recommended,
    )


def _validate_icon(file_storage, errors):
    if not file_storage or not file_storage.filename:
        errors.append('Загрузите картинку награды.')
        return None
    if not is_allowed_image(file_storage.filename):
        errors.append('Картинка: только PNG, JPG, JPEG, GIF, WEBP.')
        return None
    return file_storage


# ----- Награды за опыт -----

@admin.route('/rewards/new', methods=['POST'])
@admin_required
def reward_new():
    title = (request.form.get('title') or '').strip()
    required_xp = request.form.get('required_xp', type=int)

    errors = []
    if not title:
        errors.append('Укажите название награды.')
    if required_xp is None or required_xp < 0:
        errors.append('Укажите корректный порог опыта (XP).')
    icon_file = _validate_icon(request.files.get('icon'), errors)

    if errors:
        for e in errors:
            flash(e, 'error')
        return redirect(url_for('admin.dashboard'))

    db.session.add(Reward(
        title=title,
        required_xp=required_xp,
        icon_url=save_reward_icon(icon_file),
    ))
    db.session.commit()
    flash('Награда за опыт добавлена.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/rewards/<int:reward_id>/delete', methods=['POST'])
@admin_required
def reward_delete(reward_id):
    reward = Reward.query.get_or_404(reward_id)
    icon = reward.icon_url
    UserReward.query.filter_by(reward_id=reward.id).delete()
    db.session.delete(reward)
    db.session.commit()
    delete_reward_icon(icon)
    flash('Награда удалена.', 'info')
    return redirect(url_for('admin.dashboard'))


# ----- Недельные награды -----

@admin.route('/weekly/new', methods=['POST'])
@admin_required
def weekly_new():
    title = (request.form.get('title') or '').strip()

    errors = []
    if not title:
        errors.append('Укажите название недельной награды.')
    icon_file = _validate_icon(request.files.get('icon'), errors)

    if errors:
        for e in errors:
            flash(e, 'error')
        return redirect(url_for('admin.dashboard'))

    # позиция = следующая по очереди
    last = WeeklyReward.query.order_by(WeeklyReward.position.desc()).first()
    next_position = (last.position + 1) if last else 1

    db.session.add(WeeklyReward(
        position=next_position,
        title=title,
        icon_url=save_reward_icon(icon_file),
    ))
    db.session.commit()
    flash('Недельная награда добавлена.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/weekly/<int:weekly_id>/delete', methods=['POST'])
@admin_required
def weekly_delete(weekly_id):
    reward = WeeklyReward.query.get_or_404(weekly_id)
    icon = reward.icon_url
    UserWeeklyReward.query.filter_by(weekly_reward_id=reward.id).delete()
    db.session.delete(reward)
    db.session.commit()
    delete_reward_icon(icon)
    flash('Недельная награда удалена.', 'info')
    return redirect(url_for('admin.dashboard'))


# ----- Рекомендованные привычки -----

@admin.route('/recommended/new', methods=['POST'])
@admin_required
def recommended_new():
    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip() or None

    errors = []
    if not title:
        errors.append('Укажите название привычки.')
    icon_file = _validate_icon(request.files.get('icon'), errors)

    if errors:
        for e in errors:
            flash(e, 'error')
        return redirect(url_for('admin.dashboard'))

    db.session.add(RecommendedHabit(
        title=title,
        description=description,
        icon=save_recommended_icon(icon_file),
    ))
    db.session.commit()
    flash('Рекомендованная привычка добавлена.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/recommended/<int:rec_id>/delete', methods=['POST'])
@admin_required
def recommended_delete(rec_id):
    rec = RecommendedHabit.query.get_or_404(rec_id)
    icon = rec.icon
    db.session.delete(rec)
    db.session.commit()
    delete_recommended_icon(icon)
    flash('Рекомендованная привычка удалена.', 'info')
    return redirect(url_for('admin.dashboard'))


# ----- Экспорт сводки по пользователям (CSV) -----

@admin.route('/export/users.csv')
@admin_required
def export_users_csv():
    # счётчики привычек и выполнений по каждому пользователю
    habits_count = dict(
        db.session.query(Habit.user_id, func.count(Habit.id))
        .group_by(Habit.user_id).all()
    )
    logs_count = dict(
        db.session.query(HabitLog.user_id, func.count(HabitLog.id))
        .filter(HabitLog.is_done.is_(True))
        .group_by(HabitLog.user_id).all()
    )

    rows = []
    for u in User.query.order_by(User.id).all():
        rows.append([
            u.id,
            u.email,
            u.username,
            u.experience,
            u.days_streak,
            habits_count.get(u.id, 0),
            logs_count.get(u.id, 0),
            'да' if u.is_admin else 'нет',
            u.created_at.strftime('%d.%m.%Y'),
        ])

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=';')
    writer.writerow([
        'ID', 'Email', 'Имя', 'Опыт', 'Серия (дней)',
        'Привычек', 'Выполнений', 'Админ', 'Регистрация',
    ])
    writer.writerows(rows)

    data = '﻿' + buf.getvalue()  # BOM для Excel
    return Response(
        data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=cozyhabits_users.csv'},
    )
