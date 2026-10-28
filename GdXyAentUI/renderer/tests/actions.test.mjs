import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {Playground} from '../app.js';
import {setPath, validateMessages} from '../core.js';

const root = new URL('../../',import.meta.url);
const catalog = JSON.parse(await readFile(new URL('references/agenui/gdxy_catalog.json',root),'utf8'));
const context = JSON.parse(await readFile(new URL('examples/runtime-context.json',root),'utf8'));
async function preview(id) {
  const text = await readFile(new URL(`examples/${id}.jsonl`,root),'utf8');
  const app = new Playground(catalog,context); app.begin(context); app.parser.push(text); app.parser.finish();
  assert.deepEqual(validateMessages(app.messages,catalog,context).errors,[]);
  app.complete = true; return app;
}
async function withHost(callback, run) {
  const prior = globalThis.window;
  globalThis.window = Object.assign(new EventTarget(),{gdXyAgenUiHost:{onFunctionCall:callback}});
  try { await run(); } finally { if (prior === undefined) delete globalThis.window; else globalThis.window = prior; }
}

test('流未结束和空选项禁止确认；改变选择不调用宿主，确认成功后防重复',async () => {
  const app = await preview('selection-multiple'), button = app.nodes.get('confirm'), sent = [];
  await withHost(detail => sent.push(detail), async () => {
    assert.equal(app.canSubmit(button),false);
    app.model = setPath(app.model,'/meal/foods',['沙拉']);
    assert.equal(sent.length,0); assert.equal(app.canSubmit(button),true);
    app.complete = false; await app.submit(button); assert.equal(sent.length,0);
    app.complete = true; await app.submit(button);
    assert.equal(sent[0].query,'我想吃沙拉，需要4人一起合作');
    await app.submit(button); assert.equal(sent.length,1);
  });
});

test('宿主明确失败保留选择，允许重试；重置期间旧异步结果不污染新回复',async () => {
  const app = await preview('selection-single'), button = app.nodes.get('confirm');
  app.model = setPath(app.model,'/plan/priority',['高']);
  let fail = true;
  await withHost(() => { if (fail) throw new Error('模拟发送失败'); },async () => {
    await app.submit(button); assert.equal(app.submitted.has('confirm'),false);
    assert.deepEqual(app.model.plan.priority,['高']);
    fail = false; await app.submit(button); assert.equal(app.submitted.has('confirm'),true);
  });
  const next = await preview('selection-single'); next.model = setPath(next.model,'/plan/priority',['中']);
  let release;
  await withHost(() => new Promise(resolve => {release=resolve;}),async () => {
    const pending = next.submit(next.nodes.get('confirm')); next.reset(); release(); await pending;
    assert.deepEqual(next.results,[]); assert.equal(next.submitted.size,0); assert.equal(next.surfaceId,null);
  });
});

test('人数更新同时影响总量和确认参数，非法输入不能确认',async () => {
  const app = await preview('form-ingredients'), button = app.nodes.get('confirm');
  app.model = setPath(app.model,'/form/people','6');
  assert.equal(app.resolve(app.nodes.get('total').text),'1,200');
  assert.equal(app.canSubmit(button),true);
  app.model = setPath(app.model,'/form/people',''); assert.equal(app.canSubmit(button),false);
  app.model = setPath(app.model,'/form/people','0'); assert.equal(app.canSubmit(button),false);
  app.model = setPath(app.model,'/form/people','2.5'); assert.equal(app.canSubmit(button),false);
});
