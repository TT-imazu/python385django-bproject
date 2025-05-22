# views.py
import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect

from budget.models import (
    Budget, DateRange, BankData,BaseBudget,
    Connect, ConnectDetail, UserSettings,
    AccountCode, AccountBalance,
)

def download_budget(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="budget_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'item_name', 'itemtype', 'amount', 'specific_month',
        'daterange_id', 'account_code_id', 'sort_no1', 'sort_no2'
    ])

    # 最新の年月や条件で絞りたい場合はここをカスタマイズ
    for budget in Budget.objects.all():
        writer.writerow([
            budget.item_name,
            budget.itemtype,
            budget.amount,
            99,  # 既存Budgetに発生月はないので「毎月」として扱う
            budget.daterange.id if budget.daterange else '',
            budget.account_code.id if budget.account_code else '',
            budget.sort_no1,
            budget.sort_no2,
        ])

    return response


import io
from budget.forms import CSVUploadForm

def upload_basebudget(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['file']
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            for row in reader:
                BaseBudget.objects.create(
                    item_name=row['item_name'],
                    itemtype=row['itemtype'],
                    amount=int(row['amount']),
                    specific_month=int(row['specific_month']),
                    daterange=DateRange.objects.get(id=row['daterange_id']),
                    account_code=AccountCode.objects.get(id=row['account_code_id']),
                    sort_no1=int(row.get('sort_no1', 0)),
                    sort_no2=int(row.get('sort_no2', 0)),
                )
            return redirect('success_page')  # 完了ページや元画面へ
    else:
        form = CSVUploadForm()
    return render(request, 'budget/upload_basebudget.html', {'form': form})


def upload_success(request):
    return render(request, 'budget/upload_success.html')
