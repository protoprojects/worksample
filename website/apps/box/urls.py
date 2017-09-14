from django.conf.urls import url

from box import views

urlpatterns = [
    url(r'^exercise/$', views.box_auth_exercise, name='box_auth_exercise'),
    url(r'^box-event-callback/$', views.box_event_callback_view, name='box_event_callback'),
]
