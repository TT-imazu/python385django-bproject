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
    codename = models.CharField(max_length=8, default="")
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


class BaseBudget(models.Model):
    ITEM_TYPE_CHOICES = [
        ("その他入金", "その他入金"),
        ("自動引落", "自動引落"),
        ("個別支払", "個別支払"),
    ]
    daterange = models.ForeignKey(DateRange, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=100)
    itemtype = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES, default="入金")
    amount = models.IntegerField(default=0)  # 基本金額
    specific_month = models.PositiveSmallIntegerField(
        default=99, verbose_name="発生月 (99=毎月, 他=単月)"
    )
    account_code = models.ForeignKey(
        'AccountCode', on_delete=models.SET_NULL, null=True, blank=True
    )

    # --- 追加: 並べ替え用フィールド ---
    sort_no1 = models.PositiveSmallIntegerField(default=0, verbose_name="並べ替え（日付）")
    sort_no2 = models.PositiveSmallIntegerField(default=0, verbose_name="並べ替え（自由）")

    @classmethod
    def generate_budgets_for_month(cls, year, month):
        """
        指定した年月 (YYYYMM) に基づいて `BaseBudget` から `Budget` を作成する。
        - `specific_month == 99` の場合は「毎月」扱い
        - `specific_month == month` の場合は単月作成
        """
        budgets = []
        for base_budget in cls.objects.filter(
            models.Q(specific_month=99) | models.Q(specific_month=month)
        ):
            budget = Budget.objects.create(
                base_budget=base_budget,
                daterange=base_budget.daterange,
                item_name=base_budget.item_name,
                itemtype=base_budget.itemtype,
                amount=base_budget.amount,
                #default_amount=base_budget.amount,
                year_month=f"{year}{month:02d}",
                account_code=base_budget.account_code,
                sort_no1=base_budget.sort_no1,
                sort_no2=base_budget.sort_no2,
            )
            budgets.append(budget)
        return budgets

    def update_actual_amount(self, year, month):
        """
        `Budget` から `BaseBudget` に指定年・月の実績金額をフィードバックする
        """
        # base_budget=self の Budget のうち、対象年月が合致するものを合計
        if self.specific_month == 99 or self.specific_month == month:
            total_actual_amount = Budget.objects.filter(
                base_budget=self, year_month=f"{year}{month:02d}"
            ).aggregate(models.Sum("amount"))["amount__sum"] or 0

            self.amount = total_actual_amount
            self.save()

    @classmethod
    def update_actual_amounts_for_month(cls, year, month):
        """
        一度に、対象となる全ての BaseBudget の実績金額を反映するクラスメソッド。
        
        - specific_month == 99 (毎月) または == month (指定月) が対象
        - 上記に該当する全 BaseBudget について、Budget の合計を取得して amount に反映する
        """
        # 対象となる BaseBudget を一度に取得
        base_budgets = cls.objects.filter(
            models.Q(specific_month=99) | models.Q(specific_month=month)
        )

        for base_budget in base_budgets:
            total_actual_amount = Budget.objects.filter(
                base_budget=base_budget, year_month=f"{year}{month:02d}"
            ).aggregate(models.Sum("amount"))["amount__sum"] or 0

            # 合計金額をフィードバック
            base_budget.amount = total_actual_amount
            base_budget.save()



class Budget(models.Model):
    ITEM_TYPE_CHOICES = [
        ("工事金入金", "工事金入金"),
        ("その他入金", "その他入金"),
        ("自動引落", "自動引落"),
        ("個別支払", "個別支払"),
        ("預金振替", "預金振替"),
    ]

    base_budget = models.ForeignKey(
        BaseBudget,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="budget_entries",
    )

    daterange = models.ForeignKey(DateRange, on_delete=models.CASCADE)
    itemtype = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES, default="工事金入金")
    item_name = models.CharField(max_length=100)
    amount = models.IntegerField(default=0)         # 表示金額(実際)
    #default_amount = models.IntegerField(default=0) # 見込金額
    #actual = models.BooleanField(default=False)     # True=実際金額
    connected_number = models.CharField(max_length=20, blank=True, null=True)
    account_code = models.ForeignKey(
        AccountCode, on_delete=models.SET_NULL, null=True, blank=True
    )
    year_month = models.CharField(max_length=6, blank=True, null=True)

    # --- 追加: 並べ替え用フィールド ---
    sort_no1 = models.PositiveSmallIntegerField(default=0, verbose_name="並べ替え1（日付）")
    sort_no2 = models.PositiveSmallIntegerField(default=0, verbose_name="並べ替え2（自由）")
    confirm = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.daterange} - {self.item_name} ({self.itemtype})"

    #@property
    #def transaction_type(self):
    #    """連結用の区分: 入金/出金"""
    #    return "入金" if self.itemtype == "入金" else "出金"
    @property
    def transaction_type(self):
        """ 
        取引区分を返す:
        - 工事金入金, その他入金 → "入金"
        - 自動引落, 個別支払 → "出金"
        - 預金振替 → "振替"
        """
        if self.itemtype in ["工事金入金", "その他入金"]:
            return "入金"
        elif self.itemtype in ["自動引落", "個別支払"]:
            return "出金"
        elif self.itemtype == "預金振替":
            return "預金振替"
        return "不明"  # 予期しない値が入った場合のフォールバック


class BankData(models.Model):
    bank_id = models.CharField(max_length=64, primary_key=True)
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
