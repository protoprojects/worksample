# -*- coding: utf-8 -*-
from core.serializers import JSONWebTokenSerializer


# pylint: disable=W0223
class AdvisorJSONWebTokenSerializer(JSONWebTokenSerializer):
    @staticmethod
    def _is_advisor_validator(user):
        return user.is_advisor()

    USER_GROUP_VALIDATOR_FUNC = _is_advisor_validator
