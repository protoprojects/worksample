from django.contrib import admin

from solo.admin import SingletonModelAdmin

from vendors import models as v_models

admin.site.register(v_models.SalesforceRateQuoteInfo, SingletonModelAdmin)
admin.site.register(v_models.SalesforcesampleOneRegInfo, SingletonModelAdmin)
