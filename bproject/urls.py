from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Django管理サイト
    path('', include('budget.urls')),  # アプリ（myapp）のURL設定を組み込む
]