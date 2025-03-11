from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime

from budget.models import (
    Budget, DateRange, BankData,
    Connect, ConnectDetail, UserSettings,
    AccountCode, AccountBalance,  # ★ 追加
)

def convert_itemtype(itemtype):
    mapping = {
        "income": "入金",
        "auto": "自動引落",
        "individual": "個別支払",
    }
    return mapping.get(itemtype, "入金")

@login_required
def addbudget(request):
    user = request.user
    # -------------------------
    # 1) ユーザー設定の取得/作成
    # -------------------------
    user_settings, created = UserSettings.objects.get_or_create(
        user=user,
        defaults={
            'year_month': datetime.today().strftime('%Y%m'),
            'selected_account_code': None,
        }
    )

    if request.method == 'POST':
        # year_month と account_code_id を保存
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

        user_settings.save()

        # -- 以下は既存データ更新 / 新規追加処理 (例) --
        for key, value in request.POST.items():
            # 例: default_amount_3 → 最後の数字がBudgetのid
            if key.startswith('default_amount_') and not key.endswith('_new'):
                try:
                    item_id = int(key.split('_')[-1])
                    budget_item = Budget.objects.get(id=item_id)
                    budget_item.amount = int(value)
                    budget_item.save()
                except (ValueError, Budget.DoesNotExist):
                    pass

        # 新規項目の追加
        date_ranges = DateRange.objects.all()
        for dr in date_ranges:
            for item_type in ['income', 'auto', 'individual']:
                prefix = f"{dr.id}_{item_type}_new"
                item_name_key = f'item_name_{prefix}'
                default_amount_key = f'default_amount_{prefix}'
                itemtype_key = f'itemtype_{prefix}'
                daterange_key = f'daterange_{prefix}'
                actual_key = f'actual_{prefix}'
                yearmonth_key = f'year_month_{prefix}'

                if item_name_key in request.POST:
                    item_name = request.POST.get(item_name_key, '')
                    default_amount_str = request.POST.get(default_amount_key, '0')
                    itemtype_str = request.POST.get(itemtype_key, '入金')
                    daterange_id = request.POST.get(daterange_key)
                    actual = (request.POST.get(actual_key) == "True")
                    post_year_month = request.POST.get(yearmonth_key, user_settings.year_month)

                    try:
                        default_amount = int(default_amount_str)
                        daterange_obj = DateRange.objects.get(id=daterange_id)

                        Budget.objects.create(
                            daterange=daterange_obj,
                            itemtype=itemtype_str,
                            item_name=item_name,
                            default_amount=default_amount,
                            amount=default_amount,
                            actual=actual,
                            year_month=post_year_month,
                            # 口座コードを結びつけたい場合
                            account_code=user_settings.selected_account_code
                            # ↑ Budget側にも ForeignKey(account_code=...) がある想定なら
                        )
                    except (ValueError, DateRange.DoesNotExist):
                        pass

        return redirect('addbudget')

    # -------------------------
    # 2) 表示用: データ取得と集計
    # -------------------------
    selected_year_month = user_settings.year_month
    selected_account_code = user_settings.selected_account_code

    # 予算データ
    budgets_qs = Budget.objects.filter(year_month=selected_year_month)
    if selected_account_code:
        budgets_qs = budgets_qs.filter(account_code=selected_account_code)

    # 銀行データ
    bank_data_qs = BankData.objects.filter(
        date__startswith=selected_year_month[:4] + '-'
    )
    if selected_account_code:
        bank_data_qs = bank_data_qs.filter(account_code=selected_account_code)

    # ★ 月初残高の取得
    #    AccountBalance から該当する year_month & account_code を探す
    if selected_account_code:
        acc_balance = AccountBalance.objects.filter(
            account_code=selected_account_code,
            year_month=selected_year_month
        ).first()
    else:
        # 口座が選択されていない場合:
        # 1) 複数口座の合計を出したいなら aggregate() とか
        # 2) 口座未選択なら 0 or 任意のロジック
        acc_balance = None

    if acc_balance:
        prev_balance = acc_balance.beginning_balance
    else:
        prev_balance = 0  # 見つからなければ 0 とする等

    # 集計用
    date_ranges = DateRange.objects.all()
    budget_data = {}
    tmp_prev_balance = prev_balance  # ループのため一時的にコピー

    for dr in date_ranges:
        items_in = budgets_qs.filter(daterange=dr, itemtype="入金")
        items_auto = budgets_qs.filter(daterange=dr, itemtype="自動引落")
        items_individual = budgets_qs.filter(daterange=dr, itemtype="個別支払")

        income_total = sum(i.amount for i in items_in)
        expense_auto_total = sum(i.amount for i in items_auto)
        expense_individual_total = sum(i.amount for i in items_individual)
        total_expense = expense_auto_total + expense_individual_total
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

    return render(request, 'addbudget.html', {
        "budget_data": budget_data,
        "bank_data": bank_data_qs,
        "year_month": selected_year_month,
        "selected_account_code": selected_account_code,
        "account_codes": AccountCode.objects.all(),
        "initial_prev_balance": prev_balance,  # 画面上で使いたい場合
    })

@login_required
def addbudget_item(request):
    """
    ドラッグ＆ドロップされたデータを Budget に登録するAPI
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            item_name = data.get("item_name", "")
            amount = int(data.get("amount", 0))
            daterange_id = int(data.get("daterange_id", 0))
            itemtype_key = data.get("itemtype", "income")
            year_month = data.get("year_month", datetime.today().strftime('%Y%m'))
            account_code_id = data.get("account_code_id")  # フロントで送るなら

            # DateRange取得
            daterange_obj = DateRange.objects.get(id=daterange_id)

            # 口座コードを結びつける場合
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
                account_code=account_code_obj,  # Budget側にForeignKeyがある想定
            )
            return JsonResponse({"status": "success", "message": "保存成功"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "無効なリクエスト"})
