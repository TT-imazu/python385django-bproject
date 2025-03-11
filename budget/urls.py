from django.urls import path
#from .views import budget_connectbank, connect_data, delete_connect
from .views.connectbank_views import connectbank, connect_connectbank, delete_connectbank
from .views.addbudget_views import addbudget, addbudget_item
from .views.importbank_views import importbank
from .views.sortbank_views import sortbank

from django.urls import path
from .views.addbudget_views import addbudget, addbudget_item, unlink_connection


urlpatterns = [
    path('connectbank/', connectbank, name='connectbank'),
    path('connect_connectbank/', connect_connectbank, name='connect_connectbank'),
    path('delete_connectbank/', delete_connectbank, name='delete_connectbank'),

    path("addbudget/", addbudget, name="addbudget"),
    path("sortbank/", sortbank, name="sortbank"),
    path("addbudget_item/", addbudget_item, name="addbudget_item"),
    path("unlink_connection/", unlink_connection, name="unlink_connection"),    
    path('importbank/', importbank, name='importbank'),
]
