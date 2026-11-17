# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json
from datetime import date

CALENDAR = "https://www.gov.uk/bank-holidays.json"
DIVISION = "england-and-wales"


def pack(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def need(ok, code):
    if not ok:
        raise ValueError(code)


def day(value):
    need(type(value) is str and len(value) == 10, "INVALID_DATE")
    parsed = date.fromisoformat(value)
    need(parsed.isoformat() == value and 2019 <= parsed.year <= 2100, "INVALID_DATE")
    return parsed


def address(value):
    need(type(value) is str and len(value) == 42 and value[:2] == "0x" and all(c in "0123456789abcdefABCDEF" for c in value[2:]), "INVALID_ADDRESS")
    need(int(value[2:], 16) != 0, "ZERO_ADDRESS")
    return value.lower()


def calendar_for(today):
    response = gl.nondet.web.get(CALENDAR)
    need(response.status == 200 and len(response.body) <= 500000, "CALENDAR_UNAVAILABLE")
    body = json.loads(response.body.decode("utf-8"))
    division = body.get(DIVISION, {})
    need(division.get("division") == DIVISION, "WRONG_CALENDAR_DIVISION")
    events = division.get("events", [])
    need(type(events) is list and 1 <= len(events) <= 500, "BAD_CALENDAR")
    year = day(today).year
    selected = []
    seen = set()
    for event in events:
        when = day(event.get("date", ""))
        if when.year == year:
            need(event["date"] not in seen, "DUPLICATE_HOLIDAY")
            seen.add(event["date"])
            need(type(event.get("title")) is str and 0 < len(event["title"]) <= 200, "BAD_HOLIDAY_TITLE")
            selected.append({"date": event["date"], "title": event["title"]})
    # Absence of a holiday is not evidence of an open day if that year is absent.
    need(5 <= len(selected) <= 20, "CALENDAR_YEAR_NOT_COVERED")
    selected.sort(key=lambda row: row["date"])
    return {"url": CALENDAR, "division": DIVISION, "day": today, "holidays": selected, "business_day": day(today).weekday() < 5 and today not in seen}


def settlement_plan(invoices):
    balances = {}
    gross = 0
    for invoice in invoices:
        amount = invoice["pence"]
        gross += amount
        balances[invoice["creditor"]] = balances.get(invoice["creditor"], 0) + amount
        balances[invoice["debtor"]] = balances.get(invoice["debtor"], 0) - amount
    need(sum(balances.values()) == 0, "NET_CONSERVATION_FAILED")
    debtors = [[key, -balances[key]] for key in sorted(balances) if balances[key] < 0]
    creditors = [[key, balances[key]] for key in sorted(balances) if balances[key] > 0]
    transfers = []
    i = 0
    j = 0
    while i < len(debtors) and j < len(creditors):
        amount = min(debtors[i][1], creditors[j][1])
        transfers.append({"from": debtors[i][0], "to": creditors[j][0], "pence": amount})
        debtors[i][1] -= amount
        creditors[j][1] -= amount
        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1
    need(i == len(debtors) and j == len(creditors), "UNBALANCED_PLAN")
    return {"balances": balances, "transfers": transfers, "gross_pence": gross, "net_pence": sum(item["pence"] for item in transfers)}


class BankDayNet(gl.Contract):
    invoices: TreeMap[str, str]
    invoice_ids: str
    batches: TreeMap[u256, str]
    batch_count: u256

    def __init__(self):
        self.invoice_ids = "[]"
        self.batch_count = 0

    def _load(self, invoice_id):
        raw = self.invoices.get(invoice_id, "")
        need(bool(raw), "INVOICE_NOT_FOUND")
        return json.loads(raw)

    @gl.public.write
    def propose(self, reference: str, debtor: str, pence: int, due: str) -> str:
        need(type(reference) is str and 3 <= len(reference) <= 40 and all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in reference), "INVALID_REFERENCE")
        debtor = address(debtor)
        creditor = address(str(gl.message.sender_address))
        need(debtor != creditor, "SELF_INVOICE")
        need(type(pence) is int and 1 <= pence <= 1000000000000, "INVALID_PENCE")
        day(due)
        invoice_id = creditor + ":" + reference
        need(not self.invoices.get(invoice_id, ""), "DUPLICATE_REFERENCE")
        ids = json.loads(self.invoice_ids)
        need(len(ids) < 512, "LEDGER_FULL")
        invoice = {"id": invoice_id, "reference": reference, "creditor": creditor, "debtor": debtor, "pence": pence, "currency": "GBP", "due": due, "state": "PROPOSED", "batch_id": None}
        self.invoices[invoice_id] = pack(invoice)
        ids.append(invoice_id)
        self.invoice_ids = pack(ids)
        return invoice_id

    @gl.public.write
    def accept(self, invoice_id: str) -> str:
        invoice = self._load(invoice_id)
        need(str(gl.message.sender_address).lower() == invoice["debtor"], "DEBTOR_ONLY")
        need(invoice["state"] == "PROPOSED", "NOT_PROPOSED")
        invoice["state"] = "ACCEPTED"
        self.invoices[invoice_id] = pack(invoice)
        return pack(invoice)

    @gl.public.write
    def cancel(self, invoice_id: str) -> str:
        invoice = self._load(invoice_id)
        need(str(gl.message.sender_address).lower() == invoice["creditor"], "CREDITOR_ONLY")
        need(invoice["state"] == "PROPOSED", "NOT_PROPOSED")
        invoice["state"] = "CANCELLED"
        self.invoices[invoice_id] = pack(invoice)
        return pack(invoice)

    @gl.public.write
    def clear(self, invoice_ids_json: str) -> str:
        need(len(invoice_ids_json) <= 5000, "BATCH_TOO_LARGE")
        ids = json.loads(invoice_ids_json)
        need(type(ids) is list and 2 <= len(ids) <= 32 and all(type(i) is str for i in ids), "INVALID_BATCH")
        need(len(set(ids)) == len(ids), "DUPLICATE_INVOICE")
        ids.sort()
        today = str(gl.message_raw["datetime"])[:10]
        day(today)
        invoices = [self._load(i) for i in ids]
        for invoice in invoices:
            need(invoice["state"] == "ACCEPTED", "NOT_ACCEPTED")
            need(invoice["due"] <= today, "NOT_DUE")

        def fetch():
            return calendar_for(today)

        def validate(candidate):
            if not isinstance(candidate, gl.vm.Return):
                return False
            try:
                return pack(candidate.calldata) == pack(fetch())
            except Exception:
                return False

        calendar = gl.vm.run_nondet_unsafe(fetch, validate)
        need(calendar["business_day"], "CLEARING_DAY_CLOSED")
        plan = settlement_plan(invoices)
        batch_id = int(self.batch_count)
        batch = {"id": batch_id, "currency": "GBP", "day": today, "invoice_ids": ids, "calendar": calendar, "plan": plan, "state": "NETTED_NOT_PAID"}
        # No transfer is performed. All accepted obligations are consumed once.
        for invoice in invoices:
            invoice["state"] = "NETTED"
            invoice["batch_id"] = batch_id
            self.invoices[invoice["id"]] = pack(invoice)
        self.batches[batch_id] = pack(batch)
        self.batch_count += 1
        return pack(batch)

    @gl.public.view
    def get_invoice(self, invoice_id: str) -> str:
        return pack(self._load(invoice_id))

    @gl.public.view
    def get_batch(self, batch_id: int) -> str:
        need(type(batch_id) is int and 0 <= batch_id < self.batch_count, "BATCH_NOT_FOUND")
        return self.batches[batch_id]

    @gl.public.view
    def snapshot(self) -> str:
        return pack({"invoices": [self._load(i) for i in json.loads(self.invoice_ids)], "batches": [json.loads(self.batches[i]) for i in range(int(self.batch_count))]})
