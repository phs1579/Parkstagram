import os
from uuid import uuid4

from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User
from django.contrib.auth.hashers import make_password
from Parkstagram.settings import MEDIA_ROOT


class Join(APIView):
    def get(self, request):
        # 회원가입 페이지를 렌더링합니다.
        return render(request, "user/join.html")

    def post(self, request):
        # 회원가입 처리를 담당하는 APIView입니다.
        email = request.data.get('email', None)
        nickname = request.data.get('nickname', None)
        name = request.data.get('name', None)
        password = request.data.get('password', None)

        # 회원 정보를 생성합니다.
        User.objects.create(email=email,
                            nickname=nickname,
                            name=name,
                            password=make_password(password),
                            profile_image="default_profile.jpg")

        return Response(status=200)


class Login(APIView):
    def get(self, request):
        # 로그인 페이지를 렌더링합니다.
        return render(request, "user/login.html")

    def post(self, request):
        # 로그인 처리를 담당하는 APIView입니다.
        email = request.data.get('email', None)
        password = request.data.get('password', None)

        # 입력된 이메일로 사용자를 찾습니다.
        user = User.objects.filter(email=email).first()

        if user is None:
            # 사용자가 없을 경우 에러 응답을 반환합니다.
            return Response(status=400, data=dict(message="회원정보가 잘못되었습니다."))

        if user.check_password(password):
            # 비밀번호가 일치하는 경우 세션에 이메일을 저장하여 로그인 처리합니다.
            request.session['email'] = email
            return Response(status=200)
        else:
            # 비밀번호가 일치하지 않는 경우 에러 응답을 반환합니다.
            return Response(status=400, data=dict(message="회원정보가 잘못되었습니다."))


class LogOut(APIView):
    def get(self, request):
        # 로그아웃 처리를 담당하는 APIView입니다.
        request.session.flush()
        # 로그아웃 후 로그인 페이지를 렌더링합니다.
        return render(request, "user/login.html")


class UploadProfile(APIView):
    def post(self, request):
        # 사용자 프로필 이미지 업로드를 처리하는 APIView입니다.

        # 파일을 불러와 저장합니다.
        file = request.FILES['file']
        email = request.data.get('email')

        uuid_name = uuid4().hex
        save_path = os.path.join(MEDIA_ROOT, uuid_name)

        with open(save_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        profile_image = uuid_name

        # 이메일로 사용자를 찾아 프로필 이미지를 업데이트합니다.
        user = User.objects.filter(email=email).first()
        user.profile_image = profile_image
        user.save()

        return Response(status=200)
