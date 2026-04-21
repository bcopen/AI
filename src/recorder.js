/**
 * 录制模块 - 注入脚本与事件采集逻辑
 * 通过 page.evaluate 向页面注入事件监听脚本，捕获用户交互
 * 
 * @module recorder
 */

import { generateSelector } from './selector.js';
import { sanitize, throttle } from './utils.js';

/**
 * 录制器配置
 * @typedef {Object} RecorderConfig
 * @property {number} [inputThrottleMs=100] - input 事件节流时间
 * @property {number} [scrollDebounceMs=200] - scroll 事件防抖时间
 * @property {boolean} [sanitizeSensitive=true] - 是否脱敏敏感信息
 */

/**
 * 录制事件数据结构
 * @typedef {Object} RecordedEvent
 * @property {string} type - 事件类型
 * @property {string} selector - 元素选择器
 * @property {string} [value] - 输入值或其他数据
 * @property {number} [x] - X 坐标
 * @property {number} [y] - Y 坐标
 * @property {number} timestamp - 时间戳
 * @property {string[]} [framePath] - iframe 路径
 */

/**
 * 生成注入到页面的录制脚本
 * @param {RecorderConfig} config - 录制配置
 * @returns {string} 可注入的脚本字符串
 */
export function generateInjectionScript(config = {}) {
  const inputThrottleMs = config.inputThrottleMs ?? 100;
  const scrollDebounceMs = config.scrollDebounceMs ?? 200;
  const sanitizeSensitive = config.sanitizeSensitive ?? true;

  return `(${function(config) {
    // 严格模式，避免全局污染
    'use strict';

    const INPUT_THROTTLE_MS = config.inputThrottleMs;
    const SCROLL_DEBOUNCE_MS = config.scrollDebounceMs;
    const SANITIZE_SENSITIVE = config.sanitizeSensitive;

    // 存储录制的事件
    const recordedEvents = [];
    
    // 滚动事件合并状态
    let pendingScroll = null;
    let scrollTimeout = null;

    /**
     * 生成稳定的元素选择器
     */
    function generateSelector(element) {
      if (!element || element.nodeType !== 1) return null;

      // 优先级 1: data-testid
      const testId = element.getAttribute?.('data-testid');
      if (testId && isValidSelectorValue(testId)) {
        return '[data-testid="' + escapeSelector(testId) + '"]';
      }

      // 优先级 2: id
      if (element.id && isValidSelectorValue(element.id)) {
        return '#' + escapeSelector(element.id);
      }

      // 优先级 3: aria-label
      const ariaLabel = element.getAttribute?.('aria-label');
      if (ariaLabel && isValidSelectorValue(ariaLabel)) {
        return '[aria-label="' + escapeSelector(ariaLabel) + '"]';
      }

      // 优先级 4: role
      const role = element.getAttribute?.('role');
      if (role) {
        return '[role="' + escapeSelector(role) + '"]';
      }

      // 优先级 5: name attribute
      const nameAttr = element.getAttribute?.('name');
      if (nameAttr && isValidSelectorValue(nameAttr)) {
        const tagName = (element.tagName || 'input').toLowerCase();
        return tagName + '[name="' + escapeSelector(nameAttr) + '"]';
      }

      // 优先级 6: tag + stable classes
      const stableClasses = getStableClasses(element);
      const tagName = (element.tagName || '*').toLowerCase();
      
      if (stableClasses.length > 0) {
        return tagName + '.' + stableClasses.map(c => escapeSelector(c)).join('.');
      }

      // 优先级 7: nth-child fallback
      return generateNthChildSelector(element);
    }

    function getStableClasses(element) {
      const className = element.className;
      if (!className || typeof className !== 'string') return [];

      const dynamicPrefixes = [
        'css-', 'style-', 'sc-', '_-', 'tmp-',
        'animation-', 'transition-', 'hover-', 'focus-'
      ];

      return className.split(/\\s+/).filter(cls => {
        if (!cls || cls.length === 0) return false;
        if (/^[a-f0-9]{6,}$/i.test(cls)) return false;
        return !dynamicPrefixes.some(prefix => cls.startsWith(prefix));
      });
    }

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
          path.unshift(tagName + ':nth-child(' + index + ')');
        } else {
          path.unshift(current.tagName.toLowerCase());
        }

        current = parent;
      }

      return path.length > 0 ? path.join(' > ') : '*';
    }

    function isValidSelectorValue(value) {
      return value && value.length > 0 && value.length < 200;
    }

    function escapeSelector(str) {
      if (!str) return '';
      return str.replace(/["'\\\\]/g, '\\\\$&');
    }

    /**
     * 检测并脱敏敏感信息
     */
    function sanitize(value) {
      if (!value || typeof value !== 'string') return value;
      
      // 短密码特征
      if (value.length <= 50 && /[!@#$%^&*(),.?":{}|<>]/.test(value)) {
        return '***';
      }
      
      // 邮箱
      if (/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(value)) {
        return '***';
      }
      
      // 电话
      if (/^[\\d\\s\\-\\+\\(\\)]{8,20}$/.test(value)) {
        return '***';
      }
      
      return value;
    }

    /**
     * 获取 iframe 路径
     */
    function getFramePath(element) {
      const path = [];
      let currentWindow = window;
      
      while (currentWindow !== window.top) {
        try {
          const frameElement = currentWindow.frameElement;
          if (!frameElement) break;
          
          const selector = generateSelector(frameElement);
          if (selector) {
            path.unshift(selector);
          }
          currentWindow = currentWindow.parent;
        } catch (e) {
          // 跨域 iframe 无法访问
          break;
        }
      }
      
      return path.length > 0 ? path : undefined;
    }

    /**
     * 记录事件
     */
    function recordEvent(event) {
      const eventData = {
        type: event.type,
        selector: event.selector,
        timestamp: Date.now()
      };

      if (event.value !== undefined) {
        eventData.value = event.value;
      }
      if (event.x !== undefined) {
        eventData.x = event.x;
      }
      if (event.y !== undefined) {
        eventData.y = event.y;
      }
      if (event.framePath) {
        eventData.framePath = event.framePath;
      }

      recordedEvents.push(eventData);
    }

    /**
     * 节流处理 input 事件
     */
    const throttledInput = (function() {
      let lastCall = 0;
      let timeoutId = null;
      let pendingValue = null;
      let pendingTarget = null;

      return function(target, value) {
        const now = Date.now();
        const remaining = INPUT_THROTTLE_MS - (now - lastCall);

        pendingValue = value;
        pendingTarget = target;

        if (remaining <= 0) {
          if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
          }
          lastCall = now;
          flushInput();
        } else if (!timeoutId) {
          timeoutId = setTimeout(() => {
            lastCall = Date.now();
            timeoutId = null;
            flushInput();
          }, remaining);
        }
      };

      function flushInput() {
        if (!pendingTarget || pendingValue === null) return;
        
        const selector = generateSelector(pendingTarget);
        if (!selector) return;

        const isSensitive = pendingTarget.type === 'password' || 
                           pendingTarget.getAttribute?.('type') === 'password';
        
        recordEvent({
          type: 'input',
          selector: selector,
          value: isSensitive ? '***' : (SANITIZE_SENSITIVE ? sanitize(pendingValue) : pendingValue),
          framePath: getFramePath(pendingTarget)
        });

        pendingValue = null;
        pendingTarget = null;
      }
    })();

    /**
     * 合并 scroll 事件
     */
    function handleScroll(target) {
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }

      pendingScroll = {
        target: target,
        x: target.scrollLeft || window.scrollX,
        y: target.scrollTop || window.scrollY
      };

      scrollTimeout = setTimeout(() => {
        if (pendingScroll) {
          const selector = pendingScroll.target === document.documentElement || 
                          pendingScroll.target === document.body ||
                          pendingScroll.target === window
            ? ':root'
            : generateSelector(pendingScroll.target);
          
          if (selector) {
            recordEvent({
              type: 'scroll',
              selector: selector,
              x: pendingScroll.x,
              y: pendingScroll.y,
              framePath: getFramePath(pendingScroll.target)
            });
          }
          pendingScroll = null;
          scrollTimeout = null;
        }
      }, SCROLL_DEBOUNCE_MS);
    }

    // 事件监听器
    const listeners = new Map();

    function addListener(element, eventType, handler, options = {}) {
      element.addEventListener(eventType, handler, options);
      const key = `${eventType}-${element.tagName || 'window'}`;
      if (!listeners.has(key)) {
        listeners.set(key, []);
      }
      listeners.get(key).push({ element, eventType, handler });
    }

    // 初始化事件监听
    function initListeners() {
      // Click events
      document.addEventListener('click', (e) => {
        const target = e.target;
        const selector = generateSelector(target);
        if (!selector) return;

        recordEvent({
          type: 'click',
          selector: selector,
          x: e.clientX,
          y: e.clientY,
          framePath: getFramePath(target)
        });
      }, true);

      // Input events with throttling
      document.addEventListener('input', (e) => {
        const target = e.target;
        if (!target || !target.value) return;
        
        throttledInput(target, String(target.value));
      }, true);

      // Change events
      document.addEventListener('change', (e) => {
        const target = e.target;
        const selector = generateSelector(target);
        if (!selector) return;

        recordEvent({
          type: 'change',
          selector: selector,
          value: target.value ? String(target.value) : undefined,
          framePath: getFramePath(target)
        });
      }, true);

      // Keydown events (for special keys)
      document.addEventListener('keydown', (e) => {
        // 只记录特殊键
        const specialKeys = ['Enter', 'Tab', 'Escape', 'ArrowUp', 'ArrowDown', 
                            'ArrowLeft', 'ArrowRight', 'Home', 'End', 
                            'PageUp', 'PageDown', 'Delete', 'Backspace'];
        
        if (!specialKeys.includes(e.key)) return;

        const target = e.target;
        const selector = generateSelector(target);
        if (!selector) return;

        recordEvent({
          type: 'keydown',
          selector: selector,
          value: e.key,
          framePath: getFramePath(target)
        });
      }, true);

      // Scroll events with merging
      document.addEventListener('scroll', (e) => {
        handleScroll(e.target || document.documentElement);
      }, true);

      // Window scroll
      window.addEventListener('scroll', () => {
        handleScroll(window);
      }, true);

      // Navigation detection
      let lastUrl = location.href;
      const observer = new MutationObserver(() => {
        if (location.href !== lastUrl) {
          recordEvent({
            type: 'navigation',
            selector: ':root',
            value: location.href
          });
          lastUrl = location.href;
        }
      });

      observer.observe(document.body, { childList: true, subtree: true });

      // Popstate for history navigation
      window.addEventListener('popstate', () => {
        recordEvent({
          type: 'navigation',
          selector: ':root',
          value: location.href
        });
      });
    }

    // 获取录制结果
    window.__RECORDED_EVENTS__ = function() {
      // 刷新待处理的 input 和 scroll
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
        if (pendingScroll) {
          const selector = ':root';
          recordedEvents.push({
            type: 'scroll',
            selector: selector,
            x: pendingScroll.x,
            y: pendingScroll.y,
            timestamp: Date.now()
          });
        }
      }
      
      return recordedEvents;
    };

    window.__STOP_RECORDING__ = function() {
      // 移除所有监听器
      listeners.forEach((handlers) => {
        handlers.forEach(({ element, eventType, handler }) => {
          element.removeEventListener(eventType, handler);
        });
      });
      listeners.clear();
    };

    // 启动监听
    initListeners();

    console.log('[Recorder] Injection script loaded and listening for events');
  }.toString()})(JSON.parse('${JSON.stringify(JSON.stringify({
    inputThrottleMs: inputThrottleMs,
    scrollDebounceMs: scrollDebounceMs,
    sanitizeSensitive: sanitizeSensitive
  }))}'));`;
}

/**
 * 从页面提取录制事件
 * @param {Object} page - Playwright Page 对象
 * @returns {Promise<Array>} 录制的事件数组
 */
export async function extractRecordedEvents(page) {
  return await page.evaluate(() => {
    if (typeof window.__RECORDED_EVENTS__ === 'function') {
      return window.__RECORDED_EVENTS__();
    }
    return [];
  });
}

/**
 * 停止页面录制
 * @param {Object} page - Playwright Page 对象
 * @returns {Promise<void>}
 */
export async function stopRecordingOnPage(page) {
  try {
    await page.evaluate(() => {
      if (typeof window.__STOP_RECORDING__ === 'function') {
        window.__STOP_RECORDING__();
      }
    });
  } catch (e) {
    // 页面可能已关闭
  }
}
