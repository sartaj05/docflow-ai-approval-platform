from django.db import transaction
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace


class APITokenView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    @transaction.atomic
    def post(self, request):
        # Rotate the user's token and reveal the new secret only in this response.
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)
        return Response(
            {
                "token": token.key,
                "authorization_header": f"Token {token.key}",
            },
            status=201,
        )

    def delete(self, request):
        deleted, _ = Token.objects.filter(user=request.user).delete()
        return Response({"revoked": bool(deleted)})
