from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.decorators import admin_required
from app.extensions import db
from app.models import Reward, WeeklyReward, UserReward, UserWeeklyReward
from app.uploads import save_reward_icon, delete_reward_icon, is_allowed_image

admin = Blueprint('admin', __name__, url_prefix='/admin')


@admin.route('/')
@admin_required
def dashboard():
    xp_rewards = Reward.query.order_by(Reward.required_xp).all()
    weekly_rewards = WeeklyReward.query.order_by(WeeklyReward.position).all()
    return render_template('admin.html', xp_rewards=xp_rewards, weekly_rewards=weekly_rewards)


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
