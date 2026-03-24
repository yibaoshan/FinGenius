CREATE_HTML_TOOL_PROMPT = """你是一名资深的FinGenius前端架构师，专门构建金融分析报告的HTML页面。

## 🎯 核心任务
生成一个完整的、功能齐全的HTML金融分析报告，必须严格遵循以下技术规范：

### 📋 硬性技术要求（违反任何一条视为不合格）

#### 1. 技术栈标准
- **框架**: Bootstrap 5.3.3 (CDN) + FontAwesome 6.5.0 (CDN)
- **脚本**: 原生JavaScript，禁止jQuery
- **图表**: Chart.js 4.x (如需要)
- **编码**: UTF-8，完整可运行的单文件HTML

#### 2. HTML结构语义化
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>...</head>
<body data-theme="light">
  <nav class="navbar">...</nav>
  <main class="container">
    <section id="overview">...</section>
    <section id="analysis">...</section> 
    <section id="debate">...</section>
  </main>
  <footer>...</footer>
</body>
</html>
```

#### 3. 必需的页面模块
- **粘性导航栏**: 锚点链接(概览/分析/对话/声明) + 深色模式切换
- **投票结果卡片**: 最终结论Badge + 看涨看跌百分比 + 可视化进度条
- **分析模块**: 6个专家分析使用Bootstrap Accordion组件
- **辩论时间线**: 完整展示debate_history，支持响应式布局
- **免责声明**: 固定footer格式

#### 4. 数据访问路径 (严格按此结构访问)
```javascript
// 股票基本信息
data.stock_code
data.timestamp

// 研究结果
data.research_results.sentiment
data.research_results.risk  
data.research_results.hot_money
data.research_results.technical
data.research_results.chip_analysis
data.research_results.big_deal

// 战斗结果
data.battle_results.final_decision  // "bullish" | "bearish"
data.battle_results.vote_count.bullish  // 数字
data.battle_results.vote_count.bearish  // 数字
data.battle_results.debate_history[]  // 数组，每个元素包含speaker, content, timestamp, round

// 辩论历史格式
debate_history[i] = {
  speaker: "专家名称",
  content: "发言内容", 
  timestamp: "时间戳",
  round: 轮次号
}
```

#### 5. CSS样式规范
- **颜色主题**: 
  - 主色: #4a6bdf (FinGenius蓝)
  - 成功色: #28a745 (看涨绿)  
  - 危险色: #dc3545 (看跌红)
- **深色模式**: 使用CSS变量 + data-theme属性
- **响应式**: Mobile First，≥768px桌面布局
- **卡片设计**: 统一使用Bootstrap card组件，shadow-sm效果

#### 6. JavaScript功能要求
- **主题切换**: 完整的深色/浅色模式切换逻辑
- **平滑滚动**: 导航锚点 + 回到顶部按钮
- **数据渲染**: 必须在DOMContentLoaded中完整渲染辞论历史
- **投票可视化**: 动态计算并显示百分比进度条

#### 7. 辩论时间线实现标准
```javascript
// 必须实现的时间线渲染逻辑
function renderDebateTimeline(debateHistory) {
  const timeline = document.getElementById('debateTimeline');
  debateHistory.forEach((item, index) => {
    const isLeft = index % 2 === 0;
    const timelineItem = `
      <div class="timeline-item ${isLeft ? 'timeline-item-left' : 'timeline-item-right'}">
        <div class="card border-0 shadow-sm">
          <div class="card-header bg-primary text-white">
            <div class="d-flex justify-content-between">
              <span class="fw-bold">${item.speaker}</span>
              <small>第${item.round}轮</small>
            </div>
          </div>
          <div class="card-body">
            <p class="card-text">${item.content}</p>
            <small class="text-muted">${item.timestamp}</small>
          </div>
        </div>
      </div>
    `;
    timeline.innerHTML += timelineItem;
  });
}
```

### 📐 布局结构标准

#### Overview Section (投票结果突出显示)
- 股票标题 + 基本信息
- 投票结果卡片: Badge显示最终结论
- 看涨/看跌票数 + 百分比可视化进度条

#### Analysis Section (折叠面板)  
- 6个专家分析使用Bootstrap Accordion
- 情感分析/风险控制/游资分析/技术面/筹码/大单异动

#### Debate Section (完整时间线)
- 标题: "专家辩论过程"
- 时间线容器: 左右交错或垂直布局(移动端)
- 完整渲染所有debate_history数据

### ⚠️ 关键注意事项
1. **数据安全**: 先检查数据存在性再访问，避免undefined错误
2. **响应式**: 时间线在≤768px时自动变为垂直布局
3. **性能**: CDN资源，无大型库依赖
4. **兼容性**: 支持现代浏览器，优雅降级
5. **完整性**: 一次性输出完整可运行的HTML文件

### 📤 输出格式要求
严格按以下格式输出，不要任何额外解释：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<!-- 完整的HTML代码 -->
</html>
```

请基于提供的数据生成符合FinGenius品牌标准的专业金融分析报告。"""

CREATE_HTML_TEMPLATE_PROMPT = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FinGenius 股票分析报告</title>
    
    <!-- Bootstrap 5 & FontAwesome CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
    
    <style>
        /* FinGenius 品牌色彩和主题变量 */
        :root {
            --fg-primary: #4a6bdf;
            --fg-primary-dark: #3a5bdf;
            --fg-success: #28a745;
            --fg-danger: #dc3545;
            --fg-light-bg: #f8f9fa;
            --fg-white: #ffffff;
            --fg-dark-bg: #1a1d23;
            --fg-dark-card: #2d3748;
            --fg-dark-text: #e2e8f0;
            --fg-border: #dee2e6;
            --fg-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
        }
        
        /* 深色模式变量覆盖 */
        [data-theme="dark"] {
            --bs-body-bg: var(--fg-dark-bg);
            --bs-body-color: var(--fg-dark-text);
            --bs-card-bg: var(--fg-dark-card);
            --bs-border-color: #4a5568;
        }
        
        /* 全局样式 */
        html {
            scroll-behavior: smooth;
        }
        
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            background-color: var(--bs-body-bg, var(--fg-light-bg));
            transition: all 0.3s ease;
        }
        
        /* 导航栏样式 */
        .navbar-brand {
            font-weight: 700;
            color: var(--fg-primary) !important;
            font-size: 1.5rem;
        }
        
        .navbar {
            box-shadow: var(--fg-shadow);
            background-color: var(--bs-card-bg, var(--fg-white)) !important;
        }
        
        /* 卡片统一样式 */
        .card {
            border: none;
            box-shadow: var(--fg-shadow);
            border-radius: 0.75rem;
            background-color: var(--bs-card-bg, var(--fg-white));
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.1);
        }
        
        /* 投票结果可视化 */
        .vote-progress {
            height: 1.5rem;
            background-color: var(--fg-border);
            border-radius: 0.75rem;
            overflow: hidden;
            position: relative;
        }
        
        .vote-progress-bullish {
            background: linear-gradient(90deg, var(--fg-success), #34ce57);
            height: 100%;
            transition: width 0.8s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 0.875rem;
        }
        
        .vote-progress-bearish {
            background: linear-gradient(90deg, var(--fg-danger), #e55353);
            height: 100%;
            transition: width 0.8s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 0.875rem;
            position: absolute;
            right: 0;
            top: 0;
        }
        
        /* 时间线样式 */
        .timeline {
            position: relative;
            padding: 2rem 0;
        }
        
        .timeline::before {
            content: '';
            position: absolute;
            left: 50%;
            top: 0;
            bottom: 0;
            width: 3px;
            background: linear-gradient(to bottom, var(--fg-primary), var(--fg-primary-dark));
            transform: translateX(-50%);
            border-radius: 1.5px;
        }
        
        .timeline-item {
            position: relative;
            margin: 2.5rem 0;
        }
        
        .timeline-item-left .card {
            margin-right: 50%;
            margin-left: 0;
            transform: translateX(-1rem);
        }
        
        .timeline-item-right .card {
            margin-left: 50%;
            margin-right: 0;
            transform: translateX(1rem);
        }
        
        .timeline-item::before {
            content: '';
            position: absolute;
            left: 50%;
            top: 1.5rem;
            width: 1rem;
            height: 1rem;
            background-color: var(--fg-primary);
            border: 3px solid var(--bs-body-bg, var(--fg-white));
            border-radius: 50%;
            transform: translateX(-50%);
            z-index: 10;
        }
        
        /* 移动端时间线适配 */
        @media (max-width: 768px) {
            .timeline::before {
                left: 1rem;
            }
            
            .timeline-item::before {
                left: 1rem;
            }
            
            .timeline-item-left .card,
            .timeline-item-right .card {
                margin-left: 3rem;
                margin-right: 0;
                transform: none;
            }
        }
        
        /* 回到顶部按钮 */
        #backToTop {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 3rem;
            height: 3rem;
            border-radius: 50%;
            background-color: var(--fg-primary);
            border: none;
            color: white;
            display: none;
            z-index: 1000;
            transition: all 0.3s ease;
            box-shadow: 0 0.25rem 0.5rem rgba(0, 0, 0, 0.2);
        }
        
        #backToTop:hover {
            background-color: var(--fg-primary-dark);
            transform: translateY(-2px);
        }
        
        #backToTop.show {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* 自定义Badge样式 */
        .badge-bullish {
            background: linear-gradient(45deg, var(--fg-success), #34ce57);
            color: white;
        }
        
        .badge-bearish {
            background: linear-gradient(45deg, var(--fg-danger), #e55353);
            color: white;
        }
        
        /* 动画效果 */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .fade-in-up {
            animation: fadeInUp 0.6s ease forwards;
        }
        
        /* Accordion自定义样式 */
        .accordion-button:not(.collapsed) {
            background-color: var(--fg-primary);
            color: white;
        }
        
        .accordion-button:focus {
            box-shadow: 0 0 0 0.25rem rgba(74, 107, 223, 0.25);
        }
    </style>
</head>
<body data-theme="light">
    <!-- 粘性导航栏 -->
    <nav class="navbar navbar-expand-lg sticky-top">
        <div class="container">
            <a class="navbar-brand" href="#">
                <i class="fas fa-chart-line me-2"></i>FinGenius
            </a>
            
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto align-items-center">
                    <li class="nav-item">
                        <a class="nav-link" href="#overview">
                            <i class="fas fa-chart-pie me-1"></i>概览
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#analysis">
                            <i class="fas fa-microscope me-1"></i>分析
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#debate">
                            <i class="fas fa-comments me-1"></i>对话
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#disclaimer">
                            <i class="fas fa-info-circle me-1"></i>声明
                        </a>
                    </li>
                    <li class="nav-item ms-2">
                        <button id="themeToggle" class="btn btn-outline-primary btn-sm">
                            <i class="fas fa-moon"></i>
                        </button>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
 
    <!-- 主内容区域 -->
    <main class="container py-4">
        <!-- 概览部分 - 将被动态填充 -->
        <section id="overview" class="mb-5">
            <!-- 股票标题和投票结果将在这里渲染 -->
    </section>
 
        <!-- 分析部分 - 将被动态填充 -->
        <section id="analysis" class="mb-5">
            <!-- 6个专家分析的Accordion将在这里渲染 -->
    </section>
 
        <!-- 辩论部分 -->
        <section id="debate" class="mb-5">
            <div class="text-center mb-4">
                <h2 class="fw-bold">
                    <i class="fas fa-users me-2 text-primary"></i>专家辩论过程
                </h2>
                <p class="text-muted">AI专家实时辩论的完整记录</p>
            </div>
            
            <div class="timeline" id="debateTimeline">
                <!-- 时间线内容将被JavaScript动态渲染 -->
            </div>
    </section>
    </main>
    
    <!-- 免责声明 -->
    <footer id="disclaimer" class="bg-light py-4 mt-5 border-top">
        <div class="container text-center">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <h5 class="fw-bold mb-3">
                        <i class="fas fa-robot me-2 text-primary"></i>AI生成报告声明
                    </h5>
                    <p class="mb-2">
                        本报告由FinGenius人工智能系统自动生成，基于公开数据和算法模型进行分析。
                    </p>
                    <p class="mb-2 text-warning fw-semibold">
                        <i class="fas fa-exclamation-triangle me-1"></i>
                        内容仅供参考，不构成投资建议。投资有风险，决策需谨慎。
                    </p>
                    <p class="text-muted small mb-0">
                        &copy; 2025 FinGenius AI分析系统. 版权所有.
                    </p>
                </div>
            </div>
        </div>
    </footer>
 
    <!-- 回到顶部按钮 -->
    <button id="backToTop" title="回到顶部">
        <i class="fas fa-arrow-up"></i>
    </button>

    <!-- Bootstrap JavaScript -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // 页面数据全局变量 - 将被填充实际数据
        let reportData = window.reportData || {};
        
        // DOM加载完成后执行
        document.addEventListener('DOMContentLoaded', function() {
            // 直接渲染页面，数据将在注入时被替换
            renderPage();
            
            // 初始化交互功能
            initializeInteractions();
        });
        
        // 渲染整个页面
        function renderPage() {
            renderOverview();
            renderAnalysis();
            renderDebate();
        }
        
        // 渲染概览部分
        function renderOverview() {
            const overview = document.getElementById('overview');
            const stockCode = reportData.stock_code || '未知';
            const voteResults = reportData.vote_results || {};
            const bullishCount = voteResults.bullish || 0;
            const bearishCount = voteResults.bearish || 0;
            const finalDecision = voteResults.final_decision || 'unknown';
            
            const totalVotes = bullishCount + bearishCount;
            const bullishPct = totalVotes > 0 ? (bullishCount / totalVotes * 100).toFixed(1) : 0;
            const bearishPct = totalVotes > 0 ? (bearishCount / totalVotes * 100).toFixed(1) : 0;
            
            const decisionBadge = finalDecision.toLowerCase() === 'bullish' ? 
                `<span class="badge badge-bullish fs-4 px-3 py-2"><i class="fas fa-arrow-up me-2"></i>看涨 Bullish</span>` :
                `<span class="badge badge-bearish fs-4 px-3 py-2"><i class="fas fa-arrow-down me-2"></i>看跌 Bearish</span>`;
            
            overview.innerHTML = `
                <div class="text-center mb-4 fade-in-up">
                    <h1 class="display-4 fw-bold text-primary mb-2">
                        ${stockCode} 综合分析报告
                    </h1>
                    <p class="lead text-muted">基于FinGenius AI多专家协同分析</p>
                </div>
                
                <div class="row justify-content-center">
                    <div class="col-lg-8">
                        <div class="card border-0 shadow-lg fade-in-up">
                            <div class="card-body p-4">
                                <div class="text-center mb-4">
                                    <h3 class="card-title mb-3">
                                        <i class="fas fa-poll me-2 text-primary"></i>专家投票结果
                                    </h3>
                                    <div class="mb-4">
                                        ${decisionBadge}
                                    </div>
                                </div>
                                
                                <div class="row text-center mb-4">
                                    <div class="col-6">
                                        <div class="p-3">
                                            <h4 class="text-success mb-1">${bullishCount}</h4>
                                            <p class="text-muted mb-0">看涨票数</p>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="p-3">
                                            <h4 class="text-danger mb-1">${bearishCount}</h4>
                                            <p class="text-muted mb-0">看跌票数</p>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="vote-progress mb-3" style="position: relative;">
                                    <div class="vote-progress-bullish" style="width: ${bullishPct}%;">
                                        ${bullishPct > 15 ? bullishPct + '%' : ''}
                                    </div>
                                    <div class="vote-progress-bearish" style="width: ${bearishPct}%;">
                                        ${bearishPct > 15 ? bearishPct + '%' : ''}
                                    </div>
                                </div>
                                
                                <div class="row text-center">
                                    <div class="col-6">
                                        <small class="text-success fw-semibold">${bullishPct}% 看涨</small>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-danger fw-semibold">${bearishPct}% 看跌</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // 渲染分析部分
        function renderAnalysis() {
            const analysis = document.getElementById('analysis');
            const research = reportData.research_results || {};
            
            const analysisData = [
                { id: 'sentiment', title: '市场情感分析', icon: 'fas fa-heart-pulse', content: research.sentiment || '暂无数据' },
                { id: 'risk', title: '风险控制分析', icon: 'fas fa-shield-alt', content: research.risk || '暂无数据' },
                { id: 'hot_money', title: '游资流向分析', icon: 'fas fa-fire', content: research.hot_money || '暂无数据' },
                { id: 'technical', title: '技术面分析', icon: 'fas fa-chart-area', content: research.technical || '暂无数据' },
                { id: 'chip_analysis', title: '筹码分布分析', icon: 'fas fa-layer-group', content: research.chip_analysis || '暂无数据' },
                { id: 'big_deal', title: '大单异动分析', icon: 'fas fa-dollar-sign', content: research.big_deal || '暂无数据' }
            ];
            
            const accordionItems = analysisData.map((item, index) => `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="heading${item.id}">
                        <button class="accordion-button ${index === 0 ? '' : 'collapsed'}" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#collapse${item.id}">
                            <i class="${item.icon} me-2 text-primary"></i>
                            ${item.title}
                        </button>
                    </h2>
                    <div id="collapse${item.id}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}" 
                         data-bs-parent="#analysisAccordion">
                        <div class="accordion-body">
                            <div class="analysis-content">
                                ${formatAnalysisContent(item.content)}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
            
            analysis.innerHTML = `
                <div class="text-center mb-4">
                    <h2 class="fw-bold">
                        <i class="fas fa-microscope me-2 text-primary"></i>专家分析详情
                    </h2>
                    <p class="text-muted">六位AI专家的深度分析结果</p>
                </div>
                
                <div class="accordion" id="analysisAccordion">
                    ${accordionItems}
                </div>
            `;
        }
        
        // 格式化分析内容
        function formatAnalysisContent(content) {
            if (!content || content === '暂无数据') {
                return '<p class="text-muted"><i class="fas fa-info-circle me-2"></i>暂无分析数据</p>';
            }
            
            // 简单的文本格式化 - 将换行转为段落
            return content.split('\n\n').map(paragraph => 
                paragraph.trim() ? `<p>${paragraph.trim()}</p>` : ''
            ).join('');
        }
        
        // 渲染辩论时间线
        function renderDebate() {
            const timeline = document.getElementById('debateTimeline');
            const debateHistory = reportData.debate_history || [];
            
            if (debateHistory.length === 0) {
                timeline.innerHTML = `
                    <div class="text-center text-muted py-5">
                        <i class="fas fa-comments fa-3x mb-3 opacity-50"></i>
                        <p>暂无辩论记录</p>
                    </div>
                `;
                return;
            }
            
            timeline.innerHTML = debateHistory.map((item, index) => {
                const isLeft = index % 2 === 0;
                const speaker = item.speaker || '未知专家';
                const content = item.content || '无内容';
                const round = item.round || Math.floor(index / 2) + 1;
                const timestamp = item.timestamp || new Date().toLocaleString();
                
                return `
                    <div class="timeline-item ${isLeft ? 'timeline-item-left' : 'timeline-item-right'}">
                        <div class="card border-0 shadow-sm fade-in-up" style="animation-delay: ${index * 0.1}s">
                            <div class="card-header bg-primary text-white">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <i class="fas fa-user-tie me-2"></i>
                                        <span class="fw-bold">${speaker}</span>
                                    </div>
                                    <div class="text-end">
                                        <small class="opacity-75">第${round}轮</small>
                                    </div>
                                </div>
                            </div>
                            <div class="card-body">
                                <div class="debate-content">
                                    ${formatDebateContent(content)}
                                </div>
                                <div class="mt-3 pt-3 border-top">
                                    <small class="text-muted">
                                        <i class="fas fa-clock me-1"></i>
                                        ${timestamp}
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        // 格式化辩论内容
        function formatDebateContent(content) {
            if (!content) return '<p class="text-muted">无内容</p>';
            
            return content.split('\n').map(line => 
                line.trim() ? `<p class="mb-2">${line.trim()}</p>` : ''
            ).join('');
        }
        
        // 初始化交互功能
        function initializeInteractions() {
            // 主题切换
        const themeToggle = document.getElementById('themeToggle');
            const body = document.body;
            
            themeToggle.addEventListener('click', function() {
                const currentTheme = body.getAttribute('data-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                
                body.setAttribute('data-theme', newTheme);
                
                // 更新按钮图标
                const icon = themeToggle.querySelector('i');
                icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
                
                // 保存主题偏好
                localStorage.setItem('theme', newTheme);
            });
            
            // 恢复保存的主题
            const savedTheme = localStorage.getItem('theme') || 'light';
            body.setAttribute('data-theme', savedTheme);
            const icon = themeToggle.querySelector('i');
            icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            
            // 回到顶部按钮
            const backToTop = document.getElementById('backToTop');
            
            window.addEventListener('scroll', function() {
                if (window.pageYOffset > 400) {
                    backToTop.classList.add('show');
                } else {
                    backToTop.classList.remove('show');
                }
            });
            
            backToTop.addEventListener('click', function() {
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            });
            
            // 平滑滚动锚点
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function(e) {
                    e.preventDefault();
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                });
            });
        }
        
        // 页面数据注入点 - 这里会被实际数据替换
        window.reportData = {}; // 这个会被实际的JSON数据替换
        reportData = window.reportData;
    </script>
</body>
</html>
"""
