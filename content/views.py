from uuid import uuid4
from django.shortcuts import render, redirect
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse
from rest_framework.views import APIView
from .models import Feed, Reply, Like, Bookmark
from user.models import User
import os
from rest_framework import status
from Parkstagram.settings import MEDIA_ROOT
from django.db.models import Q
from django.contrib.auth.hashers import make_password


class Main(APIView):
    def get(self, request):
        # 세션을 통해 사용자가 로그인되었는지 확인합니다.
        email = request.session.get('email', None)

        # 사용자가 로그인되지 않았다면 로그인 페이지로 리다이렉트합니다.
        if email is None:
            return render(request, "user/login.html")

        # 로그인된 사용자에 대한 User 객체를 가져옵니다.
        user = User.objects.filter(email=email).first()

        # 사용자를 찾을 수 없다면 로그인 페이지로 리다이렉트합니다.
        if user is None:
            print(f"이메일에 대한 사용자를 찾을 수 없습니다: {email}")
            return render(request, "user/login.html")

        # id를 기준으로 내림차순으로 정렬된 모든 Feed 객체를 검색합니다.
        feed_object_list = Feed.objects.all().order_by('-id')
        feed_list = []

        # 각 피드를 순회하면서 관련 정보를 수집합니다.
        for feed in feed_object_list:
            feed_user = User.objects.filter(email=feed.email).first()

            # 피드와 관련된 사용자를 찾을 수 없으면 다음 피드로 건너뜁니다.
            if feed_user is None:
                print(f"피드 이메일에 대한 사용자를 찾을 수 없습니다: {feed.email}")
                continue

            # 현재 피드와 관련된 모든 Reply 객체를 검색합니다.
            reply_object_list = Reply.objects.filter(feed_id=feed.id)
            reply_list = []

            # 각 Reply를 순회하면서 관련 정보를 수집합니다.
            for reply in reply_object_list:
                reply_user = User.objects.filter(email=reply.email).first()
                if reply_user is not None:
                    reply_list.append(dict(reply_content=reply.reply_content, nickname=reply_user.nickname))

            # 현재 피드에 대한 좋아요 수를 세어옵니다.
            like_count = Like.objects.filter(feed_id=feed.id, is_like=True).count()

            # 로그인된 사용자가 현재 피드를 좋아요 또는 북마크 했는지 확인합니다.
            is_liked = Like.objects.filter(feed_id=feed.id, email=email, is_like=True).exists()
            is_marked = Bookmark.objects.filter(feed_id=feed.id, email=email, is_marked=True).exists()

            # feed_list에 피드에 대한 정보를 추가합니다.
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

        # 수집한 피드 정보를 사용하여 main.html 템플릿을 렌더링합니다.
        return render(request, "jinstagram/main.html", context=dict(feeds=feed_list, user=user))






class UploadFeed(APIView):
    def post(self, request):
        # 파일 업로드를 처리하는 APIView입니다.

        # 전송된 파일을 가져옵니다.
        file = request.FILES['file']

        # 고유한 파일 이름을 생성합니다.
        uuid_name = uuid4().hex
        # 저장 경로를 설정합니다.
        save_path = os.path.join(MEDIA_ROOT, uuid_name)

        # 파일을 디스크에 저장합니다.
        with open(save_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # 저장된 파일 이름을 변수에 할당합니다.
        uploaded_file_name = uuid_name
        # 피드 내용을 가져옵니다.
        content = request.data.get('content')
        # 현재 로그인된 사용자의 이메일을 가져옵니다.
        email = request.session.get('email', None)

        # Feed 모델에 새로운 피드를 생성합니다.
        Feed.objects.create(image=uploaded_file_name, content=content, email=email)

        # 클라이언트에게 성공 상태를 응답합니다.
        return Response(status=200)



class ModifyFeed(APIView):
    def post(self, request):
        # 피드 수정을 처리하는 APIView입니다.

        # 요청 데이터에서 피드 ID를 추출합니다.
        feed_id = request.data.get('feedId')
        # 피드 ID가 없으면 오류 응답을 반환합니다.
        if not feed_id:
            return Response({'error': '피드 ID가 필요합니다.'}, status=400)

        # 기존 피드 객체를 가져오거나 찾을 수 없으면 404를 반환합니다.
        feed = get_object_or_404(Feed, id=feed_id)

        # 요청을 만든 사용자가 피드의 소유자인지 확인합니다.
        email = request.session.get('email', None)
        if feed.email != email:
            raise Http404

        # 새 파일이 제공되면 이미지를 업데이트합니다.
        new_file = request.FILES.get('file')
        if new_file:
            # 새 파일을 저장합니다.
            uuid_name = uuid4().hex
            save_path = os.path.join(MEDIA_ROOT, uuid_name)
            with open(save_path, 'wb+') as destination:
                for chunk in new_file.chunks():
                    destination.write(chunk)

        # 필요한 경우 다른 필드를 업데이트합니다.
        feed.content = request.data.get('content', feed.content)

        # 변경 사항을 저장합니다.
        feed.save()

        # 성공 상태를 응답합니다.
        return Response(status=200)


class DeleteFeed(APIView):
    def post(self, request):
        # 요청 데이터에서 피드 ID를 추출합니다.
        feed_id = request.data.get('feedId')
        # 피드 ID가 없으면 오류 응답을 반환합니다.
        if not feed_id:
            return Response({'error': '피드 ID가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 기존 피드 객체를 가져오거나 찾을 수 없으면 404를 반환합니다.
        feed = get_object_or_404(Feed, id=feed_id)

        # 요청을 만든 사용자가 피드의 소유자인지 확인합니다.
        email = request.session.get('email', None)
        if feed.email != email:
            return Response({'error': '이 피드를 삭제할 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        # 피드 객체를 삭제합니다.
        feed.delete()

        # 성공 상태와 메시지를 응답합니다.
        return Response({'success': '피드가 성공적으로 삭제되었습니다.'}, status=status.HTTP_200_OK)


class Profile(APIView):
    def get(self, request):
        # 프로필 페이지를 렌더링하는 APIView입니다.

        # 세션에서 사용자 이메일을 가져옵니다.
        email = request.session.get('email', None)

        # 이메일이 없으면 로그인 페이지로 리다이렉트합니다.
        if email is None:
            return render(request, "user/login.html")

        # 사용자 이메일을 기준으로 User 객체를 가져옵니다.
        user = User.objects.filter(email=email).first()

        # 사용자를 찾을 수 없으면 로그인 페이지로 리다이렉트합니다.
        if user is None:
            return render(request, "user/login.html")

        # 사용자 이메일을 기준으로 해당 사용자의 모든 피드를 가져옵니다.
        feed_list = Feed.objects.filter(email=email)

        # 사용자가 좋아요한 피드 목록을 가져옵니다.
        like_list = list(Like.objects.filter(email=email, is_like=True).values_list('feed_id', flat=True))
        like_feed_list = Feed.objects.filter(id__in=like_list)

        # 사용자가 즐겨찾기한 피드 목록을 가져옵니다.
        bookmark_list = list(Bookmark.objects.filter(email=email, is_marked=True).values_list('feed_id', flat=True))
        bookmark_feed_list = Feed.objects.filter(id__in=bookmark_list)

        # 사용자 프로필 페이지에 표시할 피드 목록에 대한 댓글을 가져옵니다.
        feed_list_with_replies = self.get_feed_list_with_replies(feed_list, email, user)

        # 사용자가 좋아요한 피드에 대한 댓글을 가져옵니다.
        like_feed_list_with_replies = self.get_feed_list_with_replies(like_feed_list, email, user)

        # 사용자가 즐겨찾기한 피드에 대한 댓글을 가져옵니다.
        bookmark_feed_list_with_replies = self.get_feed_list_with_replies(bookmark_feed_list, email, user)

        # 프로필 페이지에 필요한 정보를 context에 담아 profile.html을 렌더링합니다.
        return render(request, 'content/profile.html', context=dict(
            feed_list=feed_list_with_replies,
            like_feed_list=like_feed_list_with_replies,
            bookmark_feed_list=bookmark_feed_list_with_replies,
            user=user
        ))

    def get_feed_list_with_replies(self, feed_list, email, user):
        # 각 피드에 대한 댓글을 가져와서 피드 정보와 함께 반환합니다.
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

            # 각 피드에 대한 좋아요 및 즐겨찾기 정보를 가져옵니다.
            like_list_for_feed = list(
                Like.objects.filter(feed_id=feed.id, is_like=True).values_list('email', flat=True))
            bookmark_list_for_feed = list(
                Bookmark.objects.filter(feed_id=feed.id, is_marked=True).values_list('email', flat=True))

            # 현재 사용자가 해당 피드를 좋아요 또는 즐겨찾기한지 확인합니다.
            is_user_liked = email in like_list_for_feed
            is_user_bookmarked = email in bookmark_list_for_feed

            # 피드 정보와 함께 feed_list_with_replies에 추가합니다.
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
        # 댓글 업로드를 처리하는 APIView입니다.

        # 요청 데이터에서 피드 ID, 댓글 내용, 사용자 이메일을 가져옵니다.
        feed_id = request.data.get('feed_id', None)
        reply_content = request.data.get('reply_content', None)
        email = request.session.get('email', None)

        # Reply 모델에 새로운 댓글을 생성합니다.
        Reply.objects.create(feed_id=feed_id, reply_content=reply_content, email=email)

        # 클라이언트에게 성공 상태를 응답합니다.
        return Response(status=200)


class ToggleLike(APIView):
    def post(self, request):
        # 좋아요 토글을 처리하는 APIView입니다.

        # 요청 데이터에서 피드 ID, 좋아요 버튼 상태, 사용자 이메일을 가져옵니다.
        feed_id = request.data.get('feed_id', None)
        favorite_text = request.data.get('favorite_text', True)

        # 좋아요 버튼 상태에 따라 is_like 변수를 설정합니다.
        if favorite_text == 'favorite_border':
            is_like = True
        else:
            is_like = False

        # 현재 로그인된 사용자의 이메일을 가져옵니다.
        email = request.session.get('email', None)

        # 해당 피드와 사용자에 대한 좋아요 객체를 가져옵니다.
        like = Like.objects.filter(feed_id=feed_id, email=email).first()

        # 좋아요 객체가 존재하면 상태를 업데이트하고, 없으면 새로 생성합니다.
        if like:
            like.is_like = is_like
            like.save()
        else:
            Like.objects.create(feed_id=feed_id, is_like=is_like, email=email)

        # 클라이언트에게 성공 상태를 응답합니다.
        return Response(status=200)


class ToggleBookmark(APIView):
    def post(self, request):
        # 즐겨찾기 토글을 처리하는 APIView입니다.

        # 요청 데이터에서 피드 ID, 즐겨찾기 버튼 상태, 사용자 이메일을 가져옵니다.
        feed_id = request.data.get('feed_id', None)
        bookmark_text = request.data.get('bookmark_text', True)

        # 즐겨찾기 버튼 상태에 따라 is_marked 변수를 설정합니다.
        if bookmark_text == 'bookmark_border':
            is_marked = True
        else:
            is_marked = False

        # 현재 로그인된 사용자의 이메일을 가져옵니다.
        email = request.session.get('email', None)

        # 해당 피드와 사용자에 대한 즐겨찾기 객체를 가져옵니다.
        bookmark = Bookmark.objects.filter(feed_id=feed_id, email=email).first()

        # 즐겨찾기 객체가 존재하면 상태를 업데이트하고, 없으면 새로 생성합니다.
        if bookmark:
            bookmark.is_marked = is_marked
            bookmark.save()
        else:
            Bookmark.objects.create(feed_id=feed_id, is_marked=is_marked, email=email)

        # 클라이언트에게 성공 상태를 응답합니다.
        return Response(status=200)



class UserProfile(APIView):
    def get(self, request):
        # 사용자 프로필을 보여주는 APIView입니다.

        # 닉네임 쿼리 파라미터를 가져옵니다.
        other_nickname = request.GET.get('nickname', '')

        # 'q' 파라미터가 있으면 other_nickname을 업데이트합니다.
        if 'q' in request.GET:
            other_nickname = request.GET['q']

        # 세션에서 현재 사용자 이메일을 가져옵니다.
        email = request.session.get('email', None)

        # 이메일이 없으면 로그인 페이지로 리다이렉트합니다.
        if email is None:
            return render(request, "user/login.html")

        # 사용자 이메일을 기준으로 User 객체를 가져옵니다.
        user = User.objects.filter(email=email).first()

        # 사용자를 찾을 수 없으면 로그인 페이지로 리다이렉트합니다.
        if user is None:
            return render(request, "user/login.html")

        # other_nickname에 해당하는 User 객체를 가져옵니다.
        feed_user = User.objects.filter(nickname=other_nickname).first()

        # feed_user가 없으면 현재 페이지를 새로고침하고 페이지 이동이 없음을 나타내는 204 No Content를 반환합니다.
        if feed_user is None:
            return HttpResponse(status=204)

        # feed_user의 이메일을 가져옵니다.
        other_email = feed_user.email

        # 사용자와 feed_user 간의 피드에 대한 댓글을 가져와 feed_list_with_replies에 저장합니다.
        feed_list_with_replies = self.get_feed_list_with_replies(feed_user, other_email, email)

        # context에 필요한 정보를 담아 userprofile.html을 렌더링합니다.
        return render(request, 'content/userprofile.html', context=dict(feed_list=feed_list_with_replies, user=user, feed_user=feed_user))

    def get_feed_list_with_replies(self, user, other_email, email):
        # 사용자와 feed_user 간의 피드에 대한 댓글을 가져와 반환하는 메서드입니다.
        feed_list_with_replies = []

        # other_email을 소유한 피드 목록을 가져옵니다.
        feed_list = Feed.objects.filter(email=other_email)

        for feed in feed_list:
            # 각 피드에 대한 댓글 목록을 가져옵니다.
            reply_object_list = Reply.objects.filter(feed_id=feed.id)
            reply_list = []
            for reply in reply_object_list:
                # 댓글을 작성한 사용자 정보를 가져옵니다.
                reply_user = User.objects.filter(email=reply.email).first()
                if reply_user is not None:
                    reply_list.append(dict(reply_content=reply.reply_content, nickname=reply_user.nickname))

            # 피드에 대한 좋아요 수를 가져옵니다.
            like_count = Like.objects.filter(feed_id=feed.id, is_like=True).count()

            # 현재 사용자가 해당 피드를 좋아요한 여부를 확인합니다.
            is_liked = Like.objects.filter(feed_id=feed.id, email=email, is_like=True).exists()

            # feed_list_with_replies에 피드 정보를 추가합니다.
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


class Updateprofile(APIView):
    def get(self, request):
        # 사용자의 프로필을 수정하는 페이지를 렌더링하는 APIView입니다.

        # 세션에서 현재 사용자 이메일을 가져옵니다.
        email = request.session.get('email', None)

        # 이메일이 없으면 로그인 페이지로 리다이렉트합니다.
        if email is None:
            return render(request, "user/login.html")

        # 사용자 이메일을 기반으로 User 객체를 가져옵니다.
        user = User.objects.filter(email=email).first()

        # 사용자를 찾을 수 없으면 로그인 페이지로 리다이렉트합니다.
        if user is None:
            print(f"User not found for email: {email}")
            return render(request, "user/login.html")

        # context에 사용자 정보를 담아 updateprofile.html을 렌더링합니다.
        return render(request, "content/updateprofile.html", context=dict(user=user))


class UserProfileUpdateView(APIView):
    template_name = 'content/updateprofile.html'  # 실제 템플릿 경로로 변경하세요

    def get(self, request):
        # 사용자의 프로필을 업데이트하는 페이지를 렌더링하는 APIView입니다.

        # 세션에서 현재 사용자 이메일을 가져옵니다.
        email = request.session.get('email', None)

        # 이메일이 없으면 로그인 페이지로 리다이렉트합니다.
        if email is None:
            return redirect('login')  # 로그인 페이지로 리다이렉트하거나 URL을 변경하세요

        # 사용자 이메일을 기반으로 User 객체를 가져옵니다.
        user = User.objects.filter(email=email).first()

        # 사용자를 찾을 수 없으면 로그인 페이지로 리다이렉트합니다.
        if user is None:
            return redirect('login')  # 로그인 페이지로 리다이렉트하거나 URL을 변경하세요

        # context에 사용자 정보를 담아 updateprofile.html을 렌더링합니다.
        return render(request, self.template_name, {'user': user})

    def post(self, request):
        # 사용자의 프로필을 업데이트하는 POST 메서드를 처리하는 APIView입니다.

        # 세션에서 현재 사용자 이메일을 가져옵니다.
        email = request.session.get('email', None)

        # 이메일이 없으면 로그인 페이지로 리다이렉트합니다.
        if email is None:
            return redirect('login')  # 로그인 페이지로 리다이렉트하거나 URL을 변경하세요

        # 사용자 이메일을 기반으로 User 객체를 가져옵니다.
        user = User.objects.filter(email=email).first()

        # 사용자를 찾을 수 없으면 로그인 페이지로 리다이렉트합니다.
        if user is None:
            return redirect('login')  # 로그인 페이지로 리다이렉트하거나 URL을 변경하세요

        # 폼 데이터를 기반으로 사용자 필드를 업데이트합니다.
        user.name = request.POST.get('name', user.name)
        user.nickname = request.POST.get('nickname', user.nickname)

        # 프로필 이미지 업데이트를 처리합니다.
        new_profile_image = request.FILES.get('input_fileupload')
        if new_profile_image:
            # 새로운 프로필 이미지를 저장합니다.
            uuid_name = uuid4().hex
            save_path = os.path.join(MEDIA_ROOT, uuid_name)
            with open(save_path, 'wb+') as destination:
                for chunk in new_profile_image.chunks():
                    destination.write(chunk)
            user.profile_image = uuid_name

        # 제공된 경우 비밀번호를 업데이트합니다.
        new_password = request.POST.get('password')
        if new_password:
            user.password = make_password(new_password)

        # 변경 사항을 저장합니다.
        user.save()

        # 프로필 페이지로 리다이렉트하거나 업데이트 성공 페이지로 변경하세요.
        return redirect('content/updateprofile.html')  # 프로필 페이지로 리다이렉트하거나 URL을 변경하세요

