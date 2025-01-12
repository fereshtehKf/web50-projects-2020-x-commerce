from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from .models import User, AuctionListing, Bid, Comment,Category
from .forms import AuctionListingForm, CommentForm, ListingForm


def index(request):
    return render(request, "auctions/index.html", {
        "listings": AuctionListing.objects.all().order_by('-created_at') 
    })
    


def categories(request):
    return render(request, "auctions/categories.html", {
        "categories": Category.objects.all(),  # Pass all categories to the template
    })   
def categories_view(request):
    selected_category_id = request.GET.get('category')
    if selected_category_id:
        selected_category = Category.objects.get(id=selected_category_id)
        listings =  AuctionListing.objects.filter(category=selected_category)
    else:
        selected_category = None
        listings = AuctionListing.objects.all()

    categories = Category.objects.all()
    context = {
        'categories': categories,
        'listings': listings,
        'selected_category': selected_category,
    }
    return render(request, 'auctions/categories.html', context)

def filter(request):
    category_id = request.GET.get('category')
    if category_id:
        listings = AuctionListing.objects.filter(category_id=category_id)
    else:
        listings = AuctionListing.objects.all()

    return render(request, 'auctions/category.html', {
        'listings': listings,
        'categories': Category.objects.all(),  # Pass categories to the template
    })

def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")


# ======================================================================================================================
@login_required(login_url='auctions/login.html')
def create(request):
    if request.method == 'POST':
        form = AuctionListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.user = request.user
            listing.save()
            return render('index')
    else:
        form = AuctionListingForm()
    return render(request, 'auctions/create.html', {'form': form})

@login_required(login_url='auctions/login.html')
def insert(request):
    form = AuctionListingForm(request.POST)
    if form.is_valid():
        auction = AuctionListing(user=request.user, **form.cleaned_data)
        if not auction.image_url:
            auction.image_url = 'https://m.media-amazon.com/images/I/31j-sT4LyML._QL70_FMwebp_.jpg'
        auction.save()
        starting_bid = auction.starting_bid
        bid = Bid(amount=starting_bid, user=request.user, auction=auction)
        bid.save()
        print("auction:" + auction.image_url)
        return HttpResponseRedirect(reverse('index'))
    else:
        return render(request, 'auctions/create.html', {
            'form': form,
            'error': form.errors
        })

    
def listing(request, id):
    current = get_object_or_404(AuctionListing, pk=id)
    highest_bid = current.bid_set.order_by('-amount').first()
    comments = Comment.objects.filter(auction=current)
    return render(request, 'auctions/listing.html', {
        'auction': current,
        'bid': highest_bid,
        'user': request.user,
        'comments': comments,
        'comment_form': CommentForm()
    })
    


def create_listing(request):
    if request.method == 'POST':
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.user = request.user  # Set the user who created the listing
            listing.save()
            return render('index')  # Redirect to the homepage or listing detail page
    else:
        form = ListingForm()
    return render(request, 'auctions/create_listing.html', {'form': form})    



@login_required(login_url='auctions/login.html')
def update_bid(request, id):
    listing = get_object_or_404(AuctionListing, id=id)  # Get the listing or return 404
    if request.method == 'POST':
        new_bid_amount = request.POST.get('bid')  # Get the new bid amount from the form
        if new_bid_amount:
            new_bid_amount = float(new_bid_amount)
            current_highest_bid = listing.bid_set.order_by('-amount').first()
            
            # Check if the new bid is valid
            if current_highest_bid and new_bid_amount <= current_highest_bid.amount:
                return render(request, 'auctions/listing.html', {
                    'auction': listing,
                    'error': 'Bid must be greater than the current highest bid.'
                })
            elif new_bid_amount < listing.starting_bid:
                return render(request, 'auctions/listing.html', {
                    'auction': listing,
                    'error': 'Bid must be at least as large as the starting bid.'
                })
            
            # Create a new bid
            bid = Bid(user=request.user, amount=new_bid_amount, auction=listing)
            bid.save()
            
            # Update the listing's bid counter
            listing.bid_counter += 1
            listing.save()
            
            return HttpResponseRedirect(reverse('listing', args=[listing.id]))
    
    return HttpResponseRedirect(reverse('listing', args=[listing.id]))



@login_required(login_url='auctions/login.html')
def close_bid(request, id):
    auction = get_object_or_404(AuctionListing, id=id)  # Get the listing or return 404

    # Ensure the user closing the bid is the one who created the listing
    if request.user != auction.user:
        return render(request, 'auctions/listing.html', {
            'auction': auction,
            'error': 'Only the creator of the listing can close the bid.'
        })

    # Get the highest bid
    highest_bid = auction.bid_set.order_by('-amount').first()

    if highest_bid:
        # Set the winner and mark the auction as inactive
        auction.winner = highest_bid.user.username
        auction.active = False
        auction.save()
    else:
        # If there are no bids, just close the auction
        auction.active = False
        auction.save()

    return HttpResponseRedirect(reverse('listing', args=[auction.id]))


@login_required(login_url='auctions/login.html')
def watchlist(request):
    return render(request, "auctions/watchlist.html", {
        "watchlist": request.user.watchlist.all()
    })


@login_required(login_url='auctions/login.html')
def watch(request, id):
    auction = get_object_or_404(AuctionListing, id=id)
    request.user.watchlist.add(auction)
    request.user.watchlist_counter += 1
    request.user.save()
    return HttpResponseRedirect(reverse('index'))


@login_required(login_url='auctions/login.html')
def unwatch(request, id):
    auction = get_object_or_404(AuctionListing, id=id)
    request.user.watchlist.remove(auction)
    request.user.watchlist_counter -= 1
    request.user.save()
    if '/unwatch/' in request.path:
        return HttpResponseRedirect(reverse('index'))
    return HttpResponseRedirect(reverse('wishlist'))


def categories(request):
    return render(request, "auctions/categories.html")


def filter(request):
    category_id = request.GET.get('category')
    if category_id:
        listings = AuctionListing.objects.filter(category_id=category_id)
    else:
        listings = AuctionListing.objects.all()

    return render(request, 'auctions/category.html', {
        'listings': listings,
        'categories': Category.objects.all(),  # Pass categories to the template
    })


def add_comment(request, id):
    anonymous = User.first_name
    if request.user is not anonymous:
        form = CommentForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data
            comment = Comment(
                user=request.user,
                auction=get_object_or_404(AuctionListing, id=id),
                **f
            )
            comment.save()
            return HttpResponseRedirect(reverse('listing', kwargs={
                'id': id
            }))
    else:
        return render(request, 'auctions/login.html', {
            'message': 'Must be logged in to be able to comment!'
        })

def watchlist(request):
    # Get the user's watchlist items
    watchlist = request.user.watchlist.all()
    context = {
        'watchlist': watchlist,
    }
    return render(request, 'auctions/watchlist.html', context)