from django.shortcuts import render
from django.db.models import Q, Sum
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
import calendar
from ..models import (
    DateRange, AccountCode, BankData, Budget,
    AccountBalance, UserSettings
)

def multibank(request):
    # ユーザー設定の取得
    user_settings = UserSettings.objects.first()
    selected_year_month = request.GET.get('year_month')
    
    # 年月が指定されていない場合は現在の年月を使用
    if not selected_year_month:
        now = datetime.now()
        selected_year_month = f"{now.year}-{now.month:02d}"
    
    try:
        # 年月を分割
        year, month = map(int, selected_year_month.split('-'))
        # データベース用の年月形式に変換（YYYYMM）
        db_year_month = f"{year}{month:02d}"
    except (ValueError, AttributeError):
        # エラーが発生した場合は現在の年月を使用
        now = datetime.now()
        year, month = now.year, now.month
        selected_year_month = f"{year}-{month:02d}"
        db_year_month = f"{year}{month:02d}"
    
    # 月の最終日を取得
    last_day_of_month = calendar.monthrange(year, month)[1]
    
    # 口座コードの取得
    account_codes = AccountCode.objects.all()
    
    # データレンジの取得
    date_ranges = DateRange.objects.all().order_by('start_day')
    
    # 各データレンジごとのデータを格納する辞書
    budget_data = {}
    
    for dr in date_ranges:
        # 日付範囲の設定（月末日を超えないように調整）
        start_day = min(dr.start_day, last_day_of_month)
        end_day = min(dr.end_day, last_day_of_month)
        
        start_date = date(year, month, start_day)
        end_date = date(year, month, end_day)
        
        # 1ヶ月前の日付を取得
        one_month_ago = start_date - relativedelta(months=1)
        
        # 各銀行のデータを格納する辞書
        banks_data = {}
        
        for account_code in account_codes:
            # 月初残高の取得
            acc_balance = AccountBalance.objects.filter(
                account_code=account_code,
                year_month=db_year_month
            ).first()
            
            if acc_balance:
                prev_balance = acc_balance.beginning_balance
            else:
                prev_balance = 0
            
            # 予算データの取得
            budgets_qs = Budget.objects.filter(
                year_month=db_year_month,
                account_code=account_code,
                daterange=dr
            ).order_by('sort_no1', 'sort_no2')
            
            # 銀行データの取得
            bank_data_qs = BankData.objects.filter(
                account_code=account_code,
                date__range=[one_month_ago, end_date]
            )
            
            # 各項目のデータを取得
            insales = budgets_qs.filter(itemtype="工事金入金")
            inregular = budgets_qs.filter(itemtype="その他入金")
            auto = budgets_qs.filter(itemtype="自動引落")
            individual = budgets_qs.filter(itemtype="個別支払")
            fundtrans = budgets_qs.filter(itemtype="預金振替")
            
            # 合計金額の計算
            income_sales_total = sum(i.amount for i in insales)
            income_regular_total = sum(i.amount for i in inregular)
            total_income = income_sales_total + income_regular_total
            expense_auto_total = sum(i.amount for i in auto)
            expense_individual_total = sum(i.amount for i in individual)
            total_expense = expense_auto_total + expense_individual_total
            total_fundtrans = sum(i.amount for i in fundtrans)
            
            # 残高の計算
            new_balance = prev_balance + total_income - total_expense + total_fundtrans
            
            # 銀行ごとのデータを格納
            banks_data[account_code.bank_code] = {
                'insales': insales,
                'inregular': inregular,
                'auto': auto,
                'individual': individual,
                'fundtrans': fundtrans,
                'income_sales_total': income_sales_total,
                'income_regular_total': income_regular_total,
                'total_income': total_income,
                'expense_auto_total': expense_auto_total,
                'expense_individual_total': expense_individual_total,
                'total_expense': total_expense,
                'total_fundtrans': total_fundtrans,
                'prev_balance': prev_balance,
                'new_balance': new_balance
            }
        
        # データレンジごとのデータを格納
        budget_data[dr] = {
            'banks': banks_data,
            'start_date': start_date,
            'end_date': end_date
        }
    
    context = {
        'date_ranges': date_ranges,
        'account_codes': account_codes,
        'budget_data': budget_data,
        'year_month': selected_year_month
    }
    
    return render(request, 'budget/multibank.html', context) 