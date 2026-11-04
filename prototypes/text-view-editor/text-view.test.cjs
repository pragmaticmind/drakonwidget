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

test("primitive and silhouette headers work without the drakon wrapper", () => {
  for (const wrapped of ["drakon\n  primitive Example (claim)\n    Do work", example]) {
    const original = parse(wrapped);
    const unwrapped = parse(wrapped.split("\n").slice(1).map((line) => line.slice(2)).join("\n"));
    assert.deepEqual(unwrapped.model, original.model);
    assert.deepEqual(unwrapped.info, original.info);
    assert.deepEqual(unwrapped.diagnostics, original.diagnostics.map((d) => ({ ...d, line: d.line - 1 })));
  }
});

test("wrapper-free input still rejects extra top-level Diagrams and unindented steps", () => {
  for (const extra of ["primitive Another", "Do work"]) {
    const { diagnostics } = parse("primitive Example\n  First step\n" + extra);
    assert.ok(diagnostics.some((d) => d.line === 3 && /One Diagram per text/.test(d.message)));
  }
});

test("inline yes/no branch jumps produce the same Model and Canvas as indented outcomes", () => {
  const inline = parse(`silhouette "Example default next branch" (claim)
  branch A
    question to C?
      yes goto C
      no goto D
  branch B
  branch C
  branch D
    action`);
  const original = parse(example);
  assert.deepEqual(inline.model, original.model);
  assert.deepEqual(inline.info, original.info);
  assert.deepEqual(inline.diagnostics, [{
    line: 6, message: "Branch “B” is never reached from the first branch.", severity: "warning"
  }]);
  assert.deepEqual(
    JSON.parse(JSON.stringify(DrakonText.toDrakonwidget(inline.model))),
    JSON.parse(JSON.stringify(DrakonText.toDrakonwidget(original.model)))
  );
});

test("inline outcomes preserve explicit exit ordering and mix with indented outcomes", () => {
  const { model, diagnostics } = parse(`drakon
  silhouette Mixed
    branch A
      question Skip?
        no goto C
        yes
          Do work
    branch B
      Done
    branch C
      Finished`);
  assert.deepEqual(diagnostics, []);
  const q = model.icons[model.branches[0].first];
  assert.equal(q.down, "no");
  assert.equal(model.icons[q.no].branch, model.branches[2].id);
  assert.equal(model.icons[q.yes].text, "Do work");
  assert.equal(model.icons[model.icons[q.yes].next].branch, model.branches[1].id);
});

for (const outcome of ["yes", "no"]) {
  test("a lone inline " + outcome + " goto remains a side guard", () => {
    const { model, diagnostics } = parse(`silhouette Guard
  branch A
    question Skip?
      ${outcome} goto C
    Continue working
  branch B
    Done
  branch C
    Finished`);
    assert.deepEqual(diagnostics, []);
    const q = model.icons[model.branches[0].first];
    assert.equal(q.down, outcome === "yes" ? "no" : "yes");
    assert.equal(model.icons[q[outcome]].branch, model.branches[2].id);
    assert.equal(model.icons[q[q.down]].text, "Continue working");
  });
}

test("inline goto @label supports arrow loops and is equivalent to an indented guard", () => {
  const concise = `primitive Retry
  @try
  Try work
  question Done?
    no goto @try
  Finish`;
  const inline = parse(concise);
  const expanded = parse(concise.replace("no goto @try", "no\n      goto @try"));
  assert.deepEqual(inline.diagnostics, []);
  assert.deepEqual(inline.model, expanded.model);
  assert.deepEqual(inline.info, expanded.info);
  assert.equal(inline.info.loops, 1);
  const canvas = DrakonText.toDrakonwidget(inline.model);
  assert.equal(Object.values(canvas.items).filter((icon) => icon.type === "arrow-loop").length, 1);
});

test("inline goto @label supports a forward join without creating an address", () => {
  const { model, diagnostics, info } = parse(`primitive Join
  question Skip?
    yes goto @done
  Do work
  @done
  Finish`);
  assert.deepEqual(diagnostics, []);
  const q = model.icons[model.branches[0].first];
  assert.equal(model.icons[q.yes].text, "Finish");
  assert.equal(model.icons[q.no].text, "Do work");
  assert.equal(info.joins, 1);
  assert.equal(info.loops, 0);
  assert.ok(!Object.values(model.icons).some((icon) => icon.type === "address"));
});

test("inline keywords are case insensitive and branch names may contain spaces", () => {
  const { model, diagnostics } = parse(`SILHOUETTE Names
  branch A
    question Ready?
      YES   GoTo   Final branch
      NO
        Work
  branch Final branch
    Finish`);
  assert.deepEqual(diagnostics, []);
  const q = model.icons[model.branches[0].first];
  assert.equal(model.icons[q.yes].branch, model.branches[1].id);
});

for (const [outcome, message] of [
  ["yes goto Missing", /There is no branch/],
  ["no goto @missing", /There is no label/],
  ["yes goto", /Write yes goto/],
  ["no Do work", /Write no goto/]
]) {
  test("invalid inline outcome is diagnosed on its source line: " + outcome, () => {
    const { diagnostics } = parse("silhouette Invalid\n  branch A\n    question Ready?\n      " + outcome);
    assert.ok(diagnostics.some((d) => d.line === 4 && message.test(d.message)));
  });
}

test("an inline outcome cannot also contain indented steps", () => {
  const { diagnostics } = parse(`silhouette Mixed
  branch A
    question Ready?
      yes goto B
        Do work
  branch B
    Finish`);
  assert.ok(diagnostics.some((d) => d.line === 4 && /cannot also have indented steps/.test(d.message)));
});

test("duplicate inline outcomes and outcomes outside questions remain invalid", () => {
  const duplicate = parse(`silhouette Duplicate
  branch A
    question Ready?
      yes goto B
      yes goto B
  branch B
    Finish`);
  assert.ok(duplicate.diagnostics.some((d) => d.line === 5 && /already has a yes block/.test(d.message)));
  const misplaced = parse("primitive Invalid\n  yes goto @done\n  @done\n  Finish");
  assert.ok(misplaced.diagnostics.some((d) => d.line === 2 && /only goes directly under a question/.test(d.message)));
});

test("inline label jumps retain branch boundaries and loop orientation checks", () => {
  const crossBranch = parse(`silhouette Invalid
  branch A
    question Ready?
      no goto @done
  branch B
    @done
    Finish`);
  assert.ok(crossBranch.diagnostics.some((d) => d.line === 4 && /stays within one branch/.test(d.message)));
  const downwardLoop = parse(`primitive Invalid
  @try
  Try work
  question Ready?
    no goto @try
    yes
  Finish`);
  assert.ok(downwardLoop.diagnostics.some((d) => d.line === 5 && /drawn downwards/.test(d.message)));
});

test("empty input and malformed wrapped headers still get actionable diagnostics", () => {
  assert.match(parse("").diagnostics[0].message, /optionally wrapped in drakon/);
  for (const input of ["drakon", "Do work", "drakon\nprimitive Invalid"]) {
    assert.ok(parse(input).diagnostics.length);
  }
  assert.ok(parse("  primitive Invalid\n    Do work").diagnostics.some((d) => /indented deeper/.test(d.message)));
});

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
        const concise = step.text.join("\n").replace(/^(\s*)(yes|no)\n\1  goto ([^\n]+)/gm, "$1$2 goto $3");
        const inline = parse(concise);
        assert.deepEqual(inline.model, parsed.model);
        assert.deepEqual(inline.info, parsed.info);
        assert.deepEqual(inline.diagnostics.filter((d) => d.severity !== "warning"), []);
        if (step.text[0] === "drakon") {
          const unwrapped = parse(concise.split("\n").slice(1).map((line) => line.slice(2)).join("\n"));
          assert.deepEqual(unwrapped.model, parsed.model);
          assert.deepEqual(unwrapped.info, parsed.info);
          assert.deepEqual(unwrapped.diagnostics.filter((d) => d.severity !== "warning"), []);
        }
      }
    });
  }
}
