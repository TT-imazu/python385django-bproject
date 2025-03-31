from django.shortcuts import render, redirect
from django.contrib import messages
from budget.models import BaseBudget, Budget
from budget.forms import BudgetGenerationForm

def generatebudget(request):
    if request.method == "POST":
        form = BudgetGenerationForm(request.POST)
        if form.is_valid():
            year_month = form.cleaned_data["year_month"]
            year, month = year_month[:4], int(year_month[4:])  # YYYYMM から年と月を取得

            # BaseBudget から該当月の Budget を作成
            created_budgets = BaseBudget.generate_budgets_for_month(int(year), month)

            messages.success(request, f"{len(created_budgets)} 件の Budget データを作成しました。")
            return redirect("generatebudget")
    else:
        form = BudgetGenerationForm()

    return render(request, "generatebudget.html", {"form": form})
