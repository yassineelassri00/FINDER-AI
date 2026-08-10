from rest_framework import serializers


class ResearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(
        max_length=500,
        trim_whitespace=True,
    )