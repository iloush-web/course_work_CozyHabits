import calendar
from datetime import datetime, date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Habit, HabitLog
from app.uploads import save_habit_icon, delete_habit_icon, is_allowed_image

main = Blueprint('main', __name__)

VALID_FREQUENCIES = ('daily', 'weekly')
VALID_DAYS = (1, 2, 3, 4, 5, 6, 7)  # 1=Пн ... 7=Вс

DAY_NAMES = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')

MONTHS_GEN = (
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
)

MONTHS_NOM = (
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
)


def _habit_scheduled_on(habit, day: date, iso_dow: int) -> bool:
    """Запланирована ли привычка на конкретный день."""
    if day < habit.created_at.date():
        return False
    if habit.frequency == 'daily':
        return True
    if habit.frequency == 'weekly' and habit.target_days:
        return iso_dow in habit.target_days
    return False


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


@main.route('/week')
@login_required
def week():
    offset = request.args.get('offset', 0, type=int)

    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    sunday = monday + timedelta(days=6)

    # какой день недели выбран (0=Пн ... 6=Вс)
    default_sel = today.weekday() if monday <= today <= sunday else 0
    sel = request.args.get('day', default_sel, type=int)
    if sel < 0 or sel > 6:
        sel = default_sel

    user_habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).all()

    # выполненные привычки за показанную неделю: {(habit_id, date)}
    week_logs = HabitLog.query.filter(
        HabitLog.user_id == current_user.id,
        HabitLog.is_done.is_(True),
        HabitLog.log_date >= monday,
        HabitLog.log_date <= sunday,
    ).all()
    done_set = {(log.habit_id, log.log_date) for log in week_logs}

    # данные по всем 7 дням (привычки рендерятся сразу, переключение — на JS)
    days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        iso_dow = i + 1  # 1=Пн ... 7=Вс

        scheduled = [h for h in user_habits if _habit_scheduled_on(h, d, iso_dow)]
        # сортировка по времени напоминания (утро -> вечер), без времени — в конец
        scheduled.sort(key=lambda h: (h.reminder_time is None, h.reminder_time))

        pending, done = [], []
        for h in scheduled:
            (done if (h.id, d) in done_set else pending).append(h)

        days.append({
            'index': i,
            'date': d,
            'date_iso': d.isoformat(),
            'name': DAY_NAMES[i],
            'day_num': d.day,
            'label': f'{d.day} {MONTHS_GEN[d.month - 1].capitalize()}',
            'is_today': d == today,
            'is_selected': i == sel,
            'pending': pending,
            'done': done,
        })

    return render_template(
        'week.html',
        days=days,
        offset=offset,
        selected_index=sel,
    )


@main.route('/habits/<int:habit_id>/toggle', methods=['POST'])
@login_required
def habit_toggle(habit_id):
    habit = _get_own_habit_or_404(habit_id)

    try:
        log_date = datetime.strptime(request.form.get('log_date', ''), '%Y-%m-%d').date()
    except ValueError:
        abort(400)

    log = HabitLog.query.filter_by(
        habit_id=habit.id, user_id=current_user.id, log_date=log_date
    ).first()

    if log:
        db.session.delete(log)  # снять отметку
    else:
        db.session.add(HabitLog(
            habit_id=habit.id, user_id=current_user.id,
            log_date=log_date, is_done=True,
        ))
    db.session.commit()

    # вернуться на ту же неделю и день
    offset = request.form.get('offset', 0, type=int)
    day = request.form.get('day', 0, type=int)
    return redirect(url_for('main.week', offset=offset, day=day))


@main.route('/profile')
@login_required
def profile():
    # награды юзера: за опыт + недельные, новые сверху
    earned = sorted(
        list(current_user.user_rewards) + list(current_user.user_weekly_rewards),
        key=lambda r: r.obtained_at,
        reverse=True,
    )
    # у UserReward есть .reward, у UserWeeklyReward — .weekly_reward; оба с title/icon_url
    rewards = [r.reward if hasattr(r, 'reward') else r.weekly_reward for r in earned]
    return render_template('profile.html', user=current_user, achievements=rewards)


@main.route('/statistics')
@login_required
def statistics():
    offset = request.args.get('offset', 0, type=int)

    today = date.today()
    # целевой месяц = текущий + offset (с переносом года)
    month_index = today.month - 1 + offset
    year = today.year + month_index // 12
    month = month_index % 12 + 1

    first_day = date(year, month, 1)
    last_dom = calendar.monthrange(year, month)[1]
    last_day = date(year, month, last_dom)

    user_habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).all()

    # выполненные привычки по датам месяца: {date: {habit_id, ...}}
    logs = HabitLog.query.filter(
        HabitLog.user_id == current_user.id,
        HabitLog.is_done.is_(True),
        HabitLog.log_date >= first_day,
        HabitLog.log_date <= last_day,
    ).all()
    done_by_date = {}
    for log in logs:
        done_by_date.setdefault(log.log_date, set()).add(log.habit_id)

    # сетка месяца (недели по 7 дней, 0 = пустая клетка)
    cal = calendar.Calendar(firstweekday=0)  # 0 = понедельник
    weeks = []
    for week in cal.monthdayscalendar(year, month):
        cells = []
        for d in week:
            if d == 0:
                cells.append({'day': None, 'status': None, 'is_today': False})
                continue

            day_date = date(year, month, d)
            iso_dow = day_date.isoweekday()  # 1=Пн ... 7=Вс
            planned = [h for h in user_habits if _habit_scheduled_on(h, day_date, iso_dow)]

            status = None
            if planned:
                planned_ids = {h.id for h in planned}
                done_ids = done_by_date.get(day_date, set()) & planned_ids
                if len(done_ids) == len(planned_ids):
                    status = 'all'      # все выполнены -> зелёный
                elif done_ids:
                    status = 'some'     # хотя бы одна -> жёлтый

            cells.append({'day': d, 'status': status, 'is_today': day_date == today})
        weeks.append(cells)

    return render_template(
        'statistics.html',
        weeks=weeks,
        day_names=DAY_NAMES,
        month_label=f'{MONTHS_NOM[month - 1]} {year}',
        offset=offset,
    )


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
