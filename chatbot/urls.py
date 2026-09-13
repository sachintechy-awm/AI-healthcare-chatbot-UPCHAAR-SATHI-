from django.urls import path
from . import views

app_name = "chatbot"

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/<int:session_id>/', views.index, name='session'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/send/', views.send_message, name='send_message'),
    path('api/new/', views.new_session, name='new_session'),
    path('api/session/<int:session_id>/delete/', views.delete_session, name='delete_session'),
]
