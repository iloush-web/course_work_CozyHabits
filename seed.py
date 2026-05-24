from app import create_app
from app.extensions import db
from app.models import User

USERS = [
    {'email': 'admin@example.com', 'username': 'admin', 'password': 'admin123', 'is_admin': True},
    {'email': 'alice@example.com', 'username': 'alice', 'password': 'alice123', 'is_admin': False},
    {'email': 'bob@example.com',   'username': 'bob',   'password': 'bob12345', 'is_admin': False},
]


def seed_users():
    app = create_app()
    with app.app_context():
        for data in USERS:
            existing = User.query.filter_by(email=data['email']).first()
            if existing:
                print(f'[skip] {data["email"]} уже существует')
                continue

            user = User(
                email=data['email'],
                username=data['username'],
                is_admin=data['is_admin'],
            )
            user.set_password(data['password'])
            db.session.add(user)
            print(f'[add]  {data["email"]} (admin={data["is_admin"]})')

        db.session.commit()
        print('\nГотово. Список пользователей:')
        for u in User.query.all():
            print(f'  {u.id:>2}  {u.email:<25}  admin={u.is_admin}  xp={u.experience}')


if __name__ == '__main__':
    seed_users()
