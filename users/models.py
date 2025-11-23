from django.db import models
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from PIL import Image
import os

from django.contrib.auth.models import AbstractUser
from utils.file_system import (
    user_avatar_upload_path,
    DirectoryManager,
    FileCleanupManager,
    FileSystemError,
)
from .validators import validate_safe_username


class User(AbstractUser):
    """Модель пользователя."""

    class Meta:
        indexes = [
            models.Index(fields=["telegram_id"], name="users_telegram_id_idx"),
            models.Index(fields=["telegram_username"], name="users_telegram_username_idx"),
        ]

    avatar = models.ImageField(
        upload_to=user_avatar_upload_path,
        blank=True,
        null=True,
        help_text="Аватарка пользователя",
        validators=[],
    )

    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="Информация о себе (до 500 символов)",
    )

    telegram_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        help_text="Telegram ID пользователя (заглушка)",
        db_index=True,
    )
    telegram_username = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Telegram username (заглушка)",
        db_index=True,
    )
    telegram_connected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Дата подключения Telegram аккаунта (заглушка)",
    )

    @property
    def has_telegram(self):
        return bool(self.telegram_id)

    def save(self, *args, **kwargs):
        """Обработка аватарки: создание папки и ресайз до 200x200px."""
        self.full_clean()
        is_new_user = self.pk is None
        old_avatar = None
        if not is_new_user:
            try:
                old_user = User.objects.get(pk=self.pk)
                old_avatar = old_user.avatar
            except User.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if self.avatar:
            try:
                if is_new_user or not old_avatar:
                    DirectoryManager.create_user_directory(self.id)

                self._resize_avatar()

            except (FileSystemError, Exception):
                pass

        if old_avatar and old_avatar != self.avatar and old_avatar.name:
            try:
                if default_storage.exists(old_avatar.name):
                    default_storage.delete(old_avatar.name)
            except Exception:
                pass

    def _resize_avatar(self):
        """Ресайз аватарки до 200x200px с центрированием."""
        if not self.avatar:
            return

        try:
            if not os.path.exists(self.avatar.path):
                return

            img = Image.open(self.avatar.path)

            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background

            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            square_img = Image.new("RGB", (200, 200), (255, 255, 255))
            x = (200 - img.width) // 2
            y = (200 - img.height) // 2
            square_img.paste(img, (x, y))
            square_img.save(self.avatar.path, "JPEG", quality=85, optimize=True)

        except FileSystemError:
            raise
        except Exception as e:
            raise FileSystemError(f"Failed to resize avatar for user {self.id}: {e}") from e

    def delete(self, *args, **kwargs):
        """Удаление пользователя с очисткой файлов."""
        user_id = self.id

        try:
            FileCleanupManager.cleanup_user_files(user_id)
        except FileSystemError:
            try:
                if self.avatar and self.avatar.name:
                    if default_storage.exists(self.avatar.name):
                        default_storage.delete(self.avatar.name)
            except Exception:
                pass
        except Exception:
            pass

        super().delete(*args, **kwargs)
