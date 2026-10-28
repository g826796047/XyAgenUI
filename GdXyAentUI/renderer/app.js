import {JsonlStream, getPath, setPath, isObject, resolveDynamic, resolveCallArguments, validateMessages, interpolateQuery} from './core.js';

const $ = id => typeof document === 'undefined' ? null : document.getElementById(id);
const node = (tag, className, text) => { const element = document.createElement(tag); if (className) element.className = className; if (text !== undefined) element.textContent = String(text); return element; };
const deepClone = value => typeof structuredClone === 'function' ? structuredClone(value) : JSON.parse(JSON.stringify(value));
const iconGlyphs = {locationOn:'⌖',info:'ⓘ',warning:'⚠',check:'✓',close:'×',star:'★',home:'⌂',search:'⌕',favorite:'♥',calendarToday:'▦',arrowForward:'→',arrowBack:'←',play:'▶',pause:'Ⅱ'};

function simpleMarkdown(value) {
  let text = String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>').replace(/`([^`]+)`/g, '<code>$1</code>');
  return text.replace(/\n/g, '<br>');
}

function renderChart(component, data) {
  const wrapper = node('div', `a2ui-chart chart-${component.chartType || 'bar'}`), series = Array.isArray(data.series) ? data.series : [];
  if (!series.length || !Array.isArray(series[0].data) || !series[0].data.length) { wrapper.textContent = '图表暂无数据'; return wrapper; }
  const points = series[0].data, max = Math.max(1, ...points.map(item => Number(item.value) || 0));
  if (component.chartType === 'donut') {
    const total = points.reduce((sum, item) => sum + Math.max(0, Number(item.value) || 0), 0) || 1; let cursor = 0;
    const colors = ['#176c73','#d47a4a','#83a95b','#687fbd','#d5ad45']; const slices = points.map((item,index) => { const start=cursor; cursor += Math.max(0, Number(item.value)||0) / total * 100; return `${colors[index % colors.length]} ${start}% ${cursor}%`; });
    const donut = node('div', 'chart-donut'); donut.style.background = `conic-gradient(${slices.join(',')})`; donut.setAttribute('role','img'); donut.setAttribute('aria-label','环形图'); wrapper.append(donut);
    points.forEach((item,index) => wrapper.append(node('div','chart-legend',`${item.label || `项目 ${index+1}`}：${item.value}`)));
    return wrapper;
  }
  const svgNS = 'http://www.w3.org/2000/svg', svg = document.createElementNS(svgNS,'svg'); svg.setAttribute('viewBox','0 0 360 180'); svg.setAttribute('role','img'); svg.setAttribute('aria-label',component.chartType === 'line' ? '折线图' : '柱状图');
  const axis = document.createElementNS(svgNS,'path'); axis.setAttribute('d','M32 12V145H350'); axis.setAttribute('stroke','#ccd7da'); axis.setAttribute('fill','none'); svg.append(axis);
  const width = 292 / points.length, color = '#176c73';
  points.forEach((point,index) => { const value = Math.max(0,Number(point.value)||0), height = value / max * 112, x=36+index*width+width*.2, y=143-height;
    if (component.chartType === 'line') { const dot=document.createElementNS(svgNS,'circle'); dot.setAttribute('cx',String(x+width*.3)); dot.setAttribute('cy',String(y)); dot.setAttribute('r','4'); dot.setAttribute('fill',color); svg.append(dot); }
    else { const bar=document.createElementNS(svgNS,'rect'); bar.setAttribute('x',String(x)); bar.setAttribute('y',String(y)); bar.setAttribute('width',String(width*.6)); bar.setAttribute('height',String(height)); bar.setAttribute('rx','3'); bar.setAttribute('fill',color); svg.append(bar); }
    const label=document.createElementNS(svgNS,'text'); label.setAttribute('x',String(x+width*.3)); label.setAttribute('y','164'); label.setAttribute('text-anchor','middle'); label.setAttribute('font-size','10'); label.setAttribute('fill','#66777d'); label.textContent = data.xAxis?.[index] || point.label || `${index+1}`; svg.append(label);
  });
  if (component.chartType === 'line') { const path=document.createElementNS(svgNS,'polyline'); const coords=points.map((point,index)=>`${36+index*width+width*.5},${143-(Math.max(0,Number(point.value)||0)/max*112)}`).join(' '); path.setAttribute('points',coords); path.setAttribute('fill','none'); path.setAttribute('stroke',color); path.setAttribute('stroke-width','3'); svg.insertBefore(path,svg.children[1]||null); }
  wrapper.append(svg); return wrapper;
}

function safeUrl(value, context = {}) {
  if (typeof value !== 'string') return '';
  try {
    const url = new URL(value, location.href);
    if (url.origin === location.origin && url.pathname.startsWith('/examples/')) return url.href;
    const allowed = context?.a2ui?.allowedResourceDomains || [];
    return ['http:', 'https:'].includes(url.protocol) && allowed.includes(url.hostname) ? url.href : '';
  } catch { return ''; }
}

function cssValue(value) {
  if (typeof value === 'number') return `${value}px`;
  return value == null ? '' : String(value);
}

function applyStyles(element, component, model, scope) {
  const styles = component.styles || {};
  for (const [key, raw] of Object.entries(styles)) {
    let value;
    try { value = resolveDynamic(raw, model, scope); } catch { continue; }
    const css = key.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`);
    if (value !== undefined && value !== null && !/url\s*\(|@import/i.test(String(value))) element.style.setProperty(css, typeof value === 'number' && ['font-weight','opacity','flex-grow','flex-shrink','order','z-index','line-height'].includes(css) ? String(value) : cssValue(value));
  }
  if (component.weight !== undefined) element.style.flexGrow = String(component.weight);
  const aligns = {start:'flex-start',end:'flex-end',center:'center',stretch:'stretch',baseline:'baseline'};
  const justifies = {start:'flex-start',end:'flex-end',center:'center',spaceBetween:'space-between',spaceAround:'space-around',spaceEvenly:'space-evenly','space-between':'space-between','space-around':'space-around','space-evenly':'space-evenly'};
  if (component.align && aligns[component.align]) element.style.alignItems = aligns[component.align];
  if (component.justify && justifies[component.justify]) element.style.justifyContent = justifies[component.justify];
  if (component.component === 'Image' && component.fit) element.style.objectFit = {fill:'fill',contain:'contain',cover:'cover',none:'none','scale-down':'scale-down'}[component.fit] || 'contain';
}

function markdownToSafeHtml(markdown) {
  let value = String(markdown ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  value = value.replace(/^### (.+)$/gm, '<h4>$1</h4>').replace(/^## (.+)$/gm, '<h3>$1</h3>').replace(/^# (.+)$/gm, '<h2>$1</h2>');
  value = value.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>').replace(/`([^`]+)`/g, '<code>$1</code>');
  value = value.replace(/^(?:- |\* )(.+)$/gm, '<li>$1</li>').replace(/(<li>.*<\/li>\n?)+/gs, chunk => `<ul>${chunk}</ul>`);
  return value.split(/\n{2,}/).map(part => /^<(h[2-4]|ul)/.test(part) ? part : `<p>${part.replace(/\n/g, '<br>')}</p>`).join('');
}

export class Playground {
  constructor(catalog, defaultContext) { this.catalog = catalog; this.defaultContext = defaultContext; this.reset(); }
  reset() {
    clearTimeout(this.timer); this.session = (this.session || 0) + 1; this.messages = []; this.nodes = new Map(); this.model = {};
    this.surfaceId = null; this.parser = null; this.started = false; this.complete = false; this.failed = false; this.cursor = 0; this.lines = [];
    this.deleted = false; this.tabs = {}; this.results = []; this.submitting = new Set(); this.submitted = new Set(); this.controlState = new Map(); this.playing = false; this.finishing = null;
    if ($('preview')) $('preview').replaceChildren(node('div', 'empty-state', '粘贴 A2UI JSONL 后开始渲染'));
    if ($('error-panel')) $('error-panel').hidden = true;
    if ($('result-panel')) $('result-panel').replaceChildren(node('p', 'inspector-empty', '点击回答中的确认按钮，这里会显示 FunctionCall 结果。'));
    if ($('messages-panel')) $('messages-panel').replaceChildren(node('p', 'inspector-empty', '解析与组件更新记录将出现在这里。'));
    if ($('surface-label')) $('surface-label').textContent = '等待创建 surface';
    if ($('progress-label')) $('progress-label').textContent = '0 / 0 条消息';
    if ($('result-count')) $('result-count').textContent = '0'; if ($('message-count')) $('message-count').textContent = '0';
    if ($('copy-result')) $('copy-result').disabled = true; if ($('status')) this.status('准备就绪');
  }
  status(text, state = '') { if ($('status')) { $('status').textContent = text; $('status').dataset.state = state; } }
  error(error) { this.failed = true; this.complete = false; if ($('error-text')) $('error-text').textContent = error.message || String(error); if ($('error-panel')) $('error-panel').hidden = false; this.status('校验失败', 'error'); this.render(); }
  begin(context) { this.reset(); this.context = deepClone(context || this.defaultContext); this.started = true; this.parser = new JsonlStream((message, line) => this.accept(message, line)); this.status('等待消息', 'streaming'); }
  prepare() {
    let context; try { context = JSON.parse($('context').value); } catch { throw new Error('运行时上下文不是有效 JSON'); }
    const source = $('source').value; if (!source.trim()) throw new Error('请先粘贴 A2UI JSONL 内容');
    this.begin(context); this.lines = source.split('\n').filter((line, index, all) => !(index === all.length - 1 && line === ''));
  }
  accept(message, line) {
    if (!isObject(message) || message.version !== 'v0.9') throw new Error(`第 ${line} 行：必须使用 A2UI v0.9`);
    const keys = ['createSurface', 'updateComponents', 'updateDataModel', 'deleteSurface'].filter(key => key in message);
    if (keys.length !== 1 || Object.keys(message).length !== 2) throw new Error(`第 ${line} 行：只能包含一个 A2UI 操作`);
    const kind = keys[0], body = message[kind]; if (!isObject(body)) throw new Error(`第 ${line} 行：${kind} 必须是对象`);
    if (kind === 'createSurface') {
      if (this.messages.length || body.catalogId !== this.catalog.catalogId || typeof body.surfaceId !== 'string') throw new Error(`第 ${line} 行：createSurface 无效`);
      this.surfaceId = body.surfaceId;
    } else {
      if (body.surfaceId !== this.surfaceId) throw new Error(`第 ${line} 行：surfaceId 不一致`);
      if (kind === 'updateComponents') {
        if (!Array.isArray(body.components) || !body.components.length) throw new Error(`第 ${line} 行：components 不能为空`);
        for (const component of body.components) { if (!isObject(component) || !component.id || !this.catalog.components[component.component]) throw new Error(`第 ${line} 行：组件 ID 或类型无效`); this.nodes.set(component.id, component); }
      } else if (kind === 'updateDataModel') this.model = setPath(this.model, body.path || '/', body.value, !('value' in body));
      else if (kind === 'deleteSurface') { this.nodes.clear(); this.model = {}; this.deleted = true; }
    }
    const firstMessage = this.messages.length === 0;
    this.messages.push(message); this.render();
    if ($('message-count')) $('message-count').textContent = String(this.messages.length);
    if ($('surface-label')) $('surface-label').textContent = this.surfaceId || '等待创建 surface';
    if ($('progress-label')) $('progress-label').textContent = `${this.messages.length} / ${this.lines.length || 0} 条消息`;
    if ($('messages-panel')) { if (firstMessage) $('messages-panel').replaceChildren(); $('messages-panel').append(node('div', 'message-entry', `${line} ${kind}`)); }
  }
  resolve(value, scope = {}) { return resolveDynamic(value, this.model, scope); }
  childrenFor(component, scope) {
    if (Array.isArray(component.children)) return component.children.map(id => ({id, scope}));
    if (isObject(component.children) && typeof component.children.componentId === 'string') {
      const list = this.resolve({path: component.children.path}, scope) || [];
      return Array.isArray(list) ? list.map(item => ({id: component.children.componentId, scope: item})) : [];
    }
    return [];
  }
  locked() { return !this.complete || this.submitting.size > 0; }
  valueAt(binding, scope = {}) { try { return this.resolve(binding, scope); } catch { return undefined; } }
  bindingPath(binding) { return isObject(binding) && typeof binding.path === 'string' && binding.path.startsWith('/') ? binding.path : null; }
  componentLabel(component, scope) { return this.valueAt(component.label, scope) ?? ''; }
  checkMessages(component, scope = {}) {
    const errors = [];
    for (const check of component.checks || []) { try { if (this.resolve(check.condition, scope) !== true) errors.push(check.message); } catch { errors.push(check.message); } }
    if (component.validationRegexp) { try { if (!new RegExp(component.validationRegexp).test(String(this.valueAt(component.value, scope) ?? ''))) errors.push('输入格式不正确'); } catch { errors.push('输入校验规则无效'); } }
    return errors;
  }
  canSubmit(component, scope = {}) {
    if (!component.action?.functionCall || this.checkMessages(component, scope).length) return false;
    if ([...this.nodes.values()].some(item => ['TextField','CheckBox','ChoicePicker','Slider','DateTimeInput'].includes(item.component) && this.checkMessages(item).length)) return false;
    try {
      const call = component.action.functionCall;
      if (!this.context?.a2ui?.allowedFunctions?.includes(call.call)) return false;
      if (call.call === 'sendMsgToXiaoyi') interpolateQuery(resolveCall(call.args || {}, this.model, scope, this));
      return true;
    } catch { return false; }
  }
  renderNode(id, ancestors = new Set(), scope = {}) {
    if (!this.nodes.has(id)) return node('div', 'component-error', `等待组件 ${id}`);
    if (ancestors.has(id)) return node('div', 'component-error', `检测到循环引用：${id}`);
    const component = this.nodes.get(id), next = new Set(ancestors).add(id), type = component.component;
    let element;
    const children = () => this.childrenFor(component, scope).map(item => this.renderNode(item.id, next, item.scope));
    if (['Column', 'Row', 'List'].includes(type)) {
      element = node('div', `a2ui-${type.toLowerCase()}`); if (type === 'List' && component.direction === 'horizontal') element.classList.add('horizontal');
      children().forEach(child => element.append(child));
    } else if (type === 'Card') { element = node('section', 'a2ui-card'); if (component.child) element.append(this.renderNode(component.child, next, scope)); }
    else if (type === 'Tabs') {
      element = node('section', 'a2ui-tabs'); const tabs = Array.isArray(component.tabs) ? component.tabs : []; const active = Math.min(Math.max(0, this.tabs[id] ?? 0), Math.max(tabs.length - 1, 0));
      const bar = node('div', 'a2ui-tab-bar'); tabs.forEach((tab, index) => { const button = node('button', 'a2ui-tab', this.valueAt(tab.title, scope) ?? `选项 ${index + 1}`); button.type = 'button'; button.disabled = this.locked(); button.setAttribute('aria-selected', String(index === active)); button.onclick = () => { this.tabs[id] = index; this.render(); }; bar.append(button); });
      element.append(bar); if (tabs[active]?.child) element.append(this.renderNode(tabs[active].child, next, scope));
    } else if (type === 'Modal') {
      element = node('div','a2ui-modal-container');
      const trigger = this.renderNode(component.trigger, next, scope), dialog = document.createElement('dialog'), close = node('button','a2ui-modal-close','关闭');
      dialog.className = 'a2ui-modal'; close.type = 'button'; close.onclick = () => dialog.close();
      trigger.setAttribute('role','button'); trigger.tabIndex = this.locked() ? -1 : 0;
      const open = () => { if (!this.locked() && !dialog.open) dialog.showModal(); };
      trigger.addEventListener('click', open); trigger.addEventListener('keydown', event => { if (['Enter',' '].includes(event.key)) { event.preventDefault(); open(); } });
      dialog.append(close, this.renderNode(component.content, next, scope)); element.append(trigger,dialog);
    }
    else if (type === 'Text') { element = node('div', `a2ui-text variant-${component.variant || 'body'}`); element.innerHTML = simpleMarkdown(this.valueAt(component.text, scope) ?? ''); }
    else if (type === 'Markdown') { element = node('div', 'a2ui-markdown'); element.innerHTML = markdownToSafeHtml(this.valueAt(component.content, scope) ?? ''); }
    else if (type === 'RichText') { element = node('div', 'a2ui-richtext', this.valueAt(component.text, scope) ?? ''); }
    else if (type === 'Image') { element = document.createElement('img'); element.className = 'a2ui-image'; const url = safeUrl(this.valueAt(component.url, scope), this.context); if (url) element.src = url; element.alt = url ? this.valueAt(component.description, scope) || '图片' : '图片资源不可用（需允许资源域名）'; }
    else if (type === 'Icon') { const name=this.valueAt(component.name, scope); element = node('span', 'a2ui-icon', typeof name === 'string' ? (iconGlyphs[name] || '◈') : '◈'); }
    else if (type === 'Video' || type === 'AudioPlayer') { element = document.createElement(type === 'Video' ? 'video' : 'audio'); element.className = `a2ui-${type.toLowerCase()}`; element.controls = true; const url = safeUrl(this.valueAt(component.url, scope), this.context); if (url) element.src = url; element.setAttribute('aria-label',this.valueAt(component.description, scope) || (url ? type : '未提供或未授权媒体资源')); }
    else if (type === 'Divider') { element = node('hr', `a2ui-divider ${component.axis === 'vertical' ? 'vertical' : ''}`); }
    else if (type === 'Button') {
      element = node('button', `a2ui-button variant-${component.variant || 'default'}`); element.type = 'button'; if (component.child) element.append(this.renderNode(component.child, next, scope));
      element.disabled = this.locked() || !this.canSubmit(component, scope) || this.submitted.has(id); element.onclick = () => this.submit(component, scope);
    } else if (type === 'TextField') {
      element = node('label', 'a2ui-field'); element.append(node('span', 'field-label', this.componentLabel(component, scope)));
      const input = component.variant === 'longText' ? document.createElement('textarea') : document.createElement('input'); input.className = 'a2ui-input'; input.type = component.variant === 'number' ? 'number' : component.variant === 'obscured' ? 'password' : 'text';
      const binding = this.bindingPath(component.value), value = binding ? getPath(this.model, binding) : (this.controlState.has(id) ? this.controlState.get(id) : this.valueAt(component.value, scope)); input.value = value == null ? '' : String(value); input.disabled = this.locked(); input.setAttribute('aria-label', this.componentLabel(component, scope));
      input.oninput = () => { if (binding) this.model = setPath(this.model, binding, input.value); else this.controlState.set(id,input.value); this.renderPreservingFocus(id); }; element.append(input);
    } else if (type === 'CheckBox') {
      element = node('label', 'choice-option'); const input = document.createElement('input'); input.type = 'checkbox'; const binding = this.bindingPath(component.value); input.checked = Boolean(binding ? getPath(this.model, binding) : (this.controlState.has(id) ? this.controlState.get(id) : this.valueAt(component.value, scope))); input.disabled = this.locked(); input.onchange = () => { if (binding) this.model = setPath(this.model, binding, input.checked); else this.controlState.set(id,input.checked); this.render(); }; element.append(input, node('span', 'option-label', this.componentLabel(component, scope)));
    } else if (type === 'ChoicePicker') {
      element = node('fieldset', 'a2ui-choice-picker'); const label = this.componentLabel(component, scope); if (label) element.append(node('legend', '', label));
      const multiple = component.variant === 'multipleSelection', binding = this.bindingPath(component.value), current = binding ? getPath(this.model, binding) : (this.controlState.has(id) ? this.controlState.get(id) : this.valueAt(component.value, scope)), selected = new Set(Array.isArray(current) ? current : []);
      for (const option of component.options || []) { const labelNode = node('label', 'choice-option'); const input = document.createElement('input'); input.type = multiple ? 'checkbox' : 'radio'; input.name = `${this.surfaceId}-${id}`; input.value = String(this.valueAt(option.value, scope) ?? ''); input.checked = selected.has(input.value); input.disabled = this.locked(); input.onchange = () => { const values = multiple ? new Set(selected) : new Set(); input.checked ? values.add(input.value) : values.delete(input.value); const result = (component.options || []).map(item => item.value).filter(value => values.has(value)); if (binding) this.model = setPath(this.model, binding, result); else this.controlState.set(id,result); this.render(); }; labelNode.append(input, node('span', 'option-label', this.valueAt(option.label, scope) ?? input.value)); element.append(labelNode); }
    } else if (type === 'Slider') {
      element = node('label', 'a2ui-field'); const input = document.createElement('input'); input.type = 'range'; input.min = String(this.valueAt(component.min, scope) ?? 0); input.max = String(this.valueAt(component.max, scope) ?? 100); input.step = 'any'; const binding = this.bindingPath(component.value); input.value = String(binding ? getPath(this.model, binding) ?? input.min : this.controlState.get(id) ?? this.valueAt(component.value, scope) ?? input.min); const valueLabel=node('span','field-label',`${this.componentLabel(component, scope)} ${input.value}`); input.disabled = this.locked(); input.oninput = () => { if (binding) this.model = setPath(this.model, binding, Number(input.value)); else this.controlState.set(id,Number(input.value)); this.renderPreservingFocus(id); }; element.append(valueLabel,input);
    } else if (type === 'DateTimeInput') {
      element = node('label', 'a2ui-field'); element.append(node('span', 'field-label', this.componentLabel(component, scope))); const input = document.createElement('input'); input.type = component.enableDate && component.enableTime ? 'datetime-local' : component.enableDate ? 'date' : 'time'; const binding = this.bindingPath(component.value); input.value = String(binding ? getPath(this.model, binding) ?? '' : this.controlState.get(id) ?? this.valueAt(component.value, scope) ?? ''); input.disabled = this.locked(); input.oninput = () => { if (binding) this.model = setPath(this.model, binding, input.value); else this.controlState.set(id,input.value); this.renderPreservingFocus(id); }; element.append(input);
    } else if (type === 'Table') {
      element = document.createElement('table'); element.className = 'a2ui-table'; const head = document.createElement('thead'); const row = document.createElement('tr'); for (const column of this.valueAt(component.columns, scope) || []) row.append(node('th', '', column)); head.append(row); element.append(head); const body = document.createElement('tbody'); for (const values of this.valueAt(component.rows, scope) || []) { const tr = document.createElement('tr'); for (const value of values) tr.append(node('td', '', value)); body.append(tr); } element.append(body);
    } else if (type === 'Carousel') { element = node('div', 'a2ui-carousel'); for (const url of this.valueAt(component.content, scope) || []) { const image = document.createElement('img'), safe = safeUrl(url, this.context); if (safe) image.src = safe; image.alt = safe ? '轮播图片' : '轮播图片资源不可用'; element.append(image); } }
    else if (type === 'Chart') { element = renderChart(component, this.valueAt(component.data, scope) || {}); }
    else if (type === 'Lottie') { element = node('div', 'a2ui-placeholder', 'Lottie 由宿主 renderer 注册后呈现'); }
    else if (type === 'Web') { element = node('div', 'a2ui-placeholder', 'Web 资源由宿主安全策略控制'); }
    else element = node('div', 'component-error', `参考 renderer 暂不呈现：${type}`);
    const validation = this.complete ? this.checkMessages(component, scope) : [];
    if (validation.length && ['TextField','CheckBox','ChoicePicker','Slider','DateTimeInput'].includes(type)) element.append(node('span','component-validation',validation.join('；')));
    element.dataset.componentId = id; applyStyles(element, component, this.model, scope); return element;
  }
  renderPreservingFocus(id) { const active = document.activeElement, start = active?.selectionStart, end = active?.selectionEnd; this.render(); const replacement = document.querySelector(`[data-component-id="${CSS.escape(id)}"] input, [data-component-id="${CSS.escape(id)}"] textarea`); replacement?.focus(); if (typeof start === 'number' && ['text','search','password','tel','url',undefined].includes(replacement?.type) && typeof replacement?.setSelectionRange === 'function') replacement.setSelectionRange(start, end); }
  render() {
    if (!$('preview')) return;
    if (this.deleted) { $('preview').replaceChildren(node('div', 'empty-state', 'Surface 已删除')); return; }
    if (this.nodes.has('root')) {
      $('preview').replaceChildren(this.renderNode('root'));
    }
  }
  async submit(component, scope) {
    const id = component.id, functionCall = component.action?.functionCall, session = this.session; if (!functionCall || this.locked() || this.submitted.has(id) || !this.canSubmit(component, scope)) return; this.submitting.add(id); this.render();
    try {
      const args = resolveCall(functionCall.args || {}, this.model, scope, this); let detail;
      if (functionCall.call === 'sendMsgToXiaoyi') { const query = interpolateQuery(args); detail = {query, functionCall: {call: functionCall.call, args: {...args, query}}, surfaceId: this.surfaceId}; }
      else if (['openSuperlink', 'openApplink', 'openDeeplink', 'openUrl'].includes(functionCall.call)) detail = {link: args, functionCall: {call: functionCall.call, args}, surfaceId: this.surfaceId};
      else detail = {functionCall: {call: functionCall.call, args}, value: args, surfaceId: this.surfaceId};
      if (window.gdXyAgenUiHost?.onFunctionCall) await window.gdXyAgenUiHost.onFunctionCall(deepClone(detail));
      if (session !== this.session) return;
      this.submitted.add(id); this.results.push(detail); this.showResult(detail); window.dispatchEvent(new CustomEvent('gdxy-a2ui:functioncall', {detail}));
    } catch (error) { if (session === this.session) { const detail = {error: error.message, functionCall, surfaceId: this.surfaceId}; this.results.push(detail); this.showResult(detail); } }
    finally { if (session === this.session) { this.submitting.delete(id); this.render(); } }
  }
  showResult(detail) { const panel = $('result-panel'); if (!panel) return; if (this.results.length === 1) panel.replaceChildren(); const entry = node('article', 'query-entry'); entry.append(node('header', '', detail.error ? '函数调用失败' : detail.functionCall?.call || '交互结果'), node('pre', '', detail.error || detail.query || JSON.stringify(detail.functionCall, null, 2))); panel.append(entry); if ($('result-count')) $('result-count').textContent = String(this.results.length); if ($('copy-result')) { $('copy-result').disabled = !detail.query; $('copy-result').onclick = () => navigator.clipboard.writeText(detail.query); } }
  async finish() {
    if (this.complete) return;
    if (this.finishing) return this.finishing;
    const session = this.session;
    if (!this.parser) throw new Error('请先开始消息流');
    if (!this.parser.closed) this.parser.finish();
    this.finishing = (async () => {
      const result = await request('/api/validate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:this.messages,context:this.context})});
      if (session !== this.session) return;
      if (!result.valid) throw new Error(result.error || 'A2UI 校验失败');
      this.complete = true; this.render(); this.status('已完成','complete');
    })();
    try { await this.finishing; } finally { if (session === this.session) this.finishing = null; }
  }
  async instant() {
    let session = this.session;
    try { this.prepare(); session=this.session; while (this.cursor < this.lines.length) this.parser.push(`${this.lines[this.cursor++]}\n`); await this.finish(); }
    catch (error) { if (session === this.session) this.error(error); }
  }
  async step() {
    if (this.playing || this.finishing) return;
    let session = this.session;
    try { if (!this.started || this.complete || this.failed) this.prepare(); session=this.session; if (this.cursor < this.lines.length) this.parser.push(`${this.lines[this.cursor++]}\n`); if (this.cursor === this.lines.length) await this.finish(); }
    catch (error) { if (session === this.session) this.error(error); }
  }
  async play() {
    if (this.playing || this.finishing) return;
    let session = this.session;
    try {
      if (!this.started || this.complete || this.failed) this.prepare(); session=this.session; this.playing=true;
      while (this.cursor < this.lines.length && session === this.session) { this.parser.push(`${this.lines[this.cursor++]}\n`); await new Promise(resolve => setTimeout(resolve,Number($('speed')?.value)||220)); }
      if (session === this.session && this.cursor === this.lines.length) await this.finish();
    } catch (error) { if (session === this.session) this.error(error); }
    finally { if (session === this.session) this.playing=false; }
  }
}

function resolveCall(value, model, scope, app) {
  return resolveCallArguments(value, model, scope, app.context?.a2ui?.allowedFunctions);
}
async function request(url, options) { const response = await fetch(url, options); const data = await response.json(); if (!response.ok) throw new Error(data.error || `请求失败：${response.status}`); return data; }

async function bootstrap() {
  if (!$('source')) return;
  try {
    const data = await request('/api/bootstrap'), app = new Playground(data.catalog, data.context);
    const updateSourceMeta = () => {
      const source = $('source'), stats = $('source-stats'), gutter = $('line-gutter');
      if (!source) return;
      const value = source.value || '', lines = value ? value.split(/\r?\n/).length : 0;
      if (stats) stats.textContent = `${lines} 行 · ${(new Blob([value]).size / 1024).toFixed(1)} KB`;
      if (gutter) gutter.textContent = lines ? Array.from({length: lines}, (_item, index) => String(index + 1)).join('\n') : '1';
    };
    const showToast = message => {
      const toast = $('toast'); if (!toast) return;
      toast.textContent = message; toast.hidden = false; clearTimeout(showToast.timer);
      showToast.timer = setTimeout(() => { toast.hidden = true; }, 2200);
    };
    for (const scenario of data.scenarios) { const option = document.createElement('option'); option.value = scenario.id; option.textContent = scenario.title || scenario.id; $('sample')?.append(option); }
    async function load() { const id = $('sample')?.value; if (!id) return; const sample = await request(`/api/example?id=${encodeURIComponent(id)}`); $('source').value = sample.text; $('context').value = JSON.stringify(sample.context, null, 2); app.reset(); updateSourceMeta(); }
    $('sample')?.addEventListener('change', load);
    $('load-sample')?.addEventListener('click', load);
    $('import-button')?.addEventListener('click', () => $('import-file')?.click());
    $('import-file')?.addEventListener('change', async event => {
      const file = event.target.files?.[0]; if (!file) return;
      try { $('source').value = await file.text(); $('sample').value = ''; app.reset(); updateSourceMeta(); showToast(`已导入 ${file.name}`); }
      catch (error) { showToast(`导入失败：${error.message}`); }
      event.target.value = '';
    });
    $('source')?.addEventListener('input', updateSourceMeta);
    $('source')?.addEventListener('scroll', () => { if ($('line-gutter')) $('line-gutter').scrollTop = $('source').scrollTop; });
    document.querySelectorAll('[data-viewport]').forEach(button => button.addEventListener('click', () => {
      const narrow = button.dataset.viewport === 'narrow'; $('preview-frame')?.classList.toggle('narrow', narrow);
      document.querySelectorAll('[data-viewport]').forEach(item => { const active = item === button; item.classList.toggle('active', active); item.setAttribute('aria-pressed', String(active)); });
    }));
    const selectInspectorTab = tab => {
      const result = tab === 'result'; $('result-panel').hidden = !result; $('messages-panel').hidden = result;
      $('result-tab').classList.toggle('active', result); $('messages-tab').classList.toggle('active', !result);
      $('result-tab').setAttribute('aria-selected', String(result)); $('messages-tab').setAttribute('aria-selected', String(!result));
    };
    $('result-tab')?.addEventListener('click', () => selectInspectorTab('result'));
    $('messages-tab')?.addEventListener('click', () => selectInspectorTab('messages'));
    $('instant')?.addEventListener('click', () => app.instant());
    $('step')?.addEventListener('click', () => app.step());
    $('play')?.addEventListener('click', () => app.play());
    $('reset')?.addEventListener('click', () => { app.reset(); updateSourceMeta(); });
    $('default-context')?.addEventListener('click', () => { $('context').value = JSON.stringify(data.context, null, 2); showToast('已恢复默认上下文'); });
    window.gdXyA2uiPreview = {
      start: context => app.begin(context),
      push: chunk => { try { if (!app.parser) throw new Error('请先调用 start'); app.parser.push(chunk); } catch (error) { app.error(error); throw error; } },
      finish: async () => { try { await app.finish(); } catch (error) { app.error(error); throw error; } },
      cancel: () => app.reset(),
      getState: () => ({complete:app.complete,failed:app.failed,messages:app.messages.length,surfaceId:app.surfaceId}),
    };
    if ($('sample')) { $('sample').value = data.scenarios[0]?.id || ''; await load(); await app.instant(); }
    updateSourceMeta();
  } catch (error) { if ($('error-text')) $('error-text').textContent = error.message; if ($('error-panel')) $('error-panel').hidden = false; }
}
if (typeof document !== 'undefined') bootstrap();
