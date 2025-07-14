from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('add/', views.add_image, name='add_image'),
    path('order/<int:doc_id>/', views.order_analysis, name='order_analysis'),
    path('pay/<int:cart_id>/', views.pay_order, name='pay_order'),
    path('result/<int:cart_id>/', views.analysis_result, name='analysis_result'),
]
