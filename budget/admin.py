# admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.contrib import admin
from .models import (
    DateRange, Budget, BankData, Connect,
    ConnectDetail, AccountCode, AccountBalance,
    UserSettings
)


@admin.register(AccountBalance)
class AccountBalanceAdmin(admin.ModelAdmin):
    list_display = ('account_code', 'year_month', 'styled_beginning_balance')
    list_filter = ('year_month', 'account_code')
    search_fields = ('account_code__bank_code', 'year_month')

    def styled_beginning_balance(self, obj):
        return format_html(
            '<div style="min-width: 250px; font-size: 16px; font-weight: bold;">{}</div>',
            obj.beginning_balance
        )
    styled_beginning_balance.short_description = 'Beginning Balance'





@admin.register(DateRange)
class DateRangeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('id', 'year_month','daterange', 'itemtype', 'item_name', 'amount', "base_budget", 'connected_number', "account_code")
    list_filter = ('itemtype', 'daterange')
    search_fields = ('item_name', "base_budget__item_name", "account_code__account_number",)

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


# ★ 新規追加: UserSettings
@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'year_month', 'selected_account_code','codename')
    list_filter = ('year_month',)
    search_fields = ('user__username', 'selected_account_code__bank_code')


from .models import BaseBudget, Budget

@admin.register(BaseBudget)
class BaseBudgetAdmin(admin.ModelAdmin):
    list_display = ("item_name", "itemtype", 'daterange', "amount", "specific_month", "account_code")
    list_filter = ("itemtype", "specific_month")
    search_fields = ("item_name", "account_code__account_number")
    actions = ["update_actual_amounts"]

    def update_actual_amounts(self, request, queryset):
        """
        選択した BaseBudget に対して、実績金額を更新する管理アクション
        """
        for base_budget in queryset:
            base_budget.update_actual_amounts_for_month(2025, 3)  # 例: 2025年3月を更新
        self.message_user(request, "実績金額を更新しました。")

    update_actual_amounts.short_description = "選択した予算の実績金額を更新"