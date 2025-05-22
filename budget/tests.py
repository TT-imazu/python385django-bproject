from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from budget.models import Budget, AccountCode, DateRange, UserSettings
import json
from datetime import datetime

class BudgetConfirmFeatureTests(TestCase):

    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')

        # Create prerequisite objects
        self.account_code = AccountCode.objects.create(
            bank_code="001", deposit_type="普通", account_number="1234567"
        )
        self.date_range = DateRange.objects.create(name="月初", start_day=1, end_day=10)
        
        # UserSettings for connectbank view
        self.user_settings = UserSettings.objects.create(
            user=self.user,
            year_month=datetime.today().strftime('%Y%m'),
            selected_account_code=self.account_code,
            selected_daterange=self.date_range
        )

        # Create a budget item
        self.budget_item = Budget.objects.create(
            daterange=self.date_range,
            item_name="Test Income",
            itemtype="その他入金",
            amount=1000,
            year_month="202310",
            account_code=self.account_code,
            sort_no1=1,
            sort_no2=1
            # confirm defaults to False
        )

    def test_budget_model_confirm_field_default(self):
        """Test that the Budget model's 'confirm' field defaults to False."""
        budget = Budget.objects.get(id=self.budget_item.id)
        self.assertFalse(budget.confirm)

    def test_budget_model_confirm_field_can_be_changed(self):
        """Test that the 'confirm' field can be changed and saved."""
        budget = Budget.objects.get(id=self.budget_item.id)
        budget.confirm = True
        budget.save()
        
        updated_budget = Budget.objects.get(id=self.budget_item.id)
        self.assertTrue(updated_budget.confirm)

        updated_budget.confirm = False
        updated_budget.save()
        
        re_updated_budget = Budget.objects.get(id=self.budget_item.id)
        self.assertFalse(re_updated_budget.confirm)

    def test_toggle_confirm_status_view_success(self):
        """Test the toggle_confirm_status view for a successful toggle."""
        self.assertFalse(self.budget_item.confirm, "Initial confirm status should be False")

        url = reverse('toggle_confirm_status', args=[self.budget_item.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertTrue(response_data['new_status'])

        self.budget_item.refresh_from_db()
        self.assertTrue(self.budget_item.confirm, "Confirm status should be True after first toggle")

        # Toggle back
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertFalse(response_data['new_status'])

        self.budget_item.refresh_from_db()
        self.assertFalse(self.budget_item.confirm, "Confirm status should be False after second toggle")

    def test_toggle_confirm_status_view_invalid_item_id(self):
        """Test the toggle_confirm_status view with an invalid item_id."""
        invalid_id = self.budget_item.id + 999 # An ID that likely doesn't exist
        url = reverse('toggle_confirm_status', args=[invalid_id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 404)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['message'], 'Budget item not found')

    def test_toggle_confirm_status_view_requires_post(self):
        """Test that the toggle_confirm_status view requires a POST request."""
        url = reverse('toggle_confirm_status', args=[self.budget_item.id])
        response = self.client.get(url) # Using GET instead of POST
        
        self.assertEqual(response.status_code, 405) # Method Not Allowed
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['message'], 'Invalid request method')

    def test_connectbank_view_context_with_confirm_status(self):
        """Test that the connectbank view's context includes items with correct confirm status."""
        # Create another budget item with confirm explicitly set to True
        budget_item_confirmed = Budget.objects.create(
            daterange=self.date_range,
            item_name="Confirmed Expense",
            itemtype="自動引落",
            amount=500,
            year_month=self.user_settings.year_month, # Ensure it's for the current user_settings year_month
            account_code=self.account_code,
            confirm=True,
            sort_no1=2,
            sort_no2=1
        )
        
        # Update self.budget_item to use the same year_month as user_settings for consistency in this test
        self.budget_item.year_month = self.user_settings.year_month
        self.budget_item.save()

        url = reverse('connectbank')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Check context for budget_data
        # The structure of budget_data is {daterange_obj: {items: {itemtype: [budget_obj, ...]}}}
        # We need to find our items within this structure.
        
        found_item_default = False
        found_item_confirmed = False
        
        context_budget_data = response.context.get('budget_data')
        self.assertIsNotNone(context_budget_data)

        for dr_obj, data_dict in context_budget_data.items():
            if dr_obj == self.date_range: # Check within the correct DateRange
                items_by_type = data_dict.get('items', {})
                
                # Check for the default item (confirm=False)
                for item in items_by_type.get("その他入金", []):
                    if item.id == self.budget_item.id:
                        self.assertFalse(item.confirm)
                        found_item_default = True
                        
                # Check for the confirmed item (confirm=True)
                for item in items_by_type.get("自動引落", []):
                    if item.id == budget_item_confirmed.id:
                        self.assertTrue(item.confirm)
                        found_item_confirmed = True
        
        self.assertTrue(found_item_default, "Default budget item not found in context or confirm status incorrect.")
        self.assertTrue(found_item_confirmed, "Confirmed budget item not found in context or confirm status incorrect.")

    def test_user_not_logged_in_toggle_confirm(self):
        """Test that toggle_confirm_status view redirects if user is not logged in."""
        self.client.logout()
        url = reverse('toggle_confirm_status', args=[self.budget_item.id])
        response = self.client.post(url)
        # Expecting a redirect to the login page
        self.assertEqual(response.status_code, 302) 
        self.assertTrue(response.url.startswith(reverse('login'))) # Or your specific login URL name

    def test_user_not_logged_in_connectbank(self):
        """Test that connectbank view redirects if user is not logged in."""
        self.client.logout()
        url = reverse('connectbank')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))
