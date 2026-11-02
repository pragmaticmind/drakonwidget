// Throwaway prototype: option A (own Schema) vs option B (JGF profile).
// Plain ESM + JSDoc so it runs with `node` and no build step.

export const OWN_ID = 'https://pragmaticmind.github.io/drakon-model/0.1/schema.json';
export const PROFILE_ID = 'https://pragmaticmind.github.io/drakon-model/0.1/jgf-profile.schema.json';

/** Fields on an own-format Icon that are exits (references to other Icons/branches). */
const EXIT_KEYS = new Set(['next', 'yes', 'no', 'cases', 'end', 'branch']);

/** Exits each Icon type must have. This is the knowledge a consumer of option A needs. */
export const REQUIRED_EXITS = {
  action: ['next'], shelf: ['next'], insertion: ['next'], case: ['next'], loopend: ['next'],
  loopbegin: ['next', 'end'], question: ['yes', 'no'], select: ['cases'], address: ['branch'], end: [],
};

/**
 * Exits of an own-format Icon as a flat list.
 * @returns {{relation: string, target: string, order?: number}[]}
 */
export function exitsOf(icon) {
  const out = [];
  for (const rel of ['next', 'yes', 'no']) if (icon[rel] !== undefined) out.push({ relation: rel, target: icon[rel] });
  (icon.cases || []).forEach((target, i) => out.push({ relation: 'case', target, order: i + 1 }));
  if (icon.end !== undefined) out.push({ relation: 'loopEnd', target: icon.end });
  if (icon.branch !== undefined) out.push({ relation: 'goto', target: icon.branch });
  return out;
}

/** Option A -> option B. */
export function toJgf(m) {
  const g = {
    id: m.id, label: m.name, type: 'drakon', directed: true,
    metadata: { profile: PROFILE_ID, schemaVersion: m.schemaVersion },
    nodes: {}, edges: [],
  };
  for (const k of ['params', 'textFormat', 'meta', 'layout']) if (m[k] !== undefined) g.metadata[k] = m[k];
  (m.branches || []).forEach((b, i) => {
    g.nodes[b.id] = { label: b.name, metadata: { drakonType: 'branch', order: i + 1 } };
    g.edges.push({ source: b.id, target: b.first, relation: 'first' });
  });
  for (const [id, icon] of Object.entries(m.icons || {})) {
    const node = {};
    if (icon.text !== undefined) node.label = icon.text;
    const md = { drakonType: icon.type };
    for (const [k, v] of Object.entries(icon)) if (!EXIT_KEYS.has(k) && k !== 'type' && k !== 'text') md[k] = v;
    node.metadata = md;
    g.nodes[id] = node;
    for (const e of exitsOf(icon)) {
      const edge = { source: id, target: e.target, relation: e.relation };
      if (e.order) edge.metadata = { order: e.order };
      g.edges.push(edge);
    }
  }
  return { graph: g };
}

/**
 * Option B -> option A. Also reports structural problems that option A cannot even
 * express (two exits with the same relation, duplicate case orders), because a
 * JSON Schema over JGF cannot correlate edges with their source node.
 */
export function fromJgf(doc) {
  const errors = [];
  const g = doc.graph || {};
  const md = g.metadata || {};
  const m = { $schema: OWN_ID, schemaVersion: md.schemaVersion, id: g.id, name: g.label };
  for (const k of ['params', 'textFormat', 'meta']) if (md[k] !== undefined) m[k] = md[k];
  const branches = [];
  const byId = {};
  const icons = {};
  for (const [id, n] of Object.entries(g.nodes || {})) {
    const nmd = n.metadata || {};
    if (nmd.drakonType === 'branch') {
      const b = { id, name: n.label, order: nmd.order };
      branches.push(b);
      byId[id] = b;
    } else {
      const icon = { type: nmd.drakonType };
      if (n.label !== undefined) icon.text = n.label;
      for (const [k, v] of Object.entries(nmd)) if (k !== 'drakonType') icon[k] = v;
      icons[id] = icon;
      byId[id] = icon;
    }
  }
  const cases = {};
  const FIELD = { first: 'first', next: 'next', yes: 'yes', no: 'no', loopEnd: 'end', goto: 'branch' };
  for (const e of g.edges || []) {
    const src = byId[e.source];
    if (!src) { errors.push(`edge from unknown node '${e.source}'`); continue; }
    if (e.relation === 'case') {
      (cases[e.source] ||= []).push({ order: e.metadata?.order, target: e.target });
      continue;
    }
    const field = FIELD[e.relation];
    if (!field) { errors.push(`unknown relation '${e.relation}'`); continue; }
    if (src[field] !== undefined) errors.push(`'${e.source}' has more than one '${e.relation}' edge`);
    else src[field] = e.target;
  }
  for (const [id, list] of Object.entries(cases)) {
    const orders = list.map((c) => c.order);
    if (new Set(orders).size !== orders.length) errors.push(`'${id}' has case edges with duplicate order`);
    list.sort((a, b) => a.order - b.order);
    icons[id].cases = list.map((c) => c.target);
  }
  branches.sort((a, b) => a.order - b.order);
  m.branches = branches.map(({ id, name, first }) => ({ id, name, first }));
  m.icons = icons;
  if (md.layout !== undefined) m.layout = md.layout;
  return { model: m, errors };
}

/**
 * The checks no JSON Schema can do in either option: references resolve, loop
 * pairing, case targets. Also re-checks required exits, because for option B the
 * profile schema cannot see them (they are edges, not node fields).
 */
export function checkModel(m) {
  const errors = [];
  const icons = m.icons || {};
  const branchIds = new Set((m.branches || []).map((b) => b.id));
  const loopEndRefs = {};
  for (const b of m.branches || []) if (!icons[b.first]) errors.push(`branch '${b.id}' starts at unknown icon '${b.first}'`);
  for (const [id, icon] of Object.entries(icons)) {
    const req = REQUIRED_EXITS[icon.type];
    if (!req) { errors.push(`'${id}' has unknown type '${icon.type}'`); continue; }
    for (const f of req) if (icon[f] === undefined) errors.push(`'${id}' (${icon.type}) is missing exit '${f}'`);
    for (const e of exitsOf(icon)) {
      if (e.relation === 'goto') { if (!branchIds.has(e.target)) errors.push(`'${id}' goes to unknown branch '${e.target}'`); }
      else if (!icons[e.target]) errors.push(`'${id}' ${e.relation} -> unknown icon '${e.target}'`);
    }
    if (icon.type === 'select') {
      if ((icon.cases || []).length < 2) errors.push(`'${id}' select needs at least 2 cases`);
      for (const c of icon.cases || []) if (icons[c] && icons[c].type !== 'case') errors.push(`'${id}' case target '${c}' is not a case icon`);
    }
    if (icon.type === 'loopbegin' && icon.end !== undefined) {
      if (icons[icon.end]?.type !== 'loopend') errors.push(`'${id}' loop end '${icon.end}' is not a loopend icon`);
      loopEndRefs[icon.end] = (loopEndRefs[icon.end] || 0) + 1;
    }
  }
  for (const [id, icon] of Object.entries(icons)) {
    if (icon.type === 'loopend' && loopEndRefs[id] !== 1) errors.push(`loopend '${id}' is paired with ${loopEndRefs[id] || 0} loop starts`);
  }
  return errors;
}

const q = (s) => JSON.stringify(s ?? '');
/** Mermaid ids: no hyphens (they collide with arrow syntax). */
const mid = (id) => String(id).replace(/[^A-Za-z0-9_]/g, '_');

/** A consumer that knows only JGF (no DRAKON knowledge) can still draw a graph. */
export function genericJgfToMermaid(doc) {
  const g = doc.graph;
  const lines = ['flowchart TD'];
  for (const [id, n] of Object.entries(g.nodes)) lines.push(`  ${mid(id)}[${q(n.label ?? id)}]`);
  for (const e of g.edges) lines.push(`  ${mid(e.source)} -->|${e.relation ?? ''}| ${mid(e.target)}`);
  return lines.join('\n') + '\n';
}

/** A consumer of option A needs `exitsOf` (one small table of DRAKON knowledge). */
export function ownToMermaid(m) {
  const lines = ['flowchart TD'];
  for (const b of m.branches) {
    lines.push(`  ${mid(b.id)}([${q(b.name)}])`, `  ${mid(b.id)} --> ${mid(b.first)}`);
  }
  for (const [id, icon] of Object.entries(m.icons)) {
    const label = icon.text ?? icon.type;
    lines.push(icon.type === 'question' || icon.type === 'select' ? `  ${mid(id)}{${q(label)}}` : `  ${mid(id)}[${q(label)}]`);
    for (const e of exitsOf(icon)) lines.push(`  ${mid(id)} -->|${e.relation}| ${mid(e.target)}`);
  }
  return lines.join('\n') + '\n';
}

/** Key-order-insensitive deep equality. */
export function deepEqual(a, b) {
  if (a === b) return true;
  if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null) return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const ka = Object.keys(a), kb = Object.keys(b);
  if (ka.length !== kb.length) return false;
  return ka.every((k) => deepEqual(a[k], b[k]));
}
