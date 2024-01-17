from uuid import uuid4
from django.shortcuts import render
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.views import APIView
from .models import Feed, Reply, Like, Bookmark
from user.models import User
import os
from rest_framework import status
from Parkstagram.settings import MEDIA_ROOT


class Main(APIView):
    def get(self, request):
        email = request.session.get('email', None)

        if email is None:
            return render(request, "user/login.html")

        user = User.objects.filter(email=email).first()

        if user is None:
            print(f"User not found for email: {email}")
            return render(request, "user/login.html")

        feed_object_list = Feed.objects.all().order_by('-id')  # select * from content_feed;
        feed_list = []

        for feed in feed_object_list:
            feed_user = User.objects.filter(email=feed.email).first()
            if feed_user is None:
                print(f"User not found for feed email: {feed.email}")
                continue

            reply_object_list = Reply.objects.filter(feed_id=feed.id)
            reply_list = []
            for reply in reply_object_list:
                reply_user = User.objects.filter(email=reply.email).first()
                if reply_user is not None:
                    reply_list.append(dict(reply_content=reply.reply_content, nickname=reply_user.nickname))

            like_count = Like.objects.filter(feed_id=feed.id, is_like=True).count()
            is_liked = Like.objects.filter(feed_id=feed.id, email=email, is_like=True).exists()
            is_marked = Bookmark.objects.filter(feed_id=feed.id, email=email, is_marked=True).exists()

            feed_list.append(dict(
                id=feed.id,
                image=feed.image,
                content=feed.content,
                like_count=like_count,
                profile_image=feed_user.profile_image,
                nickname=feed_user.nickname,
                reply_list=reply_list,
                is_liked=is_liked,
                is_marked=is_marked
            ))

        return render(request, "jinstagram/main.html", context=dict(feeds=feed_list, user=user))





class UploadFeed(APIView):
    def post(self, request):

        # 일단 파일 불러와
        file = request.FILES['file']

        uuid_name = uuid4().hex
        save_path = os.path.join(MEDIA_ROOT, uuid_name)

        with open(save_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        asdf = uuid_name
        content123 = request.data.get('content')
        email = request.session.get('email', None)

        Feed.objects.create(image=asdf, content=content123, email=email)

        return Response(status=200)


class ModifyFeed(APIView):
    def post(self, request):
        # Extract the feed ID from the request data
        feed_id = request.data.get('feedId')
        if not feed_id:
            return Response({'error': 'Feed ID is required.'}, status=400)

        # Get the existing feed object or raise 404 if not found
        feed = get_object_or_404(Feed, id=feed_id)

        # Check if the user making the request is the owner of the feed
        email = request.session.get('email', None)
        if feed.email != email:
            raise Http404

        # If a new file is provided, update the image
        new_file = request.FILES.get('file')
        if new_file:
            # Save the new file
            uuid_name = uuid4().hex
            save_path = os.path.join(MEDIA_ROOT, uuid_name)
            with open(save_path, 'wb+') as destination:
                for chunk in new_file.chunks():
                    destination.write(chunk)


        # Update other fields if needed
        feed.content = request.data.get('content', feed.content)

        # Save the changes
        feed.save()

        return Response(status=200)

class DeleteFeed(APIView):
    def post(self, request):
        # Extract the feed ID from the request data
        feed_id = request.data.get('feedId')
        if not feed_id:
            return Response({'error': 'Feed ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the existing feed object or raise 404 if not found
        feed = get_object_or_404(Feed, id=feed_id)

        # Check if the user making the request is the owner of the feed
        email = request.session.get('email', None)
        if feed.email != email:
            return Response({'error': 'You are not authorized to delete this feed.'}, status=status.HTTP_403_FORBIDDEN)

        # Delete the feed object
        feed.delete()

        return Response({'success': 'Feed deleted successfully.'}, status=status.HTTP_200_OK)

class Profile(APIView):
    def get(self, request):
        email = request.session.get('email', None)

        if email is None:
            return render(request, "user/login.html")

        user = User.objects.filter(email=email).first()

        if user is None:
            return render(request, "user/login.html")

        feed_list = Feed.objects.filter(email=email)
        like_list = list(Like.objects.filter(email=email, is_like=True).values_list('feed_id', flat=True))
        like_feed_list = Feed.objects.filter(id__in=like_list)
        bookmark_list = list(Bookmark.objects.filter(email=email, is_marked=True).values_list('feed_id', flat=True))
        bookmark_feed_list = Feed.objects.filter(id__in=bookmark_list)

        # Fetch replies for each feed in the user's profile
        feed_list_with_replies = self.get_feed_list_with_replies(feed_list, email, user)

        # Fetch replies for each feed in the liked feed list
        like_feed_list_with_replies = self.get_feed_list_with_replies(like_feed_list, email, user)

        # Fetch replies for each feed in the bookmarked feed list
        bookmark_feed_list_with_replies = self.get_feed_list_with_replies(bookmark_feed_list, email, user)

        return render(request, 'content/profile.html', context=dict(
            feed_list=feed_list_with_replies,
            like_feed_list=like_feed_list_with_replies,
            bookmark_feed_list=bookmark_feed_list_with_replies,
            user=user
        ))

    def get_feed_list_with_replies(self, feed_list, email, user):
        feed_list_with_replies = []

        for feed in feed_list:
            reply_object_list = Reply.objects.filter(feed_id=feed.id)
            reply_list = []
            for reply in reply_object_list:
                reply_user = User.objects.filter(email=reply.email).first()
                if reply_user is not None:
                    reply_list.append(dict(reply_content=reply.reply_content, nickname=reply_user.nickname))

            like_count = Like.objects.filter(feed_id=feed.id, is_like=True).count()
            is_liked = Like.objects.filter(feed_id=feed.id, email=email, is_like=True).exists()
            is_marked = Bookmark.objects.filter(feed_id=feed.id, email=email, is_marked=True).exists()

            # Fetch likes and bookmarks for each feed
            like_list_for_feed = list(
                Like.objects.filter(feed_id=feed.id, is_like=True).values_list('email', flat=True))
            bookmark_list_for_feed = list(
                Bookmark.objects.filter(feed_id=feed.id, is_marked=True).values_list('email', flat=True))

            # Check if the current user liked or bookmarked this feed
            is_user_liked = email in like_list_for_feed
            is_user_bookmarked = email in bookmark_list_for_feed

            feed_list_with_replies.append(dict(
                id=feed.id,
                image=feed.image,
                content=feed.content,
                like_count=like_count,
                profile_image=user.profile_image,
                nickname=user.nickname,
                reply_list=reply_list,
                is_liked=is_liked,
                is_marked=is_marked,
                is_user_liked=is_user_liked,
                is_user_bookmarked=is_user_bookmarked
            ))

        return feed_list_with_replies




class UploadReply(APIView):
    def post(self, request):
        feed_id = request.data.get('feed_id', None)
        reply_content = request.data.get('reply_content', None)
        email = request.session.get('email', None)

        Reply.objects.create(feed_id=feed_id, reply_content=reply_content, email=email)

        return Response(status=200)


class ToggleLike(APIView):
    def post(self, request):
        feed_id = request.data.get('feed_id', None)
        favorite_text = request.data.get('favorite_text', True)

        if favorite_text == 'favorite_border':
            is_like = True
        else:
            is_like = False
        email = request.session.get('email', None)

        like = Like.objects.filter(feed_id=feed_id, email=email).first()

        if like:
            like.is_like = is_like
            like.save()
        else:
            Like.objects.create(feed_id=feed_id, is_like=is_like, email=email)

        return Response(status=200)


class ToggleBookmark(APIView):
    def post(self, request):
        feed_id = request.data.get('feed_id', None)
        bookmark_text = request.data.get('bookmark_text', True)
        print(bookmark_text)
        if bookmark_text == 'bookmark_border':
            is_marked = True
        else:
            is_marked = False
        email = request.session.get('email', None)

        bookmark = Bookmark.objects.filter(feed_id=feed_id, email=email).first()

        if bookmark:
            bookmark.is_marked = is_marked
            bookmark.save()
        else:
            Bookmark.objects.create(feed_id=feed_id, is_marked=is_marked, email=email)

        return Response(status=200)


class UserProfile(APIView):
    def get(self, request):
        # 닉네임 쿼리 파라미터 가져오기
        other_nickname = request.GET.get('nickname', '')

        email = request.session.get('email', None)

        if email is None:
            return render(request, "user/login.html")

        user = User.objects.filter(email=email).first()

        if user is None:
            return render(request, "user/login.html")

        feed_user = User.objects.filter(nickname=other_nickname).first()
        other_email = feed_user.email
        feed_list_with_replies = self.get_feed_list_with_replies(feed_user, other_email, email)

        return render(request, 'content/userprofile.html', context=dict(feed_list=feed_list_with_replies, user=user, feed_user=feed_user))

    def get_feed_list_with_replies(self, user, other_email, email):
        feed_list_with_replies = []

        feed_list = Feed.objects.filter(email=other_email)

        for feed in feed_list:
            reply_object_list = Reply.objects.filter(feed_id=feed.id)
            reply_list = []
            for reply in reply_object_list:
                reply_user = User.objects.filter(email=reply.email).first()
                if reply_user is not None:
                    reply_list.append(dict(reply_content=reply.reply_content, nickname=reply_user.nickname))

            like_count = Like.objects.filter(feed_id=feed.id, is_like=True).count()
            is_liked = Like.objects.filter(feed_id=feed.id, email=email, is_like=True).exists()

            feed_list_with_replies.append(dict(
                id=feed.id,
                image=feed.image,
                content=feed.content,
                like_count=like_count,
                profile_image=user.profile_image,
                nickname=user.nickname,
                reply_list=reply_list,
                is_liked=is_liked,
            ))

        return feed_list_with_replies


