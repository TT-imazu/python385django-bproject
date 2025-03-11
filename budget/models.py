# models.py
from django.db import models
from django.contrib.auth.models import User

class AccountCode(models.Model):
    bank_code = models.CharField(max_length=10)
    deposit_type = models.CharField(max_length=50)
    account_number = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.bank_code} / {self.deposit_type} / {self.account_number}"


class AccountBalance(models.Model):
    account_code = models.ForeignKey(AccountCode, on_delete=models.CASCADE)
    year_month = models.CharField(max_length=6)
    beginning_balance = models.IntegerField()

    def __str__(self):
        return f"{self.account_code} - {self.year_month} : {self.beginning_balance}"


class DateRange(models.Model):
    """
    予算データの期間 (例: '1～9日', '10～19日' 等) を表す。
    start_day = 1, end_day = 9 なら「1日～9日」を意味する
    """
    name = models.CharField(max_length=50)
    start_day = models.PositiveSmallIntegerField(default=1, verbose_name="開始日")
    end_day = models.PositiveSmallIntegerField(default=1, verbose_name="終了日")

    def __str__(self):
        return f"{self.name} ({self.start_day}～{self.end_day}日)"


class UserSettings(models.Model):
    """
    Userが選択中の年月/口座/期間等を保持
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    year_month = models.CharField(max_length=6, default="", verbose_name="選択中の年月")
    selected_account_code = models.ForeignKey(
        'AccountCode', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="選択口座コード"
    )
    # ★ 追加: DateRangeも選択できるようにする
    selected_daterange = models.ForeignKey(
        DateRange, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="選択中の期間"
    )
    
    end_day = models.IntegerField(default=0, verbose_name="選択中の日付")
    connectflag = models.BooleanField(default=False, verbose_name="選択中の連携区分")     # True=実際金額

    def __str__(self):
        return f"{self.user.username} - {self.year_month} - {self.selected_account_code} - {self.selected_daterange}"




class Budget(models.Model):
    ITEM_TYPE_CHOICES = [
        ("入金", "入金"),
        ("自動引落", "自動引落"),
        ("個別支払", "個別支払"),
    ]
    daterange = models.ForeignKey(DateRange, on_delete=models.CASCADE)
    itemtype = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES, default="入金")
    item_name = models.CharField(max_length=100)
    amount = models.IntegerField(default=0)         # 表示金額(実際)
    default_amount = models.IntegerField(default=0) # 見込金額
    actual = models.BooleanField(default=False)     # True=実際金額
    connected_number = models.CharField(max_length=20, blank=True, null=True)
    account_code = models.ForeignKey(
        AccountCode, on_delete=models.SET_NULL, null=True, blank=True
    )
    year_month = models.CharField(max_length=6, blank=True, null=True)

    # --- 追加: 並べ替え用フィールド ---
    sort_no1 = models.PositiveSmallIntegerField(default=0, verbose_name="並べ替え1（2桁）")
    sort_no2 = models.PositiveSmallIntegerField(default=0, verbose_name="並べ替え2（3桁）")

    def __str__(self):
        return f"{self.daterange} - {self.item_name} ({self.itemtype})"

    @property
    def transaction_type(self):
        """連結用の区分: 入金/出金"""
        return "入金" if self.itemtype == "入金" else "出金"


class BankData(models.Model):
    bank_id = models.CharField(max_length=50, primary_key=True)
    date = models.DateField()
    item_name = models.CharField(max_length=100)
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=10)
    connected_number = models.CharField(max_length=20, blank=True, null=True)
    account_code = models.ForeignKey(
        AccountCode, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.date} {self.item_name} {self.amount}"


class Connect(models.Model):
    connect_number = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"連結番号: {self.connect_number}"


class ConnectDetail(models.Model):
    connect = models.ForeignKey(Connect, on_delete=models.CASCADE)
    bank_data = models.ForeignKey(BankData, on_delete=models.CASCADE, null=True, blank=True)
    budget_data = models.ForeignKey(Budget, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        if self.bank_data:
            return f"{self.connect.connect_number} - Bank:{self.bank_data.bank_id}"
        elif self.budget_data:
            return f"{self.connect.connect_number} - Budget:{self.budget_data.id}"
        return f"{self.connect.connect_number}"
