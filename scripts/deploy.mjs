import {startRun,ensureDeployment} from './runtime.mjs';
const name=JSON.parse(await (await import('node:fs/promises')).readFile('package.json','utf8')).name;
const run=await startRun(name.startsWith('bankday')?3:1);console.log('Deployed contract:',await ensureDeployment(run));
