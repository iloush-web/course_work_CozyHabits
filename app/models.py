from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import JSON

from app.extensions import db, bcrypt, login_manager


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    experience = db.Column(db.Integer, default=0, nullable=False)
    days_streak = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    habits = db.relationship('Habit', backref='user', lazy=True, cascade='all, delete-orphan')
    habit_logs = db.relationship('HabitLog', backref='user', lazy=True, cascade='all, delete-orphan')
    user_rewards = db.relationship('UserReward', backref='user', lazy=True, cascade='all, delete-orphan')
    user_weekly_rewards = db.relationship('UserWeeklyReward', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)


class Habit(db.Model):
    __tablename__ = 'habits'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(255), default='star', nullable=True)  # путь к картинке или 'star'
    frequency = db.Column(db.String(20), nullable=False)  # 'daily' / 'weekly'
    target_days = db.Column(JSON, nullable=True)  # list[int], напр. [1, 3, 5]
    reminder_time = db.Column(db.Time, nullable=True)
    color = db.Column(db.String(20), default='#4CAF50', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    logs = db.relationship('HabitLog', backref='habit', lazy=True, cascade='all, delete-orphan')


class RecommendedHabit(db.Model):
    """Каталог рекомендуемых привычек (наполняет админ). Юзер копирует себе в habits."""
    __tablename__ = 'recommended_habits'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(255), default='star', nullable=True)


class HabitLog(db.Model):
    __tablename__ = 'habit_logs'

    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habits.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    log_date = db.Column(db.Date, nullable=False)
    is_done = db.Column(db.Boolean, default=True, nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ----- Награды за опыт (XP) -----

class Reward(db.Model):
    """Каталог наград за опыт. Открывается при достижении required_xp."""
    __tablename__ = 'rewards'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    icon_url = db.Column(db.String(255), nullable=False)
    required_xp = db.Column(db.Integer, nullable=False)  # порог опыта

    user_rewards = db.relationship('UserReward', backref='reward', lazy=True, cascade='all, delete-orphan')


class UserReward(db.Model):
    """Какой пользователь открыл какую XP-награду."""
    __tablename__ = 'user_rewards'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reward_id = db.Column(db.Integer, db.ForeignKey('rewards.id'), nullable=False)
    obtained_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'reward_id', name='uq_user_reward'),
    )


# ----- Недельные награды (выдаются по очереди) -----

class WeeklyReward(db.Model):
    """Каталог недельных наград. Выдаются по очереди (position)."""
    __tablename__ = 'weekly_rewards'

    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer, unique=True, nullable=False)  # порядок выдачи: 1, 2, 3...
    title = db.Column(db.String(120), nullable=False)
    icon_url = db.Column(db.String(255), nullable=False)

    user_weekly_rewards = db.relationship('UserWeeklyReward', backref='weekly_reward', lazy=True, cascade='all, delete-orphan')


class UserWeeklyReward(db.Model):
    """Недельная награда, полученная пользователем."""
    __tablename__ = 'user_weekly_rewards'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    weekly_reward_id = db.Column(db.Integer, db.ForeignKey('weekly_rewards.id'), nullable=False)
    obtained_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'weekly_reward_id', name='uq_user_weekly_reward'),
    )
