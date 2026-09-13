from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    """A single conversation thread, owned by a logged-in user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="chat_sessions",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=64, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        owner = self.user.username if self.user_id else self.session_key
        return f"Session ({owner}) {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def title(self):
        """Short label for the sidebar history list, from the first user message."""
        first = self.messages.filter(role="user").order_by("created_at").first()
        if not first:
            return "New chat"
        text = first.content.strip().replace("\n", " ")
        return text[:42] + ("…" if len(text) > 42 else "")


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("bot", "Bot"),
    )

    session = models.ForeignKey(ChatSession, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"
