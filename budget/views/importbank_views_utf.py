# myapp/views.py
import hashlib
import csv
from datetime import datetime
from django.shortcuts import render, redirect
from budget.models import BankData, AccountCode
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

def importbank(request):
    # 1. bank_id 生成関数 (ハッシュ値のみ生成, 連番なし)
    def generate_bank_id(date, item_name, amount):
        base_data_str = f"{date}{item_name}{amount}"
        return hashlib.sha256(base_data_str.encode()).hexdigest()

    # 2. AccountCode 取得/作成関数 (変更なし)
    def get_or_create_account_code(bank_name, branch_name, account_number, deposit_type):
        try:
            account_code = AccountCode.objects.get(
                bank_code=bank_name,
                deposit_type=deposit_type,
                account_number=account_number,
            )
        except AccountCode.DoesNotExist:
            account_code = AccountCode.objects.create(
                bank_code=bank_name,
                deposit_type=deposit_type,
                account_number=account_number,
            )
        return account_code

    # 3. データ取り込み関数
    if request.method == 'POST' and request.FILES['data_file']:
        data_file = request.FILES['data_file']

        if not data_file.name.endswith('.csv'):
            messages.error(request, "エラー:csvファイルをアップロードしてください。")
            return HttpResponseRedirect(reverse('importbank'))

        file_content = data_file.read().decode('utf-8')
        lines = file_content.splitlines()
        reader = csv.reader(lines)
        next(reader)  # ヘッダーを読み飛ばす

        # 既存データの bank_id を取得 (重複チェック用)
        existing_bank_ids = set(BankData.objects.values_list('bank_id', flat=True))

        added_count = 0
        skipped_count = 0

        for row in reader:
            date_str, bank_name, branch_name, deposit_type, account_number, item_name, memo, withdrawal, deposit, balance = row
            date = datetime.strptime(date_str, '%Y年%m月%d日').date()
            amount = int(withdrawal.replace('"', '').replace('\\', '').replace(',', '')) if withdrawal else int(deposit.replace('"', '').replace('\\', '').replace(',', ''))
            transaction_type = "出金" if withdrawal else "入金"

            bank_id = generate_bank_id(date, item_name, amount)  # ハッシュ値を生成

            # 重複チェック: 既存の bank_id と一致するか確認
            if bank_id in existing_bank_ids:
                print(f"Skipping existing data: {row} (bank_id: {bank_id})")
                skipped_count += 1
                continue  # 重複データはスキップ

            bank_name = bank_name.replace('【法人】', '')
            deposit_type = "当座" if deposit_type == "当座" else "その他"
            account_code = get_or_create_account_code(bank_name, branch_name, account_number, deposit_type)

            BankData.objects.create(
                bank_id=bank_id,
                date=date,
                item_name=item_name,
                amount=amount,
                transaction_type=transaction_type,
                account_code=account_code,
            )
            added_count += 1
        messages.success(request, f"{added_count}件のデータを追加しました")
        if skipped_count > 0:
             messages.warning(request, f"{skipped_count}件の重複データが見つかりました")

        return redirect("importbank")

    return render(request, 'importbank.html')