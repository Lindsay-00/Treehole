from django.db import models

# model for post
class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    content = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_on']
