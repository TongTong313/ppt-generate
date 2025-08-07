// 全局变量
let currentOutline = '';
let isGenerating = false;

// DOM元素
const elements = {
    userQuery: document.getElementById('user-query'),
    referenceContent: document.getElementById('reference-content'),
    fileInput: document.getElementById('file-input'),
    fileName: document.getElementById('file-name'),
    generateOutlineBtn: document.getElementById('generate-outline-btn'),
    generateContentBtn: document.getElementById('generate-content-btn'),
    clearBtn: document.getElementById('clear-btn'),
    loadingOverlay: document.getElementById('loading-overlay'),
    
    resultsSection: document.querySelector('.results-section'),
    
    // 工作空间相关元素
    workspaceArea: document.getElementById('workspace-area'),
    workspaceTitle: document.getElementById('workspace-title'),
    workspaceStatus: document.getElementById('workspace-status'),
    workspaceStatusContainer: document.getElementById('workspace-status-container'),
    workspaceWelcome: document.getElementById('workspace-welcome'),
    workspaceThinking: document.getElementById('workspace-thinking'),
    workspaceThinkingContent: document.getElementById('workspace-thinking-content'),
    workspaceGenerating: document.getElementById('workspace-generating'),
    workspaceGeneratingContent: document.getElementById('workspace-generating-content'),
    workspaceGeneratingTitle: document.getElementById('workspace-generating-title'),
    workspaceOutline: document.getElementById('workspace-outline'),
    workspaceContent: document.getElementById('workspace-content'),
    workspaceOutlineContent: document.getElementById('workspace-outline-content'),
    workspacePageContent: document.getElementById('workspace-page-content'),

    outlineResult: document.getElementById('outline-result'),
    outlineContent: document.getElementById('outline-content'),

    contentResult: document.getElementById('content-result'),
    pageContent: document.getElementById('page-content')
};

// 初始化事件监听器
function initEventListeners() {
    // 文件上传
    elements.fileInput.addEventListener('change', handleFileUpload);
    
    // 按钮事件
    elements.generateOutlineBtn.addEventListener('click', generateOutline);
    elements.generateContentBtn.addEventListener('click', generateContent);
    elements.clearBtn.addEventListener('click', clearAll);
    
    // 输入验证
    elements.userQuery.addEventListener('input', validateInputs);
}

// 文件上传处理
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    elements.fileName.textContent = file.name;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        let content = e.target.result;
        
        // 尝试检测和修复编码问题
        try {
            // 如果内容包含乱码，尝试重新解码
            if (content.includes('�') || /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]/.test(content)) {
                console.log('检测到可能的编码问题，尝试重新读取文件');
                // 重新以不同编码读取
                const readerGBK = new FileReader();
                readerGBK.onload = function(e2) {
                    elements.referenceContent.value = e2.target.result;
                    validateInputs();
                };
                // 尝试以GBK编码读取
                readerGBK.readAsText(file, 'GBK');
                return;
            }
        } catch (error) {
            console.log('编码检测失败，使用原始内容');
        }
        
        elements.referenceContent.value = content;
        validateInputs();
    };
    
    reader.onerror = function() {
        alert('文件读取失败，请检查文件格式');
        elements.fileName.textContent = '';
    };
    
    // 首先尝试UTF-8编码
    reader.readAsText(file, 'UTF-8');
}

// 输入验证
function validateInputs() {
    const hasQuery = elements.userQuery.value.trim().length > 0;
    elements.generateOutlineBtn.disabled = !hasQuery || isGenerating;
}

// 切换思考过程显示
function toggleThinking(type) {
    const thinkingSection = document.getElementById(`${type}-thinking`);
    const thinkingContent = document.getElementById(`${type}-thinking-content`);
    const toggleBtn = document.querySelector(`#${type}-thinking .toggle-thinking i`);
    
    if (!thinkingSection || !thinkingContent || !toggleBtn) {
        console.error('思考区域元素未找到:', type);
        return;
    }
    
    // 检查当前显示状态
    const isHidden = thinkingContent.style.display === 'none' || 
                     getComputedStyle(thinkingContent).display === 'none';
    
    if (isHidden) {
        thinkingContent.style.display = 'block';
        toggleBtn.className = 'fas fa-eye-slash';
    } else {
        thinkingContent.style.display = 'none';
        toggleBtn.className = 'fas fa-eye';
    }
}

// 更新工作空间视图
function updateWorkspaceView({ mode, status, statusText, thinkingContent, generatingContent, generatingTitle, outlineContent }) {
    // 显示状态指示器
    if (status || statusText) {
        elements.workspaceStatusContainer.style.display = 'block';
        if (status) {
            elements.workspaceStatus.className = `status ${status}`;
        }
        if (statusText) {
            elements.workspaceStatus.textContent = statusText;
        }
    }
    
    // 根据模式切换显示内容
    switch (mode) {
        case 'welcome':
            elements.workspaceWelcome.style.display = 'block';
            elements.workspaceThinking.style.display = 'none';
            elements.workspaceGenerating.style.display = 'none';
            if (elements.workspaceOutline) elements.workspaceOutline.style.display = 'none';
            if (elements.workspaceContent) elements.workspaceContent.style.display = 'none';
            elements.workspaceStatusContainer.style.display = 'none';
            break;
            
        case 'thinking':
            elements.workspaceWelcome.style.display = 'none';
            elements.workspaceThinking.style.display = 'block';
            elements.workspaceGenerating.style.display = 'none';
            if (elements.workspaceOutline) elements.workspaceOutline.style.display = 'none';
            if (elements.workspaceContent) elements.workspaceContent.style.display = 'none';
            
            if (thinkingContent) {
                elements.workspaceThinkingContent.textContent += thinkingContent;
                elements.workspaceThinkingContent.scrollTop = elements.workspaceThinkingContent.scrollHeight;
            }
            break;
            
        case 'generating':
            elements.workspaceWelcome.style.display = 'none';
            elements.workspaceThinking.style.display = 'block'; // 保持思考过程可见
            elements.workspaceGenerating.style.display = 'block';
            if (elements.workspaceOutline) elements.workspaceOutline.style.display = 'none';
            if (elements.workspaceContent) elements.workspaceContent.style.display = 'none';
            
            if (generatingTitle) {
                elements.workspaceGeneratingTitle.textContent = generatingTitle;
            }
            
            if (generatingContent) {
                elements.workspaceGeneratingContent.innerHTML += generatingContent;
                elements.workspaceGeneratingContent.scrollTop = elements.workspaceGeneratingContent.scrollHeight;
            }
            break;
            
        case 'outline':
            elements.workspaceWelcome.style.display = 'none';
            elements.workspaceThinking.style.display = 'none';
            elements.workspaceGenerating.style.display = 'none';
            if (elements.workspaceOutline) {
                elements.workspaceOutline.style.display = 'block';
                if (outlineContent && elements.workspaceOutlineContent) {
                    elements.workspaceOutlineContent.innerHTML = createEditableOutlineContent(outlineContent);
                }
            }
            if (elements.workspaceContent) elements.workspaceContent.style.display = 'none';
            break;
            
        case 'content':
            elements.workspaceWelcome.style.display = 'none';
            elements.workspaceThinking.style.display = 'none';
            elements.workspaceGenerating.style.display = 'none';
            if (elements.workspaceOutline) elements.workspaceOutline.style.display = 'none';
            if (elements.workspaceContent) {
                elements.workspaceContent.style.display = 'block';
            }
            break;
    }
}

// 显示加载动画
function showLoading(show = true) {
    elements.loadingOverlay.style.display = show ? 'flex' : 'none';
}

// 生成PPT大纲
async function generateOutline() {
    if (isGenerating) return;
    
    const query = elements.userQuery.value.trim();
    const referenceContent = elements.referenceContent.value.trim();
    
    if (!query) {
        alert('请输入PPT主题需求');
        return;
    }
    
    isGenerating = true;
    elements.generateOutlineBtn.disabled = true;
    elements.generateContentBtn.disabled = true;
    
    // 准备UI
    elements.resultsSection.style.display = 'block';
    if (elements.outlineResult) elements.outlineResult.style.display = 'none';
    if (elements.contentResult) elements.contentResult.style.display = 'none';
    
    // 清空工作空间内容
    elements.workspaceThinkingContent.textContent = '';
    elements.workspaceGeneratingContent.innerHTML = '';

    updateWorkspaceView({
        mode: 'thinking',
        status: 'thinking',
        statusText: 'AI思考中...'
    });
    
    try {
        // 使用WebSocket进行实时通信
        await generateOutlineWithWebSocket(query, referenceContent);
    } catch (error) {
        console.error('生成大纲失败:', error);
        updateWorkspaceView({ mode: 'welcome', status: 'error', statusText: '生成失败' });
        alert('生成大纲失败，请重试');
    } finally {
        isGenerating = false;
        elements.generateOutlineBtn.disabled = false;
        validateInputs();
    }
}

// 模拟大纲生成过程
async function simulateOutlineGeneration(query, referenceContent) {
    // 模拟思考过程
    const thinkingSteps = [
        '正在分析用户需求...',
        '解析参考内容...',
        '确定PPT主题和结构...',
        '生成大纲框架...',
        '优化大纲逻辑...',
        '完成大纲生成'
    ];
    
    for (let i = 0; i < thinkingSteps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 800));
        elements.outlineThinkingContent.textContent += thinkingSteps[i] + '\n';
        elements.outlineThinkingContent.scrollTop = elements.outlineThinkingContent.scrollHeight;
    }
    
    // 更新状态为生成中
    updateStatus('outline', 'generating', '生成中');
    
    // 模拟生成大纲内容
    const sampleOutline = `
<outline>
1. ${query}的背景介绍
   - 历史发展概述
   - 当前发展现状
   - 重要性和意义

2. 核心概念和原理
   - 基本定义和概念
   - 核心技术原理
   - 关键特征分析

3. 应用场景和案例
   - 主要应用领域
   - 典型应用案例
   - 成功实践经验

4. 发展趋势和展望
   - 技术发展趋势
   - 市场前景分析
   - 未来发展方向

5. 总结和思考
   - 关键要点总结
   - 启示和思考
   - 行动建议
</outline>
    `;
    
    // 逐字显示大纲
    await typeText(elements.outlineContent, formatOutlineContent(sampleOutline), 30);
    
    // 保存大纲
    currentOutline = sampleOutline;
    
    // 更新状态
    updateStatus('outline', 'completed', '已完成');
    
    // 启用生成内容按钮
    elements.generateContentBtn.disabled = false;
}

// 显示生成过程窗口
function showGeneratingWindow(type) {
    const windowId = type === 'outline' ? 'outline-generating-window' : 'content-generating-window';
    let window = document.getElementById(windowId);
    
    if (!window) {
        // 创建生成过程窗口
        window = document.createElement('div');
        window.id = windowId;
        window.className = 'generating-window';
        window.innerHTML = `
            <div class="generating-header">
                <h4>${type === 'outline' ? '大纲生成过程' : '内容生成过程'}</h4>
                <button class="close-btn" onclick="hideGeneratingWindow('${type}')">&times;</button>
            </div>
            <div class="generating-content" id="${type}-generating-content"></div>
        `;
        document.body.appendChild(window);
    }
    
    window.style.display = 'block';
    // 清空之前的内容
    const content = document.getElementById(`${type}-generating-content`);
    if (content) content.textContent = '';
}

// 隐藏生成过程窗口
function hideGeneratingWindow(type) {
    const windowId = type === 'outline' ? 'outline-generating-window' : 'content-generating-window';
    const window = document.getElementById(windowId);
    if (window) {
        window.style.display = 'none';
    }
}

// 更新生成过程内容
function updateGeneratingContent(type, content) {
    const contentElement = document.getElementById(`${type}-generating-content`);
    if (contentElement) {
        // 将换行符转换为HTML换行标签，保持格式
        const formattedContent = content.replace(/\n/g, '<br>');
        contentElement.innerHTML += formattedContent;
        contentElement.scrollTop = contentElement.scrollHeight;
    }
}

// 创建可编辑的大纲内容
function createEditableOutlineContent(outline) {
    if (!outline) return '';
    
    // 移除<outline>标签
    let content = outline.replace(/<\/?outline>/g, '');
    
    const editableHtml = `
        <div class="outline-editor">
            <div class="editor-header">
                <h4>大纲内容（可编辑）</h4>
                <div class="editor-actions">
                    <button class="btn btn-outline" onclick="resetOutline()">重置</button>
                    <button class="btn btn-primary" onclick="confirmOutline()">确认并生成内容</button>
                </div>
            </div>
            <textarea class="outline-textarea" id="outline-editor" placeholder="请编辑大纲内容...">${content.trim()}</textarea>
        </div>
    `;
    
    return editableHtml;
}

// 格式化大纲内容（只读显示）
function formatOutlineContent(outline) {
    if (!outline) return '';
    
    // 移除<outline>标签
    let content = outline.replace(/<\/?outline>/g, '');
    
    // 转换为HTML格式
    content = content
        .split('\n')
        .map(line => {
            line = line.trim();
            if (!line) return '';
            
            // 主标题（数字开头）
            if (/^\d+\./.test(line)) {
                return `<h3>${line}</h3>`;
            }
            // 子标题（- 开头）
            else if (line.startsWith('- ')) {
                return `<p class="sub-item">${line}</p>`;
            }
            // 其他内容
            else {
                return `<p>${line}</p>`;
            }
        })
        .filter(line => line)
        .join('');
    
    return content;
}

// 重置大纲到原始状态
function resetOutline() {
    const editor = document.getElementById('outline-editor');
    if (editor && currentOutline) {
        const content = currentOutline.replace(/<\/?outline>/g, '');
        editor.value = content.trim();
    }
}

// 确认大纲并启用内容生成
function confirmOutline() {
    const editor = document.getElementById('outline-editor');
    if (editor) {
        // 更新当前大纲
        currentOutline = `<outline>\n${editor.value}\n</outline>`;
        
        // 显示确认后的大纲（只读）在工作空间中
        if (elements.workspaceOutlineContent) {
            elements.workspaceOutlineContent.innerHTML = `
                <div class="confirmed-outline">
                    <div class="outline-header">
                        <h4>已确认的大纲</h4>
                        <button class="btn btn-outline" onclick="editOutline()">重新编辑</button>
                    </div>
                    ${formatOutlineContent(currentOutline)}
                </div>
            `;
        }
        
        // 启用内容生成按钮
        elements.generateContentBtn.disabled = false;
    }
}

// 重新编辑大纲
function editOutline() {
    if (elements.workspaceOutlineContent) {
        elements.workspaceOutlineContent.innerHTML = createEditableOutlineContent(currentOutline);
    }
    elements.generateContentBtn.disabled = true;
}

// 生成PPT内容
async function generateContent() {
    if (isGenerating || !currentOutline) return;
    
    const referenceContent = elements.referenceContent.value.trim();
    
    isGenerating = true;
    elements.generateContentBtn.disabled = true;
    elements.generateOutlineBtn.disabled = true;
    
    // 准备UI
    elements.resultsSection.style.display = 'block';
    
    // 清空工作空间内容
    elements.workspaceThinkingContent.textContent = '';
    elements.workspaceGeneratingContent.innerHTML = '';
    if (elements.workspacePageContent) {
        elements.workspacePageContent.innerHTML = '';
    }

    updateWorkspaceView({
        mode: 'thinking',
        status: 'thinking',
        statusText: 'AI思考中...'
    });
    
    try {
        // 使用WebSocket进行实时通信
        await generateContentWithWebSocket(currentOutline, referenceContent);
    } catch (error) {
        console.error('生成内容失败:', error);
        updateWorkspaceView({ mode: 'welcome', status: 'error', statusText: '生成失败' });
        alert('生成内容失败，请重试');
    } finally {
        isGenerating = false;
        elements.generateContentBtn.disabled = false;
        elements.generateOutlineBtn.disabled = false;
    }
}

// 模拟内容生成过程
async function simulateContentGeneration(outline, referenceContent) {
    // 模拟思考过程
    const thinkingSteps = [
        '分析PPT大纲结构...',
        '规划页面布局和内容...',
        '生成开头页内容...',
        '生成目录页内容...',
        '生成正文页面内容...',
        '生成结尾页内容...',
        '优化页面内容和格式...',
        '完成PPT内容生成'
    ];
    
    for (let i = 0; i < thinkingSteps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        elements.contentThinkingContent.textContent += thinkingSteps[i] + '\n';
        elements.contentThinkingContent.scrollTop = elements.contentThinkingContent.scrollHeight;
    }
    
    // 更新状态为生成中
    updateStatus('content', 'generating', '生成中');
    
    // 模拟生成页面内容
    const samplePages = [
        {
            title: '人工智能发展历程',
            summary: '本次汇报将全面介绍人工智能的发展历程、核心技术和未来展望',
            body: '汇报单位：XX科技公司\n汇报时间：2024年1月\n汇报人：张三',
            advice: '开头页通常不需要添加图片或表格'
        },
        {
            title: '目录',
            summary: '本PPT的主要内容结构和章节安排',
            body: '1. 人工智能背景介绍\n2. 核心概念和原理\n3. 应用场景和案例\n4. 发展趋势和展望\n5. 总结和思考',
            advice: '目录页通常不需要添加图片或表格'
        },
        {
            title: '人工智能背景介绍',
            summary: '介绍人工智能的历史发展、现状和重要意义',
            body: '1. 历史发展概述：人工智能概念最早由图灵在1950年提出，经历了多次发展浪潮，从早期的符号主义到现在的深度学习，每个阶段都有重要的技术突破和应用进展。\n\n2. 当前发展现状：目前人工智能已经在图像识别、自然语言处理、语音识别等领域取得了显著成果，各大科技公司都在加大投入，推动AI技术的产业化应用。\n\n3. 重要性和意义：人工智能被认为是第四次工业革命的核心驱动力，将深刻改变人类的生产生活方式，提高效率，创造新的商业模式和就业机会。',
            advice: '建议添加人工智能发展时间线图表，展示重要里程碑事件'
        }
    ];
    
    // 逐页显示内容
    for (let i = 0; i < samplePages.length; i++) {
        const pageHtml = createPageHtml(samplePages[i], i + 1);
        elements.pageContent.innerHTML += pageHtml;
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // 滚动到最新内容
        const lastPage = elements.pageContent.lastElementChild;
        if (lastPage) {
            lastPage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
    
    // 更新状态
    updateStatus('content', 'completed', '已完成');
}

// 创建页面HTML
function createPageHtml(page, pageNumber) {
    return `
        <div class="ppt-page">
            <div class="ppt-page-title">第${pageNumber}页：${page.title}</div>
            <div class="ppt-page-summary">${page.summary}</div>
            <div class="ppt-page-body">
                <strong>页面内容：</strong><br>
                ${page.body.replace(/\n/g, '<br>')}
            </div>
            <div class="ppt-page-advice">
                <strong>图像和表格建议：</strong><br>
                ${page.advice}
            </div>
        </div>
    `;
}

// 打字机效果
async function typeText(element, html, speed = 50) {
    element.innerHTML = '';
    
    // 创建临时元素来解析HTML
    const temp = document.createElement('div');
    temp.innerHTML = html;
    
    // 直接设置HTML内容（简化版本）
    element.innerHTML = html;
    
    // 添加淡入动画
    element.style.opacity = '0';
    element.style.transition = 'opacity 0.5s ease-in';
    
    await new Promise(resolve => setTimeout(resolve, 100));
    element.style.opacity = '1';
}

// 清空所有内容
function clearAll() {
    if (isGenerating) {
        if (!confirm('正在生成中，确定要清空吗？')) {
            return;
        }
    }
    
    // 清空输入
    elements.userQuery.value = '';
    elements.referenceContent.value = '';
    elements.fileName.textContent = '';
    elements.fileInput.value = '';
    
    // 隐藏结果
    elements.outlineResult.style.display = 'none';
    elements.contentResult.style.display = 'none';
    
    // 清空内容
    elements.outlineThinkingContent.textContent = '';
    elements.contentThinkingContent.textContent = '';
    elements.outlineContent.innerHTML = '';
    elements.pageContent.innerHTML = '';
    
    // 重置状态
    currentOutline = '';
    isGenerating = false;
    
    // 重置按钮状态
    validateInputs();
    elements.generateContentBtn.disabled = true;
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initEventListeners();
    validateInputs();
    
    // 添加一些示例文本
    elements.userQuery.placeholder = '例如：制作一个关于人工智能发展历程的PPT，包括历史背景、核心技术、应用案例和未来展望';
});

// WebSocket相关函数
function createWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;
    return new WebSocket(wsUrl);
}

// 使用WebSocket生成大纲
function generateOutlineWithWebSocket(query, referenceContent) {
    return new Promise((resolve, reject) => {
        const ws = createWebSocket();
        
        ws.onopen = () => {
            ws.send(JSON.stringify({
                action: 'generate_outline',
                query: query,
                reference_content: referenceContent
            }));
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'thinking':
                    updateWorkspaceView({ 
                        mode: 'thinking',
                        thinkingContent: data.content 
                    });
                    break;
                case 'generating_start':
                    updateWorkspaceView({ 
                        mode: 'generating',
                        status: 'generating', 
                        statusText: '正在生成大纲...',
                        generatingTitle: '正在生成大纲...'
                    });
                    break;
                case 'outline_generating':
                    updateWorkspaceView({ 
                        mode: 'generating',
                        generatingContent: data.content.replace(/\n/g, '<br>') 
                    });
                    break;
                case 'outline_complete':
                    currentOutline = data.outline;
                    updateWorkspaceView({ 
                        mode: 'outline',
                        status: 'completed', 
                        statusText: '大纲生成完成',
                        outlineContent: data.outline
                    });
                    elements.generateContentBtn.disabled = false;
                    ws.close();
                    resolve();
                    break;
                    
                case 'error':
                    console.error('WebSocket错误:', data.message);
                    ws.close();
                    reject(new Error(data.message));
                    break;
            }
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket连接错误:', error);
            console.log('回退到模拟模式');
            // 回退到模拟模式
            simulateOutlineGeneration(query, referenceContent).then(resolve).catch(reject);
        };
        
        ws.onclose = (event) => {
            console.log('WebSocket连接已关闭', event.code, event.reason);
            // 如果是异常关闭且还没有完成，回退到模拟模式
            if (event.code !== 1000 && !currentOutline) {
                console.log('WebSocket异常关闭，回退到模拟模式');
                simulateOutlineGeneration(query, referenceContent).then(resolve).catch(reject);
            }
        };
    });
}

// 使用WebSocket生成内容
function generateContentWithWebSocket(outline, referenceContent) {
    return new Promise((resolve, reject) => {
        const ws = createWebSocket();
        
        ws.onopen = () => {
            ws.send(JSON.stringify({
                action: 'generate_content',
                outline: outline,
                reference_content: referenceContent
            }));
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'thinking':
                    updateWorkspaceView({ 
                        mode: 'thinking',
                        thinkingContent: data.content 
                    });
                    break;
                case 'generating_start':
                    updateWorkspaceView({ 
                        mode: 'generating',
                        status: 'generating', 
                        statusText: '正在生成内容...',
                        generatingTitle: '正在生成PPT内容...'
                    });
                    elements.pageContent.innerHTML = ''; // 清空旧内容
                    break;
                case 'page_generated':
                    // 实时渲染页面卡片到工作空间
                    renderPageCardToWorkspace(data.page, data.page_number);
                    
                    // 在生成过程中显示进度
                    const currentContent = elements.workspaceGeneratingContent.innerHTML;
                    const newProgress = `<div class="page-progress">✅ 第${data.page_number}页已生成</div>`;
                    updateWorkspaceView({ 
                        mode: 'generating',
                        generatingContent: currentContent + newProgress
                    });
                    break;
                case 'content_complete':
                    updateWorkspaceView({ 
                        mode: 'content',
                        status: 'completed', 
                        statusText: '内容生成完成'
                    });
                    showContentConfirmationButtons();
                    ws.close();
                    resolve();
                    break;
                    
                case 'error':
                    console.error('WebSocket错误:', data.message);
                    ws.close();
                    reject(new Error(data.message));
                    break;
            }
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket连接错误:', error);
            // 如果WebSocket失败，回退到模拟模式
            console.log('回退到模拟模式');
            simulateContentGeneration(outline, referenceContent).then(resolve).catch(reject);
        };
        
        ws.onclose = () => {
            console.log('WebSocket连接已关闭');
        };
    });
}

// 导出函数供HTML调用
// 内容生成相关的全局变量
let streamingContent = '';
let currentPageBuffer = '';
let pageCount = 0;
let isEditingContent = false;
let originalPages = [];

// 初始化内容生成区域
function initContentGenerationArea() {
    // 清空工作空间页面内容
    if (elements.workspacePageContent) {
        elements.workspacePageContent.innerHTML = '';
    }
    streamingContent = '';
    currentPageBuffer = '';
    pageCount = 0;
}

// 处理流式内容
function processStreamingContent(content) {
    streamingContent += content;
    currentPageBuffer += content;
    
    // 检查是否有完整的页面标签
    const pageMatches = streamingContent.match(/<page>([\s\S]*?)<\/page>/g);
    if (pageMatches) {
        // 渲染已完成的页面
        pageMatches.forEach((pageContent, index) => {
            if (index >= pageCount) {
                renderPageCard(pageContent, pageCount + 1);
                pageCount++;
            }
        });
        
        // 更新当前缓冲区为未完成的内容
        const lastPageEnd = streamingContent.lastIndexOf('</page>');
        if (lastPageEnd !== -1) {
            currentPageBuffer = streamingContent.substring(lastPageEnd + 7);
        }
    }
    
    // 显示当前正在生成的内容（减少换行频率）
    updateStreamingDisplay();
}

// 更新流式显示（优化换行和文本填充）
function updateStreamingDisplay() {
    const displayElement = document.getElementById('content-streaming-display');
    if (displayElement) {
        // 只显示当前页面缓冲区的内容，优化换行处理
        let displayContent = currentPageBuffer;
        
        // 移除<outline>标识符，确保不在流式输出中显示
        displayContent = displayContent.replace(/<outline>/g, '').replace(/<\/outline>/g, '');
        
        // 保持自然的文本流，让CSS控制换行
        displayContent = displayContent.replace(/\n{3,}/g, '\n\n'); // 最多保留两个换行
        displayContent = displayContent.trim();
        
        displayElement.textContent = displayContent;
        displayElement.scrollTop = displayElement.scrollHeight;
    }
}

// 渲染页面卡片到工作空间
function renderPageCardToWorkspace(pageData, pageNumber) {
    // 解析页面数据，隐藏<outline>标识符
    let cleanPageData = pageData.replace(/<outline>.*?<\/outline>/gs, '');
    
    const titleMatch = cleanPageData.match(/<title>(.*?)<\/title>/s);
    const summaryMatch = cleanPageData.match(/<summary>(.*?)<\/summary>/s);
    const bodyMatch = cleanPageData.match(/<body>(.*?)<\/body>/s);
    const adviceMatch = cleanPageData.match(/<img_table_advice>(.*?)<\/img_table_advice>/s);
    
    const title = titleMatch ? titleMatch[1].trim() : `第${pageNumber}页`;
    const summary = summaryMatch ? summaryMatch[1].trim() : '';
    const body = bodyMatch ? bodyMatch[1].trim() : '';
    const advice = adviceMatch ? adviceMatch[1].trim() : '';
    
    // 创建页面卡片HTML
    const cardHtml = `
        <div class="page-card" data-page="${pageNumber}">
            <div class="page-card-header">
                <i class="fas fa-file-alt"></i>
                <span>第${pageNumber}页</span>
            </div>
            <div class="page-card-content">
                <div class="page-card-title">${title}</div>
                ${summary ? `<div class="page-card-summary">${summary}</div>` : ''}
                <div class="page-card-body">${body.replace(/\n/g, '<br>')}</div>
                ${advice ? `<div class="page-card-advice">${advice.replace(/\n/g, '<br>')}</div>` : ''}
            </div>
        </div>
    `;
    
    // 确保工作空间内容区域可见
    if (elements.workspaceContent) {
        elements.workspaceContent.style.display = 'block';
    }
    
    // 添加页面卡片到工作空间
    const targetContainer = elements.workspacePageContent;
    if (targetContainer) {
        const pageContainer = document.createElement('div');
        pageContainer.innerHTML = cardHtml;
        targetContainer.appendChild(pageContainer.firstElementChild);
        
        // 滚动到最新内容
        const lastCard = targetContainer.lastElementChild;
        if (lastCard) {
            lastCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
}

// 渲染页面卡片（保留原函数用于兼容）
function renderPageCard(pageContent, pageNumber) {
    const pageData = parsePageContent(pageContent);
    const cardHtml = createPageCard(pageData, pageNumber);
    
    // 移除或更新生成过程显示
    const generatingProcess = document.getElementById('content-generating-inline');
    if (generatingProcess && pageNumber === 1) {
        generatingProcess.style.display = 'none';
    }
    
    // 添加页面卡片到工作空间
    const targetContainer = elements.workspacePageContent || elements.pageContent;
    if (targetContainer) {
        const pageContainer = document.createElement('div');
        pageContainer.innerHTML = cardHtml;
        targetContainer.appendChild(pageContainer.firstElementChild);
        
        // 滚动到最新内容
        const lastCard = targetContainer.lastElementChild;
        if (lastCard) {
            lastCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
}

// 解析页面内容
function parsePageContent(pageContent) {
    console.log('解析页面内容:', pageContent);
    
    // 移除<outline>标识符，确保不在前端显示
    let cleanContent = pageContent.replace(/<outline>/g, '').replace(/<\/outline>/g, '');
    
    const titleMatch = cleanContent.match(/<title>([\s\S]*?)<\/title>/);
    const summaryMatch = cleanContent.match(/<summary>([\s\S]*?)<\/summary>/);
    const bodyMatch = cleanContent.match(/<body>([\s\S]*?)<\/body>/);
    const adviceMatch = cleanContent.match(/<img_table_advice>([\s\S]*?)<\/img_table_advice>/);
    
    console.log('标题匹配:', titleMatch);
    console.log('总结匹配:', summaryMatch);
    console.log('正文匹配:', bodyMatch);
    console.log('建议匹配:', adviceMatch);
    
    const result = {
        title: titleMatch ? titleMatch[1].trim() : '无标题',
        summary: summaryMatch ? summaryMatch[1].trim() : '无总结',
        body: bodyMatch ? bodyMatch[1].trim() : '无内容',
        advice: adviceMatch ? adviceMatch[1].trim() : '无建议'
    };
    
    console.log('解析结果:', result);
    return result;
}

// 创建页面卡片HTML
function createPageCard(pageData, pageNumber) {
    return `
        <div class="page-card" data-page="${pageNumber}">
            <div class="page-card-header" onclick="togglePageDetails(${pageNumber})">
                <div class="page-number">第 ${pageNumber} 页</div>
                <div class="page-title-summary">
                    <h3>${pageData.title}</h3>
                    <p>${pageData.summary}</p>
                </div>
                <div class="page-actions">
                    <button class="toggle-details-btn">
                        <i class="fas fa-chevron-down"></i>
                    </button>
                </div>
            </div>
            <div class="page-card-details" style="display: none;">
                <div class="page-body-section">
                    <h4>正文内容</h4>
                    <div class="content-text">${pageData.body.replace(/\n/g, '<br>')}</div>
                </div>
                <div class="page-advice-section">
                    <h4>图标建议</h4>
                    <div class="advice-text">${pageData.advice.replace(/\n/g, '<br>')}</div>
                </div>
            </div>
        </div>
    `;
}

// 完成当前页面渲染
function finalizeCurrentPage(pageData, pageNumber) {
    // 这个函数在page_generated事件中调用，用于最终确认页面内容
    console.log(`页面 ${pageNumber} 生成完成`);
}

// 显示内容确认按钮
function showContentConfirmationButtons() {
    const confirmationHtml = `
        <div class="content-confirmation" id="content-confirmation">
            <div class="confirmation-header">
                <h3>内容生成完成</h3>
                <p>请检查生成的PPT内容，您可以编辑任何页面或确认完成。</p>
            </div>
            <div class="confirmation-actions">
                <button class="btn btn-secondary" onclick="resetContent()">
                    <i class="fas fa-undo"></i> 重新生成
                </button>
                <button class="btn btn-primary" onclick="confirmContent()">
                    <i class="fas fa-check"></i> 确认完成
                </button>
            </div>
        </div>
    `;
    
    elements.pageContent.insertAdjacentHTML('beforeend', confirmationHtml);
}

// 切换页面详情显示
function togglePageDetails(pageNumber) {
    const pageCard = document.querySelector(`[data-page="${pageNumber}"]`);
    if (!pageCard) return;

    const details = pageCard.querySelector('.page-card-details');
    const icon = pageCard.querySelector('.toggle-details-btn i');

    if (details.style.display === 'none') {
        details.style.display = 'block';
        icon.className = 'fas fa-chevron-up';
    } else {
        details.style.display = 'none';
        icon.className = 'fas fa-chevron-down';
    }
}

// 重新生成内容
function resetContent() {
    if (confirm('确定要重新生成内容吗？这将清除当前所有内容。')) {
        elements.pageContent.innerHTML = '';
        generateContent();
    }
}

// 确认内容
function confirmContent() {
    const confirmation = document.getElementById('content-confirmation');
    if (confirmation) {
        confirmation.innerHTML = `
            <div class="content-confirmed">
                <div class="success-message">
                    <i class="fas fa-check-circle"></i>
                    <h3>内容已确认</h3>
                    <p>PPT内容生成完成，您可以继续其他操作。</p>
                </div>
            </div>
        `;
    }
    isEditingContent = false;
}

// 折叠功能
function toggleCollapse(type) {
    const wrapper = document.getElementById(`${type}-content-wrapper`);
    const icon = document.getElementById(`${type}-collapse-icon`);
    
    if (wrapper.style.display === 'none') {
        wrapper.style.display = 'block';
        icon.className = 'fas fa-chevron-up';
    } else {
        wrapper.style.display = 'none';
        icon.className = 'fas fa-chevron-down';
    }
}

window.toggleThinking = toggleThinking;
window.toggleCollapse = toggleCollapse;
window.resetOutline = resetOutline;
window.confirmOutline = confirmOutline;
window.editOutline = editOutline;
window.togglePageDetails = togglePageDetails;
window.resetContent = resetContent;
window.confirmContent = confirmContent;