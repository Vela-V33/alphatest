# Screenshot Feature Verification Guide

**CRITICAL UPDATE**: Enhanced debugging and path normalization added as of latest commit.

## Recent Improvements (Latest Deployment)

If screenshots weren't appearing before, the following fixes have been applied:

1. **Path Normalization**: Screenshot lookup now tries multiple path formats (original, Path object, resolved absolute)
2. **Comprehensive Debugging**: Detailed console output shows exact data flow and path matching
3. **Better Error Detection**: Warnings now show available paths when lookup fails

After updating to the latest version, you should see extensive debug output that will help identify the exact issue.

### How to Update Your Deployment

```bash
# Pull latest changes
cd ~/alphatest
git pull origin claude/setup-public-website-GjkNy

# Redeploy to Cloud Run (same command as before)
gcloud run deploy alphatest \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 80 \
  --max-instances 10 \
  --env-vars-file env.yaml \
  --project alphatest-482117
```

### What to Look For in Debug Output

When you run a test, you should now see:

```
[DEBUG] ===== REPORT GENERATION STARTED =====
[DEBUG] Data keys: ['results', 'issues', 'screenshots', 'steps', ...]
[DEBUG] Results count: 1
[DEBUG] Screenshots count: 6
[DEBUG] First result keys: ['command', 'status', 'steps', ...]
[DEBUG] First result has steps: True
[DEBUG] First result steps count: 3
[DEBUG] First step structure: ['step', 'timestamp', 'thinking', 'action', 'result', 'screenshot_before', 'screenshot_after']

[DEBUG] ===== SCREENSHOT PROCESSING =====
[DEBUG] Total screenshots in data: 6
[DEBUG] Total results in data: 1
[DEBUG] ✓ Copied screenshot: 001_step_1_before.png
[DEBUG]   - Registered paths: /app/reports/.../001_step_1_before.png, /app/reports/.../001_step_1_before.png
[DEBUG] ✓ Copied screenshot: 002_step_1_after.png
[DEBUG]   - Registered paths: /app/reports/.../002_step_1_after.png, /app/reports/.../002_step_1_after.png
...
[DEBUG] Total screenshots copied: 18
[DEBUG] Screenshot lookup keys (first 3): ['/app/reports/.../001_step_1_before.png', ...]

[DEBUG] ===== TEST RESULTS HTML GENERATION =====
[DEBUG] Number of test results: 1
[DEBUG] Screenshot lookup has 18 entries
[DEBUG] Test 1: Navigate to homepage
[DEBUG]   - Status: passed
[DEBUG]   - Steps: 3
[DEBUG]   - First step keys: ['step', 'timestamp', 'thinking', 'action', 'result', 'screenshot_before', 'screenshot_after']
[DEBUG]   - First step has screenshot_before: True
[DEBUG]   - First step has screenshot_after: True
[DEBUG]   Step 1: before=True, after=True
[DEBUG]     - Before path from step: /app/reports/.../001_step_1_before.png
[DEBUG]     - Before filename resolved: 001_step_1_before.png
[DEBUG]     - After path from step: /app/reports/.../002_step_1_after.png
[DEBUG]     - After filename resolved: 002_step_1_after.png
```

**KEY INDICATORS**:
- ✅ `Screenshots count: > 0` - Screenshots were captured
- ✅ `Total screenshots copied: > 0` - Screenshots were processed
- ✅ `First step has screenshot_before: True` - Step data has screenshot fields
- ✅ `Before filename resolved: <filename>` - Path lookup succeeded

**PROBLEM INDICATORS**:
- ❌ `Screenshots count: 0` - No screenshots captured (browser/Playwright issue)
- ❌ `Total screenshots copied: 0` - Screenshots captured but files not found
- ❌ `First step has screenshot_before: False` - Screenshot fields not set on steps
- ❌ `Before screenshot NOT FOUND in lookup!` - Path format mismatch (now should be fixed)

---

## What Screenshot Features SHOULD Work

AlphaTest has comprehensive screenshot features built into test reports:

### ✅ **Feature 1: Expandable Per-Step Screenshots**
- Each test step has a **►** arrow icon on the right
- Click the arrow to expand and see before/after screenshots
- Arrow rotates 90° when expanded (becomes **▼**)

### ✅ **Feature 2: Before/After Comparison**
- Screenshots appear in a 2-column grid
- Left: "Before Action" screenshot
- Right: "After Action" screenshot
- Shows visual changes between steps

### ✅ **Feature 3: Modal Zoom**
- Click any screenshot image to view full-size
- Dark modal overlay appears
- Press ESC or click background to close
- High-resolution view for details

### ✅ **Feature 4: Screenshot Gallery**
- At the bottom of each report
- Section titled "📸 All Screenshots"
- Grid layout showing all captured screenshots
- Click any thumbnail to zoom

---

## How to Verify Features Are Working

### **Step 1: Run a Real Test (NOT just scans)**

**IMPORTANT**: The screenshot features **ONLY** appear when you run an actual **TEST**, not just compliance scans.

```bash
# 1. Start AlphaTest
python main.py

# 2. Open in browser
http://localhost:5000

# 3. Create/open a project

# 4. Run a test with a command like:
"Navigate to the homepage, click the login button, and verify the login form appears"
```

**Screenshots are captured during test execution:**
- Before each action (before clicking, typing, etc.)
- After each action (after clicking, typing, etc.)

### **Step 2: Check Console Output**

When the test runs, you should see:

```
🚀 Starting browser...
✓ Browser ready!
📸 Screenshot: before_navigate (145023 bytes)
📸 Screenshot: after_navigate (156789 bytes)
📸 Screenshot: before_click_login (148234 bytes)
📸 Screenshot: after_click_login (149012 bytes)
📸 Screenshot: before_type_email (147890 bytes)
📸 Screenshot: after_type_email (148901 bytes)

🔍 Running compliance scans...
   ♿ Accessibility: WCAG AA
   🔒 Security: 3 missing headers (57% compliant)
   ⚡ Performance: Good (80/100)

[DEBUG] ===== SCREENSHOT PROCESSING =====
[DEBUG] Total screenshots in data: 6
[DEBUG] Total results in data: 1
[DEBUG] ✓ Copied screenshot: 001_before_navigate.png
[DEBUG] ✓ Copied screenshot: 002_after_navigate.png
[DEBUG] ✓ Copied screenshot: 003_before_click_login.png
[DEBUG] ✓ Copied screenshot: 004_after_click_login.png
[DEBUG] ✓ Copied screenshot: 005_before_type_email.png
[DEBUG] ✓ Copied screenshot: 006_after_type_email.png
[DEBUG] Total screenshots copied: 6
[DEBUG] ===== END SCREENSHOT PROCESSING =====

[DEBUG] ===== TEST RESULTS HTML GENERATION =====
[DEBUG] Number of test results: 1
[DEBUG] Screenshot lookup has 6 entries
[DEBUG] Test 1: Navigate to homepage and click login
[DEBUG]   - Status: passed
[DEBUG]   - Steps: 3
[DEBUG]   Step 1: before=True, after=True
[DEBUG]   - Before screenshot: 001_before_navigate.png
[DEBUG]   - After screenshot: 002_after_navigate.png
[DEBUG]   Step 2: before=True, after=True
[DEBUG]   - Before screenshot: 003_before_click_login.png
[DEBUG]   - After screenshot: 004_after_click_login.png
[DEBUG]   Step 3: before=True, after=True
[DEBUG]   - Before screenshot: 005_before_type_email.png
[DEBUG]   - After screenshot: 006_after_type_email.png
[DEBUG] ===== END TEST RESULTS HTML GENERATION =====
```

### **Step 3: Open the Generated Report**

After test completes:
```
Test complete!
Report URL: /reports/{project_id}/{session_id}
```

Click "View Report" or navigate to:
```
http://localhost:5000/reports/{project_id}/{session_id}/report.html
```

### **Step 4: Verify Screenshot Features in Report**

#### **A. Check Expandable Steps**

Look for the test results section:
```
📝 Test Steps

┌─────────────────────────────────────────────────────────┐
│ Step 1: Navigate to homepage                         ► │
├─────────────────────────────────────────────────────────┤
│ Looking at the page, I can see...                      │
└─────────────────────────────────────────────────────────┘
```

**Verify**:
- [ ] Each step has a **►** arrow on the right
- [ ] Steps have a clickable cursor (pointer)
- [ ] Steps have a subtle background on hover

#### **B. Click the Arrow to Expand**

Click the **►** arrow:

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: Navigate to homepage                         ▼ │ ← Arrow rotated
├─────────────────────────────────────────────────────────┤
│ Looking at the page, I can see...                      │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────┬─────────────────┐                  │
│ │ Before Action   │ After Action    │                  │
│ │ [Screenshot]    │ [Screenshot]    │                  │
│ └─────────────────┴─────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

**Verify**:
- [ ] Arrow rotated 90° (now pointing down ▼)
- [ ] Screenshots section appeared below the step text
- [ ] Two images side-by-side (Before | After)
- [ ] Images load properly (not broken image icons)

#### **C. Test Modal Zoom**

Click on any screenshot image:

```
┌───────────────────────────────────────────────────┐
│                                                   │
│                                                   │
│           ┌─────────────────────┐                │
│           │                     │                │
│           │  [Full Screenshot]  │                │
│           │                     │                │
│           └─────────────────────┘                │
│                                                   │
│                                                   │
└───────────────────────────────────────────────────┘
Dark overlay - Press ESC or click to close
```

**Verify**:
- [ ] Dark overlay appears (90% black background)
- [ ] Screenshot shown at full resolution
- [ ] Pressing ESC closes the modal
- [ ] Clicking background closes the modal

#### **D. Check Screenshot Gallery**

Scroll to the bottom of the report:

```
📸 All Screenshots
┌─────┬─────┬─────┬─────┬─────┬─────┐
│ [1] │ [2] │ [3] │ [4] │ [5] │ [6] │
└─────┴─────┴─────┴─────┴─────┴─────┘
Step 1  Step 1  Step 2  Step 2  Step 3  Step 3
```

**Verify**:
- [ ] Section titled "📸 All Screenshots" exists
- [ ] Thumbnails of all screenshots displayed
- [ ] Grid layout (6 per row on desktop)
- [ ] Each thumbnail shows step number
- [ ] Clicking thumbnail opens modal zoom

---

## Common Issues and Solutions

### ❌ **Issue 1: No Screenshots at All**

**Symptoms**:
- Debug log shows: `Total screenshots in data: 0`
- No expandable arrows on steps
- No screenshot gallery section

**Causes**:
1. Only ran compliance scans, not an actual test
2. Test failed before any steps executed
3. Browser didn't capture screenshots

**Solution**:
```bash
# Run a simple test command first
"Navigate to the homepage"

# Check console for screenshot capture messages:
📸 Screenshot: before_navigate (145023 bytes)
📸 Screenshot: after_navigate (156789 bytes)

# If you don't see these, there's a browser/Playwright issue
```

### ❌ **Issue 2: Screenshots Captured But Not Appearing**

**Symptoms**:
- Debug log shows: `Total screenshots in data: 10`
- Debug log shows: `Total screenshots copied: 0`
- Console shows screenshot capture but not copy

**Causes**:
1. File path issues (wrong directory)
2. Permission issues (can't copy files)
3. Screenshots exist but paths don't match

**Solution**:
```bash
# Check if screenshots exist
ls reports/{project_id}/{session_id}/screenshots/

# Check permissions
chmod -R 755 reports/

# Check debug output for warnings:
[WARNING] Screenshot file not found: /path/to/screenshot.png
```

### ❌ **Issue 3: Arrows Don't Expand**

**Symptoms**:
- Screenshots ARE in the report HTML
- Arrows visible but clicking does nothing
- No console errors in browser DevTools

**Causes**:
1. JavaScript not loading
2. JavaScript errors preventing execution
3. Element IDs don't match

**Solution**:
```javascript
// Open browser DevTools (F12)
// Go to Console tab
// Check for errors

// Try manually in console:
toggleStep('step-0-0')

// If this works, the JavaScript is fine
// If this fails, there's a JavaScript error
```

### ❌ **Issue 4: Modal Doesn't Open**

**Symptoms**:
- Screenshots visible in steps
- Clicking image does nothing
- No modal overlay appears

**Causes**:
1. JavaScript error preventing modal
2. CSS z-index issue
3. Event handler not attached

**Solution**:
```javascript
// Open browser DevTools (F12)
// Try manually in console:
openModal('screenshots/001_before_navigate.png')

// Check if modal appears
// If yes, event handler issue
// If no, JavaScript/CSS issue
```

---

## Debugging Checklist

Use this checklist to diagnose screenshot issues:

### **Phase 1: Test Execution**
- [ ] Running an actual TEST (not just scans)
- [ ] Test command has user interactions (navigate, click, type)
- [ ] Console shows `📸 Screenshot:` messages
- [ ] Screenshot file sizes > 1000 bytes

### **Phase 2: Report Generation**
- [ ] Console shows `[DEBUG] ===== SCREENSHOT PROCESSING =====`
- [ ] `Total screenshots in data` > 0
- [ ] `Total screenshots copied` > 0
- [ ] No `[WARNING] Screenshot file not found` messages
- [ ] `Screenshot lookup has X entries` where X > 0

### **Phase 3: HTML Generation**
- [ ] Console shows `[DEBUG] ===== TEST RESULTS HTML GENERATION =====`
- [ ] `Number of test results` > 0
- [ ] Each step shows `before=True, after=True`
- [ ] Before/after screenshots show filenames

### **Phase 4: Browser Rendering**
- [ ] Report opens without JavaScript errors (F12 console)
- [ ] Step cards visible with content
- [ ] Arrows (►) visible on steps that have screenshots
- [ ] Clicking arrow rotates it to ▼
- [ ] Screenshots appear below step text

### **Phase 5: Interactive Features**
- [ ] Clicking screenshot opens modal
- [ ] Dark overlay appears
- [ ] Large image displayed
- [ ] ESC key closes modal
- [ ] Screenshot gallery visible at bottom
- [ ] Gallery thumbnails clickable

---

## File Structure for Screenshots

After a successful test with screenshots:

```
reports/
└── {project_id}/
    └── {session_id}/
        ├── report.html          ← Main HTML report
        ├── report.json          ← JSON data
        ├── junit.xml            ← CI/CD format
        └── screenshots/         ← Screenshot directory
            ├── 001_before_navigate.png
            ├── 002_after_navigate.png
            ├── 003_before_click_login.png
            ├── 004_after_click_login.png
            ├── 005_before_type_email.png
            └── 006_after_type_email.png
```

**Verify this structure**:
```bash
# Check report directory exists
ls -la reports/{project_id}/{session_id}/

# Check screenshots directory
ls -la reports/{project_id}/{session_id}/screenshots/

# Check screenshot file sizes
du -h reports/{project_id}/{session_id}/screenshots/*

# Should show files > 100KB each
```

---

## Expected Behavior Summary

### **When Test Runs**:
1. Browser launches (headless)
2. For each test step:
   - Capture screenshot BEFORE action → `001_before_X.png`
   - Execute action (navigate, click, type, etc.)
   - Capture screenshot AFTER action → `002_after_X.png`
3. After all test steps:
   - Run compliance scans (accessibility, security, performance)
   - These scans do NOT capture screenshots
4. Generate report:
   - Copy all screenshots to report directory
   - Build HTML with screenshot references
   - Create expandable step cards
   - Add screenshot gallery

### **When Report Viewed**:
1. Report loads in browser
2. Test results section shows steps
3. Steps with screenshots have ► arrows
4. Clicking arrow expands to show before/after images
5. Clicking images opens modal zoom
6. Bottom of report has gallery of all screenshots

---

## Quick Test

To quickly verify screenshot features work:

```bash
# 1. Start AlphaTest
python main.py

# 2. Create a test project with URL: https://example.com

# 3. Run this simple test command:
"Navigate to the homepage and scroll down"

# 4. Wait for test to complete (should take ~10 seconds)

# 5. Check console output for:
[DEBUG] Total screenshots in data: 2
[DEBUG] Total screenshots copied: 2

# 6. Open the report and verify:
- Step 1 has a ► arrow
- Clicking arrow shows 2 screenshots
- Screenshots load (before and after scroll)
- Clicking screenshot opens modal
- Gallery shows 2 thumbnails at bottom
```

If ALL of these work, the screenshot features are functioning correctly!

---

## Still Having Issues?

If you've verified all the above and screenshots still don't work:

1. **Check browser DevTools Console (F12)**
   - Look for JavaScript errors
   - Check Network tab for failed image loads
   - Verify screenshot files load (200 status)

2. **Verify file permissions**
   ```bash
   chmod -R 755 reports/
   ```

3. **Check Cloud Run logs** (if deployed)
   ```bash
   gcloud run services logs read alphatest --region us-central1 --limit 100
   ```

4. **Enable verbose logging**
   - All debug output is now in console
   - Check for WARNING messages
   - Verify screenshot paths

5. **Test locally first**
   - Run `python main.py` locally
   - Verify features work locally
   - Then deploy to Cloud Run

---

**Last Updated**: December 25, 2025
**Next Review**: After first deployment test
