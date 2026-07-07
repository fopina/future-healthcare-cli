import datetime as dt
import unittest
from unittest.mock import MagicMock, patch

import click

from futurehealth.client.models import Reimbursement, ReimbursementPaginationResult, UnifiedRefundsResult
from futurehealth.commands.check import Check

REAL_DATE = dt.date


def refunds_page(refunds, current_page=1, total_pages=1):
    return UnifiedRefundsResult(
        refunds=refunds,
        pagination_result=ReimbursementPaginationResult(current_page=current_page, total_pages=total_pages),
    )


def refund(expense_date, process_nr='1'):
    return Reimbursement(
        process_nr=process_nr,
        type='Medical',
        person_name='Person',
        expense_date=expense_date,
        total_value=10,
        status='Submitted',
        claims=[],
    )


class TestCheck(unittest.TestCase):
    def test_limit_stops_after_requested_number_of_refunds(self):
        contract = MagicMock()
        contract.validate_feature.return_value = True
        contract.unified_refunds.return_value = refunds_page(
            [refund('2026-07-02', '1'), refund('2026-07-01', '2'), refund('2026-06-30', '3')],
            current_page=1,
            total_pages=2,
        )

        cmd = Check(limit=2)
        cmd.contract = contract

        with (
            patch('futurehealth.commands.check.click.echo') as echo,
            patch('futurehealth.commands.check.ensure_error_details_files') as ensure_error_details,
        ):
            cmd()

        ensure_error_details.assert_called_once_with(tls_verify=True)
        self.assertEqual(echo.call_count, 2)
        contract.unified_refunds.assert_called_once_with(page_size=20, page=1)

    def test_last_days_stops_when_refund_is_older_than_cutoff(self):
        contract = MagicMock()
        contract.validate_feature.return_value = True
        contract.unified_refunds.return_value = refunds_page(
            [refund('2026-07-02', '1'), refund('2026-06-25', '2'), refund('2026-06-24', '3')],
            current_page=1,
            total_pages=2,
        )

        cmd = Check(last_days=7)
        cmd.contract = contract

        with (
            patch('futurehealth.commands.check.dt.date') as date,
            patch('futurehealth.commands.check.click.echo') as echo,
            patch('futurehealth.commands.check.ensure_error_details_files') as ensure_error_details,
        ):
            date.today.return_value = REAL_DATE(2026, 7, 2)
            cmd()

        ensure_error_details.assert_called_once_with(tls_verify=True)
        self.assertEqual(echo.call_count, 2)
        contract.unified_refunds.assert_called_once_with(page_size=20, page=1)

    def test_invalid_limit_is_rejected(self):
        cmd = Check(limit=0)

        with self.assertRaises(click.ClickException):
            cmd.validate_options()

    def test_invalid_last_days_is_rejected(self):
        cmd = Check(last_days=0)

        with self.assertRaises(click.ClickException):
            cmd.validate_options()
