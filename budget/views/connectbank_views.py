import json, uuid
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
import calendar
from django.contrib.auth.decorators import login_required

from budget.models import (
    Budget, DateRange, BankData,
    Connect, ConnectDetail
)

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
def connectbank(request):
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

        return redirect('connectbank')

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
    return render(request, 'budget/connectbank.html', context)


@csrf_exempt
def connect_connectbank(request):
    """
    連結処理 (AJAX想定)
    合計金額が一致し、かつ「入金は入金のみ」「出金は出金のみ」で連結
    """
    if request.method == 'POST':
        payload = json.loads(request.body)
        connect_items = payload.get('connect_items', [])
        # connect_items = [
        #   {"id": "...", "amount": 1000, "type": "入金/出金", "source": "bank/budget"},
        #   ...
        # ]

        if not connect_items:
            return JsonResponse({'success': False, 'message': 'データがありません'}, status=400)
        
        # チェック機能の追加
        for item in connect_items:
            if item['source'] == 'bank':
                bank_item = BankData.objects.filter(pk=item['id'], connected_number__isnull=False).first()
                if bank_item:
                    return JsonResponse({'success': False, 'message': f'銀行データ {bank_item.item_name} は既に連結されています'}, status=400)
            else:
                budget_item = Budget.objects.filter(pk=item['id'], connected_number__isnull=False).first()
                if budget_item:
                    return JsonResponse({'success': False, 'message': f'予算データ {budget_item.item_name} は既に連結されています'}, status=400)



        # Bank側とBudget側で分割して金額チェック
        bank_list = [x for x in connect_items if x['source'] == 'bank']
        budget_list = [x for x in connect_items if x['source'] == 'budget']

        if not bank_list or not budget_list:
            # 片側だけだと「合計金額が一致」とは言えないのでエラー
            return JsonResponse({
                'success': False,
                'message': '銀行データと予算データの両方を選択してください'
            }, status=400)

        # それぞれのtype(入金/出金)が統一されているか確認
        # 銀行データは全行同じtransaction_typeか？
        bank_type = bank_list[0]['type']
        if any(x['type'] != bank_type for x in bank_list):
            return JsonResponse({
                'success': False,
                'message': '銀行データ内で入金・出金が混在しています'
            }, status=400)

        # 予算データも同様
        budget_type = budget_list[0]['type']
        if any(x['type'] != budget_type for x in budget_list):
            return JsonResponse({
                'success': False,
                'message': '予算データ内で入金・出金が混在しています'
            }, status=400)

        # 「入金」と「出金」が混在していないか (銀行側と予算側で一致が必要)
        if bank_type != budget_type:
            return JsonResponse({
                'success': False,
                'message': '出金と入金を連結することはできません'
            }, status=400)

        sum_bank = sum(x['amount'] for x in bank_list)
        sum_budget = sum(x['amount'] for x in budget_list)
        if sum_bank != sum_budget:
            return JsonResponse({
                'success': False,
                'message': f'合計金額が一致しません (銀行側:{sum_bank} / 予算側:{sum_budget})'
            }, status=400)

        # ここまで通れば連結可能
        connect_number = str(uuid.uuid4())[:8]  # 連結番号を発行
        connect_obj = Connect.objects.create(connect_number=connect_number)

        # 連結明細登録 & 各データに connected_number を付与
        for item in connect_items:
            if item['source'] == 'bank':
                try:
                    bank_item = BankData.objects.get(pk=item['id'])
                    if bank_item.connected_number:
                        # すでに連結されているならスキップ or エラー
                        continue
                    bank_item.connected_number = connect_number
                    bank_item.save()
                    ConnectDetail.objects.create(
                        connect=connect_obj,
                        bank_data=bank_item
                    )
                except BankData.DoesNotExist:
                    pass
            else:
                try:
                    budget_item = Budget.objects.get(id=item['id'])
                    if budget_item.connected_number:
                        # すでに連結されているならスキップ or エラー
                        continue
                    budget_item.connected_number = connect_number
                    budget_item.save()
                    ConnectDetail.objects.create(
                        connect=connect_obj,
                        budget_data=budget_item
                    )
                except Budget.DoesNotExist:
                    pass

        return JsonResponse({
            'success': True,
            'connect_number': connect_number,
            'message': '連結が完了しました'
        })
    return JsonResponse({'success': False}, status=400)


@login_required
@csrf_exempt
def toggle_confirm_status(request, item_id):
    if request.method == 'POST':
        try:
            budget_item = Budget.objects.get(pk=item_id)
            budget_item.confirm = not budget_item.confirm
            budget_item.save()
            return JsonResponse({'success': True, 'new_status': budget_item.confirm})
        except Budget.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Budget item not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


@csrf_exempt
def delete_connectbank(request):
    """
    連結削除 (AJAX想定)
    """
    if request.method == 'POST':
        body = json.loads(request.body)
        conn_number = body.get('connect_number')
        if not conn_number:
            return JsonResponse({'success': False, 'message': '連結番号がありません'}, status=400)

        try:
            connect_obj = Connect.objects.get(connect_number=conn_number)
        except Connect.DoesNotExist:
            return JsonResponse({'success': False, 'message': '連結番号が存在しません'}, status=404)

        details = ConnectDetail.objects.filter(connect=connect_obj)
        for detail in details:
            if detail.bank_data:
                detail.bank_data.connected_number = None
                detail.bank_data.save()
            if detail.budget_data:
                detail.budget_data.connected_number = None
                detail.budget_data.save()
        details.delete()
        connect_obj.delete()

        return JsonResponse({'success': True, 'message': '連結を解除しました'})

    return JsonResponse({'success': False}, status=400)
