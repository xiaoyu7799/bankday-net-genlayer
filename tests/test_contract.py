"""Mocked-host accounting/calendar tests. No live consensus is claimed."""
import unittest,types,sys,importlib.util,json
class Map(dict):
    @classmethod
    def __class_getitem__(cls,item):return cls
class Return:
    def __init__(self,value):self.calldata=value
A='0x'+'a'*40;B='0x'+'b'*40;C='0x'+'c'*40
EVENTS=[{'date':'2026-'+d,'title':'Holiday'} for d in ['01-01','04-03','04-06','05-04','05-25','08-31','12-25','12-28']]
class Host:
    Contract=object
    def __init__(self):
        self.message=types.SimpleNamespace(sender_address=A);self.message_raw={'datetime':'2026-11-17T12:00:00Z'}
        self.public=types.SimpleNamespace(write=lambda f:f,view=lambda f:f);self.vm=types.SimpleNamespace(Return=Return,run_nondet_unsafe=self.run)
        self.nondet=types.SimpleNamespace(web=types.SimpleNamespace(get=self.get));self.disagree=False;self.status=200;self.events=EVENTS
    def get(self,url):return types.SimpleNamespace(status=self.status,body=json.dumps({'england-and-wales':{'division':'england-and-wales','events':self.events}}).encode())
    def run(self,fetch,validate):
        result=fetch()
        if self.disagree or not validate(Return(result)):raise ValueError('NO_CONSENSUS')
        return result
host=Host();sdk=types.ModuleType('genlayer');sdk.gl=host;sdk.TreeMap=Map;sdk.u256=int;sys.modules['genlayer']=sdk
spec=importlib.util.spec_from_file_location('contract','contracts/bankday_net.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class Tests(unittest.TestCase):
    def setUp(self):
        host.message.sender_address=A;host.message_raw['datetime']='2026-11-17T12:00:00Z';host.events=list(EVENTS);host.status=200;host.disagree=False
        self.x=c.BankDayNet();self.x.invoices=Map();self.x.batches=Map()
    def invoice(self,creditor,debtor,pence,ref,due='2020-01-01'):
        host.message.sender_address=creditor;i=self.x.propose(ref,debtor,pence,due);host.message.sender_address=debtor;self.x.accept(i);return i
    def cycle(self):return [self.invoice(A,B,10000,'inv-1'),self.invoice(B,C,7000,'inv-2'),self.invoice(C,A,4000,'inv-3'),self.invoice(A,C,2000,'inv-4')]
    def test_multilateral_plan_conserves_exact_pence(self):
        ids=self.cycle();batch=json.loads(self.x.clear(json.dumps(ids)));plan=batch['plan'];self.assertEqual(plan['balances'],{A:8000,B:-3000,C:-5000});self.assertEqual(plan['gross_pence'],23000);self.assertEqual(plan['net_pence'],8000);self.assertEqual(sum(t['pence'] for t in plan['transfers']),8000)
        for i in ids:self.assertEqual(json.loads(self.x.get_invoice(i))['state'],'NETTED')
    def test_fully_offset_cycle_has_zero_transfers(self):
        ids=[self.invoice(A,B,10,'inv-1'),self.invoice(B,A,10,'inv-2')];batch=json.loads(self.x.clear(json.dumps(ids)));self.assertEqual(batch['plan']['transfers'],[])
    def test_debtor_signature_required(self):
        i=self.x.propose('invoice',B,100,'2020-01-01');host.message.sender_address=C
        with self.assertRaisesRegex(ValueError,'DEBTOR_ONLY'):self.x.accept(i)
    def test_accepted_invoice_is_not_unilaterally_cancelable(self):
        i=self.invoice(A,B,10,'invoice');host.message.sender_address=A
        with self.assertRaisesRegex(ValueError,'NOT_PROPOSED'):self.x.cancel(i)
    def test_cancellation_is_terminal(self):
        i=self.x.propose('invoice',B,100,'2020-01-01');self.x.cancel(i);host.message.sender_address=B
        with self.assertRaisesRegex(ValueError,'NOT_PROPOSED'):self.x.accept(i)
    def test_duplicates_and_replay(self):
        ids=self.cycle()
        with self.assertRaisesRegex(ValueError,'DUPLICATE_INVOICE'):self.x.clear(json.dumps([ids[0],ids[0]]))
        self.x.clear(json.dumps(ids))
        with self.assertRaisesRegex(ValueError,'NOT_ACCEPTED'):self.x.clear(json.dumps(ids))
    def test_future_and_unaccepted_do_not_clear(self):
        ids=[self.invoice(A,B,10,'invoice','2099-01-01'),self.invoice(B,A,10,'other')]
        with self.assertRaisesRegex(ValueError,'NOT_DUE'):self.x.clear(json.dumps(ids))
        host.message.sender_address=A;i=self.x.propose('draft',B,10,'2020-01-01')
        with self.assertRaisesRegex(ValueError,'NOT_ACCEPTED'):self.x.clear(json.dumps([i,ids[1]]))
    def test_weekend_and_official_holiday_block_without_state_change(self):
        ids=self.cycle();before=self.x.snapshot()
        for today in ['2026-11-21','2026-12-25']:
            host.message_raw['datetime']=today+'T12:00:00Z'
            with self.assertRaisesRegex(ValueError,'CLEARING_DAY_CLOSED'):self.x.clear(json.dumps(ids))
            self.assertEqual(before,self.x.snapshot())
    def test_missing_year_is_not_an_open_day(self):
        ids=self.cycle();host.message_raw['datetime']='2027-11-17T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'CALENDAR_YEAR_NOT_COVERED'):self.x.clear(json.dumps(ids))
    def test_source_failure_and_validator_disagreement_preserve_obligations(self):
        ids=self.cycle();before=self.x.snapshot()
        for status,disagree in [(503,False),(200,True)]:
            host.status=status;host.disagree=disagree
            with self.assertRaises(ValueError):self.x.clear(json.dumps(ids))
            self.assertEqual(before,self.x.snapshot())
    def test_invalid_amount_reference_self_and_duplicate(self):
        for amount in [0,-1,True,1000000000001]:
            with self.assertRaisesRegex(ValueError,'INVALID_PENCE'):self.x.propose('invoice',B,amount,'2020-01-01')
        with self.assertRaisesRegex(ValueError,'SELF_INVOICE'):self.x.propose('invoice',A,10,'2020-01-01')
        self.x.propose('invoice',B,10,'2020-01-01')
        with self.assertRaisesRegex(ValueError,'DUPLICATE_REFERENCE'):self.x.propose('invoice',B,10,'2020-01-01')
    def test_parser_rejects_duplicate_holiday(self):
        host.events=EVENTS+[EVENTS[0]]
        with self.assertRaisesRegex(ValueError,'DUPLICATE_HOLIDAY'):c.calendar_for('2026-11-17')
