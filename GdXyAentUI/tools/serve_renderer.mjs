import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateMessages} from '../renderer/core.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const webRoot = path.join(root, 'renderer');
const catalog = JSON.parse(await readFile(path.join(root, 'references/agenui/gdxy_catalog.json'), 'utf8'));
const scenarios = JSON.parse(await readFile(path.join(root, 'examples/scenarios.json'), 'utf8'));
const port = Number(process.env.GDXY_PORT || 8766);
const allFunctions = Object.keys(catalog.functions);
const defaultContext = {
  a2ui: {
    catalogId: catalog.catalogId,
    allowedComponents: Object.keys(catalog.components),
    allowedFunctions: allFunctions,
    allowedResourceDomains: [],
  },
};

const contentTypes = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.json':'application/json; charset=utf-8','.jsonl':'application/jsonl; charset=utf-8'};
const json = (response, status, value) => { const data = JSON.stringify(value); response.writeHead(status, {'Content-Type':'application/json; charset=utf-8','Content-Length':Buffer.byteLength(data)}); response.end(data); };
const readBody = request => new Promise((resolve, reject) => { const chunks=[]; let size=0; request.on('data', chunk => { size += chunk.length; if (size > 8*1024*1024) reject(new Error('请求体过大')); else chunks.push(chunk); }); request.on('end', () => { try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')); } catch (error) { reject(new Error(`JSON 无效：${error.message}`)); } }); request.on('error', reject); });
function safePath(base, requestPath) { const relative = requestPath.replace(/^\/+/, '') || 'index.html'; const target = path.resolve(base, relative); return target === base || target.startsWith(`${base}${path.sep}`) ? target : null; }
async function staticFile(response, requestPath) {
  let base = webRoot, relative = requestPath;
  if (requestPath.startsWith('/examples/')) { base = path.join(root, 'examples'); relative = requestPath.slice('/examples/'.length); }
  const target = safePath(base, relative); if (!target) return json(response, 403, {error:'禁止访问'});
  try { const data = await readFile(target); response.writeHead(200, {'Content-Type': contentTypes[path.extname(target).toLowerCase()] || 'application/octet-stream'}); response.end(data); }
  catch { json(response, 404, {error:'文件不存在'}); }
}
async function handle(request, response) {
  const url = new URL(request.url, `http://${request.headers.host || '127.0.0.1'}`);
  try {
    if (request.method === 'GET' && url.pathname === '/api/bootstrap') return json(response, 200, {catalog, context: defaultContext, scenarios});
    if (request.method === 'GET' && url.pathname === '/api/example') {
      const id = url.searchParams.get('id'), item = scenarios.find(entry => entry.id === id); if (!item) return json(response, 404, {error:'样例不存在'});
      const text = await readFile(path.join(root, 'examples', `${id}.jsonl`), 'utf8');
      let context = defaultContext; try { context = JSON.parse(await readFile(path.join(root, 'examples', 'runtime-context.json'), 'utf8')); } catch {}
      return json(response, 200, {text, context, query: item.query});
    }
    if (request.method === 'POST' && url.pathname === '/api/validate') {
      const payload = await readBody(request), result = validateMessages(payload.messages, catalog, payload.context || defaultContext);
      if (result.errors.length) return json(response, 422, {valid:false, error:result.errors.join('\n'), errors:result.errors});
      return json(response, 200, {valid:true, componentCount:result.nodes.size, dataModel:result.model, surfaceId:result.surfaceId});
    }
    if (request.method === 'GET') return staticFile(response, url.pathname);
    json(response, 405, {error:'不支持的请求'});
  } catch (error) { json(response, 400, {error:error.message || String(error)}); }
}
createServer(handle).listen(port, '127.0.0.1', () => console.log(`GdXyAentUI renderer: http://127.0.0.1:${port}`));
