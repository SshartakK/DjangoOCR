from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Docs(models.Model):
    file_path = models.CharField(max_length=255)
    size = models.FloatField(help_text='Размер файла в Кб')

    def __str__(self):
        return self.file_path

class UsersToDocs(models.Model):
    username = models.CharField(max_length=150)
    docs = models.ForeignKey(Docs, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.username} - {self.docs.file_path}"

class Price(models.Model):
    file_type = models.CharField(max_length=16)
    price = models.FloatField(help_text='Цена за 1 Кб')

    def __str__(self):
        return f"{self.file_type}: {self.price}"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    docs = models.ForeignKey(Docs, on_delete=models.CASCADE)
    order_price = models.FloatField()
    payment = models.BooleanField(default=False)

    def __str__(self):
        return f"Order by {self.user.username} for {self.docs.file_path}"
