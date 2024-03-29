from django.urls import path
from .views import UploadFeed, Profile, Main, UploadReply, ToggleLike, ToggleBookmark, UserProfile, ModifyFeed,DeleteFeed,Updateprofile,UserProfileUpdateView

urlpatterns = [
    path('upload', UploadFeed.as_view()),
    path('modify', ModifyFeed.as_view()),
    path('delete', DeleteFeed.as_view()),
    path('reply', UploadReply.as_view()),
    path('like', ToggleLike.as_view()),
    path('bookmark', ToggleBookmark.as_view()),
    path('profile', Profile.as_view()),
    path('userprofile', UserProfile.as_view()),
    path('main', Main.as_view()),
    path('updateprofile',Updateprofile.as_view()),
    path('userupdate/', UserProfileUpdateView.as_view())
]