SYSTEM_PROMPT = """
You are an expert at extracting information from Portuguese receipts and invoices (faturas and recibos).
You understand Portuguese business document formats, tax identification numbers (NIF), and common abbreviations.
Always extract information accurately and return only valid JSON and nothing else.
If information is unclear or missing, use null values and explain in _message field.
"""

USER_TEXT_PROMPT = """
Extract the following information from the following PDF text and return a JSON object:

Required fields:
- business_nif: The business NIF (starts with 5, 9 digits total) - this is the company's tax number
- personal_nif: The customer's NIF (does NOT start with 5, 9 digits total) - this is the individual's tax number
- invoice_number: Receipt/invoice number (usually starts with FR, FT, RC, or similar)
- date: Date in YYYY-MM-DD format (convert from DD-MM-YYYY or other formats if needed)
- total_amount: Total amount paid (numeric value, include currency if present)

Validation rules:
- NIFs must be exactly 9 digits
- Business NIF must start with 5
- Personal NIF must NOT start with 5
- Date must be in YYYY-MM-DD format
- Total amount MUST be a number, DO NOT extract currency (EUR or €)
"""

USER_VISION_PROMPT = """
Analyze this Portuguese receipt/invoice image and extract the following information as JSON:

Required fields:
- business_nif: Business NIF (9 digits, starts with 5) - company's tax number
- personal_nif: Personal NIF (9 digits, does NOT start with 5) - individual's tax number
- invoice_number: Document number (FR, FT, RC, etc.)
- date: Date in YYYY-MM-DD format
- total_amount: Total payment amount

Important notes:
- Look for "NIF", "Número de Identificação Fiscal", or "Contribuinte" labels
- Business NIFs typically start with 5 (large companies)
- Personal NIF must NOT start with 5
- Dates may be in DD/MM/YYYY or DD-MM-YYYY format - convert to YYYY-MM-DD
- Total amount MUST be a number, DO NOT extract currency (EUR or €)
"""
