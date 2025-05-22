from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import (
    AccountCode, AccountBalance, DateRange, Budget,
    UserSettings, BaseBudget
)
from django.db.models import Sum, Q
from collections import defaultdict

@login_required
def period_summary(request):
    # ユーザー設定の取得または作成
    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # フォームから送信されたデータを処理
        year_month = request.POST.get('year_month', user_settings.year_month)
        connectflag = request.POST.get('connectflag') == '1'

        # ユーザー設定を更新
        user_settings.year_month = year_month
        user_settings.connectflag = connectflag
        user_settings.save()
    else:
        year_month = user_settings.year_month
        connectflag = user_settings.connectflag

    # 期間の取得
    date_ranges = DateRange.objects.all().order_by('start_day')

    # 期間ごとのデータを集計
    periods = []
    for dr in date_ranges:
        # 期間ごとのデータ構造
        period_data = {
            'name': dr.name,
            'start_day': dr.start_day,
            'end_day': dr.end_day,
            'banks': [],
            'income_categories': [],
            'expense_categories': [],
            'transfer_categories': [],
            'total_prev_balance': 0,
            'total_income': 0,
            'total_expense': 0,
            'total_transfer': 0,
            'total_new_balance': 0
        }

        # 銀行口座ごとのデータを集計
        banks = AccountCode.objects.all()
        for bank in banks:
            # 前月残高の取得
            prev_balance = AccountBalance.objects.filter(
                account_code=bank,
                year_month=year_month
            ).first()
            prev_balance_amount = prev_balance.beginning_balance if prev_balance else 0

            # 予算データの取得
            budgets = Budget.objects.filter(
                daterange=dr,
                year_month=year_month,
                account_code=bank
            )
            if connectflag:
                budgets = budgets.filter(connected_number__isnull=False)

            # 入金・出金・振替の集計
            bank_data = {
                'code': f"{bank.bank_code} {bank.deposit_type}",
                'prev_balance': prev_balance_amount,
                'income': 0,
                'expense': 0,
                'transfer': 0
            }

            for budget in budgets:
                if budget.transaction_type == '入金':
                    bank_data['income'] += budget.amount
                elif budget.transaction_type == '出金':
                    bank_data['expense'] += budget.amount
                elif budget.transaction_type == '預金振替':
                    bank_data['transfer'] += budget.amount

            bank_data['new_balance'] = (
                bank_data['prev_balance'] +
                bank_data['income'] -
                bank_data['expense']
            )

            period_data['banks'].append(bank_data)
            period_data['total_prev_balance'] += bank_data['prev_balance']
            period_data['total_income'] += bank_data['income']
            period_data['total_expense'] += bank_data['expense']
            period_data['total_transfer'] += bank_data['transfer']
            period_data['total_new_balance'] += bank_data['new_balance']

        # カテゴリごとの集計
        categories = defaultdict(lambda: {
            'name': '',
            'total': 0,
            'banks': []
        })

        for budget in Budget.objects.filter(
            daterange=dr,
            year_month=year_month
        ):
            if connectflag and not budget.connected_number:
                continue

            category = categories[budget.itemtype]
            category['name'] = budget.itemtype
            category['total'] += budget.amount

            bank_code = f"{budget.account_code.bank_code} {budget.account_code.deposit_type}"
            bank_amount = next(
                (b['amount'] for b in category['banks'] if b['code'] == bank_code),
                None
            )
            if bank_amount is None:
                category['banks'].append({
                    'code': bank_code,
                    'amount': budget.amount
                })
            else:
                bank_amount += budget.amount

        # カテゴリを入金・出金・振替に分類
        for category in categories.values():
            if category['name'] in ['工事金入金', 'その他入金']:
                period_data['income_categories'].append(category)
            elif category['name'] in ['自動引落', '個別支払']:
                period_data['expense_categories'].append(category)
            elif category['name'] == '預金振替':
                period_data['transfer_categories'].append(category)

        periods.append(period_data)

    return render(request, 'period_summary.html', {
        'periods': periods,
        'user_settings': user_settings
    }) 