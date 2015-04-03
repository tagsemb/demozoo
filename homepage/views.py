import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages

from forums.models import Topic
from productions.models import Production
from comments.models import Comment
from parties.models import Party

from homepage.models import Banner, NewsStory
from homepage.forms import NewsStoryForm

def home(request):
	if request.user.is_authenticated():
		banner = Banner.objects.filter(show_for_logged_in_users=True).order_by('-created_at').first()
	else:
		banner = Banner.objects.filter(show_for_anonymous_users=True).order_by('-created_at').first()

	latest_releases = Production.objects.filter(
		default_screenshot__isnull=False, release_date_date__isnull=False
	).select_related(
		'default_screenshot'
	).prefetch_related(
		'author_nicks', 'author_affiliation_nicks', 'platforms', 'types'
	).order_by('-release_date_date', '-created_at')[:5]

	one_year_ago = datetime.datetime.now() - datetime.timedelta(365)
	latest_additions = Production.objects.exclude(
		release_date_date__gte=one_year_ago
	).prefetch_related(
		'author_nicks', 'author_affiliation_nicks', 'platforms', 'types'
	).order_by('-created_at')[:5]

	comments = Comment.objects.filter(
		content_type=ContentType.objects.get_for_model(Production)
	).select_related(
		'user'
	).prefetch_related(
		'commentable'
	).order_by('-created_at')[:5]

	upcoming_parties = Party.objects.filter(
		start_date_date__gt=datetime.datetime.now()
	).order_by('start_date_date')[:8]

	return render(request, 'homepage/home.html', {
		'banner': banner,
		'news_stories': NewsStory.objects.order_by('-created_at')[:6],
		'forum_topics': Topic.objects.order_by('-last_post_at').select_related('created_by_user', 'last_post_by_user')[:5],
		'latest_releases': latest_releases,
		'latest_additions': latest_additions,
		'comments': comments,
		'upcoming_parties': upcoming_parties,
	})


def edit_news(request, news_story_id):
	if not request.user.has_perm('homepage.change_newsstory'):
		return redirect('home')

	news_story = get_object_or_404(NewsStory, id=news_story_id)
	if request.method == 'POST':
		form = NewsStoryForm(request.POST, instance=news_story)
		if form.is_valid():
			form.save()
			messages.success(request, "News story updated")
			return redirect('home')
	else:
		form = NewsStoryForm(instance=news_story)

	return render(request, 'homepage/edit_news.html', {
		'news_story': news_story,
		'form': form,
	})
