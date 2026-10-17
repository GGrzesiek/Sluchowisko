from django.urls import path

from . import views

urlpatterns = [
    path("stories/", views.story_list, name="story-list"),
    path("stories/<str:group_id>/", views.story_detail, name="story-detail"),
    path("lines/<str:number>/stories/", views.line_stories, name="line-stories"),
]
