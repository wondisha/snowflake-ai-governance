# 🎬 Quick Demo Guide (10-15 Minutes)

**Perfect for quick recording or live demo**

---

## ⏱️ Quick Walkthrough (10-15 minutes total)

### 1. INTRO (30 seconds)

**Say:**
"Today I'm showing you a production-grade autonomous Snowflake governance system with 5 agents managing security, performance, costs, health, and data protection automatically."

**Show:**
- GitHub repo: https://github.com/wondisha/snowflake-ai-governance
- Click: README.md

---

### 2. DASHBOARD OVERVIEW (5 minutes)

**Open: Snowsight Dashboard**

**Page-by-page (30 seconds each):**

1. **Overview** 
   - Point out: Policies, Security Rules, Incidents, Approvals
   - Say: "Central hub showing all governance metrics"

2. **Security**
   - Show: PII detection count
   - Say: "Automatically detects sensitive data"

3. **Performance**
   - Show: Optimizable queries
   - Say: "Our agent auto-tunes queries and scales warehouses"

4. **Cost**
   - Show: Credits used, warehouses
   - Say: "Agent auto-suspends idle warehouses to save money"

5. **Health**
   - Show: Warehouse metrics
   - Say: "Continuous health monitoring with alerts"

6. **Incidents**
   - Show: Active incidents
   - Say: "All detected issues tracked and logged"

7. **Agents**
   - Show: All 5 agents running
   - Say: "Security, Performance, Cost, Health, Spillage - all autonomous"

8. **Inactive Users**
   - Show: User management interface
   - Say: "Automatically manages user lifecycle, flags inactive users"

---

### 3. AGENT AUDIT LOG (2 minutes)

**Run SQL Query:**

```sql
SELECT EVENT_TYPE, ACTION_DESCRIPTION, STATUS, EVENT_TIMESTAMP
FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS
WHERE ACTOR_EMAIL = 'system@governance'
ORDER BY EVENT_TIMESTAMP DESC
LIMIT 10;
```

**Say:**
"Every autonomous action is logged. Here's what agents did automatically:
- Performance: Scaled warehouses, suspended idle ones
- Cost: Suspended unused warehouses
- Security: Processed approvals
- Health: Monitored metrics
- Spillage: Watched for data breaches"

---

### 4. DEPLOYMENT DEMO (1 minute)

**Show Terminal:**

```bash
python deploy.py deployment_config.json
```

**Say:**
"The entire system deployed in 16 seconds with zero errors. All 20+ governance objects created and configured automatically."

---

### 5. KEY FEATURES (1 minute)

**List on screen or narrate:**

✅ 5 Autonomous Agents  
✅ Real-time Dashboard (8 pages)  
✅ Slack Alerts  
✅ Email Reports  
✅ Approval Workflows  
✅ User Lifecycle Management  
✅ Complete Audit Logging  
✅ Multi-Environment Support  
✅ Open Source (MIT)  

---

### 6. CLOSING (30 seconds)

**Say:**
"This is a complete, production-ready governance solution. Deploy to any Snowflake account in minutes. Everything is on GitHub with full documentation."

**Show:**
- GitHub: https://github.com/wondisha/snowflake-ai-governance

---

## 🎥 Recording Instructions:

### Tools You Can Use:
1. **OBS Studio** (Free, Windows/Mac/Linux)
2. **ScreenFlow** (Mac only)
3. **Camtasia** (Professional)
4. **Windows Built-in** (Windows 10+)

### Setup:
1. Open Snowsight in browser
2. Open this guide in another window
3. Hit record
4. Follow the guide section by section
5. Pause between sections for natural pacing

### Quick Tips:
- Speak clearly and at normal pace
- Zoom in when showing details
- Let dashboard load fully before showing
- Use mouse cursor to point to key elements
- Total time: ~12 minutes with natural pausing

---

## 📋 Checklist Before Recording:

- [ ] Logged into Snowflake (QZCIUOS-DB05264)
- [ ] Dashboard open in Snowsight
- [ ] Snowflake worksheet open for SQL queries
- [ ] GitHub repo open
- [ ] Recording tool ready
- [ ] Quiet environment
- [ ] High resolution (1920x1080+)

---

## 🎬 Expected Result:

A professional 10-15 minute demo showing:
- ✅ Complete governance system
- ✅ Real-time monitoring
- ✅ Autonomous agents in action
- ✅ Production deployment
- ✅ Enterprise-grade features

Perfect for:
- YouTube demonstrations
- Client presentations
- Internal team training
- Portfolio/resume showcasing
- GitHub project promotion
