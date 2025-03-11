# addbudget_views.py

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime
import uuid

from budget.models import (
    Budget, DateRange, BankData,
    Connect, ConnectDetail, UserSettings,
    AccountCode, AccountBalance,
)


def convert_itemtype(itemtype):
    """Ajaxドラッグ＆ドロップ時の 'income' → '入金' 等の変換用"""
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
    # 1) ユーザー設定を取得・更新
    # -------------------------
    user_settings, _ = UserSettings.objects.get_or_create(
        user=user,
        defaults={
            'year_month': datetime.today().strftime('%Y%m'),
            'selected_account_code': None,
        }
    )

    if request.method == 'POST':
        # 年月と口座を取得してUserSettingsに保存
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

        # -------------------------
        # (A) 既存レコードの更新
        # -------------------------
        for key, value in request.POST.items():
            # 例: default_amount_3 → Budget.id = 3
            if key.startswith('default_amount_') and not key.endswith('_new'):
                budget_id_str = key.split('_')[-1]
                try:
                    budget_id = int(budget_id_str)
                    budget_item = Budget.objects.get(id=budget_id)
                    budget_item.default_amount = int(value or 0)
                    budget_item.save()
                except (ValueError, Budget.DoesNotExist):
                    pass

            # sort_no1_XX → Budget.id=XX
            if key.startswith('sort_no1_') and not key.endswith('_new'):
                budget_id_str = key.replace('sort_no1_', '')
                try:
                    budget_id = int(budget_id_str)
                    b = Budget.objects.get(pk=budget_id)
                    b.sort_no1 = int(value or 0)
                    b.save()
                except (ValueError, Budget.DoesNotExist):
                    pass

            # sort_no2_XX → Budget.id=XX
            if key.startswith('sort_no2_') and not key.endswith('_new'):
                budget_id_str = key.replace('sort_no2_', '')
                try:
                    budget_id = int(budget_id_str)
                    b = Budget.objects.get(pk=budget_id)
                    b.sort_no2 = int(value or 0)
                    b.save()
                except (ValueError, Budget.DoesNotExist):
                    pass

        # -------------------------
        # (B) 新規レコードの追加
        # -------------------------
        date_ranges = DateRange.objects.all()
        for dr in date_ranges:
            for item_type in ['income', 'auto', 'individual']:
                # prefix = "{DateRange.id}_{item_type}_new" 例: "5_income_new"
                prefix = f"{dr.id}_{item_type}_new"

                item_name_key = f'item_name_{prefix}'
                default_amount_key = f'default_amount_{prefix}'
                sort_no1_key = f'sort_no1_{prefix}'
                sort_no2_key = f'sort_no2_{prefix}'
                itemtype_key = f'itemtype_{prefix}'
                daterange_key = f'daterange_{prefix}'
                actual_key = f'actual_{prefix}'
                yearmonth_key = f'year_month_{prefix}'

                if item_name_key in request.POST:
                    item_name = request.POST.get(item_name_key, '')
                    default_amount_str = request.POST.get(default_amount_key, '0')
                    sort_no1_str = request.POST.get(sort_no1_key, '0')
                    sort_no2_str = request.POST.get(sort_no2_key, '0')
                    itemtype_str = request.POST.get(itemtype_key, '入金')
                    daterange_id = request.POST.get(daterange_key)
                    actual = (request.POST.get(actual_key) == "True")
                    post_year_month = request.POST.get(yearmonth_key, user_settings.year_month)

                    try:
                        default_amount = int(default_amount_str)
                        s1 = int(sort_no1_str)
                        s2 = int(sort_no2_str)
                        daterange_obj = DateRange.objects.get(id=daterange_id)

                        Budget.objects.create(
                            daterange=daterange_obj,
                            itemtype=itemtype_str,
                            item_name=item_name,
                            default_amount=default_amount,
                            amount=default_amount,  # 新規時点では amount=default_amount など運用次第
                            actual=actual,
                            year_month=post_year_month,
                            account_code=user_settings.selected_account_code,
                            sort_no1=s1,
                            sort_no2=s2,
                        )
                    except (ValueError, DateRange.DoesNotExist):
                        pass

        return redirect('addbudget')

    # -------------------------
    # 2) データ取得して画面表示用に加工
    # -------------------------
    selected_year_month = user_settings.year_month
    selected_account_code = user_settings.selected_account_code

    # Budget
    budgets_qs = Budget.objects.filter(year_month=selected_year_month)
    if selected_account_code:
        budgets_qs = budgets_qs.filter(account_code=selected_account_code)

    # BankData (選択年月のyear & monthでフィルタする例)
    bank_data_qs = BankData.objects.all()
    try:
        y = int(selected_year_month[:4])
        m = int(selected_year_month[4:])
        bank_data_qs = bank_data_qs.filter(date__year=y, date__month=m)
    except:
        pass
    if selected_account_code:
        bank_data_qs = bank_data_qs.filter(account_code=selected_account_code)

    # 月初残高(あれば)
    acc_balance = None
    if selected_account_code:
        acc_balance = AccountBalance.objects.filter(
            account_code=selected_account_code,
            year_month=selected_year_month
        ).first()
    if acc_balance:
        prev_balance = acc_balance.beginning_balance
    else:
        prev_balance = 0

    # DateRangeごとの集計データ
    date_ranges = DateRange.objects.all().order_by('start_day')
    budget_data = {}
    tmp_prev_balance = prev_balance

    for dr in date_ranges:
        items_in = budgets_qs.filter(daterange=dr, itemtype="入金")\
                             .order_by('sort_no1', 'sort_no2')
        items_auto = budgets_qs.filter(daterange=dr, itemtype="自動引落")\
                               .order_by('sort_no1', 'sort_no2')
        items_individual = budgets_qs.filter(daterange=dr, itemtype="個別支払")\
                                     .order_by('sort_no1', 'sort_no2')

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
        "initial_prev_balance": prev_balance,
    })


@login_required
def addbudget_item(request):
    """
    Ajax経由のドラッグ&ドロップでBudgetを作る簡易API
    """
    if request.method == "POST":
        try:
            print('連結開始1')
            data = json.loads(request.body)
            item_id = data.get("item_id")
            item_name = data.get("item_name", "")
            amount = int(data.get("amount", 0))
            daterange_id = int(data.get("daterange_id", 0))
            itemtype_key = data.get("itemtype", "income")
            year_month = data.get("year_month", datetime.today().strftime('%Y%m'))
            account_code_id = data.get("account_code_id")

            from_dragdrop = data.get("from_dragdrop", False)
            bank_id = data.get("bank_id")
            print('bank_id',bank_id)
            print('item_id',item_id)

            # DateRange
            dr_obj = DateRange.objects.get(id=daterange_id)

            print('連結開始2')

            # 口座コード
            ac_obj = None
            if account_code_id:
                try:
                    ac_obj = AccountCode.objects.get(id=account_code_id)
                except AccountCode.DoesNotExist:
                    pass

            itemtype_str = convert_itemtype(itemtype_key)

            # (1) Budgetを作成 (未連携状態)
            new_budget = Budget.objects.create(
                daterange=dr_obj,
                itemtype=itemtype_str,
                item_name=item_name,
                amount=amount,
                default_amount=amount,
                actual=True,
                year_month=year_month,
                account_code=ac_obj,
                sort_no1=0,
                sort_no2=0,
                connected_number=None  # 最初は未連携
            )
            print('連結開始3')
            # (2) ドラッグ&ドロップなら BankData と連携する
            if from_dragdrop:
                # BankData取得
                print('連結開始4')
                try:
                    print('bank_id',bank_id)
                    bank_obj = BankData.objects.get(pk=bank_id)
                    print('連結開始5')
                except BankData.DoesNotExist:
                    return JsonResponse({"status": "error", "message": "指定の銀行データが見つかりません"})

                print('連結開始6')
                # Connectを作成
                connect_number = str(uuid.uuid4())[:8]
                print(connect_number)
                connect_obj = Connect.objects.create(connect_number=connect_number)
                print('連結開始7')
                # BankData & Budget に connect_number を設定
                bank_obj.connected_number = connect_number
                bank_obj.save()
                print('連結開始8')
                new_budget.connected_number = connect_number
                new_budget.save()

                # ConnectDetail 2件作成
                ConnectDetail.objects.create(
                    connect=connect_obj,
                    bank_data=bank_obj
                )
                ConnectDetail.objects.create(
                    connect=connect_obj,
                    budget_data=new_budget
                )
                msg = "Budget新規作成 & BankData連携"
            else:
                # ドラッグ＆ドロップでない場合は連携せず、普通に完了
                msg = "Budget新規作成(連携なし)"

            return JsonResponse({"status": "success", "message": msg})


        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "無効なリクエスト"})
