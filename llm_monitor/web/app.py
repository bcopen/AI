"""
Web 应用 - FastAPI 实现
提供价格展示、对比、历史曲线、导出等功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from models.schema import init_db, Vendor, Model, CurrentPrice, PriceHistory, VendorNews
from services.price_tracker import PriceTracker
from services.comparison import PriceComparator
from services.news_monitor import NewsMonitor

app = FastAPI(title="LLM Monitor API", description="大模型价格监控系统 API")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "llm_monitor.db")
SessionLocal, engine = init_db(f"sqlite:///{db_path}")


@app.get("/")
async def root():
    return {"message": "LLM Monitor API", "docs": "/docs", "web": "/web"}


@app.get("/api/prices")
async def get_prices(vendor: Optional[str] = None):
    """获取当前价格列表"""
    db = SessionLocal()
    try:
        tracker = PriceTracker(db)
        prices = tracker.get_current_prices(vendor_name=vendor)
        return prices
    finally:
        db.close()


@app.get("/api/prices/history/{vendor}/{model}")
async def get_price_history(vendor: str, model: str, days: int = Query(default=30, ge=1, le=365)):
    """获取价格历史记录"""
    db = SessionLocal()
    try:
        tracker = PriceTracker(db)
        history = tracker.get_price_history(vendor, model, days=days)
        return history
    finally:
        db.close()


@app.get("/api/compare/{scenario}")
async def compare_prices(scenario: str):
    """按场景对比价格"""
    db = SessionLocal()
    try:
        comparator = PriceComparator(db)
        results = comparator.compare_by_scenario(scenario)
        for i, item in enumerate(results):
            item["rank"] = i + 1
        return results[:20]
    finally:
        db.close()


@app.get("/api/news")
async def get_news(limit: int = Query(default=20, ge=1, le=100)):
    """获取新闻动态"""
    db = SessionLocal()
    try:
        monitor = NewsMonitor(db)
        news = monitor.get_recent_news(limit=limit)
        return news
    finally:
        db.close()


@app.get("/api/vendors")
async def get_vendors():
    """获取厂商列表"""
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).filter(Vendor.enabled == True).all()
        return [{"name": v.name, "display_name": v.display_name, "pricing_url": v.pricing_url} for v in vendors]
    finally:
        db.close()


@app.get("/api/export/csv")
async def export_csv(vendor: Optional[str] = None):
    """导出 CSV"""
    db = SessionLocal()
    try:
        tracker = PriceTracker(db)
        filename = f"llm_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = f"/tmp/{filename}"
        if tracker.export_to_csv(filepath, vendor):
            return FileResponse(path=filepath, media_type="text/csv", filename=filename)
        else:
            raise HTTPException(status_code=404, detail="No data to export")
    finally:
        db.close()


@app.get("/api/export/excel")
async def export_excel(vendor: Optional[str] = None):
    """导出 Excel"""
    db = SessionLocal()
    try:
        tracker = PriceTracker(db)
        filename = f"llm_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = f"/tmp/{filename}"
        if tracker.export_to_excel(filepath, vendor):
            return FileResponse(path=filepath, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=filename)
        else:
            raise HTTPException(status_code=404, detail="No data to export")
    finally:
        db.close()


@app.get("/api/stats")
async def get_stats():
    """获取统计数据"""
    db = SessionLocal()
    try:
        vendor_count = db.query(Vendor).filter(Vendor.enabled == True).count()
        model_count = db.query(Model).count()
        price_count = db.query(CurrentPrice).count()
        news_count = db.query(VendorNews).count()
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_changes = db.query(PriceHistory).filter(PriceHistory.snapshot_date >= seven_days_ago).count()
        return {
            "vendor_count": vendor_count,
            "model_count": model_count,
            "price_count": price_count,
            "news_count": news_count,
            "recent_changes": recent_changes
        }
    finally:
        db.close()


@app.get("/web", response_class=HTMLResponse)
async def web_interface():
    """Web 界面"""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Monitor - 大模型价格监控</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-100 min-h-screen">
    <nav class="bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg">
        <div class="container mx-auto px-4 py-4">
            <div class="flex justify-between items-center">
                <h1 class="text-2xl font-bold">🤖 LLM Monitor</h1>
                <div class="space-x-4">
                    <button onclick="showSection('prices')" class="hover:bg-white/20 px-3 py-2 rounded">价格列表</button>
                    <button onclick="showSection('compare')" class="hover:bg-white/20 px-3 py-2 rounded">价格对比</button>
                    <button onclick="showSection('history')" class="hover:bg-white/20 px-3 py-2 rounded">历史曲线</button>
                    <button onclick="showSection('news')" class="hover:bg-white/20 px-3 py-2 rounded">新闻动态</button>
                    <button onclick="showSection('export')" class="hover:bg-white/20 px-3 py-2 rounded">导出报表</button>
                </div>
            </div>
        </div>
    </nav>
    <div class="container mx-auto px-4 py-8">
        <div id="stats-section" class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8"></div>
        <div id="prices-section" class="section bg-white rounded-lg shadow p-6"></div>
        <div id="compare-section" class="section hidden bg-white rounded-lg shadow p-6"></div>
        <div id="history-section" class="section hidden bg-white rounded-lg shadow p-6"></div>
        <div id="news-section" class="section hidden bg-white rounded-lg shadow p-6"></div>
        <div id="export-section" class="section hidden bg-white rounded-lg shadow p-6"></div>
    </div>
    <script>
const API_BASE='/api';let historyChart=null;
function showSection(id){document.querySelectorAll('.section').forEach(e=>e.classList.add('hidden'));document.getElementById(id+'-section').classList.remove('hidden');if(id==='prices')loadPrices();else if(id==='compare')loadComparison();else if(id==='history')loadHistory();else if(id==='news')loadNews();else if(id==='export')loadExport();}
async function loadStats(){const r=await fetch(API_BASE+'/stats');const d=await r.json();document.getElementById('stats-section').innerHTML='<div class="bg-white rounded-lg shadow p-4"><div class="text-gray-500 text-sm">厂商</div><div class="text-2xl font-bold text-blue-600">'+d.vendor_count+'</div></div><div class="bg-white rounded-lg shadow p-4"><div class="text-gray-500 text-sm">模型</div><div class="text-2xl font-bold text-green-600">'+d.model_count+'</div></div><div class="bg-white rounded-lg shadow p-4"><div class="text-gray-500 text-sm">价格</div><div class="text-2xl font-bold text-purple-600">'+d.price_count+'</div></div><div class="bg-white rounded-lg shadow p-4"><div class="text-gray-500 text-sm">新闻</div><div class="text-2xl font-bold text-orange-600">'+d.news_count+'</div></div><div class="bg-white rounded-lg shadow p-4"><div class="text-gray-500 text-sm">7 天变化</div><div class="text-2xl font-bold text-red-600">'+d.recent_changes+'</div></div>';}
async function loadVendors(){const r=await fetch(API_BASE+'/vendors');const vs=await r.json();let opts='<option value="">全部厂商</option>';vs.forEach(v=>{opts+='<option value="'+v.name+'">'+v.display_name+'</option>';});return opts;}
async function loadPrices(){const v=document.getElementById('vendor-filter')?document.getElementById('vendor-filter').value:'';const url=v?API_BASE+'/prices?vendor='+v:API_BASE+'/prices';const r=await fetch(url);const ps=await r.json();let h='<h2 class="text-xl font-bold mb-4">💰 当前价格</h2><div class="mb-4"><select id="vendor-filter" class="border rounded px-3 py-2" onchange="loadPrices()">'+await loadVendors()+'</select></div><div class="overflow-x-auto"><table class="w-full table-auto"><thead class="bg-gray-50"><tr><th class="px-4 py-2 text-left">厂商</th><th class="px-4 py-2 text-left">模型</th><th class="px-4 py-2 text-right">输入</th><th class="px-4 py-2 text-right">输出</th><th class="px-4 py-2 text-right">上下文</th><th class="px-4 py-2 text-left">能力</th></tr></thead><tbody>';ps.forEach(p=>{h+='<tr class="border-t"><td class="px-4 py-2">'+p.vendor_display_name+'</td><td class="px-4 py-2 font-medium">'+p.model_name+'</td><td class="px-4 py-2 text-right">$'+p.input_price.toFixed(6)+'</td><td class="px-4 py-2 text-right">$'+p.output_price.toFixed(6)+'</td><td class="px-4 py-2 text-right">'+(p.context_window?p.context_window.toLocaleString():'-')+'</td><td class="px-4 py-2 text-sm">'+(p.capabilities?p.capabilities.join(', '):'-')+'</td></tr>';});h+='</tbody></table></div>';document.getElementById('prices-section').innerHTML=h;}
async function loadComparison(){const s=document.getElementById('scenario-select').value;const r=await fetch(API_BASE+'/compare/'+s);const rs=await r.json();let h='<h2 class="text-xl font-bold mb-4">⚖️ 价格对比</h2><div class="mb-4"><select id="scenario-select" class="border rounded px-3 py-2"><option value="chat">聊天对话</option><option value="code">代码生成</option><option value="long_text">长文本</option><option value="multimodal">多模态</option></select><button onclick="loadComparison()" class="bg-green-500 text-white px-4 py-2 rounded ml-2">对比</button></div><div class="overflow-x-auto"><table class="w-full table-auto"><thead class="bg-gray-50"><tr><th class="px-4 py-2">排名</th><th class="px-4 py-2">厂商</th><th class="px-4 py-2">模型</th><th class="px-4 py-2 text-right">输入</th><th class="px-4 py-2 text-right">输出</th><th class="px-4 py-2 text-right">成本</th></tr></thead><tbody>';rs.forEach(r=>{h+='<tr class="border-t '+(r.rank<=3?'bg-yellow-50':'')+'"><td class="px-4 py-2 font-bold">'+(r.rank===1?'🥇':r.rank===2?'🥈':r.rank===3?'🥉':r.rank)+'</td><td class="px-4 py-2">'+r.vendor_display_name+'</td><td class="px-4 py-2 font-medium">'+r.model_name+'</td><td class="px-4 py-2 text-right">$'+r.input_price.toFixed(6)+'</td><td class="px-4 py-2 text-right">$'+r.output_price.toFixed(6)+'</td><td class="px-4 py-2 text-right font-bold text-green-600">$'+r.cost_usd.toFixed(6)+'</td></tr>';});h+='</tbody></table></div>';document.getElementById('compare-section').innerHTML=h;}
async function loadHistory(){let h='<h2 class="text-xl font-bold mb-4">📈 价格历史曲线</h2><div class="mb-4"><select id="history-vendor" class="border rounded px-3 py-2" onchange="loadHistoryModels()"><option value="">选择厂商</option></select><select id="history-model" class="border rounded px-3 py-2 ml-2"><option value="">选择模型</option></select><select id="history-days" class="border rounded px-3 py-2 ml-2"><option value="7">7 天</option><option value="30">30 天</option><option value="90">90 天</option></select><button onclick="loadHistoryChart()" class="bg-purple-500 text-white px-4 py-2 rounded ml-2">查看</button></div><canvas id="history-chart" height="100"></canvas>';document.getElementById('history-section').innerHTML=h;const rv=await fetch(API_BASE+'/vendors');const vs=await rv.json();const sv=document.getElementById('history-vendor');vs.forEach(v=>{sv.innerHTML+='<option value="'+v.name+'">'+v.display_name+'</option>';});}
async function loadHistoryModels(){const v=document.getElementById('history-vendor').value;if(!v)return;const r=await fetch(API_BASE+'/prices?vendor='+v);const ps=await r.json();const sm=document.getElementById('history-model');sm.innerHTML='<option value="">选择模型</option>'+ps.map(p=>'<option value="'+p.model_name+'">'+p.model_name+'</option>').join('');}
async function loadHistoryChart(){const v=document.getElementById('history-vendor').value;const m=document.getElementById('history-model').value;const d=document.getElementById('history-days').value;if(!v||!m){alert('请选择厂商和模型');return;}const r=await fetch(API_BASE+'/prices/history/'+v+'/'+m+'?days='+d);const hist=await r.json();const ctx=document.getElementById('history-chart').getContext('2d');if(historyChart)historyChart.destroy();historyChart=new Chart(ctx,{type:'line',data:{labels:hist.map(h=>new Date(h.snapshot_date).toLocaleDateString()),datasets:[{label:'输入价格',data:hist.map(h=>h.input_price),borderColor:'rgb(59,130,246)',tension:0.1},{label:'输出价格',data:hist.map(h=>h.output_price),borderColor:'rgb(16,185,129)',tension:0.1}]},options:{responsive:true,plugins:{title:{display:true,text:v+' - '+m+' 价格走势'}}}});}
async function loadNews(){const r=await fetch(API_BASE+'/news');const ns=await r.json();let h='<h2 class="text-xl font-bold mb-4">📰 最新动态</h2><div class="space-y-4">';ns.forEach(n=>{h+='<div class="border-l-4 border-orange-500 pl-4 py-2"><div class="font-bold">'+n.title+'</div><div class="text-sm text-gray-600">'+n.vendor_display_name+' · '+n.news_type+'</div>'+(n.url?'<a href="'+n.url+'" target="_blank" class="text-blue-500 text-sm">详情 →</a>':'')+'</div>';});h+='</div>';document.getElementById('news-section').innerHTML=h;}
async function loadExport(){let h='<h2 class="text-xl font-bold mb-4">📥 导出报表</h2><div class="grid grid-cols-1 md:grid-cols-2 gap-4"><div class="border rounded p-4"><h3 class="font-bold mb-2">CSV 格式</h3><p class="text-gray-600 text-sm mb-4">适用于 Excel、Numbers 等</p><button onclick="window.location.href=API_BASE+\'/export/csv\'" class="bg-blue-500 text-white px-4 py-2 rounded w-full">下载 CSV</button></div><div class="border rounded p-4"><h3 class="font-bold mb-2">Excel 格式</h3><p class="text-gray-600 text-sm mb-4">包含多个工作表，按厂商分类</p><button onclick="window.location.href=API_BASE+\'/export/excel\'" class="bg-green-500 text-white px-4 py-2 rounded w-full">下载 Excel</button></div></div>';document.getElementById('export-section').innerHTML=h;}
loadStats();loadPrices();
    </script>
</body>
</html>
    """)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
