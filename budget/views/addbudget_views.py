from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar
import uuid

from django.db.models import Q


from budget.models import (
    Budget, DateRange, BankData,
    Connect, ConnectDetail, UserSettings,
    AccountCode, AccountBalance,
)

def convert_itemtype(itemtype):
    """Ajaxドラッグ＆ドロップ時の 'income' → '入金' 等の変換用"""
    mapping = {
        "insales": "工事金入金",
        "inregular": "その他入金",
        "auto": "自動引落",
        "individual": "個別支払",
        "fundtrans": "預金振替"
    }
    return mapping.get(itemtype, "工事金入金")

@login_required
def addbudget(request):
    user = request.user

    # -------------------------
    # 1) ユーザー設定を取得・作成
    # -------------------------
    user_settings, created = UserSettings.objects.get_or_create(
        user=user,
        defaults={
            'year_month': datetime.today().strftime('%Y%m'),
            'selected_account_code': None,
            'selected_daterange': None,
            'end_day': 0,
            'connectflag': False,
        }
    )

    if request.method == 'POST':
        # year_month & account_code
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

        # DateRangeの更新
        new_daterange_id = request.POST.get('daterange_id')
        if new_daterange_id:
            try:
                dr = DateRange.objects.get(pk=new_daterange_id)
                user_settings.selected_daterange = dr
            except DateRange.DoesNotExist:
                user_settings.selected_daterange = None
        else:
            user_settings.selected_daterange = None

        # end_dayの更新 (数値として扱う)
        new_end_day = request.POST.get('end_day')
        if new_end_day:
            try:
                user_settings.end_day = int(new_end_day)
            except ValueError:
                user_settings.end_day = 0
        else:
            user_settings.end_day = 0

        # connectflag (チェックボックス)
        new_connectflag = request.POST.get('connectflag')
        user_settings.connectflag = bool(new_connectflag)

        # ユーザー設定保存
        user_settings.save()

        # (A) 既存レコードの更新
        for key, value in request.POST.items():
            if key.startswith('amount_') and not key.endswith('_new'):
                budget_id_str = key.split('_')[-1]
                try:
                    budget_id = int(budget_id_str)
                    budget_item = Budget.objects.get(id=budget_id)
                    budget_item.amount = int(value or 0)
                    budget_item.save()
                except (ValueError, Budget.DoesNotExist):
                    pass

            if key.startswith('sort_no1_') and not key.endswith('_new'):
                budget_id_str = key.replace('sort_no1_', '')
                try:
                    budget_id = int(budget_id_str)
                    b = Budget.objects.get(pk=budget_id)
                    b.sort_no1 = int(value or 0)
                    b.save()
                except (ValueError, Budget.DoesNotExist):
                    pass

            if key.startswith('sort_no2_') and not key.endswith('_new'):
                budget_id_str = key.replace('sort_no2_', '')
                try:
                    budget_id = int(budget_id_str)
                    b = Budget.objects.get(pk=budget_id)
                    b.sort_no2 = int(value or 0)
                    b.save()
                except (ValueError, Budget.DoesNotExist):
                    pass

        # (B) 新規レコードの追加
        date_ranges = DateRange.objects.all()
        for dr in date_ranges:
            for item_type in ['insales', 'inregular', 'auto', 'individual','fundtrans']:
                prefix = f"{dr.id}_{item_type}_new"

                item_name_key = f'item_name_{prefix}'
                amount_key = f'amount_{prefix}'
                sort_no1_key = f'sort_no1_{prefix}'
                sort_no2_key = f'sort_no2_{prefix}'
                itemtype_key = f'itemtype_{prefix}'
                daterange_key = f'daterange_{prefix}'
                #actual_key = f'True'
                yearmonth_key = f'year_month_{prefix}'

                if item_name_key in request.POST:
                    item_name = request.POST.get(item_name_key, '')
                    amount_str = request.POST.get(amount_key, '0')
                    sort_no1_str = request.POST.get(sort_no1_key, '0')
                    sort_no2_str = request.POST.get(sort_no2_key, '0')
                    itemtype_str = request.POST.get(itemtype_key, '工事金入金')
                    daterange_id = request.POST.get(daterange_key)
                    #actual = (request.POST.get(actual_key) == "True")
                    post_year_month = request.POST.get(yearmonth_key, user_settings.year_month)

                    try:
                        amount = int(amount_str)
                        s1 = int(sort_no1_str)
                        s2 = int(sort_no2_str)
                        daterange_obj = DateRange.objects.get(id=daterange_id)

                        Budget.objects.create(
                            daterange=daterange_obj,
                            itemtype=itemtype_str,
                            item_name=item_name,
                            amount=amount,
                            #default_amount=0,
                            #actual=actual,
                            year_month=post_year_month,
                            account_code=user_settings.selected_account_code,
                            sort_no1=s1,
                            sort_no2=s2,
                        )
                    except (ValueError, DateRange.DoesNotExist):
                        pass

        return redirect('addbudget')

    # -------------------------
    # 2) 表示用データの取得
    # -------------------------
    selected_year_month = user_settings.year_month
    selected_account_code = user_settings.selected_account_code
    selected_daterange = user_settings.selected_daterange
    selected_end_day = user_settings.end_day
    selected_connectflag = user_settings.connectflag

    # 年月から year, month を取り出す
    year = int(selected_year_month[:4])
    month = int(selected_year_month[4:])
    start_day = 1

    # DateRangeが選択されていれば、そのend_dayを取得
    if selected_daterange:
        end_day = selected_daterange.end_day
        if end_day == 31:
            end_day = calendar.monthrange(year, month)[1]
    else:
        end_day = calendar.monthrange(year, month)[1]

    # ユーザー指定のend_dayがあれば上書き
    if selected_end_day > 0:
        end_day = selected_end_day

    start_date = date(year, month, start_day)
    end_date = date(year, month, end_day)

    # 1ヶ月前の日付を取得
    one_month_ago = start_date - relativedelta(months=1)

    # Budgetをフィルタ
    budgets_qs = Budget.objects.filter(year_month=selected_year_month)

    fundtrans_qs = budgets_qs.filter(itemtype="預金振替")
    amount_fundtrans = sum(i.amount for i in fundtrans_qs)
    
    if selected_account_code:
        budgets_qs = budgets_qs.filter(account_code=selected_account_code)

    # end_dayがあれば sort_no1 <= end_day
    if selected_end_day:
        budgets_qs = budgets_qs.filter(sort_no1__lte=selected_end_day)
    else:
        # DateRangeが選択されていればそれ以下のid
        if selected_daterange:
            budgets_qs = budgets_qs.filter(daterange__id__lte=selected_daterange.id)

    # connectflag が True なら connected_number のあるもののみ
    if selected_connectflag:
        budgets_qs = budgets_qs.filter(connected_number__isnull=False)

    # 並び順
    budgets_qs = budgets_qs.order_by('sort_no1', 'sort_no2', 'id')

    # 銀行データ
    bank_data_qs = BankData.objects.filter(date__range=[one_month_ago, end_date])
    if selected_account_code:
        bank_data_qs = bank_data_qs.filter(account_code=selected_account_code)

    # 既にconnected_numberがあるものを除外（連携済は除く）
    bank_data_qs = bank_data_qs.filter(
        Q(connected_number__isnull=True) | Q(connected_number='')
    )

    # 月初残高
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

    # DateRangeのリスト
    if selected_daterange:
        date_ranges = DateRange.objects.filter(id__lte=selected_daterange.id)
    else:
        date_ranges = DateRange.objects.all()

    # 予算データをループしながら集計
    budget_data = {}
    tmp_prev_balance = prev_balance

    for dr in date_ranges:
        items_insales = budgets_qs.filter(daterange=dr, itemtype="工事金入金")
        items_inregular = budgets_qs.filter(daterange=dr, itemtype="その他入金")
        items_auto = budgets_qs.filter(daterange=dr, itemtype="自動引落")
        items_individual = budgets_qs.filter(daterange=dr, itemtype="個別支払")
        items_fundtrans = budgets_qs.filter(daterange=dr, itemtype="預金振替")

        income_sales_total = sum(i.amount for i in items_insales)
        income_regular_total = sum(i.amount for i in items_inregular)
        total_income = income_sales_total + income_regular_total
        expense_auto_total = sum(i.amount for i in items_auto)
        expense_individual_total = sum(i.amount for i in items_individual)
        total_expense = expense_auto_total + expense_individual_total
        total_fundtrans = sum(i.amount for i in items_fundtrans)
        new_balance = tmp_prev_balance + total_income - total_expense + total_fundtrans

        budget_data[dr] = {
            "items": {
                "工事金入金": items_insales.order_by('sort_no1', 'sort_no2'),                
                "その他入金": items_inregular.order_by('sort_no1', 'sort_no2'),
                "自動引落": items_auto.order_by('sort_no1', 'sort_no2'),
                "個別支払": items_individual.order_by('sort_no1', 'sort_no2'),
                "預金振替": items_fundtrans.order_by('sort_no1', 'sort_no2'),
            },
            "income_sales": income_sales_total,
            "income_regular": income_regular_total,
            "total_income": total_income,
            "expense_auto_total": expense_auto_total,
            "expense_individual_total": expense_individual_total,
            "total_expense": total_expense,
            "total_fundtrans": total_fundtrans,
            "prev_balance": tmp_prev_balance,
            "new_balance": new_balance,
        }
        tmp_prev_balance = new_balance

    date_ranges_all = DateRange.objects.all().order_by('start_day')

    context = {
        "initial_prev_balance": prev_balance,
        "budget_data": budget_data,
        "bank_data": bank_data_qs,
        "year_month": selected_year_month,
        "selected_account_code": selected_account_code,
        "account_codes": AccountCode.objects.all(),
        "user_settings": user_settings,
        "date_ranges_all": date_ranges_all,
        "amount_fundtrans": amount_fundtrans,
    }
    return render(request, 'addbudget.html', context)


@login_required
def addbudget_item(request):
    """
    Ajaxでのドラッグ&ドロップ時:
      1) Budget を新規作成
      2) BankData と連携(connected_number付与)
    """
    if request.method == "POST":
        try:
            # -------------------------
            # 1) ユーザー設定を取得
            # -------------------------
            # ユーザーの user_code を取得
            user = request.user
            user_settings = UserSettings.objects.get(user=user)
            user_codename = user_settings.codename
            year_month =  user_settings.year_month

            data = json.loads(request.body)
            item_id = data.get("item_id")            # 画面で "bank_id" と同じ
            item_name = data.get("item_name", "")
            amount = int(data.get("amount", 0))
            day_num = int(data.get("day_num", 0))

            # 月をまたいだ未処理があった場合
            if day_num > user_settings.end_day:
                day_num = user_settings.end_day

            daterange_id = int(data.get("daterange_id", 0))
            itemtype_key = data.get("itemtype", "income")
            #///
            #year_month = data.get("year_month", datetime.today().strftime('%Y%m'))
            #///
            account_code_id = data.get("account_code_id")
            from_dragdrop = data.get("from_dragdrop", False)
            bank_id = data.get("bank_id")  # BankDataの主キー

            # DateRangeオブジェクト
            dr_obj = DateRange.objects.get(id=daterange_id)

            # 口座コード
            ac_obj = None
            if account_code_id:
                try:
                    ac_obj = AccountCode.objects.get(id=account_code_id)
                except AccountCode.DoesNotExist:
                    pass

            # itemtype を 'income'→'入金' 等に変換
            itemtype_str = convert_itemtype(itemtype_key)




            # item_name の前に user_code を追加
            item_name = f"[{user_codename}]{item_name}" if user_codename else item_name


            # (1) Budgetレコード新規作成 (まだ connected_number は付けない)
            new_budget = Budget.objects.create(
                daterange=dr_obj,
                itemtype=itemtype_str,
                item_name=item_name,
                amount=amount,
                #default_amount=0,
                #actual=True,
                year_month=year_month,
                account_code=ac_obj,
                sort_no1=day_num,
                sort_no2=0,
                connected_number=None
            )

            # (2) BankData と連携
            if from_dragdrop:
                # BankData取得
                try:
                    bank_obj = BankData.objects.get(pk=bank_id)
                except BankData.DoesNotExist:
                    return JsonResponse({"status": "error", "message": "指定の銀行データが見つかりません"})

                # UUIDで連結番号生成 (先頭8桁など)
                connect_number = str(uuid.uuid4())[:8]

                # Connectテーブルを作り、そこに BankData & Budget の関係をConnectDetailで保存
                connect_obj = Connect.objects.create(connect_number=connect_number)

                # BankData更新
                bank_obj.connected_number = connect_number
                bank_obj.save()

                # Budget更新
                new_budget.connected_number = connect_number
                new_budget.save()

                # ConnectDetail
                ConnectDetail.objects.create(connect=connect_obj, bank_data=bank_obj)
                ConnectDetail.objects.create(connect=connect_obj, budget_data=new_budget)

                msg = "Budget新規作成 & BankData連携完了"
            else:
                msg = "Budget新規作成(連携なし)"

            return JsonResponse({"status": "success", "message": msg})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "無効なリクエスト"})


from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

@login_required
@csrf_exempt  # 必要に応じてCSRFチェックを無効化
def unlink_connection(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            connected_number = data.get("connected_number")

            # 連結情報を取得
            connect = Connect.objects.filter(connect_number=connected_number).first()
            if not connect:
                return JsonResponse({"status": "error", "message": "連結情報が見つかりません"})

            with transaction.atomic():
                # 関連するBudgetとBankDataを解除
                Budget.objects.filter(connected_number=connected_number).update(connected_number=None)
                BankData.objects.filter(connected_number=connected_number).update(connected_number=None)

                # ConnectDetailも削除
                ConnectDetail.objects.filter(connect=connect).delete()

                # Connect自体も削除
                connect.delete()

            return JsonResponse({"status": "success", "message": "連結解除完了"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "無効なリクエスト"})
