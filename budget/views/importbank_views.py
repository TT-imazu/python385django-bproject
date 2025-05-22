# myapp/views.py
import hashlib
import csv
from datetime import datetime
from django.shortcuts import render, redirect
from budget.models import BankData, AccountCode
from django.contrib import messages
from django.utils.dateparse import parse_date

def importbank(request):
    # 1. bank_id 生成関数 (連番を含めてハッシュ化)
    def generate_bank_id(date, item_name, amount, account_code_str, no):
        data_str = f"{date}{item_name}{amount}{account_code_str}{no}"
        return hashlib.sha256(data_str.encode()).hexdigest()

    # 2. AccountCode 取得/作成関数
    def get_or_create_account_code(bank_name, branch_name, account_number, deposit_type):
        # 銀行コードのマッピング
        bank_code_mapping = {
            'もみじ銀行': 'momiji',
            '広島銀行': 'hiroshima',
            '三菱UFJ銀行': 'mufj',
            '山陰合同銀行': 'sanin',
            '中国銀行': 'chugoku',
        }
        
        # 銀行名から正しい銀行コードを取得
        base_bank_code = bank_code_mapping.get(bank_name)
        if not base_bank_code:
            raise ValueError(f"未知の銀行名です: {bank_name}")
        
        # 口座種別のコード化
        deposit_code = "1" if deposit_type == "当座" else "2"
        
        # 完全な口座コードの生成（例：momiji_1_123456）
        full_bank_code = f"{base_bank_code}_{deposit_code}_{account_number}"
        
        try:
            account_code = AccountCode.objects.get(
                bank_code=full_bank_code,
                deposit_type=deposit_type,
                account_number=account_number,
            )
        except AccountCode.DoesNotExist:
            account_code = AccountCode.objects.create(
                bank_code=full_bank_code,
                deposit_type=deposit_type,
                account_number=account_number,
            )
        return account_code

    # 3. データ取り込み関数
    if request.method == 'POST' and request.FILES['data_file']:
        data_file = request.FILES['data_file']

        if not data_file.name.endswith('.csv'):
            messages.error(request, "エラー:csvファイルをアップロードしてください。")
            return redirect("importbank")

        file_content = data_file.read().decode('shift_jis')  # または 'cp932'
        lines = file_content.splitlines()
        reader = csv.reader(lines)
        next(reader)  # ヘッダーを読み飛ばす

        # 既存データの bank_id を取得 (DB との重複チェック用)
        existing_bank_ids_db = set(BankData.objects.values_list('bank_id', flat=True))
        # 読み込みデータ内での重複をカウントするための辞書
        duplicate_counts = {}  # キー: (date, item_name, amount, account_code), 値: 出現回数

        added_count = 0
        skipped_count = 0

        for row in reader:
            date_str, bank_name, branch_name, deposit_type, account_number, item_name, memo, withdrawal, deposit, balance = row
            date = datetime.strptime(date_str, '%Y年%m月%d日').date()
            amount = int(withdrawal.replace('"', '').replace('\\', '').replace(',', '')) if withdrawal else int(deposit.replace('"', '').replace('\\', '').replace(',', ''))
            transaction_type = "出金" if withdrawal else "入金"

            bank_name = bank_name.replace('【法人】', '')
            deposit_type = "当座" if deposit_type == "当座" else "その他"
            account_code_obj = get_or_create_account_code(bank_name, branch_name, account_number, deposit_type)
            account_code_str = str(account_code_obj)

            # data.txt 内での重複カウントと連番の初期値を決定
            base_data_tuple = (date, item_name, amount, account_code_str)  # タプルにする
            if base_data_tuple in duplicate_counts:
                duplicate_counts[base_data_tuple] += 1
            else:
                duplicate_counts[base_data_tuple] = 0  # 初期値は 0
            no = duplicate_counts[base_data_tuple]

            # bank_id 生成 (連番を含めてハッシュ化)
            bank_id = generate_bank_id(date, item_name, amount, account_code_str, no)

            # 重複チェック: 既存の bank_id と一致するか確認(DB)
            if bank_id in existing_bank_ids_db:
                print(f"Skipping existing data: {row} (bank_id: {bank_id})")
                skipped_count += 1
                continue  # 重複データはスキップ

            BankData.objects.create(
                bank_id=bank_id,
                date=date,
                item_name=item_name,
                amount=amount,
                transaction_type=transaction_type,
                account_code=account_code_obj,
            )
            added_count += 1

        # メッセージを追加
        if added_count > 0:
            messages.success(request, f"{added_count} 件のデータを追加しました。")
        if skipped_count > 0:
            messages.warning(request, f"{skipped_count} 件の重複データが見つかりました (スキップしました)。")

        return redirect("importbank")

    return render(request, 'budget/importbank.html')