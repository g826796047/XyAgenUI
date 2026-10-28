import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateMessages, interpolateQuery, resolveCallArguments, getPath, setPath, schemaErrors} from '../renderer/core.js';

const catalog = JSON.parse(await readFile(new URL('../references/agenui/gdxy_catalog.json', import.meta.url), 'utf8'));
const context = JSON.parse(await readFile(new URL('../examples/runtime-context.json', import.meta.url), 'utf8'));
const load = async id => (await readFile(new URL(`../examples/${id}.jsonl`, import.meta.url), 'utf8')).trim().split(/\r?\n/).map(line => JSON.parse(line));
const minimal = () => [
  {version:'v0.9',createSurface:{surfaceId:'test',catalogId:catalog.catalogId}},
  {version:'v0.9',updateComponents:{surfaceId:'test',components:[{id:'root',component:'Column',children:['text']},{id:'text',component:'Text',text:'回答'}]}},
];

test('组件画廊覆盖官方 25 种组件并通过项目合同', async () => {
  const messages = await load('component-gallery');
  const result = validateMessages(messages, catalog, context);
  assert.deepEqual(result.errors, []);
  assert.deepEqual([...new Set([...result.nodes.values()].map(node => node.component))].sort(), Object.keys(catalog.components).sort());
});

test('所有运行时白名单包含普通组件，未声明的函数不因嵌套获得权限', async () => {
  const messages = minimal();
  assert.ok(validateMessages(messages,catalog,{a2ui:{allowedComponents:['Text']}}).errors.some(error => error.includes('Column 未在')));
  const call = {call:'formatNumber',args:{value:{call:'calculateNumber',args:{left:1,right:2,operator:'add'}}}};
  assert.throws(() => resolveCallArguments(call,{}, {}, ['formatNumber']), /calculateNumber.*白名单/);
  const sample = await load('form-ingredients');
  const restricted = structuredClone(context); restricted.a2ui.allowedFunctions = ['sendMsgToXiaoyi','formatNumber'];
  assert.ok(validateMessages(sample,catalog,restricted).errors.some(error => error.includes('calculateNumber 未在')));
});

test('ChoicePicker 单选使用数组，拒绝字符串、多个选择和重复选项值', async () => {
  const messages = await load('selection-single');
  assert.deepEqual(validateMessages(messages,catalog,context).errors,[]);
  const data = messages.at(-1).updateDataModel.value;
  data.priority = '高';
  assert.ok(validateMessages(messages,catalog,context).errors.some(error => error.includes('字符串数组')));
  data.priority = ['高','中'];
  assert.ok(validateMessages(messages,catalog,context).errors.some(error => error.includes('单选不能')));
  data.priority = [];
  const picker = messages[1].updateComponents.components.find(node => node.component === 'ChoicePicker');
  picker.options[1].value = picker.options[0].value;
  assert.ok(validateMessages(messages,catalog,context).errors.some(error => error.includes('value 必须唯一')));
});

test('消息 envelope 拒绝非对象以及操作体额外属性', () => {
  for (const value of ['text',1,null,[],{}]) assert.ok(validateMessages([value],catalog,context).errors.length);
  const messages = minimal(); messages[1].updateComponents.unknown = true;
  assert.ok(validateMessages(messages,catalog,context).errors.some(error => error.includes('不支持属性 unknown')));
  assert.equal(schemaErrors('anything',false,catalog).length,1);
});

test('引用图拒绝缺失引用、多父节点和循环，允许跨消息更新现有 ID', () => {
  const messages = minimal(), nodes = messages[1].updateComponents.components;
  nodes[0].children.push('missing');
  assert.ok(validateMessages(messages,catalog,context).errors.some(error => error.includes('不存在')));
  nodes[0].children.pop(); nodes.push({id:'button',component:'Button',child:'text',action:{functionCall:{call:'sendMsgToXiaoyi',args:{query:'继续'}}}}); nodes[0].children.push('button');
  assert.ok(validateMessages(messages,catalog,context).errors.some(error => error.includes('多个父节点')));
  nodes.splice(2); nodes[0].children = ['root'];
  assert.ok(validateMessages(messages,catalog,context).errors.some(error => error.includes('循环')));
  nodes[0].children = ['text'];
  messages.push({version:'v0.9',updateComponents:{surfaceId:'test',components:[{id:'text',component:'Text',text:'新的完整回答'}]}});
  assert.deepEqual(validateMessages(messages,catalog,context).errors,[]);
  nodes.push({...nodes[1]});
  assert.ok(validateMessages(messages,catalog,context).errors.some(error => error.includes('ID 重复')));
});

test('query 插值不递归解释选项文本，空值、数值和损坏模板不发送', () => {
  assert.equal(interpolateQuery({a:'${b}',b:'原值',query:'${a}，${b}'}),'${b}，原值');
  for (const value of [[], '', false, 4, null, undefined]) assert.throws(() => interpolateQuery({a:value,query:'${a}'}));
  assert.throws(() => interpolateQuery({query:'请给出${missing'}),/格式错误/);
  assert.throws(() => interpolateQuery({extra:'未用到',query:'继续'}),/不完整/);
});

test('路径拒绝原型写入和非法数组索引，校验失败不污染进程', () => {
  assert.throws(() => setPath({},'/__proto__/polluted',true),/原型/);
  assert.equal({}.polluted,undefined);
  assert.throws(() => getPath({},'/constructor/prototype'),/原型/);
  const messages = minimal();
  messages.push({version:'v0.9',updateDataModel:{surfaceId:'test',path:'/__proto__/polluted',value:true}});
  assert.ok(validateMessages(messages,catalog,context).errors.some(error => error.includes('原型')));
});

test('数据模型多次局部更新与 surface 删除符合生命周期', () => {
  const messages = minimal();
  messages.push({version:'v0.9',updateDataModel:{surfaceId:'test',path:'/form',value:{people:'4',note:'临时'}}});
  messages.push({version:'v0.9',updateDataModel:{surfaceId:'test',path:'/form/people',value:'6'}});
  messages.push({version:'v0.9',updateDataModel:{surfaceId:'test',path:'/form/note'}});
  let result = validateMessages(messages,catalog,context);
  assert.deepEqual(result.errors,[]); assert.deepEqual(result.model,{form:{people:'6'}});
  messages.push({version:'v0.9',deleteSurface:{surfaceId:'test'}});
  result = validateMessages(messages,catalog,context); assert.deepEqual(result.errors,[]); assert.equal(result.deleted,true);
  messages.push({version:'v0.9',updateDataModel:{surfaceId:'test',value:{}}});
  assert.ok(validateMessages(messages,catalog,context).errors.some(error => error.includes('已删除')));
});
