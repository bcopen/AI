/**
 * 工具函数模块
 * 提供脱敏、节流、日志等通用工具函数
 * 
 * @module utils
 */

/**
 * 敏感信息脱敏
 * @param {string} value - 原始值
 * @param {string} [mask='***'] - 脱敏掩码
 * @returns {string} 脱敏后的值
 */
export function sanitize(value, mask = '***') {
  if (!value || typeof value !== 'string') return value;
  
  // 检测是否为敏感字段
  const sensitivePatterns = [
    /password/i, /passwd/i, /pwd/i, /secret/i, /token/i,
    /api[_-]?key/i, /auth/i, /credential/i
  ];
  
  // 如果值看起来像密码（短且包含特殊字符）或匹配敏感模式
  if (value.length <= 50 && /[!@#$%^&*(),.?":{}|<>]/.test(value)) {
    return mask;
  }
  
  // 检测是否可能是邮箱或电话
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
    return mask;
  }
  
  if (/^[\d\s\-\+\(\)]{8,20}$/.test(value)) {
    return mask;
  }
  
  return value;
}

/**
 * 创建节流函数
 * @param {Function} fn - 需要节流的函数
 * @param {number} delay - 延迟时间（毫秒）
 * @returns {Function} 节流后的函数
 */
export function throttle(fn, delay) {
  let lastCall = 0;
  let timeoutId = null;
  
  return function(...args) {
    const now = Date.now();
    const remaining = delay - (now - lastCall);
    
    if (remaining <= 0) {
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
      lastCall = now;
      fn.apply(this, args);
    } else if (!timeoutId) {
      timeoutId = setTimeout(() => {
        lastCall = Date.now();
        timeoutId = null;
        fn.apply(this, args);
      }, remaining);
    }
  };
}

/**
 * 创建防抖函数
 * @param {Function} fn - 需要防抖的函数
 * @param {number} delay - 延迟时间（毫秒）
 * @returns {Function} 防抖后的函数
 */
export function debounce(fn, delay) {
  let timeoutId = null;
  
  return function(...args) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

/**
 * 日志工具类
 */
export class Logger {
  /**
   * @param {Object} options - 配置选项
   * @param {boolean} [options.verbose=true] - 是否输出详细日志
   * @param {string} [options.prefix=''] - 日志前缀
   */
  constructor(options = {}) {
    this.verbose = options.verbose ?? true;
    this.prefix = options.prefix || '';
  }

  /**
   * 输出信息日志
   * @param {...any} args - 日志参数
   */
  info(...args) {
    if (this.verbose) {
      console.log(`[${this._timestamp()}]${this.prefix ? ` ${this.prefix}` : ''}`, ...args);
    }
  }

  /**
   * 输出警告日志
   * @param {...any} args - 日志参数
   */
  warn(...args) {
    console.warn(`[${this._timestamp()}]${this.prefix ? ` ${this.prefix}` : ''} [WARN]`, ...args);
  }

  /**
   * 输出错误日志
   * @param {...any} args - 日志参数
   */
  error(...args) {
    console.error(`[${this._timestamp()}]${this.prefix ? ` ${this.prefix}` : ''} [ERROR]`, ...args);
  }

  /**
   * 输出调试日志
   * @param {...any} args - 日志参数
   */
  debug(...args) {
    if (this.verbose) {
      console.debug(`[${this._timestamp()}]${this.prefix ? ` ${this.prefix}` : ''} [DEBUG]`, ...args);
    }
  }

  /**
   * 获取时间戳字符串
   * @returns {string} 格式化时间戳
   */
  _timestamp() {
    return new Date().toISOString().slice(11, 23);
  }
}

/**
 * 深拷贝对象
 * @template T
 * @param {T} obj - 要拷贝的对象
 * @returns {T} 拷贝后的对象
 */
export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * 安全地访问嵌套对象属性
 * @param {Object} obj - 对象
 * @param {string} path - 属性路径，如 'a.b.c'
 * @param {any} defaultValue - 默认值
 * @returns {any} 属性值或默认值
 */
export function safeGet(obj, path, defaultValue = undefined) {
  try {
    return path.split('.').reduce((acc, part) => acc?.[part], obj) ?? defaultValue;
  } catch {
    return defaultValue;
  }
}

/**
 * 睡眠指定时间
 * @param {number} ms - 毫秒数
 * @returns {Promise<void>}
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 格式化字节数
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的大小
 */
export function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}
