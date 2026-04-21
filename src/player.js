/**
 * 回放模块 - JSON 解析与 Playwright 执行引擎
 * 读取录制数据，按时间戳排序后逐条执行，支持智能同步和重试机制
 * 
 * @module player
 */

import { parseSelectorForLocator } from './selector.js';
import { Logger, sleep } from './utils.js';

/**
 * 回放器配置
 * @typedef {Object} PlayerConfig
 * @property {number} [timeout=5000] - 元素等待超时时间
 * @property {number} [networkIdleTimeout=3000] - 网络空闲等待超时
 * @property {number} [maxRetries=2] - 最大重试次数
 * @property {number} [retryDelayMs=500] - 重试延迟基数
 * @property {boolean} [screenshots=false] - 是否每步截图
 * @property {string} [screenshotDir='./screenshots'] - 截图目录
 * @property {boolean} [verbose=true] - 是否输出详细日志
 */

/**
 * 回放事件数据
 * @typedef {Object} PlaybackEvent
 * @property {string} type - 事件类型
 * @property {string} selector - 元素选择器
 * @property {string} [value] - 输入值或其他数据
 * @property {number} [x] - X 坐标
 * @property {number} [y] - Y 坐标
 * @property {number} timestamp - 时间戳
 * @property {string[]} [framePath] - iframe 路径
 */

/**
 * 回放结果
 * @typedef {Object} PlaybackResult
 * @property {boolean} success - 是否成功
 * @property {number} totalSteps - 总步骤数
 * @property {number} executedSteps - 已执行步骤数
 * @property {Array<string>} errors - 错误信息列表
 * @property {number} duration - 执行时长（毫秒）
 */

export class Player {
  /**
   * @param {import('playwright').Page} page - Playwright Page 对象
   * @param {PlayerConfig} [config] - 配置选项
   */
  constructor(page, config = {}) {
    this.page = page;
    this.config = {
      timeout: config.timeout ?? 5000,
      networkIdleTimeout: config.networkIdleTimeout ?? 3000,
      maxRetries: config.maxRetries ?? 2,
      retryDelayMs: config.retryDelayMs ?? 500,
      screenshots: config.screenshots ?? false,
      screenshotDir: config.screenshotDir || './screenshots',
      verbose: config.verbose ?? true
    };
    
    this.logger = new Logger({ 
      verbose: this.config.verbose,
      prefix: '[Player]'
    });
    
    this.errors = [];
    this.executedSteps = 0;
  }

  /**
   * 执行回放
   * @param {Array<PlaybackEvent>} events - 录制的事件数组
   * @returns {Promise<PlaybackResult>} 回放结果
   */
  async play(events) {
    const startTime = Date.now();
    
    if (!events || events.length === 0) {
      return {
        success: true,
        totalSteps: 0,
        executedSteps: 0,
        errors: [],
        duration: 0
      };
    }

    // 按时间戳排序
    const sortedEvents = [...events].sort((a, b) => a.timestamp - b.timestamp);
    
    this.logger.info(`Starting playback of ${sortedEvents.length} events`);
    
    for (let i = 0; i < sortedEvents.length; i++) {
      const event = sortedEvents[i];
      this.executedSteps = i + 1;
      
      try {
        await this._executeEvent(event, i);
        
        // 可选：每步截图
        if (this.config.screenshots) {
          await this._takeScreenshot(i);
        }
      } catch (error) {
        const errorMsg = `Step ${i + 1}/${sortedEvents.length} failed: ${event.type} on "${event.selector}" - ${error.message}`;
        this.logger.error(errorMsg);
        this.errors.push(errorMsg);
        
        // 关键操作失败后尝试等待网络空闲
        try {
          await this.page.waitForLoadState('networkidle', { 
            timeout: this.config.networkIdleTimeout 
          }).catch(() => {});
        } catch {}
      }
    }

    const duration = Date.now() - startTime;
    const success = this.errors.length === 0;
    
    this.logger.info(`Playback completed: ${success ? 'SUCCESS' : 'FAILED'} (${duration}ms)`);
    
    return {
      success,
      totalSteps: sortedEvents.length,
      executedSteps: this.executedSteps,
      errors: this.errors,
      duration
    };
  }

  /**
   * 执行单个事件
   * @private
   * @param {PlaybackEvent} event - 事件数据
   * @param {number} index - 事件索引
   */
  async _executeEvent(event, index) {
    const { type, selector, value, x, y, framePath } = event;
    
    this.logger.debug(`Executing step ${index + 1}: ${type} on ${selector}`);
    
    // 获取目标（考虑 iframe）
    let target = this.page;
    if (framePath && framePath.length > 0) {
      target = await this._getFrameTarget(framePath);
      if (!target) {
        throw new Error(`Cannot access frame path: ${framePath.join(' > ')}`);
      }
    }

    // 根据事件类型执行不同操作
    switch (type) {
      case 'click':
        await this._executeClick(target, selector, x, y);
        break;
      case 'input':
        await this._executeInput(target, selector, value);
        break;
      case 'change':
        await this._executeChange(target, selector, value);
        break;
      case 'keydown':
        await this._executeKeydown(target, selector, value);
        break;
      case 'scroll':
        await this._executeScroll(target, selector, x, y);
        break;
      case 'navigation':
        await this._executeNavigation(target, value);
        break;
      default:
        this.logger.warn(`Unknown event type: ${type}`);
    }

    // 关键操作后等待网络空闲
    if (['click', 'change', 'keydown'].includes(type) && value !== 'Enter') {
      try {
        await this.page.waitForLoadState('networkidle', { 
          timeout: this.config.networkIdleTimeout 
        }).catch(() => {});
      } catch {}
    }
  }

  /**
   * 执行点击操作
   * @private
   * @param {import('playwright').Page|import('playwright').Frame} target - 目标对象
   * @param {string} selector - 选择器
   * @param {number} [x] - X 坐标
   * @param {number} [y] - Y 坐标
   */
  async _executeClick(target, selector, x, y) {
    await this._withRetry(async () => {
      const locator = this._getLocator(target, selector);
      
      // 等待元素 attached
      await locator.waitFor('attached', { timeout: this.config.timeout });
      
      // 如果有坐标，使用坐标点击
      if (x !== undefined && y !== undefined) {
        await locator.click({ position: { x, y }, timeout: this.config.timeout });
      } else {
        await locator.click({ timeout: this.config.timeout });
      }
    }, `click on ${selector}`);
  }

  /**
   * 执行输入操作
   * @private
   * @param {import('playwright').Page|import('playwright').Frame} target - 目标对象
   * @param {string} selector - 选择器
   * @param {string} [value] - 输入值
   */
  async _executeInput(target, selector, value) {
    await this._withRetry(async () => {
      const locator = this._getLocator(target, selector);
      
      await locator.waitFor('attached', { timeout: this.config.timeout });
      
      if (value === '***') {
        // 脱敏值，跳过实际输入或输入占位符
        this.logger.debug('Skipping sensitive input value');
        return;
      }
      
      await locator.fill(value || '', { timeout: this.config.timeout });
    }, `input on ${selector}`);
  }

  /**
   * 执行 change 操作
   * @private
   * @param {import('playwright').Page|import('playwright').Frame} target - 目标对象
   * @param {string} selector - 选择器
   * @param {string} [value] - 值
   */
  async _executeChange(target, selector, value) {
    await this._withRetry(async () => {
      const locator = this._getLocator(target, selector);
      
      await locator.waitFor('attached', { timeout: this.config.timeout });
      
      // 如果是 select，使用 selectOption
      const tagName = await locator.evaluate(el => el.tagName.toLowerCase()).catch(() => '');
      if (tagName === 'select' && value) {
        await locator.selectOption(value, { timeout: this.config.timeout });
      } else {
        // 其他情况触发 change 事件
        await locator.dispatchEvent('change', { timeout: this.config.timeout });
      }
    }, `change on ${selector}`);
  }

  /**
   * 执行 keydown 操作
   * @private
   * @param {import('playwright').Page|import('playwright').Frame} target - 目标对象
   * @param {string} selector - 选择器
   * @param {string} [key] - 按键
   */
  async _executeKeydown(target, selector, key) {
    await this._withRetry(async () => {
      const locator = this._getLocator(target, selector);
      
      await locator.waitFor('attached', { timeout: this.config.timeout });
      await locator.focus({ timeout: this.config.timeout });
      
      if (key) {
        await this.page.keyboard.press(key, { delay: 50 });
      }
    }, `keydown ${key} on ${selector}`);
  }

  /**
   * 执行滚动操作
   * @private
   * @param {import('playwright').Page|import('playwright').Frame} target - 目标对象
   * @param {string} selector - 选择器
   * @param {number} [x] - X 坐标
   * @param {number} [y] - Y 坐标
   */
  async _executeScroll(target, selector, x, y) {
    try {
      if (selector === ':root' || !selector) {
        // 滚动到指定位置
        if (x !== undefined || y !== undefined) {
          await this.page.evaluate(({ x, y }) => {
            window.scrollTo(x ?? window.scrollX, y ?? window.scrollY);
          }, { x, y });
        }
      } else {
        // 滚动特定元素
        const locator = this._getLocator(target, selector);
        await locator.evaluate(el => {
          el.scrollTop = el.scrollHeight;
        }).catch(() => {});
      }
    } catch (error) {
      this.logger.warn(`Scroll failed: ${error.message}`);
    }
  }

  /**
   * 执行导航操作
   * @private
   * @param {import('playwright').Page|import('playwright').Frame} target - 目标对象
   * @param {string} [url] - 目标 URL
   */
  async _executeNavigation(target, url) {
    if (url && url !== this.page.url()) {
      try {
        await this.page.goto(url, { 
          waitUntil: 'networkidle',
          timeout: this.config.timeout 
        });
      } catch (error) {
        this.logger.warn(`Navigation to ${url} failed: ${error.message}`);
      }
    }
  }

  /**
   * 获取 Locator（支持多种选择器策略）
   * @private
   * @param {import('playwright').Page|import('playwright').Frame} target - 目标对象
   * @param {string} selector - 原始选择器
   * @returns {import('playwright').Locator}
   */
  _getLocator(target, selector) {
    if (selector === ':root') {
      return target.locator('html').first();
    }

    const parsed = parseSelectorForLocator(selector);
    
    switch (parsed.type) {
      case 'testid':
        return target.getByTestId(parsed.value);
      case 'id':
        return target.locator(`#${parsed.value}`);
      case 'label':
        return target.getByLabel(parsed.value);
      case 'role':
        return target.getByRole(parsed.value);
      case 'css':
      default:
        return target.locator(selector);
    }
  }

  /**
   * 获取 iframe 目标
   * @private
   * @param {string[]} framePath - iframe 选择器路径
   * @returns {Promise<import('playwright').Frame|null>}
   */
  async _getFrameTarget(framePath) {
    let currentFrame = null;
    
    for (const selector of framePath) {
      const frames = this.page.frames();
      const matchingFrame = frames.find(frame => {
        try {
          const url = frame.url();
          return url !== '';
        } catch {
          return false;
        }
      });
      
      if (matchingFrame) {
        currentFrame = matchingFrame;
      }
    }
    
    return currentFrame || this.page;
  }

  /**
   * 带重试的执行
   * @private
   * @param {Function} fn - 执行函数
   * @param {string} description - 操作描述
   */
  async _withRetry(fn, description) {
    let lastError;
    
    for (let attempt = 0; attempt <= this.config.maxRetries; attempt++) {
      try {
        await fn();
        return;
      } catch (error) {
        lastError = error;
        
        if (attempt < this.config.maxRetries) {
          const delay = this.config.retryDelayMs * Math.pow(2, attempt);
          this.logger.debug(`Retry ${attempt + 1}/${this.config.maxRetries} for ${description} after ${delay}ms`);
          await sleep(delay);
        }
      }
    }
    
    throw lastError;
  }

  /**
   * 截图
   * @private
   * @param {number} stepIndex - 步骤索引
   */
  async _takeScreenshot(stepIndex) {
    try {
      const fs = await import('fs');
      const path = await import('path');
      
      // 确保目录存在
      if (!fs.existsSync(this.config.screenshotDir)) {
        fs.mkdirSync(this.config.screenshotDir, { recursive: true });
      }
      
      const filename = `step-${String(stepIndex).padStart(4, '0')}-${Date.now()}.png`;
      const filepath = path.join(this.config.screenshotDir, filename);
      
      await this.page.screenshot({ path: filepath, fullPage: false });
      this.logger.debug(`Screenshot saved: ${filepath}`);
    } catch (error) {
      this.logger.warn(`Failed to take screenshot: ${error.message}`);
    }
  }

  /**
   * 获取错误列表
   * @returns {Array<string>}
   */
  getErrors() {
    return [...this.errors];
  }

  /**
   * 重置状态
   */
  reset() {
    this.errors = [];
    this.executedSteps = 0;
  }
}

/**
 * 从文件加载录制数据
 * @param {string} filePath - JSON 文件路径
 * @returns {Promise<Array<PlaybackEvent>>}
 */
export async function loadRecordingFile(filePath) {
  const fs = await import('fs');
  
  if (!fs.existsSync(filePath)) {
    throw new Error(`Recording file not found: ${filePath}`);
  }
  
  const content = await fs.promises.readFile(filePath, 'utf-8');
  const data = JSON.parse(content);
  
  if (!Array.isArray(data)) {
    throw new Error('Invalid recording format: expected an array of events');
  }
  
  return data;
}
