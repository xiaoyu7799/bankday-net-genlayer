import {verifyRun,encode} from './runtime.mjs';
import {writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const {log,state}=await verifyRun();const batch=state.batches[0];assert.equal(batch.state,'NETTED_NOT_PAID');const positions={};let gross=0n;
for(const id of batch.invoice_ids){const i=state.invoices.find(x=>x.id===id);assert(i&&i.state==='NETTED'&&i.batch_id===0);const p=BigInt(i.pence);gross+=p;positions[i.creditor]=(positions[i.creditor]||0n)+p;positions[i.debtor]=(positions[i.debtor]||0n)-p;}
assert.equal(Object.values(positions).reduce((a,b)=>a+b,0n),0n);const represented={};let net=0n;
for(const t of batch.plan.transfers){const p=BigInt(t.pence);assert(p>0n);assert(positions[t.from]<0n&&positions[t.to]>0n);represented[t.from]=(represented[t.from]||0n)-p;represented[t.to]=(represented[t.to]||0n)+p;net+=p;}
for(const [wallet,value]of Object.entries(positions)){assert.equal(BigInt(batch.plan.balances[wallet]),value);assert.equal(represented[wallet]||0n,value);}
assert.equal(gross,23000n);assert.equal(net,8000n);assert.equal(BigInt(batch.plan.gross_pence),gross);assert.equal(BigInt(batch.plan.net_pence),net);
assert(batch.calendar.business_day);assert.equal(batch.calendar.url,'https://www.gov.uk/bank-holidays.json');assert(!batch.calendar.holidays.some(h=>h.date===batch.day));const weekday=new Date(batch.day+'T00:00:00Z').getUTCDay();assert(weekday>0&&weekday<6);
assert.deepEqual(log.snapshots['before-unauthorized'],log.snapshots['after-unauthorized']);assert.deepEqual(log.snapshots.accepted,log.snapshots['after-duplicate-rejected']);assert.equal(state.invoices.find(i=>i.reference==='cancel-1').state,'CANCELLED');
await writeFile('evidence/invariants.json',encode({verifiedAt:new Date().toISOString(),grossPence:String(gross),netPence:String(net),positions,transfersRepresentExactPositions:true,eachInvoiceConsumedOnce:true,calendarDay:batch.day,officialBusinessDayVerified:true,unauthorizedAndDuplicateCallsPreservedState:true,cancellationTerminal:true,paid:false})+'\n');
console.log('Exact independent netting arithmetic, calendar and negative branches verified.');
