import assert from 'node:assert/strict';
import {startRun,ensureDeployment} from './runtime.mjs';
const run=await startRun(3);if(run.done){console.log('Acceptance already complete; npm run verify performs read-only verification.');process.exit(0);}
await ensureDeployment(run);
const [A,B,C]=run.accounts.map(a=>a.address.toLowerCase());const invoice=(owner,ref)=>owner+':'+ref;
const specs=[[0,B,10000,'net-1',1],[1,C,7000,'net-2',2],[2,A,4000,'net-3',0],[0,C,2000,'net-4',2]];
const ids=[];
for(const [owner,debtor,pence,ref,payer] of specs){const id=invoice([A,B,C][owner],ref);ids.push(id);await run.operation('propose-'+ref,'propose',[ref,debtor,pence,'2020-01-01'],owner);if(ref==='net-1'){const pending=await run.snapshot('before-unauthorized','get_invoice',[id]);await run.operation('reject-unauthorized','accept',[id],2,'FAILURE');assert.deepEqual(await run.snapshot('after-unauthorized','get_invoice',[id]),pending);}await run.operation('accept-'+ref,'accept',[id],payer);}
const accepted=await run.snapshot('accepted');
await run.operation('reject-duplicate-batch','clear',[JSON.stringify([ids[0],ids[0]])],0,'FAILURE');assert.deepEqual(await run.snapshot('after-duplicate-rejected'),accepted);
await run.operation('clear-multilateral','clear',[JSON.stringify(ids)],2);
const batch=await run.snapshot('netted-batch','get_batch',[0]);assert.equal(batch.state,'NETTED_NOT_PAID');assert.equal(batch.plan.gross_pence,23000);assert.equal(batch.plan.net_pence,8000);assert.deepEqual(batch.plan.balances,{[A]:8000,[B]:-3000,[C]:-5000});assert.equal(batch.plan.transfers.length,2);
await run.operation('reject-clearing-replay','clear',[JSON.stringify(ids)],0,'FAILURE');
await run.operation('propose-cancel','propose',['cancel-1',B,100,'2020-01-01'],0);const cancelledId=invoice(A,'cancel-1');await run.operation('cancel-draft','cancel',[cancelledId],0);await run.operation('reject-accept-cancelled','accept',[cancelledId],1,'FAILURE');
const final=await run.snapshot('final');assert.equal(final.invoices.filter(i=>i.state==='NETTED').length,4);assert.equal(final.invoices.at(-1).state,'CANCELLED');assert.equal(final.batches.length,1);await run.finish();
