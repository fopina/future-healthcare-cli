SYSTEM_PROMPT = """"""

USER_TEXT_PROMPT = """
In the attached receipt, extract the following details, outputting a JSON object with field names mentioned:
* Two NIF (Número de Identificação Fiscal): one starts with 5 named "business", the other does not named "personal". Both must be 9 digits long.
* Receipt or invoice number, usually starting with FR or V, named "invoice"
* Date: might be YEAR-MM-DD or DD-MM-YEAR, convert to YEAR-MM-DD if needed, named "date"
* Total amount paid, named "total"
Do not include any text apart from the JSON, not even markdown. If you need to include any message, use _message field in the json.
"""

USER_VISION_PROMPT = USER_TEXT_PROMPT
