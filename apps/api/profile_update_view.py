from django.db import transaction
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace
from apps.audit.models import AuditAction
from apps.audit.services.audit_logger import create_audit_log


class ProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    designation = serializers.CharField(max_length=120, required=False, allow_blank=True)


class CurrentProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    @transaction.atomic
    def patch(self, request):
        profile = getattr(request.user, "profile", None)
        if not profile or not profile.is_active:
            return Response({"detail": "An active profile is required."}, status=403)
        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user_fields = []
        profile_fields = []
        for field in ("full_name", "phone", "designation"):
            if field not in serializer.validated_data:
                continue
            value = serializer.validated_data[field].strip()
            if field == "full_name":
                request.user.full_name = value
                user_fields.append(field)
            else:
                setattr(profile, field, value)
                profile_fields.append(field)
        if user_fields:
            user_fields.append("updated_at")
            request.user.save(update_fields=user_fields)
        if profile_fields:
            profile_fields.append("updated_at")
            profile.save(update_fields=profile_fields)
        create_audit_log(
            request=request,
            organization=profile.organization,
            action=AuditAction.UPDATED,
            model_name="UserProfile",
            object_id=profile.pk,
            message="Profile details updated through the API.",
            extra_data={"fields": list(serializer.validated_data)},
        )
        return Response({
            "id": request.user.pk,
            "username": request.user.get_username(),
            "email": request.user.email,
            "full_name": request.user.full_name,
            "phone": profile.phone,
            "designation": profile.designation,
        })
