from app import create_app
from app.extensions import db
from app.models import User, Reward, WeeklyReward

USERS = [
    {'email': 'admin@example.com', 'username': 'admin', 'password': 'admin123', 'is_admin': True},
    {'email': 'alice@example.com', 'username': 'alice', 'password': 'alice123', 'is_admin': False},
    {'email': 'bob@example.com',   'username': 'bob',   'password': 'bob12345', 'is_admin': False},
]

# Награды за опыт: (title, required_xp, icon_url)
REWARDS = [
    ('Первый росток',     50,  'images/rewards/exp_50.png'),
    ('Тёплый огонёк',    100,  'images/rewards/exp_100.png'),
    ('Уютный хранитель', 250,  'images/rewards/exp_250.png'),
    ('Мастер привычек',  500,  'images/rewards/exp_500.png'),
]

# Недельные награды по очереди: (position, title, icon_url)
WEEKLY_REWARDS = [
    (1, 'Семечко недели',   'images/weekly_rewards/week_1.png'),
    (2, 'Листок недели',    'images/weekly_rewards/week_2.png'),
    (3, 'Бутон недели',     'images/weekly_rewards/week_3.png'),
    (4, 'Цветок недели',    'images/weekly_rewards/week_4.png'),
    (5, 'Букет недели',     'images/weekly_rewards/week_5.png'),
]


def seed():
    app = create_app()
    with app.app_context():
        # --- пользователи ---
        for data in USERS:
            if User.query.filter_by(email=data['email']).first():
                print(f'[skip] user {data["email"]}')
                continue
            user = User(email=data['email'], username=data['username'], is_admin=data['is_admin'])
            user.set_password(data['password'])
            db.session.add(user)
            print(f'[add]  user {data["email"]} (admin={data["is_admin"]})')

        # --- награды за опыт ---
        for title, xp, icon in REWARDS:
            if Reward.query.filter_by(title=title).first():
                print(f'[skip] reward {title}')
                continue
            db.session.add(Reward(title=title, icon_url=icon, required_xp=xp))
            print(f'[add]  reward {title} ({xp} XP)')

        # --- недельные награды ---
        for position, title, icon in WEEKLY_REWARDS:
            if WeeklyReward.query.filter_by(position=position).first():
                print(f'[skip] weekly {position}')
                continue
            db.session.add(WeeklyReward(position=position, title=title, icon_url=icon))
            print(f'[add]  weekly #{position} {title}')

        db.session.commit()

        print('\nГотово.')
        print('Пользователи:')
        for u in User.query.all():
            print(f'  {u.id:>2}  {u.email:<25}  admin={u.is_admin}  xp={u.experience}')


if __name__ == '__main__':
    seed()
