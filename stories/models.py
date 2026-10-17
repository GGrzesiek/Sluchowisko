from django.db import models


class Story(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        VERIFIED = "verified"
        REJECTED = "rejected"

    group_id = models.CharField(max_length=10, unique=True)
    title = models.CharField(max_length=200)
    narration = models.TextField()
    text = models.TextField()
    audio_url = models.CharField(max_length=500, blank=True)
    audio_seconds = models.PositiveIntegerField(null=True, blank=True)
    photos = models.JSONField(default=list)
    sources = models.JSONField(default=list)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    generated_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "stories"
        ordering = ["group_id"]

    def save(self, *args, **kwargs):
        if self.status != self.Status.VERIFIED:
            self.audio_url, self.audio_seconds = "", None
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = {*kwargs["update_fields"], "audio_url", "audio_seconds"}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.group_id} {self.title}"
