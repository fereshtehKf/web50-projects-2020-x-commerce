from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    watchlist_counter = models.IntegerField(default=0, blank=True)
    watchlist = models.ManyToManyField('AuctionListing', related_name='watchlist', blank=True)
    pass


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)  # Ensure category names are unique

    def __str__(self):
        return self.name

class AuctionListing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    starting_bid = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)  # Updated field
    image_url = models.URLField(default='https://m.media-amazon.com/images/I/31j-sT4LyML._QL70_FMwebp_.jpg')
    bid_counter = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    winner = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f'{self.title}: by {self.user.username}'


class Bid(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    created_at = models.DateTimeField(auto_now=True)
    auction = models.ForeignKey(AuctionListing, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.amount} on {self.auction} by {self.user.username}'


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    auction = models.ForeignKey(AuctionListing, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.user}: {self.text}'