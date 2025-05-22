# addbudget_views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime, date
import calendar  # 月の最終日を取得するために使用


from budget.models import (
    Budget, DateRange, BankData,
    Connect, ConnectDetail, UserSettings,
    AccountCode, AccountBalance,
)

def convert_itemtype(itemtype):
    mapping = {
        "income": "入金",
        "auto": "自動引落",
        "individual": "個別支払",
    }
    return mapping.get(itemtype, "入金")

@login_required
def sortbank(request):
    user = request.user
    user_settings, created = UserSettings.objects.get_or_create(
        user=user,
        defaults={
            'year_month': datetime.today().strftime('%Y%m'),
            'selected_account_code': None,
            'selected_daterange': None,
        }
    )

    if request.method == 'POST':
        # year_month, account_codeの更新
        new_year_month = request.POST.get('year_month')
        if new_year_month:
            user_settings.year_month = new_year_month

        new_account_code_id = request.POST.get('account_code_id')
        if new_account_code_id:
            try:
                ac = AccountCode.objects.get(pk=new_account_code_id)
                user_settings.selected_account_code = ac
            except AccountCode.DoesNotExist:
                user_settings.selected_account_code = None

        # ★ 追加: DateRangeの更新
        new_daterange_id = request.POST.get('daterange_id')
        if new_daterange_id:
            try:
                dr = DateRange.objects.get(pk=new_daterange_id)
                user_settings.selected_daterange = dr
            except DateRange.DoesNotExist:
                user_settings.selected_daterange = None

        user_settings.save()

        # 予算データの既存レコード更新(例: default_amount_〇〇など)
        for key, value in request.POST.items():
            # sort_no1_XX or sort_no2_XX であれば並べ替え番号を更新
            if key.startswith('sort_no1_') or key.startswith('sort_no2_'):
                try:
                    item_id = int(key.split('_')[-1])
                    budget_item = Budget.objects.get(id=item_id)
                    if key.startswith('sort_no1_'):
                        budget_item.sort_no1 = int(value or 0)
                    else:
                        budget_item.sort_no2 = int(value or 0)
                    budget_item.save()
                except (ValueError, Budget.DoesNotExist):
                    pass

            # 例: default_amount_3 → Budget.id=3のdefault_amountを更新
            if key.startswith('default_amount_') and not key.endswith('_new'):
                try:
                    item_id = int(key.split('_')[-1])
                    budget_item = Budget.objects.get(id=item_id)
                    budget_item.amount = int(value)  # 実際のamountも更新する場合
                    budget_item.save()
                except (ValueError, Budget.DoesNotExist):
                    pass

        # (必要なら) 新規項目の追加処理 ... （省略/既存のままでもOK）

        return redirect('sortbank')

    # -------------------------------------------------------
    # 表示用データの取得
    # -------------------------------------------------------
    selected_year_month = user_settings.year_month
    selected_account_code = user_settings.selected_account_code
    selected_daterange = user_settings.selected_daterange

    # 日付範囲の作成
    year = int(selected_year_month[:4])
    month = int(selected_year_month[4:])
    if selected_daterange:
        start_day = selected_daterange.start_day
        end_day = selected_daterange.end_day

        # **もしend_dayが31の場合、その月の月末に変更**
        if end_day == 31:
            end_day = calendar.monthrange(year, month)[1]  # 月の最終日を取得
    else:
        # DateRange未選択なら、その月全体を対象にする
        start_day = 1
        end_day = calendar.monthrange(year, month)[1]  # 月末を取得


    start_date = date(year, month, start_day)  # `datetime.date` 型
    end_date = date(year, month, end_day)      # `datetime.date` 型

    # 予算データ取得 (年月とDateRangeで絞り込み)
    budgets_qs = Budget.objects.filter(year_month=selected_year_month)
    print('--1--')
    print(budgets_qs)
    if selected_account_code:
        budgets_qs = budgets_qs.filter(account_code=selected_account_code)
    if selected_daterange:
        budgets_qs = budgets_qs.filter(daterange=selected_daterange)

    # 並べ替え (sort_no1, sort_no2)
    budgets_qs = budgets_qs.order_by('sort_no1', 'sort_no2', 'id')
    print('--2--')
    print(budgets_qs)
    # 銀行データ取得 (日付範囲で絞り込み)
    bank_data_qs = BankData.objects.filter(date__range=[start_date, end_date])
    if selected_account_code:
        bank_data_qs = bank_data_qs.filter(account_code=selected_account_code)

    # 月初残高の取得
    if selected_account_code:
        acc_balance = AccountBalance.objects.filter(
            account_code=selected_account_code,
            year_month=selected_year_month
        ).first()
    else:
        acc_balance = None

    prev_balance = acc_balance.beginning_balance if acc_balance else 0

    date_ranges = DateRange.objects.all()
    budget_data = {}
    tmp_prev_balance = prev_balance

    if selected_daterange:
        print('id', selected_daterange.id)
        date_ranges = [selected_daterange]  # リスト化する（for ループで使いやすい形に）
    else:
        date_ranges = DateRange.objects.all()

    print('==3==')
    print(date_ranges)

    for dr in date_ranges:
        # itemtype別に抽出 & 並べ替え済み
        items_in = budgets_qs.filter(daterange=dr, itemtype="入金")
        items_auto = budgets_qs.filter(daterange=dr, itemtype="自動引落")
        items_individual = budgets_qs.filter(daterange=dr, itemtype="個別支払")

        # 入金合計, 出金合計
        income_total = sum(i.amount for i in items_in)
        expense_auto_total = sum(i.amount for i in items_auto)
        expense_individual_total = sum(i.amount for i in items_individual)
        total_expense = expense_auto_total + expense_individual_total

        print(dr,income_total)

        new_balance = tmp_prev_balance + income_total - total_expense

        budget_data[dr] = {
            "items": {
                "入金": items_in,
                "自動引落": items_auto,
                "個別支払": items_individual,
            },
            "income_total": income_total,
            "expense_auto_total": expense_auto_total,
            "expense_individual_total": expense_individual_total,
            "total_expense": total_expense,
            "prev_balance": tmp_prev_balance,
            "new_balance": new_balance,
        }
        tmp_prev_balance = new_balance

    #return render(request, 'addbudget.html', {
    #    "budget_data": budget_data,
    #    "bank_data": bank_data_qs,
    #    "year_month": selected_year_month,
    #    "selected_account_code": selected_account_code,
    #    "account_codes": AccountCode.objects.all(),
    #    "initial_prev_balance": prev_balance,
    #})

    import json

    #print("=== DEBUG: budget_data ===")
    #print(json.dumps(budget_data, ensure_ascii=False, indent=2))  # コンソールに出力    

    # テンプレートへ渡す
    #return render(request, 'addbudget.html', {
    #    "bank_data": bank_data_qs,
    #    "budgets": budget_data,
    #    "year_month": selected_year_month,
    #    "selected_account_code": selected_account_code,
    #    "selected_daterange": selected_daterange,
    #    "account_codes": AccountCode.objects.all(),
    #    "date_ranges": DateRange.objects.all(),  # テンプレートで選択肢表示用
    #})
    return render(request, 'budget/sortbank.html', {
        "budget_data": budget_data,
        "bank_data": bank_data_qs,
        "year_month": selected_year_month,
        "selected_account_code": selected_account_code,
        "selected_daterange": selected_daterange,
        "account_codes": AccountCode.objects.all(),
        "date_ranges": DateRange.objects.all(),
        "initial_prev_balance": prev_balance,
    })


@login_required
def addbudget_item(request):
    """ドラッグ＆ドロップされたデータを Budget に登録するAPI"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            item_name = data.get("item_name", "")
            amount = int(data.get("amount", 0))
            daterange_id = int(data.get("daterange_id", 0))
            itemtype_key = data.get("itemtype", "income")
            year_month = data.get("year_month", datetime.today().strftime('%Y%m'))
            account_code_id = data.get("account_code_id")

            daterange_obj = DateRange.objects.get(id=daterange_id)
            account_code_obj = None
            if account_code_id:
                try:
                    account_code_obj = AccountCode.objects.get(id=account_code_id)
                except AccountCode.DoesNotExist:
                    pass

            itemtype_str = convert_itemtype(itemtype_key)

            Budget.objects.create(
                daterange=daterange_obj,
                itemtype=itemtype_str,
                item_name=item_name,
                amount=amount,
                default_amount=amount,
                actual=True,
                year_month=year_month,
                account_code=account_code_obj,
            )
            return JsonResponse({"status": "success", "message": "保存成功"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "無効なリクエスト"})
