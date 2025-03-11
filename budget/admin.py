# admin.py

from django.contrib import admin
from .models import (
    DateRange, Budget, BankData, Connect,
    ConnectDetail, AccountCode, AccountBalance,
    UserSettings
)

@admin.register(DateRange)
class DateRangeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('id', 'daterange', 'itemtype', 'item_name', 'amount', 'default_amount', 'actual', 'connected_number')
    list_filter = ('itemtype', 'daterange')
    search_fields = ('item_name',)

@admin.register(BankData)
class BankDataAdmin(admin.ModelAdmin):
    list_display = ('bank_id', 'date', 'item_name', 'amount', 'transaction_type', 'connected_number')
    list_filter = ('transaction_type', 'date')
    search_fields = ('item_name', 'bank_id')

@admin.register(Connect)
class ConnectAdmin(admin.ModelAdmin):
    list_display = ('connect_number', 'created_at')
    search_fields = ('connect_number',)

@admin.register(ConnectDetail)
class ConnectDetailAdmin(admin.ModelAdmin):
    list_display = ('connect', 'bank_data', 'budget_data')
    list_filter = ('connect',)

# ★ 新規追加: AccountCode
@admin.register(AccountCode)
class AccountCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'bank_code', 'deposit_type', 'account_number')
    search_fields = ('bank_code', 'account_number', 'deposit_type')

# ★ 新規追加: AccountBalance
@admin.register(AccountBalance)
class AccountBalanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_code', 'year_month', 'beginning_balance')
    list_filter = ('year_month', 'account_code')
    search_fields = ('account_code__bank_code', 'year_month')

# ★ 新規追加: UserSettings
@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'year_month', 'selected_account_code')
    list_filter = ('year_month',)
    search_fields = ('user__username', 'selected_account_code__bank_code')
