// 测试动作定义
const ACTIONS = {
    navigate: {
        name: '🌐 导航',
        params: [
            { name: 'url', label: 'URL', type: 'text', placeholder: 'https://example.com' }
        ]
    },
    click: {
        name: '🖱️ 点击',
        params: [
            { name: 'selector', label: '选择器', type: 'text', placeholder: '#button, .class, xpath=//' }
        ]
    },
    input: {
        name: '⌨️ 输入',
        params: [
            { name: 'selector', label: '选择器', type: 'text', placeholder: '#username' },
            { name: 'value', label: '值', type: 'text', placeholder: '输入内容' }
        ]
    },
    wait: {
        name: '⏳ 等待',
        params: [
            { name: 'timeout', label: '时间 (ms)', type: 'number', placeholder: '1000' }
        ]
    },
    waitForSelector: {
        name: '🎯 等待元素',
        params: [
            { name: 'selector', label: '选择器', type: 'text', placeholder: '#element' },
            { name: 'timeout', label: '超时 (ms)', type: 'number', placeholder: '5000' }
        ]
    },
    screenshot: {
        name: '📷 截图',
        params: []
    },
    assert: {
        name: '✅ 断言',
        params: [
            { name: 'selector', label: '选择器', type: 'text', placeholder: '#result' },
            { name: 'expected', label: '期望值', type: 'text', placeholder: '期望包含的文本' }
        ]
    },
    login: {
        name: '🔐 登录',
        params: [
            { name: 'usernameSelector', label: '用户名选择器', type: 'text', placeholder: '#username' },
            { name: 'passwordSelector', label: '密码选择器', type: 'text', placeholder: '#password' },
            { name: 'submitSelector', label: '提交按钮选择器', type: 'text', placeholder: '#submit' },
            { name: 'username', label: '用户名', type: 'text', placeholder: '用户名' },
            { name: 'password', label: '密码', type: 'text', placeholder: '密码' }
        ]
    }
};

let stepCount = 0;

// 初始化页面
document.addEventListener('DOMContentLoaded', () => {
    addStep(); // 添加第一个步骤
});

// 添加步骤
function addStep() {
    stepCount++;
    const template = document.getElementById('stepTemplate');
    const clone = template.content.cloneNode(true);
    const stepItem = clone.querySelector('.step-item');
    
    // 设置步骤编号
    stepItem.querySelector('.step-number').textContent = stepCount;
    
    // 填充动作选择器
    const select = stepItem.querySelector('.action-select');
    for (const [key, value] of Object.entries(ACTIONS)) {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = value.name;
        select.appendChild(option);
    }
    
    // 监听动作变化
    select.addEventListener('change', (e) => {
        renderParams(stepItem, e.target.value);
    });
    
    // 添加到容器
    document.getElementById('stepsContainer').appendChild(stepItem);
    
    // 渲染默认参数
    renderParams(stepItem, select.value);
}

// 渲染参数输入框
function renderParams(stepItem, action) {
    const paramsContainer = stepItem.querySelector('.step-params');
    paramsContainer.innerHTML = '';
    
    const actionConfig = ACTIONS[action];
    if (!actionConfig || !actionConfig.params) return;
    
    actionConfig.params.forEach(param => {
        const group = document.createElement('div');
        group.className = 'param-group';
        
        const label = document.createElement('label');
        label.textContent = param.label;
        group.appendChild(label);
        
        const input = document.createElement('input');
        input.type = param.type;
        input.placeholder = param.placeholder;
        input.dataset.param = param.name;
        group.appendChild(input);
        
        paramsContainer.appendChild(group);
    });
}

// 移除步骤
function removeStep(button) {
    const stepItem = button.closest('.step-item');
    stepItem.remove();
    updateStepNumbers();
}

// 更新步骤编号
function updateStepNumbers() {
    const steps = document.querySelectorAll('.step-item');
    steps.forEach((step, index) => {
        step.querySelector('.step-number').textContent = index + 1;
    });
    stepCount = steps.length;
}

// 清空步骤
function clearSteps() {
    document.getElementById('stepsContainer').innerHTML = '';
    stepCount = 0;
    addStep();
}

// 收集测试配置
function collectConfig() {
    const steps = [];
    const stepItems = document.querySelectorAll('.step-item');
    
    stepItems.forEach(stepItem => {
        const action = stepItem.querySelector('.action-select').value;
        const params = {};
        
        const inputs = stepItem.querySelectorAll('[data-param]');
        inputs.forEach(input => {
            const paramName = input.dataset.param;
            let value = input.value;
            
            // 数字类型转换
            if (input.type === 'number') {
                value = parseInt(value) || 0;
            }
            
            if (value) {
                params[paramName] = value;
            }
        });
        
        steps.push({ action, params });
    });
    
    return { steps };
}

// 运行测试
async function runTest() {
    const testName = document.getElementById('testName').value || 'Test';
    const config = collectConfig();
    
    if (config.steps.length === 0) {
        alert('请至少添加一个测试步骤');
        return;
    }
    
    // 显示状态区域
    document.getElementById('statusSection').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';
    
    const statusText = document.getElementById('statusText');
    const progressBar = document.getElementById('progressBar');
    
    try {
        statusText.textContent = '正在执行测试...';
        progressBar.style.width = '30%';
        
        const response = await fetch('/api/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: testName,
                config: config
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            progressBar.style.width = '100%';
            statusText.textContent = '测试完成！';
            showResults(data.summary, data.report);
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        progressBar.style.width = '100%';
        statusText.textContent = '测试失败：' + error.message;
        alert('测试执行失败：' + error.message);
    }
}

// 显示结果
function showResults(summary, reportPath) {
    const resultsSection = document.getElementById('resultsSection');
    const summaryDiv = document.getElementById('summary');
    const reportLink = document.getElementById('reportLink');
    
    summaryDiv.innerHTML = `
        <div class="stat-card stat-total">
            <h3>${summary.total}</h3>
            <p>总步骤</p>
        </div>
        <div class="stat-card stat-passed">
            <h3>${summary.passed}</h3>
            <p>通过</p>
        </div>
        <div class="stat-card stat-failed">
            <h3>${summary.failed}</h3>
            <p>失败</p>
        </div>
        <div class="stat-card stat-rate">
            <h3>${summary.pass_rate.toFixed(1)}%</h3>
            <p>通过率</p>
        </div>
    `;
    
    // 生成报告链接
    const reportFilename = reportPath.split('/').pop();
    reportLink.innerHTML = `
        <a href="/reports/${reportFilename}" target="_blank">📄 查看完整测试报告</a>
    `;
    
    resultsSection.style.display = 'block';
}
