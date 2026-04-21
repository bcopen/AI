/**
 * 稳定选择器生成算法模块
 * 按优先级生成可重用的选择器：data-testid → id → role+text/aria-label → tag.class
 * 
 * @module selector
 */

/**
 * 生成稳定的元素选择器
 * @param {Element} element - 目标 DOM 元素
 * @returns {string|null} 生成的选择器字符串
 */
export function generateSelector(element) {
  if (!element || element.nodeType !== 1) return null;

  // 优先级 1: data-testid
  const testId = element.getAttribute?.('data-testid');
  if (testId && isValidSelectorValue(testId)) {
    return `[data-testid="${escapeSelector(testId)}"]`;
  }

  // 优先级 2: id
  if (element.id && isValidSelectorValue(element.id)) {
    return `#${escapeSelector(element.id)}`;
  }

  // 优先级 3: aria-label
  const ariaLabel = element.getAttribute?.('aria-label');
  if (ariaLabel && isValidSelectorValue(ariaLabel)) {
    return `[aria-label="${escapeSelector(ariaLabel)}"]`;
  }

  // 优先级 4: role + text (for buttons, links, etc.)
  const role = element.getAttribute?.('role');
  if (role) {
    const text = getElementText(element).trim();
    if (text && text.length < 100) {
      return `[role="${escapeSelector(role)}"]`;
    }
  }

  // 优先级 5: name attribute (for inputs)
  const nameAttr = element.getAttribute?.('name');
  if (nameAttr && isValidSelectorValue(nameAttr)) {
    const tagName = element.tagName?.toLowerCase() || 'input';
    return `${tagName}[name="${escapeSelector(nameAttr)}"]`;
  }

  // 优先级 6: tag + class combination (filter dynamic classes)
  const stableClasses = getStableClasses(element);
  const tagName = element.tagName?.toLowerCase() || '*';
  
  if (stableClasses.length > 0) {
    return `${tagName}.${stableClasses.map(c => escapeSelector(c)).join('.')}`;
  }

  // 优先级 7: tag + nth-child fallback
  return generateNthChildSelector(element);
}

/**
 * 获取元素的稳定类名（排除动态生成的类）
 * @param {Element} element - DOM 元素
 * @returns {string[]} 稳定的类名数组
 */
function getStableClasses(element) {
  const className = element.className;
  if (!className || typeof className !== 'string') return [];

  // 过滤掉常见的动态类名前缀
  const dynamicPrefixes = [
    'css-', 'style-', 'sc-', '_-', 'tmp-', 
    'animation-', 'transition-', 'hover-', 'focus-',
    'active-', 'visited-', 'before', 'after'
  ];

  return className.split(/\s+/).filter(cls => {
    if (!cls || cls.length === 0) return false;
    // 排除看起来像哈希的类名
    if (/^[a-f0-9]{6,}$/i.test(cls)) return false;
    // 排除动态前缀
    return !dynamicPrefixes.some(prefix => cls.startsWith(prefix));
  });
}

/**
 * 生成 nth-child 选择器作为最后的手段
 * @param {Element} element - DOM 元素
 * @returns {string} nth-child 选择器
 */
function generateNthChildSelector(element) {
  const path = [];
  let current = element;

  while (current && current.nodeType === 1) {
    const parent = current.parentElement;
    if (!parent) break;

    const siblings = Array.from(parent.children).filter(
      el => el.tagName === current.tagName && el.nodeType === 1
    );

    if (siblings.length > 1) {
      const index = siblings.indexOf(current) + 1;
      const tagName = current.tagName.toLowerCase();
      path.unshift(`${tagName}:nth-child(${index})`);
    } else {
      const tagName = current.tagName.toLowerCase();
      path.unshift(tagName);
    }

    current = parent;
  }

  return path.length > 0 ? path.join(' > ') : '*';
}

/**
 * 获取元素的可见文本内容
 * @param {Element} element - DOM 元素
 * @returns {string} 文本内容
 */
function getElementText(element) {
  return element.textContent?.replace(/\s+/g, ' ').trim() || '';
}

/**
 * 验证选择器值是否安全
 * @param {string} value - 选择器值
 * @returns {boolean} 是否有效
 */
function isValidSelectorValue(value) {
  return value && value.length > 0 && value.length < 200;
}

/**
 * 转义 CSS 选择器特殊字符
 * @param {string} str - 原始字符串
 * @returns {string} 转义后的字符串
 */
function escapeSelector(str) {
  if (!str) return '';
  // CSS.escape polyfill for basic cases
  return str.replace(/["'\\]/g, '\\$&');
}

/**
 * 将选择器转换为 Playwright Locator 策略
 * @param {string} selector - 原始选择器
 * @returns {{type: string, value: string}} Locator 策略对象
 */
export function parseSelectorForLocator(selector) {
  // data-testid
  const testIdMatch = selector.match(/^\[data-testid="([^"]+)"\]$/);
  if (testIdMatch) {
    return { type: 'testid', value: testIdMatch[1] };
  }

  // id
  const idMatch = selector.match(/^#(.+)$/);
  if (idMatch) {
    return { type: 'id', value: idMatch[1] };
  }

  // aria-label
  const ariaLabelMatch = selector.match(/^\[aria-label="([^"]+)"\]$/);
  if (ariaLabelMatch) {
    return { type: 'label', value: ariaLabelMatch[1] };
  }

  // role
  const roleMatch = selector.match(/^\[role="([^"]+)"\]$/);
  if (roleMatch) {
    return { type: 'role', value: roleMatch[1] };
  }

  // default: css selector
  return { type: 'css', value: selector };
}
