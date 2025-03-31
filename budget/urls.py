from django.urls import path
#from .views import budget_connectbank, connect_data, delete_connect
from .views.connectbank_views import connectbank, connect_connectbank, delete_connectbank
from .views.addbudget_views import addbudget, addbudget_item
from .views.importbank_views import importbank
from .views.sortbank_views import sortbank

from .views.generatebudget_views import generatebudget

from django.urls import path
from .views.addbudget_views import addbudget, addbudget_item, unlink_connection
from .views.makebasebudget_views import download_budget, upload_basebudget, upload_success
from .views.connectbank_1to1_views import connectbank_1to1, connect_connectbank_1to1

urlpatterns = [
    path('connectbank/', connectbank, name='connectbank'),
    path('connect_connectbank/', connect_connectbank, name='connect_connectbank'),
    path('delete_connectbank/', delete_connectbank, name='delete_connectbank'),

    path("addbudget/", addbudget, name="addbudget"),
    path("sortbank/", sortbank, name="sortbank"),
    path("addbudget_item/", addbudget_item, name="addbudget_item"),
    path("unlink_connection/", unlink_connection, name="unlink_connection"),    
    path('importbank/', importbank, name='importbank'),
    path("generatebudget/", generatebudget, name="generatebudget"),
    path('download_budget/', download_budget, name='download_budget'),
    path('upload_basebudget/', upload_basebudget, name='upload_basebudget'),
    path('upload_success/', upload_success, name='upload_success'),
    path('connectbank_1to1/', connectbank_1to1, name='connectbank_1to1'),
    path('connectbank_1to1/connect/', connect_connectbank_1to1, name='connect_connectbank_1to1'),
]
