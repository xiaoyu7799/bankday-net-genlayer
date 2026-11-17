import {createAccount,createClient} from 'genlayer-js';
import {studionet} from 'genlayer-js/chains';
import {readFile} from 'node:fs/promises';
import {read,finalized,success,encode} from '../scripts/runtime.mjs';
const config=JSON.parse(await readFile('deployment.json','utf8'));
const [mode='read',fn='snapshot',raw='[]']=process.argv.slice(2);const args=JSON.parse(raw);
if(config.chainId!==61999)throw new Error('Only Stable Studionet is supported');
if(mode==='read'){console.log(encode(await read(config.address,fn,args)));}
else if(mode==='write'){
 if(!process.env.PRIVATE_KEY)throw new Error('PRIVATE_KEY must be supplied through a secure environment');
 const client=createClient({chain:studionet,account:createAccount(process.env.PRIVATE_KEY)});
 if(BigInt(await client.request({method:'eth_chainId'}))!==61999n)throw new Error('Wrong RPC chain');
 const hash=await client.writeContract({address:config.address,functionName:fn,args,value:0n,leaderOnly:false});
 console.log('Submitted',hash);const tx=await finalized(hash,s=>console.log(s));
 if(!success(tx))throw new Error('Finalized call failed; inspect the public receipt');
 console.log(encode(await read(config.address,'snapshot')));
}else throw new Error('Use read or write');
