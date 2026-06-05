"""Отправка web-push уведомлений через pywebpush."""
import json

from flask import current_app
from pywebpush import webpush, WebPushException

from app.extensions import db
from app.models import PushSubscription


def send_push_to_subscription(sub: PushSubscription, title: str, body: str, url: str = '/') -> bool:
    """Отправить пуш одной подписке. Возвращает False, если подписка мертва (удалена)."""
    payload = json.dumps({'title': title, 'body': body, 'url': url})

    try:
        webpush(
            subscription_info={
                'endpoint': sub.endpoint,
                'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
            },
            data=payload,
            vapid_private_key=current_app.config['VAPID_PRIVATE_KEY'],
            vapid_claims={'sub': current_app.config['VAPID_CLAIM_EMAIL']},
        )
        return True
    except WebPushException as e:
        # 404/410 — подписка больше не действительна, чистим её из БД
        status = getattr(e.response, 'status_code', None)
        if status in (404, 410):
            db.session.delete(sub)
            db.session.commit()
        else:
            current_app.logger.warning('Push failed: %s', e)
        return False


def send_push_to_user(user_id: int, title: str, body: str, url: str = '/') -> int:
    """Отправить пуш на все устройства пользователя. Возвращает число успешных."""
    sent = 0
    subs = PushSubscription.query.filter_by(user_id=user_id).all()
    for sub in subs:
        if send_push_to_subscription(sub, title, body, url):
            sent += 1
    return sent
