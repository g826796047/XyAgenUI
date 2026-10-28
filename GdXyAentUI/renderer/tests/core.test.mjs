import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JsonlStream, getPath, setPath, validateMessages, interpolateQuery, resolveDynamic, resolveCallArguments} from '../core.js';

const root = new URL('../../', import.meta.url);
const catalog = JSON.parse(await readFile(new URL('references/agenui/gdxy_catalog.json', root), 'utf8'));
const context = JSON.parse(await readFile(new URL('examples/runtime-context.json', root), 'utf8'));

test('JSONL 可分片解析并保留中文', () => {
  const source = '{"version":"v0.9"}\r\n{"text":"你好👋"}', values = [];
  const stream = new JsonlStream((message, line) => values.push([message, line]));
  for (let i = 0; i < source.length; i += 2) stream.push(source.slice(i, i + 2));
  stream.finish(); assert.equal(values.length, 2); assert.equal(values[1][0].text, '你好👋'); assert.throws(() => stream.push('{}'), /流已经结束/);
});

test('A2UI AGenUI 样例通过消息、组件图和函数校验', async () => {
  for (const id of ['short-answer','structured-summary','comparison','image-answer','selection-multiple','selection-single','form-ingredients','markdown','function-call-link']) {
    const text = await readFile(new URL(`examples/${id}.jsonl`, root), 'utf8');
    const messages = text.trim().split(/\r?\n/).map(line => JSON.parse(line));
    const result = validateMessages(messages, catalog, context); assert.deepEqual(result.errors, [], `${id}: ${result.errors.join('; ')}`);
  }
});

test('ChoicePicker 选择数组可按 query 模板组装', () => {
  assert.deepEqual(getPath({meal:{foods:['披萨','沙拉']}}, '/meal/foods'), ['披萨','沙拉']);
  assert.equal(interpolateQuery({foods:['披萨','沙拉'], people:'4', query:'我想吃${foods}，需要${people}人一起合作'}), '我想吃披萨和沙拉，需要4人一起合作');
});

test('嵌套的宿主 calculateNumber 可驱动绑定展示值', () => {
  const value = resolveDynamic({
    call: 'formatNumber', args: {value: {call: 'calculateNumber', args: {
      left: {path: '/form/people'}, right: {path: '/form/perPerson'}, operator: 'multiply',
    }}, decimals: 0},
  }, {form: {people: 4, perPerson: 200}});
  assert.equal(value, '800');
  assert.throws(() => resolveDynamic({call: 'calculateNumber', args: {
    left: 4, right: 0, operator: 'divide',
  }}, {}), /运算无效/);
});

test('FunctionCall 参数对象递归读取最新绑定值并拒绝未授权函数', () => {
  const args = resolveCallArguments({
    meal: {foods: {path: '/meal/foods'}, people: {path: '/meal/people'}},
    formatted: {call: 'formatNumber', args: {value: {path: '/meal/people'}, decimals: 0}},
    query: '吃什么？',
  }, {meal: {foods: ['披萨', '沙拉'], people: 4}}, {}, ['formatNumber']);
  assert.deepEqual(args.meal.foods, ['披萨', '沙拉']);
  assert.equal(args.meal.people, 4);
  assert.equal(args.formatted, '4');
  assert.throws(() => resolveCallArguments({value: {call: 'calculateNumber', args: {left: 1, right: 2, operator: 'add'}}}, {}, {}, []), /白名单/);
});

test('多选数据变更后，FunctionCall 使用最新选择组装 query', async () => {
  const text = await readFile(new URL('examples/selection-multiple.jsonl', root), 'utf8');
  const messages = text.trim().split(/\r?\n/).map(line => JSON.parse(line));
  const button = messages.find(message => message.updateComponents)?.updateComponents.components.find(component => component.id === 'confirm');
  const args = resolveCallArguments(button.action.functionCall.args, {meal: {foods: ['沙拉', '烤蔬菜'], people: '6'}}, {}, context.a2ui.allowedFunctions);
  assert.equal(interpolateQuery(args), '我想吃沙拉和烤蔬菜，需要6人一起合作');
});

test('表单数值先转换为字符串再插入 query', async () => {
  const text = await readFile(new URL('examples/form-ingredients.jsonl', root), 'utf8');
  const messages = text.trim().split(/\r?\n/).map(line => JSON.parse(line));
  const button = messages.find(message => message.updateComponents)?.updateComponents.components.find(component => component.id === 'confirm');
  const args = resolveCallArguments(button.action.functionCall.args, {form: {people: 6, perPerson: 180}}, {}, context.a2ui.allowedFunctions);
  assert.equal(interpolateQuery(args), '请按6人、每人180克给我整理采购清单');
});

test('数据模型支持局部更新和删除', () => {
  let model = setPath({}, '/form/people', 6); model = setPath(model, '/form/perPerson', 200); assert.equal(getPath(model, '/form/people'), 6); model = setPath(model, '/form/perPerson', undefined, true); assert.equal(getPath(model, '/form/perPerson'), undefined);
});

test('拒绝旧组件字段和 action.event', () => {
  const messages = [
    {version:'v0.9', createSurface:{surfaceId:'bad', catalogId:catalog.catalogId}},
    {version:'v0.9', updateComponents:{surfaceId:'bad', components:[{id:'root', component:'Column', children:['text']},{id:'text', component:'Text', content:'旧字段'}]}},
    {version:'v0.9', updateComponents:{surfaceId:'bad', components:[{id:'button', component:'Button', child:'text', action:{event:{name:'submit'}}}]}},
  ];
  const result = validateMessages(messages, catalog, context); assert.ok(result.errors.some(error => error.includes('不支持属性 content'))); assert.ok(result.errors.some(error => error.includes('action.event')));
});
