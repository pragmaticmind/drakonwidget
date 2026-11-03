const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const context = vm.createContext({});
vm.runInContext(html.match(/<script id="logic">([\s\S]*?)<\/script>/)[1], context);
const DrakonText = context.DrakonText;
const parse = (text) => JSON.parse(JSON.stringify(DrakonText.parse(text)));
const example = `drakon
  silhouette "Example default next branch" (claim)
    branch A
      question to C?
        yes
          goto C
        no
          goto D
    branch B
    branch C
    branch D
      action`;

test("a branch without goto continues to the next branch through an address Icon", () => {
  const { model, diagnostics } = parse(`drakon
  silhouette Example
    branch A
      Do A
    branch B
      Do B`);
  assert.deepEqual(diagnostics, []);
  const action = model.icons[model.branches[0].first];
  assert.deepEqual(model.icons[action.next], { type: "address", branch: model.branches[1].id });
  const lastAction = model.icons[model.branches[1].first];
  assert.equal(model.icons[lastAction.next].type, "end");
});

test("explicit jumps skip B while empty B and C default to the next branch", () => {
  const { model, diagnostics } = parse(example);
  assert.deepEqual(diagnostics, [{
    line: 9,
    message: "Branch “B” is never reached from the first branch.",
    severity: "warning"
  }]);
  const [a, b, c, d] = model.branches;
  const question = model.icons[a.first];
  assert.equal(model.icons[question.yes].branch, c.id);
  assert.equal(model.icons[question.no].branch, d.id);
  assert.equal(model.icons[b.first].branch, c.id);
  assert.equal(model.icons[c.first].branch, d.id);
  const canvas = DrakonText.toDrakonwidget(model);
  const entries = Object.entries(canvas.items).filter(([, item]) => item.type === "branch");
  assert.deepEqual(entries.map(([, item]) => item.content), ["A", "B", "C", "D"]);
  assert.equal(canvas.items[entries[0][1].one].one, entries[2][0]);
  assert.equal(canvas.items[entries[0][1].one].two, entries[3][0]);
  assert.equal(entries[1][1].one, entries[2][0]);
  assert.equal(entries[2][1].one, entries[3][0]);
});

test("the original explicit-jump example warns only on B, not its Icons", () => {
  const explicit = example.replace("    branch B\n", "    branch B\n      goto C\n")
    .replace("    branch C\n", "    branch C\n      goto D\n");
  const { model, diagnostics } = parse(explicit);
  assert.equal(diagnostics.length, 1);
  assert.equal(diagnostics[0].severity, "warning");
  assert.equal(diagnostics[0].line, 9);
  assert.match(diagnostics[0].message, /Branch “B”/);
  assert.equal(Object.values(model.icons).filter((icon) => icon.type === "address").length, 4);
});

test("a disconnected cycle warns once on each branch even when both have incoming jumps", () => {
  const { diagnostics } = parse(`drakon
  silhouette Cycles
    branch A
      goto D
    branch B
      Do B
      goto C
    branch C
      Do C
      goto B
    branch D
      Done`);
  assert.deepEqual(diagnostics.map((d) => [d.line, d.severity]), [[5, "warning"], [8, "warning"]]);
});

test("reachable cycles, self jumps, and backward branch jumps do not warn", () => {
  const { diagnostics, info } = parse(`drakon
  silhouette Cycles
    branch A
      goto C
    branch B
      goto A
    branch C
      question Again?
        yes
          goto B
        no
          goto C`);
  assert.deepEqual(diagnostics, []);
  assert.equal(info.hasEnd, false);
});

test("an omitted question outcome defaults to the next branch, preserving the explicit outcome", () => {
  const { model, diagnostics } = parse(`drakon
  silhouette Outcomes
    branch A
      question Skip B?
        yes
          goto C
    branch B
      Do B
    branch C
      Done`);
  assert.deepEqual(diagnostics, []);
  const question = model.icons[model.branches[0].first];
  assert.equal(model.icons[question.yes].branch, model.branches[2].id);
  assert.equal(model.icons[question.no].branch, model.branches[1].id);
});

test("empty branches chain through addresses and the empty final branch reaches End", () => {
  const { model, diagnostics } = parse(`drakon
  silhouette Empty
    branch A
    branch B
    branch C`);
  assert.deepEqual(diagnostics, []);
  assert.equal(model.icons[model.branches[0].first].branch, model.branches[1].id);
  assert.equal(model.icons[model.branches[1].first].branch, model.branches[2].id);
  assert.equal(model.icons[model.branches[2].first].type, "end");
  const canvas = DrakonText.toDrakonwidget(model);
  Object.values(canvas.items).forEach((item) => {
    if (item.one) assert.ok(canvas.items[item.one], "every Canvas connection has a target");
  });
});

test("select outcomes and a loop ending at a branch bottom inherit the default transition", () => {
  const { model, diagnostics } = parse(`drakon
  silhouette Blocks
    branch A
      select Which?
        case First
          loop Each item
            Handle item
        case Otherwise
    branch B
      Done`);
  assert.deepEqual(diagnostics, []);
  const select = model.icons[model.branches[0].first];
  const loop = model.icons[model.icons[select.cases[0]].next];
  const next = model.icons[loop.end].next;
  assert.equal(model.icons[select.cases[1]].next, next);
  assert.equal(model.icons[next].branch, model.branches[1].id);
});

test("a jump in unreachable local code does not make its target branch reachable", () => {
  const { diagnostics } = parse(`drakon
  silhouette Dead code
    branch A
      question Skip B?
        yes
          goto C
        no
          goto C
      goto B
    branch B
      Do B
    branch C
      Done`);
  assert.ok(diagnostics.some((d) => d.line === 9 && d.severity !== "warning"));
  assert.deepEqual(diagnostics.filter((d) => d.severity === "warning").map((d) => d.line), [10]);
});

test("branch-name matching stays case insensitive and generated address IDs do not collide", () => {
  const { model, diagnostics } = parse(`drakon
  silhouette Names
    branch A
      question Skip?
        yes
          goto c
        no
          action to-b
    branch B
      Do B
    branch C
      Done`);
  assert.deepEqual(diagnostics, []);
  assert.equal(model.icons["to-b"].type, "action");
  assert.equal(model.icons["to-b-2"].type, "address");
});

test("primitives retain their implicit End and invalid gotos remain errors", () => {
  const primitive = parse("drakon\n  primitive Example\n    Do work");
  assert.deepEqual(primitive.diagnostics, []);
  assert.equal(primitive.model.icons[primitive.model.icons[primitive.model.branches[0].first].next].type, "end");
  const invalid = parse("drakon\n  silhouette Example\n    branch A\n      goto Missing");
  assert.ok(invalid.diagnostics.some((d) => /There is no branch/.test(d.message) && d.severity !== "warning"));
});

// Read the existing examples as inputs; exercise only the public parser/adapter.
const scenarioSource = html.match(/var SCENARIOS = ([\s\S]*?);\s*var SNIPPETS/)[1];
const scenarios = JSON.parse(JSON.stringify(vm.runInNewContext("(" + scenarioSource + ")")));
for (const scenario of scenarios) {
  for (const step of scenario.steps) {
    test("walkthrough parses and adapts without crashing: " + scenario.name + " / " + step.label, () => {
      const parsed = parse(step.text.join("\n"));
      assert.ok(parsed.model);
      const canvas = DrakonText.toDrakonwidget(parsed.model);
      assert.ok(canvas.items);
      if (scenario.name !== "Mistakes" && !/Loop drawn down|Loop with no way out|Typo/.test(step.label)) {
        assert.deepEqual(parsed.diagnostics.filter((d) => d.severity !== "warning"), []);
      }
    });
  }
}
