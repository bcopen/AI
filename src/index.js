#!/usr/bin/env node

/**
 * CLI 入口模块
 * 支持 record 和 play 命令
 * 
 * @module index
 */

import { chromium } from 'playwright';
import { generateInjectionScript, extractRecordedEvents, stopRecordingOnPage } from './recorder.js';
import { Player, loadRecordingFile } from './player.js';
import { Logger } from './utils.js';
import { createInterface } from 'readline';
import { promises as fs } from 'fs';
import path from 'path';

const logger = new Logger({ verbose: true, prefix: '[CLI]' });

/**
 * 显示帮助信息
 */
function showHelp() {
  console.log(`
Playwright Recorder & Player - Web 操作录制与回放系统

用法:
  node index.js <command> [options]

命令:
  record <url> [output.json]   录制指定 URL 的页面操作
  play <recording.json>        回放录制的操作

示例:
  node index.js record https://example.com
  node index.js record https://example.com my-recording.json
  node index.js play recording.json
  node index.js play recording.json --screenshots

选项:
  --help, -h                   显示帮助信息
  --headless                   无头模式运行（录制时默认关闭）
  --screenshots                回放时每步截图
  --verbose                    输出详细日志

退出录制:
  在终端按 Enter 键结束录制
`);
}

/**
 * 解析命令行参数
 * @param {string[]} args - 原始参数
 * @returns {{command: string, url?: string, file?: string, output?: string, options: Object}}
 */
function parseArgs(args) {
  const result = {
    command: '',
    url: '',
    file: '',
    output: 'recording.json',
    options: {
      headless: false,
      screenshots: false,
      verbose: true
    }
  };

  const flags = [];
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    if (arg === '--help' || arg === '-h') {
      showHelp();
      process.exit(0);
    } else if (arg === '--headless') {
      result.options.headless = true;
    } else if (arg === '--screenshots') {
      result.options.screenshots = true;
    } else if (arg === '--no-verbose') {
      result.options.verbose = false;
    } else if (!arg.startsWith('-')) {
      flags.push(arg);
    }
  }

  if (flags.length >= 1) {
    result.command = flags[0];
  }
  if (flags.length >= 2) {
    if (result.command === 'record') {
      result.url = flags[1];
    } else if (result.command === 'play') {
      result.file = flags[1];
    }
  }
  if (flags.length >= 3 && result.command === 'record') {
    result.output = flags[2];
  }

  return result;
}

/**
 * 录制命令
 * @param {string} url - 目标 URL
 * @param {string} outputFile - 输出文件路径
 * @param {Object} options - 选项
 */
async function recordCommand(url, outputFile, options = {}) {
  logger.info(`Starting recording session for: ${url}`);
  logger.info(`Output file: ${outputFile}`);
  logger.info('Perform your actions in the browser...');
  logger.info('Press ENTER in this terminal to stop recording\n');

  const browser = await chromium.launch({
    headless: options.headless ?? false,
    args: ['--start-maximized']
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });

  const page = await context.newPage();

  // 注入录制脚本
  const injectionScript = generateInjectionScript({
    inputThrottleMs: 100,
    scrollDebounceMs: 200,
    sanitizeSensitive: true
  });

  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.evaluate(injectionScript);
    logger.info('Recording script injected successfully');
  } catch (error) {
    logger.error(`Failed to load page: ${error.message}`);
    await browser.close();
    process.exit(1);
  }

  // 等待用户按 Enter 结束
  const rl = createInterface({
    input: process.stdin,
    output: process.stdout
  });

  await new Promise((resolve) => {
    rl.question('', () => {
      resolve();
    });
  });

  rl.close();

  // 提取录制事件
  logger.info('Extracting recorded events...');
  const events = await extractRecordedEvents(page);
  
  // 停止录制
  await stopRecordingOnPage(page);

  logger.info(`Recorded ${events.length} events`);

  // 保存为 JSON
  const outputPath = path.resolve(outputFile);
  await fs.writeFile(outputPath, JSON.stringify(events, null, 2), 'utf-8');
  
  logger.info(`Recording saved to: ${outputPath}`);

  await browser.close();
}

/**
 * 回放命令
 * @param {string} inputFile - 输入文件路径
 * @param {Object} options - 选项
 */
async function playCommand(inputFile, options = {}) {
  logger.info(`Loading recording from: ${inputFile}`);

  let events;
  try {
    events = await loadRecordingFile(inputFile);
  } catch (error) {
    logger.error(`Failed to load recording: ${error.message}`);
    process.exit(1);
  }

  logger.info(`Loaded ${events.length} events`);

  const browser = await chromium.launch({
    headless: options.headless ?? false
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });

  const page = await context.newPage();

  const player = new Player(page, {
    timeout: 5000,
    networkIdleTimeout: 3000,
    maxRetries: 2,
    screenshots: options.screenshots ?? false,
    screenshotDir: './screenshots',
    verbose: options.verbose ?? true
  });

  try {
    const result = await player.play(events);

    if (result.success) {
      logger.info(`✓ Playback completed successfully!`);
      logger.info(`  Total steps: ${result.totalSteps}`);
      logger.info(`  Duration: ${result.duration}ms`);
    } else {
      logger.warn(`⚠ Playback completed with errors`);
      logger.info(`  Executed: ${result.executedSteps}/${result.totalSteps}`);
      logger.info(`  Errors: ${result.errors.length}`);
      
      result.errors.forEach((err, i) => {
        logger.error(`  ${i + 1}. ${err}`);
      });
    }

    // 非零退出码表示有错误
    if (!result.success) {
      process.exit(1);
    }
  } catch (error) {
    logger.error(`Playback failed: ${error.message}`);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

/**
 * 主函数
 */
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    showHelp();
    process.exit(0);
  }

  const { command, url, file, output, options } = parseArgs(args);

  switch (command) {
    case 'record':
      if (!url) {
        logger.error('Please provide a URL to record');
        console.log('\nExample: node index.js record https://example.com\n');
        process.exit(1);
      }
      await recordCommand(url, output, options);
      break;

    case 'play':
      if (!file) {
        logger.error('Please provide a recording file');
        console.log('\nExample: node index.js play recording.json\n');
        process.exit(1);
      }
      await playCommand(file, options);
      break;

    default:
      logger.error(`Unknown command: ${command}`);
      showHelp();
      process.exit(1);
  }
}

// 运行主函数
main().catch(error => {
  logger.error(`Fatal error: ${error.message}`);
  process.exit(1);
});
