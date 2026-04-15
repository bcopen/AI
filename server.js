const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const Database = require('better-sqlite3');
const { v4: uuidv4 } = require('uuid');
const cron = require('node-cron');
const { chromium } = require('playwright');
const path = require('path');

const app = express();
const PORT = 3000;

app.use(cors());
app.use(bodyParser.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

const db = new Database('./test_automation.db');
console.log('Connected to SQLite database');

db.exec(`CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL, description TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)`);
db.exec(`CREATE TABLE IF NOT EXISTS test_cases (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, name TEXT NOT NULL, description TEXT, steps TEXT, expected_result TEXT, status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)`);
db.exec(`CREATE TABLE IF NOT EXISTS test_reports (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, project_name TEXT NOT NULL, report_name TEXT NOT NULL, total_cases INTEGER, passed INTEGER, failed INTEGER, skipped INTEGER, execution_time TEXT, details TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)`);
db.exec(`CREATE TABLE IF NOT EXISTS scheduled_tasks (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, task_name TEXT NOT NULL, cron_expression TEXT NOT NULL, test_case_ids TEXT, is_active INTEGER DEFAULT 1, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)`);

let browser = null, recordingPage = null, isRecording = false;
async function getBrowser() { if (!browser) browser = await chromium.launch({ headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] }); return browser; }

// Projects
app.get('/api/projects', (req, res) => { try { res.json(db.prepare('SELECT * FROM projects ORDER BY created_at DESC').all()); } catch(e) { res.status(500).json({error:e.message}); }});
app.get('/api/projects/:id', (req, res) => { try { res.json(db.prepare('SELECT * FROM projects WHERE id = ?').get(req.params.id)); } catch(e) { res.status(500).json({error:e.message}); }});
app.post('/api/projects', (req, res) => { const {name,url,description}=req.body; const id=uuidv4(); try { db.prepare('INSERT INTO projects (id,name,url,description) VALUES (?,?,?,?)').run(id,name,url,description||''); res.json({id,name,url,description,created_at:new Date().toISOString()}); } catch(e) { res.status(500).json({error:e.message}); }});
app.put('/api/projects/:id', (req, res) => { const {name,url,description}=req.body; try { db.prepare('UPDATE projects SET name=?,url=?,description=? WHERE id=?').run(name,url,description,req.params.id); res.json({message:'Updated'}); } catch(e) { res.status(500).json({error:e.message}); }});
app.delete('/api/projects/:id', (req, res) => { try { db.prepare('DELETE FROM test_cases WHERE project_id=?').run(req.params.id); db.prepare('DELETE FROM projects WHERE id=?').run(req.params.id); res.json({message:'Deleted'}); } catch(e) { res.status(500).json({error:e.message}); }});

// Test Cases
app.get('/api/projects/:projectId/test-cases', (req, res) => { try { res.json(db.prepare('SELECT * FROM test_cases WHERE project_id=? ORDER BY created_at DESC').all(req.params.projectId)); } catch(e) { res.status(500).json({error:e.message}); }});
app.post('/api/test-cases', (req, res) => { const {project_id,name,description,steps,expected_result}=req.body; const id=uuidv4(); try { db.prepare('INSERT INTO test_cases (id,project_id,name,description,steps,expected_result) VALUES (?,?,?,?,?,?)').run(id,project_id,name,description||'',JSON.stringify(steps||[]),expected_result||''); res.json({id,project_id,name,description,steps,expected_result,status:'pending',created_at:new Date().toISOString()}); } catch(e) { res.status(500).json({error:e.message}); }});
app.put('/api/test-cases/:id', (req, res) => { const {name,description,steps,expected_result}=req.body; try { db.prepare('UPDATE test_cases SET name=?,description=?,steps=?,expected_result=? WHERE id=?').run(name,description,JSON.stringify(steps),expected_result,req.params.id); res.json({message:'Updated'}); } catch(e) { res.status(500).json({error:e.message}); }});
app.delete('/api/test-cases/:id', (req, res) => { try { db.prepare('DELETE FROM test_cases WHERE id=?').run(req.params.id); res.json({message:'Deleted'}); } catch(e) { res.status(500).json({error:e.message}); }});

app.post('/api/test-cases/generate-ai', async (req, res) => { const {project_id,description}=req.body; const id=uuidv4(); const steps=[{action:'navigate',target:req.body.url||'',data:''},{action:'click',target:'button#login',data:''},{action:'input',target:'input#username',data:'testuser'},{action:'click',target:'button[type="submit"]',data:''}]; try { db.prepare('INSERT INTO test_cases (id,project_id,name,description,steps,expected_result) VALUES (?,?,?,?,?,?)').run(id,project_id,'AI: '+(description?.substring(0,30)||'Test'),description||'',JSON.stringify(steps),'Success'); res.json({id,project_id,name:'AI: '+description,description,steps,expected_result:'Success',status:'pending'}); } catch(e) { res.status(500).json({error:e.message}); }});

app.post('/api/test-cases/generate-mcp', async (req, res) => { const {project_id,url}=req.body; try { const br=await getBrowser(); const page=await br.newPage(); await page.goto(url,{waitUntil:'networkidle',timeout:10000}); const elements=await page.evaluate(()=>{const els=document.querySelectorAll('a,button,input,select,textarea');return Array.from(els).slice(0,15).map(el=>({tag:el.tagName.toLowerCase(),id:el.id,class:el.className,type:el.type}));}); await page.close(); const steps=[{action:'navigate',target:url,data:''}]; elements.forEach(el=>{let sel=el.id?'#'+el.id:(el.tag+(el.class?'.'+el.class.split(' ')[0]:''));if(el.tag==='input')steps.push({action:'input',target:sel,data:'test'});else if(el.tag==='button')steps.push({action:'click',target:sel,data:''});}); const id=uuidv4(); db.prepare('INSERT INTO test_cases (id,project_id,name,description,steps,expected_result) VALUES (?,?,?,?,?,?)').run(id,project_id,'MCP: '+new URL(url).hostname,'Auto-generated',JSON.stringify(steps),'Success'); res.json({id,project_id,steps,expected_result:'Success'}); } catch(e) { res.status(500).json({error:e.message}); }});

app.post('/api/test-cases/:id/execute', async (req, res) => { const tc=db.prepare('SELECT * FROM test_cases WHERE id=?').get(req.params.id); if(!tc)return res.status(404).json({error:'Not found'}); const steps=JSON.parse(tc.steps||'[]'); const results=[]; let passed=true; const startTime=Date.now(); try { const br=await getBrowser(); const page=await br.newPage(); for(const step of steps){try{if(step.action==='navigate')await page.goto(step.target,{waitUntil:'networkidle',timeout:10000});else if(step.action==='click')await page.click(step.target,{timeout:5000});else if(step.action==='input')await page.fill(step.target,step.data,{timeout:5000});else if(step.action==='assert'){const v=await page.isVisible(step.target);if(step.data==='visible'&&!v)passed=false;}results.push({step,status:'passed'});}catch(e){results.push({step,status:'failed',error:e.message});passed=false;}} await page.close(); const execTime=((Date.now()-startTime)/1000).toFixed(2)+'s'; db.prepare('UPDATE test_cases SET status=? WHERE id=?').run(passed?'passed':'failed',req.params.id); const rid=uuidv4(); db.prepare('INSERT INTO test_reports (id,project_id,project_name,report_name,total_cases,passed,failed,skipped,execution_time,details) VALUES (?,?,?,?,?,?,?,?,?,?)').run(rid,tc.project_id,'Test',tc.name+'_'+new Date().toISOString().split('T')[0],1,passed?1:0,passed?0:1,0,execTime,JSON.stringify(results)); res.json({passed,executionTime:execTime,results,reportId:rid}); } catch(e) { res.status(500).json({error:e.message}); }});

app.post('/api/test-cases/batch-execute', async (req, res) => { const {test_case_ids,project_id}=req.body; const results=[]; let totalPassed=0,totalFailed=0; const startTime=Date.now(); try { const br=await getBrowser(); for(const tid of test_case_ids){const tc=db.prepare('SELECT * FROM test_cases WHERE id=?').get(tid);if(!tc)continue;const steps=JSON.parse(tc.steps||'[]');const page=await br.newPage();let ok=true;for(const s of steps){try{if(s.action==='navigate')await page.goto(s.target,{waitUntil:'networkidle',timeout:10000});else if(s.action==='click')await page.click(s.target,{timeout:5000});else if(s.action==='input')await page.fill(s.target,s.data,{timeout:5000});}catch(e){ok=false;}}await page.close();if(ok)totalPassed++;else totalFailed++;db.prepare('UPDATE test_cases SET status=? WHERE id=?').run(ok?'passed':'failed',tid);results.push({testCaseId:tid,passed:ok});} const execTime=((Date.now()-startTime)/1000).toFixed(2)+'s'; const proj=db.prepare('SELECT name FROM projects WHERE id=?').get(project_id); const rid=uuidv4(); db.prepare('INSERT INTO test_reports (id,project_id,project_name,report_name,total_cases,passed,failed,skipped,execution_time,details) VALUES (?,?,?,?,?,?,?,?,?,?)').run(rid,project_id,proj?.name||'Batch','Batch_'+new Date().toISOString().split('T')[0],test_case_ids.length,totalPassed,totalFailed,0,execTime,JSON.stringify(results)); res.json({total:test_case_ids.length,passed:totalPassed,failed:totalFailed,executionTime:execTime,results,reportId:rid}); } catch(e) { res.status(500).json({error:e.message}); }});

// Recording
app.post('/api/recording/start', async (req, res) => { const {start_url}=req.body; if(isRecording)return res.status(400).json({error:'Already recording'}); try { const sid=uuidv4(); isRecording=true; const br=await getBrowser(); recordingPage=await br.newPage(); await recordingPage.addInitScript(()=>{window.recordingData=[];document.addEventListener('click',e=>{window.recordingData.push({action:'click',target:e.target.tagName.toLowerCase(),timestamp:Date.now()});});}); await recordingPage.goto(start_url,{waitUntil:'networkidle'}); res.json({sessionId:sid,message:'Recording started',url:start_url}); } catch(e) { res.status(500).json({error:e.message}); }});
app.post('/api/recording/stop', async (req, res) => { if(!isRecording||!recordingPage)return res.status(400).json({error:'Not recording'}); try { const actions=await recordingPage.evaluate(()=>window.recordingData||[]); await recordingPage.close(); recordingPage=null; isRecording=false; res.json({message:'Stopped',actions,totalActions:actions.length}); } catch(e) { res.status(500).json({error:e.message}); }});
app.get('/api/recording/status', (req, res) => { res.json({isRecording,hasPage:!!recordingPage}); });
app.post('/api/recording/generate-test-case', (req, res) => { const {project_id,actions,name}=req.body; const id=uuidv4(); try { db.prepare('INSERT INTO test_cases (id,project_id,name,description,steps,expected_result) VALUES (?,?,?,?,?,?)').run(id,project_id,name||'Recorded','From recording',JSON.stringify(actions),'Success'); res.json({id,project_id,name,steps:actions}); } catch(e) { res.status(500).json({error:e.message}); }});

// Reports
app.get('/api/reports', (req, res) => { try { res.json(db.prepare('SELECT * FROM test_reports ORDER BY created_at DESC').all()); } catch(e) { res.status(500).json({error:e.message}); }});
app.get('/api/reports/:id', (req, res) => { try { res.json(db.prepare('SELECT * FROM test_reports WHERE id=?').get(req.params.id)); } catch(e) { res.status(500).json({error:e.message}); }});
app.get('/api/projects/:projectId/reports', (req, res) => { try { res.json(db.prepare('SELECT * FROM test_reports WHERE project_id=? ORDER BY created_at DESC').all(req.params.projectId)); } catch(e) { res.status(500).json({error:e.message}); }});

// Scheduled Tasks
const scheduledJobs = new Map();
function scheduleTask(taskId, cronExpr, projectId, testCaseIds) {
    if (scheduledJobs.has(taskId)) scheduledJobs.get(taskId).stop();
    const job = cron.schedule(cronExpr, async () => {
        console.log('Executing scheduled:', taskId);
        let passed=0, failed=0;
        for(const tid of testCaseIds){const tc=db.prepare('SELECT * FROM test_cases WHERE id=?').get(tid);if(!tc)continue;const steps=JSON.parse(tc.steps||'[]');const br=await getBrowser();const page=await br.newPage();let ok=true;for(const s of steps){try{if(s.action==='navigate')await page.goto(s.target);else if(s.action==='click')await page.click(s.target);}catch(e){ok=false;}}await page.close();if(ok)passed++;else failed++;}
        const proj=db.prepare('SELECT name FROM projects WHERE id=?').get(projectId);
        const rid=uuidv4();
        db.prepare('INSERT INTO test_reports (id,project_id,project_name,report_name,total_cases,passed,failed,skipped,execution_time,details) VALUES (?,?,?,?,?,?,?,?,?,?)').run(rid,projectId,proj?.name||'','Scheduled_'+Date.now(),testCaseIds.length,passed,failed,0,'N/A','[]');
    });
    scheduledJobs.set(taskId, job);
}

app.get('/api/scheduled-tasks', (req, res) => { try { res.json(db.prepare('SELECT * FROM scheduled_tasks ORDER BY created_at DESC').all()); } catch(e) { res.status(500).json({error:e.message}); }});
app.post('/api/scheduled-tasks', (req, res) => { const {project_id,task_name,cron_expression,test_case_ids}=req.body; const id=uuidv4(); try { db.prepare('INSERT INTO scheduled_tasks (id,project_id,task_name,cron_expression,test_case_ids) VALUES (?,?,?,?,?)').run(id,project_id,task_name,cron_expression,JSON.stringify(test_case_ids||[])); scheduleTask(id,cron_expression,project_id,test_case_ids||[]); res.json({id,project_id,task_name,cron_expression,test_case_ids,is_active:1}); } catch(e) { res.status(500).json({error:e.message}); }});
app.delete('/api/scheduled-tasks/:id', (req, res) => { try { db.prepare('DELETE FROM scheduled_tasks WHERE id=?').run(req.params.id); res.json({message:'Deleted'}); } catch(e) { res.status(500).json({error:e.message}); }});

// Load existing tasks on startup
db.prepare('SELECT * FROM scheduled_tasks WHERE is_active=1').all().forEach(t => { scheduleTask(t.id, t.cron_expression, t.project_id, JSON.parse(t.test_case_ids || '[]')); });

app.listen(PORT, () => { console.log('Server running on http://localhost:' + PORT); });
process.on('SIGINT', async () => { if(browser)await browser.close(); process.exit(0); });
