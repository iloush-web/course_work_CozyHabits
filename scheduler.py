"""Планировщик напоминаний о привычках.

Раз в минуту проверяет привычки, у которых reminder_time совпадает с текущим
временем и которые запланированы на сегодня, и шлёт пуш владельцу.

Запускается отдельным процессом (в docker — отдельный контейнер на том же образе):
    python scheduler.py
"""
import time
from datetime import datetime, date

from app import create_app
from app.extensions import db
from app.models import Habit
from app.routes import _habit_scheduled_on
from app.push import send_push_to_user

CHECK_INTERVAL = 60  # секунд


def run_once(app):
    """Один проход: найти привычки на текущую минуту и разослать пуши."""
    with app.app_context():
        now = datetime.now()
        today = date.today()
        iso_dow = today.isoweekday()  # 1=Пн ... 7=Вс
        cur_hm = (now.hour, now.minute)

        habits = (
            Habit.query
            .filter(Habit.is_active.is_(True), Habit.reminder_time.isnot(None))
            .all()
        )

        for habit in habits:
            rt = habit.reminder_time
            if (rt.hour, rt.minute) != cur_hm:
                continue
            if not _habit_scheduled_on(habit, today, iso_dow):
                continue

            send_push_to_user(
                habit.user_id,
                'Пора выполнить привычку 🌿',
                habit.title,
                url='/week',
            )


def main():
    app = create_app()
    print('[scheduler] запущен, интервал', CHECK_INTERVAL, 'сек', flush=True)
    # выравниваемся на начало минуты, чтобы не пропускать/не дублировать
    while True:
        run_once(app)
        # спим до следующей минуты
        sleep_for = CHECK_INTERVAL - datetime.now().second
        time.sleep(max(1, sleep_for))


if __name__ == '__main__':
    main()
