import json, uuid
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from budget.models import (
    Budget, DateRange, BankData,
    Connect, ConnectDetail
)

def connectbank(request):
    """
    メイン画面: 予算データ + 銀行データ + 連結テーブル
    """
    date_ranges = DateRange.objects.all().order_by('id')
    budget_data = {}
    prev_balance = 50000

    # 銀行データをDBから取得 (例: 全件)
    bank_data = BankData.objects.all().order_by('date')

    if request.method == 'POST':
        # 1) 予算データの更新処理(既存行)
        for key, value in request.POST.items():
            if key.startswith('default_amount_') and not key.endswith('_new'):
                try:
                    item_id = int(key.split('_')[-1])
                    budget_item = Budget.objects.get(id=item_id)
                    budget_item.amount = int(value)
                    budget_item.save()
                except (ValueError, Budget.DoesNotExist):
                    pass

        # 2) 新規追加分の処理
        for dr in date_ranges:
            for item_type in ['income', 'auto', 'individual']:
                item_name_key = f'item_name_{dr.id}_{item_type}_new'
                default_amount_key = f'default_amount_{dr.id}_{item_type}_new'
                itemtype_key = f'itemtype_{dr.id}_{item_type}_new'
                daterange_key = f'daterange_{dr.id}_{item_type}_new'
                actual_key = f'actual_{dr.id}_{item_type}_new'

                if item_name_key in request.POST:
                    item_name = request.POST.get(item_name_key)
                    default_amount_str = request.POST.get(default_amount_key, '0')
                    itemtype_str = request.POST.get(itemtype_key)
                    daterange_id = request.POST.get(daterange_key)
                    actual = (request.POST.get(actual_key) == "True")

                    try:
                        default_amount = int(default_amount_str)
                        dr_obj = DateRange.objects.get(id=daterange_id)
                        Budget.objects.create(
                            daterange=dr_obj,
                            itemtype=itemtype_str,
                            item_name=item_name,
                            default_amount=default_amount,
                            actual=actual,
                            amount=default_amount
                        )
                    except (ValueError, DateRange.DoesNotExist):
                        pass

        return redirect('connectbank')

    # 画面表示用データの構築
    for dr in date_ranges:
        items_in = Budget.objects.filter(daterange=dr, itemtype="入金")
        items_auto = Budget.objects.filter(daterange=dr, itemtype="自動引落")
        items_individual = Budget.objects.filter(daterange=dr, itemtype="個別支払")

        income_total = sum(i.amount for i in items_in)
        expense_auto_total = sum(i.amount for i in items_auto)
        expense_individual_total = sum(i.amount for i in items_individual)
        total_expense = expense_auto_total + expense_individual_total
        new_balance = prev_balance + income_total - total_expense

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
            "prev_balance": prev_balance,
            "new_balance": new_balance,
        }
        prev_balance = new_balance

    return render(request, 'connectbank.html', {
        "budget_data": budget_data,
        "bank_data": bank_data
    })


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
