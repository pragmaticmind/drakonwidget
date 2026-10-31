// Run: npm install && npm run compare
// Validates the sample in both formats, round-trips A -> B -> A, then feeds the same
// deliberately broken Diagrams to both and reports which layer catches each problem.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import Ajv from 'ajv';
import {
  toJgf, fromJgf, checkModel, genericJgfToMermaid, ownToMermaid, deepEqual, OWN_ID, PROFILE_ID,
} from './lib.mjs';

const here = new URL('.', import.meta.url);
const read = (p) => JSON.parse(readFileSync(new URL(p, here), 'utf8'));
const write = (p, s) => writeFileSync(new URL(p, here), s);
const clone = (o) => structuredClone(o);
mkdirSync(new URL('out/', here), { recursive: true });

const ajv = new Ajv({ discriminator: true, strict: false, allErrors: false });
ajv.addSchema(read('schema/jgf-v2.1.schema.json'));
ajv.addSchema(read('schema/own.schema.json'));
ajv.addSchema(read('schema/jgf-profile.schema.json'));
const validateOwn = ajv.getSchema(OWN_ID);
const validateJgf = ajv.getSchema(PROFILE_ID);
const firstError = (v) => {
  const e = v.errors?.[0];
  return e ? `${e.instancePath || '/'} ${e.message}${e.params?.missingProperty ? ` '${e.params.missingProperty}'` : ''}` : '';
};

// 1. The sample, both ways.
const own = read('samples/expense-claim.own.json');
const jgf = toJgf(own);
write('samples/expense-claim.jgf.json', JSON.stringify(jgf, null, 2) + '\n');
const back = fromJgf(jgf);
console.log('## Sample: Handle expense claim\n');
console.log(`- own Schema valid: ${validateOwn(own)} ${firstError(validateOwn)}`);
console.log(`- JGF profile valid (incl. JGF v2.1 core): ${validateJgf(jgf)} ${firstError(validateJgf)}`);
console.log(`- code checks clean: own=${checkModel(own).length === 0}, jgf=${back.errors.length + checkModel(back.model).length === 0}`);
console.log(`- lossless round trip A -> B -> A: ${deepEqual(own, back.model)}`);

const pretty = (o) => JSON.stringify(o, null, 2);
const lines = (s) => s.split('\n').length;
const count = (o) => (typeof o === 'object' && o !== null ? Object.values(o).reduce((n, v) => n + 1 + count(v), 0) : 0);
console.log('\n## Size\n');
console.log('| | own | JGF profile |\n|---|---|---|');
console.log(`| minified bytes | ${JSON.stringify(own).length} | ${JSON.stringify(jgf).length} |`);
console.log(`| JSON values (keys + array items) | ${count(own)} | ${count(jgf)} |`);
console.log(`| pretty-printed lines | ${lines(pretty(own))} | ${lines(pretty(jgf))} |`);
console.log(`| schema lines | ${lines(readFileSync(new URL('schema/own.schema.json', here), 'utf8'))} | ${lines(readFileSync(new URL('schema/jgf-profile.schema.json', here), 'utf8'))} + JGF core ${lines(readFileSync(new URL('schema/jgf-v2.1.schema.json', here), 'utf8'))} |`);

write('out/generic-jgf.mmd', genericJgfToMermaid(jgf));
write('out/own.mmd', ownToMermaid(own));

// 2. Broken Diagrams. `own` mutates the option A model (option B is derived with toJgf);
// `jgf` mutates the option B document directly, for faults option A cannot express.
const mutations = [
  { name: 'unknown Icon type', own: (m) => { m.icons.book.type = 'actoin'; } },
  { name: 'action without text', own: (m) => { delete m.icons.book.text; } },
  { name: "question missing its 'no' exit", own: (m) => { delete m.icons['has-receipt'].no; } },
  { name: 'question missing exit orientation (down)', own: (m) => { delete m.icons['has-receipt'].down; } },
  { name: 'insertion without target Diagram id', own: (m) => { delete m.icons.finance.diagram; } },
  { name: 'select with only one case', own: (m) => { m.icons.amount.cases = ['small']; delete m.icons.medium; delete m.icons.large; delete m.icons.manager; delete m.icons.finance; } },
  { name: 'dangling reference', own: (m) => { m.icons['auto-approve'].next = 'nowhere'; } },
  { name: 'loop start not paired with a loop end', own: (m) => { delete m.icons['each-line'].end; } },
  { name: 'unknown field on an Icon (typo `colour`)', own: (m) => { m.icons.book.colour = 'red'; } },
  { name: 'action with two `next` exits', own: null, jgf: (d) => { d.graph.edges.push({ source: 'book', target: 'transfer', relation: 'next' }); } },
  { name: 'two cases with the same order', own: null, jgf: (d) => { d.graph.edges.find((e) => e.relation === 'case' && e.metadata.order === 2).metadata.order = 1; } },
];

const verdictOwn = (m) => {
  if (!validateOwn(m)) return ['schema', firstError(validateOwn)];
  const errs = checkModel(m);
  return errs.length ? ['code', errs[0]] : ['MISSED', ''];
};
const verdictJgf = (d) => {
  if (!validateJgf(d)) return ['schema', firstError(validateJgf)];
  const { model, errors } = fromJgf(d);
  const errs = [...errors, ...checkModel(model)];
  return errs.length ? ['code', errs[0]] : ['MISSED', ''];
};

console.log('\n## Broken Diagrams: which layer catches the fault\n');
console.log('| fault | own Schema | JGF profile |\n|---|---|---|');
const details = ['# Broken Diagrams: first error reported\n'];
for (const mu of mutations) {
  let a = ['cannot be written', 'the format has no way to express this fault'];
  let doc;
  if (mu.own) {
    const m = clone(own);
    mu.own(m);
    a = verdictOwn(m);
    doc = toJgf(m);
  } else {
    doc = clone(jgf);
    mu.jgf(doc);
  }
  // A typo'd field lands in node.metadata in JGF, mirroring how option B stores everything.
  const b = verdictJgf(doc);
  console.log(`| ${mu.name} | ${a[0]} | ${b[0]} |`);
  details.push(`## ${mu.name}\n\n- own: **${a[0]}**: ${a[1]}\n- JGF: **${b[0]}**: ${b[1]}\n`);
}
write('out/broken-report.md', details.join('\n'));
console.log('\nDetails: out/broken-report.md; Mermaid: out/own.mmd, out/generic-jgf.mmd');
