from django.urls import path
from .views import (
    connectbank, connect_connectbank, delete_connectbank,
    addbudget, addbudget_item, unlink_connection,
    importbank, sortbank, generatebudget,
    download_budget, upload_basebudget, upload_success,
    connectbank_1to1, connect_connectbank_1to1,
    multibank, delete_budget_item
)

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
    path('multibank/', multibank, name='multibank'),
    path('connectbank_1to1/', connectbank_1to1, name='connectbank_1to1'),
    path('connectbank_1to1/connect/', connect_connectbank_1to1, name='connect_connectbank_1to1'),
    path('delete_budget_item/', delete_budget_item, name='delete_budget_item'),
]
