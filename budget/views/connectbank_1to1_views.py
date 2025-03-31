import json
import uuid
import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.contrib.auth.decorators import login_required

# models.py 側で使う想定
from budget.models import (
    Budget, BankData, Connect, ConnectDetail,
    AccountCode, AccountBalance, DateRange, UserSettings
)

@login_required
def connectbank_1to1(request):
    """
    1) 画面表示 (予算と銀行を1画面に表示)
    2) 予算データ更新(POST) 
    3) ドラッグ＆ドロップは JS から connect_connectbank_1to1() に投げる
    """
    user = request.user

    # -------------------------------------------
    # 1) ユーザー設定 (同じロジックを使う例)
    # -------------------------------------------
    user_settings, _ = UserSettings.objects.get_or_create(
        user=user,
        defaults={
            'year_month': datetime.today().strftime('%Y%m'),
            'selected_account_code': None,
            'selected_daterange': None,
            'end_day': 0,
            'connectflag': False
        }
    )

    if request.method == 'POST':
        # 予算更新かどうかを判定
        if request.POST.get("update_budget") == "1":
            # (A) ユーザー設定の更新
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
            else:
                user_settings.selected_account_code = None

            new_daterange_id = request.POST.get('daterange_id')
            if new_daterange_id:
                try:
                    dr = DateRange.objects.get(pk=new_daterange_id)
                    user_settings.selected_daterange = dr
                except DateRange.DoesNotExist:
                    user_settings.selected_daterange = None
            else:
                user_settings.selected_daterange = None

            new_end_day = request.POST.get('end_day')
            if new_end_day:
                try:
                    user_settings.end_day = int(new_end_day)
                except ValueError:
                    user_settings.end_day = 0
            else:
                user_settings.end_day = 0

            new_connectflag = request.POST.get('connectflag')
            user_settings.connectflag = bool(new_connectflag)

            user_settings.save()

            # (B) 既存予算レコードの更新
            for key, value in request.POST.items():
                # 例: amount_123 → Budget.id=123 のamount更新
                if key.startswith('amount_'):
                    budget_id_str = key.split('_')[-1]
                    try:
                        budget_id = int(budget_id_str)
                        b = Budget.objects.get(pk=budget_id)
                        b.amount = int(value or 0)
                        b.save()
                    except (ValueError, Budget.DoesNotExist):
                        pass

                if key.startswith('sort_no1_'):
                    budget_id_str = key.replace('sort_no1_', '')
                    try:
                        budget_id = int(budget_id_str)
                        b = Budget.objects.get(pk=budget_id)
                        b.sort_no1 = int(value or 0)
                        b.save()
                    except (ValueError, Budget.DoesNotExist):
                        pass

                if key.startswith('sort_no2_'):
                    budget_id_str = key.replace('sort_no2_', '')
                    try:
                        budget_id = int(budget_id_str)
                        b = Budget.objects.get(pk=budget_id)
                        b.sort_no2 = int(value or 0)
                        b.save()
                    except (ValueError, Budget.DoesNotExist):
                        pass

                if key.startswith('item_name_'):
                    budget_id_str = key.replace('item_name_', '')
                    try:
                        budget_id = int(budget_id_str)
                        b = Budget.objects.get(pk=budget_id)
                        b.item_name = value
                        b.save()
                    except (ValueError, Budget.DoesNotExist):
                        pass

            return redirect('connectbank_1to1')
        else:
            # 通常のユーザー設定変更POST (update_budget=なし)
            new_year_month = request.POST.get('year_month')
            if new_year_month:
                user_settings.year_month = new_year_month
            # ... 他の項目も同様に更新 ...
            user_settings.save()
            return redirect('connectbank_1to1')

    # -------------------------------------------
    # 2) 表示用データを用意
    # -------------------------------------------
    selected_year_month = user_settings.year_month
    selected_account_code = user_settings.selected_account_code
    selected_daterange = user_settings.selected_daterange
    selected_end_day = user_settings.end_day
    selected_connectflag = user_settings.connectflag

    # 年月を数値化して日付範囲を作る
    year = int(selected_year_month[:4])
    month = int(selected_year_month[4:])
    start_day = 1
    if selected_daterange:
        end_day = selected_daterange.end_day
        if end_day == 31:
            end_day = calendar.monthrange(year, month)[1]
    else:
        end_day = calendar.monthrange(year, month)[1]
    if selected_end_day > 0:
        end_day = selected_end_day

    start_date = date(year, month, start_day)
    end_date = date(year, month, end_day)

    # 1ヶ月前
    one_month_ago = start_date - relativedelta(months=1)

    # Budget絞り込み
    budgets_qs = Budget.objects.filter(year_month=selected_year_month)
    if selected_account_code:
        budgets_qs = budgets_qs.filter(account_code=selected_account_code)
    if selected_connectflag:
        budgets_qs = budgets_qs.filter(connected_number__isnull=False)
    # sort_no1 <= end_day
    if selected_end_day:
        budgets_qs = budgets_qs.filter(sort_no1__lte=selected_end_day)
    else:
        if selected_daterange:
            budgets_qs = budgets_qs.filter(daterange__id__lte=selected_daterange.id)
    budgets_qs = budgets_qs.order_by('sort_no1','sort_no2','id')

    # 銀行データ絞り込み
    bank_qs = BankData.objects.filter(date__range=[one_month_ago, end_date])
    if selected_account_code:
        bank_qs = bank_qs.filter(account_code=selected_account_code)
    if selected_connectflag:
        bank_qs = bank_qs.filter(connected_number__isnull=False)
    else:
        # 連結済を含める場合でも良いが、わかりやすくするなら下記のように何もしない
        pass

    # 月初残高を取得
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

    # DateRange 一覧
    date_ranges_all = DateRange.objects.all().order_by('start_day')
    # 画面で表示するDateRangeを決める
    if selected_daterange:
        used_date_ranges = DateRange.objects.filter(id__lte=selected_daterange.id)
    else:
        used_date_ranges = DateRange.objects.all().order_by('start_day')

    # 予算の集計
    budget_data = {}
    tmp_prev_balance = prev_balance
    for dr in used_date_ranges:
        qs_dr = budgets_qs.filter(daterange=dr)
        items_by_type = {}
        # 種別をユニークに集めて仕分け
        all_types = qs_dr.values_list('itemtype', flat=True).distinct()
        for t in all_types:
            items_by_type[t] = qs_dr.filter(itemtype=t)

        # 入金合計などを計算(例)
        income_total = sum(x.amount for x in qs_dr if "入金" in x.itemtype)
        expense_total = sum(x.amount for x in qs_dr if "支払" in x.itemtype or "引落" in x.itemtype)
        fundtrans_total = sum(x.amount for x in qs_dr if "振替" in x.itemtype)
        # 新残高 = 前残 + 入金 - 出金 + 振替(独自ルール次第)
        new_bal = tmp_prev_balance + income_total - expense_total + fundtrans_total

        budget_data[dr] = {
            "items": items_by_type,
            "new_balance": new_bal,
        }
        tmp_prev_balance = new_bal

    context = {
        "user_settings": user_settings,
        "account_codes": AccountCode.objects.all(),
        "date_ranges_all": date_ranges_all,
        "budget_data": budget_data,
        "bank_data": bank_qs.order_by('date'),
        "initial_prev_balance": prev_balance,
    }
    return render(request, 'connectbank_1to1.html', context)

@csrf_exempt
@login_required
def connect_connectbank_1to1(request):
    """
    1対1連結のAJAX用エンドポイント
    - bank_id, budget_id を受け取り
    - 金額/種別の最終確認をして Connect / ConnectDetail を登録
    - 連結番号を付与
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        bank_id = data.get('bank_id')
        budget_id = data.get('budget_id')
        if not bank_id or not budget_id:
            return JsonResponse({'success': False, 'message': 'bank_idまたはbudget_idが指定されていません'}, status=400)

        try:
            bank_item = BankData.objects.get(pk=bank_id)
            budget_item = Budget.objects.get(pk=budget_id)
        except (BankData.DoesNotExist, Budget.DoesNotExist):
            return JsonResponse({'success': False, 'message': '該当データが見つかりません'}, status=404)

        # 既に連結済みか？
        if bank_item.connected_number:
            return JsonResponse({'success': False, 'message': '銀行データはすでに連結されています'}, status=400)
        if budget_item.connected_number:
            return JsonResponse({'success': False, 'message': '予算データはすでに連結されています'}, status=400)

        # (必要に応じて、金額・種別のサーバー側チェックを行ってもOK)
        # ここでは最小限とし、JS側でチェック済みと仮定

        # 連結番号を発行
        conn_number = str(uuid.uuid4())[:8]
        connect_obj = Connect.objects.create(connect_number=conn_number)

        # 銀行データに 連結番号をセット
        bank_item.connected_number = conn_number
        bank_item.save()

        # 予算データに 連結番号をセット
        budget_item.connected_number = conn_number
        budget_item.save()

        # ConnectDetail にも記録
        ConnectDetail.objects.create(connect=connect_obj, bank_data=bank_item)
        ConnectDetail.objects.create(connect=connect_obj, budget_data=budget_item)

        return JsonResponse({
            'success': True,
            'connect_number': conn_number,
            'message': '1対1連結が完了しました'
        })

    return JsonResponse({'success': False, 'message': 'POSTのみ対応'}, status=405)
