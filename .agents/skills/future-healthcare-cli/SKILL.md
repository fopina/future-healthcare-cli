---
name: future-healthcare-cli
description: Use the Future Healthcare CLI to submit reimbursement receipts after extracting receipt metadata before invoking the command.
---

# Future Healthcare CLI

Use this skill when the user wants to submit a Future Healthcare reimbursement, check refund status/history, inspect
the CLI workflow, or prepare a `future-healthcare submit` command.

Always use the `future-healthcare` CLI for Future Healthcare actions. Do not call the Python library, client classes,
or Future Healthcare API endpoints directly from agent code.

## Submit Workflow

1. When a submission is requested or started, the first file shared by the user must be the invoice/receipt. Treat that
   first file as the `RECEIPT_FILE` positional argument to `future-healthcare submit`. Any extra files are supporting
   attachments and must be passed as positional arguments after the invoice/receipt path.

2. Make sure the user is logged in. Do not ask for, accept, or pass credentials via chat. Credentials must be
   configured outside the conversation with the CLI configuration command. To inspect or edit the local config, tell
   the caller to use:

   ```bash
   future-healthcare config
   future-healthcare config --edit
   ```

3. Extract receipt metadata from the invoice/receipt before calling the CLI. The CLI does not read receipts with a
   model provider. Inspect the receipt yourself and produce these fields:

   - `business_nif`: Portuguese business NIF, exactly 9 digits, usually starting with `5`.
   - `invoice_number`: receipt or invoice number, often beginning with `FR`, `FT`, `RC`, or a similar prefix.
   - `total_amount`: total amount paid as a number, without currency symbols.
   - `date`: treatment or payment date. Prefer `YYYY-MM-DD` when possible.
   - `person`: the assumed insured person name for `--person`, chosen from `future-healthcare beneficiaries`.
   - `service`: the assumed service name for `--service`, chosen from `future-healthcare services`.

4. Always list the available beneficiaries and submission services before running `submit`:

   ```bash
   future-healthcare beneficiaries
   future-healthcare services
   ```

   Use the `beneficiaries` output as the source of valid `--person` values. Compare all person names found on the
   invoice, receipt, customer block, and beneficiary block against the listed beneficiaries. Prefer an exact full-name
   match; otherwise accept a clear partial-name match only when it identifies exactly one listed beneficiary. If no
   invoice name matches a listed beneficiary, or if the match is ambiguous, ask the user which listed beneficiary name
   to use for the `--person` flag.

   Pick the `--service` value from that list. If the receipt does not confidently map to one listed service, ask the
   user which service to use.

5. Before calling `future-healthcare submit`, show the extracted values and assumed routing choices to the user and ask
   them to confirm they are correct. Include `business_nif`, `invoice_number`, `total_amount`, `date`, assumed
   `person`, assumed `service`, whether `--primary-entity` will be used, and the invoice
   file path that will be used as `RECEIPT_FILE`. Also ask whether there are any extra supporting files to attach after
   the invoice. If the detected service from the invoice is `Medicamentos`, explicitly ask for the prescription file;
   this extra prescription attachment is mandatory for `Medicamentos` submissions. If any field is missing, unclear, or
   likely misread, ask the user to provide or correct it. Do not guess NIFs, dates, invoice numbers, totals, person
   names, service names, or supporting attachment paths.

6. Run the CLI with explicit values:

   ```bash
   future-healthcare submit /path/to/receipt.pdf \
     --business-nif 509876543 \
     --invoice-number 'INV 2026/0001' \
     --total-amount 40 \
     --date '2026-03-14'
   ```

7. Pass optional routing hints when known:

   ```bash
   future-healthcare submit /path/to/receipt.pdf \
     --business-nif 509876543 \
     --invoice-number 'INV 2026/0001' \
     --total-amount 40 \
     --date '2026-03-14' \
     --person 'Alice' \
     --service 'Dentist'
   ```

8. Pass extra supporting attachments as positional arguments immediately after the invoice/receipt path and before any
   options. For example:

   ```bash
   future-healthcare submit /path/to/invoice.pdf /path/to/prescription.pdf \
     --business-nif 509876543 \
     --invoice-number 'INV 2026/0001' \
     --total-amount 40 \
     --date '2026-03-14' \
     --person 'Alice' \
     --service 'Medicamentos' \
     --primary-entity
   ```

9. If the selected service is `Medicamentos`, include `--primary-entity`; the company requires medicines to have
   already been paid by the state as well. For other services, do not include `--primary-entity` by default. If the
   invoice or user context suggests another entity, subsidy, copayment, or prior coverage for a non-`Medicamentos`
   service, ask the user whether `--primary-entity` applies before submitting.

10. If the command prompts for insured person, service, building, or review corrections, answer from user-provided
   context. When context is missing, ask the user.

11. If `submit` fails after one or more documents were uploaded, do not try to reuse or clean up the uploaded document
   GUIDs. After fixing the required parameters, run `future-healthcare submit` again normally and let the CLI upload the
   documents again with new GUIDs.

12. If `future-healthcare check` or `future-healthcare submit` fails because the session is missing or invalid, ask the
   user for approval to refresh the session, then run `login` without parameters:

   ```bash
   future-healthcare login
   ```

   If `login` fails because credentials are missing, do not ask the user to provide credentials in chat and do not pass
   `-u`/`-p` values yourself. Tell the caller to either run `future-healthcare login` themselves or add credentials
   with `future-healthcare config --edit`, then rerun `future-healthcare login` after the config is saved.

## Check Workflow

Use `check` when the user wants to inspect refund status/history, confirm whether a recent submission appears, compare
submitted amounts with reimbursed amounts, or avoid submitting a duplicate receipt.

Run:

```bash
future-healthcare check
```

When the prompt asks for only the last `N` submissions/results, limit the result count:

```bash
future-healthcare check --limit N
```

When the prompt asks for submissions/refunds in the last `N` days, limit by date from today:

```bash
future-healthcare check --last-days N
```

These flags can be combined when both constraints are requested, for example:

```bash
future-healthcare check --limit 5 --last-days 30
```

The command lists refund entries across available pages. Each line includes treatment or expense date, service or refund
type, insured person, status or reimbursement amount, and total value. Use the output to:

- Identify whether the receipt or treatment date may already have been submitted.
- Confirm the insured person and service used on previous claims.
- Check whether a refund has been paid, partially paid, rejected, or is still pending.
- Gather context before choosing `--person` or `--service` for a new `submit` command.

If `check` fails because refund consultation is unavailable, report that the current contract does not expose refund
checking. If it fails because the session is missing or invalid, follow the login/session guidance in the submit
workflow.

## Notes

- The invoice/receipt path is always the first positional argument to `submit`; attachments after the receipt path are
  uploaded as supporting documents.
- The CLI stores tokens, config, logs, and copied submission inputs under its platform-specific user config directory.
- Do not pass API keys or model-provider settings to this CLI; receipt understanding belongs to the agent before invocation.
- Never collect or transmit Future Healthcare username/password values through chat. Use saved CLI config plus
  `future-healthcare login` instead.
