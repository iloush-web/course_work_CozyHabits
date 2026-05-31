import os
import uuid

from flask import current_app
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
HABIT_ICONS_SUBDIR = 'uploads/habits'      # relative to /static
REWARD_ICONS_SUBDIR = 'uploads/rewards'    # relative to /static
AVATARS_SUBDIR = 'uploads/avatars'         # relative to /static
MAX_ICON_SIZE = 800  # px (square)


def _ext(filename: str) -> str:
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def is_allowed_image(filename: str) -> bool:
    return _ext(filename) in ALLOWED_EXTENSIONS


def _process_to_square(file_storage) -> Image.Image:
    """Open uploaded file, center-crop to square, downscale to MAX_ICON_SIZE if larger."""
    img = Image.open(file_storage.stream)
    img = ImageOps.exif_transpose(img)  # respect EXIF orientation

    side = min(img.width, img.height)
    img = ImageOps.fit(img, (side, side), method=Image.LANCZOS, centering=(0.5, 0.5))

    if img.width > MAX_ICON_SIZE:
        img = img.resize((MAX_ICON_SIZE, MAX_ICON_SIZE), Image.LANCZOS)

    return img


def _save_image(file_storage, subdir: str) -> str | None:
    """Save uploaded image (cropped to square, max 800x800) into subdir. Return path relative to /static."""
    if not file_storage or not file_storage.filename:
        return None

    if not is_allowed_image(file_storage.filename):
        return None

    ext = _ext(file_storage.filename)
    if ext == 'jpg':
        ext = 'jpeg'

    name = secure_filename(f'{uuid.uuid4().hex}.{ext}')

    abs_dir = os.path.join(current_app.static_folder, *subdir.split('/'))
    os.makedirs(abs_dir, exist_ok=True)
    abs_path = os.path.join(abs_dir, name)

    img = _process_to_square(file_storage)

    save_kwargs = {}
    if ext == 'jpeg':
        if img.mode != 'RGB':
            img = img.convert('RGB')
        save_kwargs = {'quality': 90, 'optimize': True}
    elif ext == 'png':
        save_kwargs = {'optimize': True}

    img.save(abs_path, **save_kwargs)

    return f'{subdir}/{name}'


def _delete_image(rel_path: str | None, subdir: str) -> None:
    """Delete previously saved file. Safe to call with None."""
    if not rel_path:
        return
    if not rel_path.startswith(subdir + '/'):
        return  # guard against deleting unrelated paths

    abs_path = os.path.join(current_app.static_folder, *rel_path.split('/'))
    try:
        os.remove(abs_path)
    except OSError:
        pass


def save_habit_icon(file_storage) -> str | None:
    return _save_image(file_storage, HABIT_ICONS_SUBDIR)


def delete_habit_icon(rel_path: str | None) -> None:
    _delete_image(rel_path, HABIT_ICONS_SUBDIR)


def save_reward_icon(file_storage) -> str | None:
    return _save_image(file_storage, REWARD_ICONS_SUBDIR)


def delete_reward_icon(rel_path: str | None) -> None:
    _delete_image(rel_path, REWARD_ICONS_SUBDIR)


def save_avatar(file_storage) -> str | None:
    return _save_image(file_storage, AVATARS_SUBDIR)


def delete_avatar(rel_path: str | None) -> None:
    _delete_image(rel_path, AVATARS_SUBDIR)
