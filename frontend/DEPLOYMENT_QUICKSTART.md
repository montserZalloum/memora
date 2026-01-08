# Production Deployment - Quick Reference

## 🎯 One-Liner Deployment

```bash
cd /home/corex/aurevia-bench/apps/memora/frontend && npm run build && echo "✅ BUILD COMPLETE. Deploy to server."
```

---

## 📋 5-Minute Setup Checklist

### ✅ Local (Already Done)
- [x] Vite config updated (`base`, `outDir`, `manifest`)
- [x] Portal controller created (`memora/www/play.py`)
- [x] Portal template created (`memora/www/play.html`)
- [x] Production build executed (`npm run build`)
- [x] Assets generated in `memora/public/frontend/`

### 📋 On Live Server

**Step 1: Build**
```bash
cd /home/corex/aurevia-bench/apps/memora/frontend
npm run build
```

**Step 2: Clear Cache**
```bash
bench clear-cache
bench build
```

**Step 3: Restart (if needed)**
```bash
sudo supervisorctl restart frappe-memora-web
# OR
bench start  # for development
```

**Step 4: Test**
```
Visit: https://x.conanacademy.com/play
Open DevTools (F12)
Check: window.csrf_token exists
Play: Complete a lesson
```

---

## 🔗 Key Files

| File | Purpose | Status |
|------|---------|--------|
| `frontend/vite.config.ts` | Build configuration | ✅ Updated |
| `memora/www/play.py` | Request handler | ✅ Created |
| `memora/www/play.html` | HTML template | ✅ Created |
| `memora/public/frontend/.vite/manifest.json` | Asset mapping | ✅ Generated |
| `memora/public/frontend/assets/main-*.js` | React app (327KB) | ✅ Built |
| `memora/public/frontend/assets/main-*.css` | Styles (5.6KB) | ✅ Built |

---

## 🚀 Access URLs

**Development:**
- Dev Server: http://localhost:5173/
- Frappe Portal: http://localhost:8000/play

**Production:**
- Live: https://x.conanacademy.com/play

---

## 🔐 Security

### CSRF Token
```js
window.csrf_token  // Available in app
// Use: headers['X-Frappe-CSRF-Token']: window.csrf_token
```

### User Session
```js
window.frappe_user  // Current user
// Check: if (frappe_user !== 'Guest')
```

---

## 📊 Performance

- **Total Size**: 106.69KB gzipped
  - JS: 104.98KB
  - CSS: 1.71KB
- **Load Time**: 2-3 seconds typical
- **Hashed Assets**: Cache busting enabled ✓

---

## ⚠️ If Something Goes Wrong

**Assets not loading (404)**
```bash
# Check manifest exists
cat memora/public/frontend/.vite/manifest.json

# Rebuild
npm run build

# Clear cache
bench clear-cache
```

**Page not found (/play)**
```bash
# Verify files exist
ls memora/www/play.py
ls memora/www/play.html

# Rebuild
bench build
```

**CSRF token not found**
```js
// In console, check:
window.csrf_token
window.frappe_user

// If missing, reload page
// If still missing, check play.html has injection
```

---

## 📝 Building for Updates

Each time you update the code:

```bash
# 1. Make changes in src/
# 2. Build
npm run build

# 3. On server
bench clear-cache

# 4. No restart needed! Just reload browser
```

**Why?** Vite generates new hashes, manifest.json updates, play.py reads new hashes, browser gets new assets.

---

## 🎓 Understanding the Flow

```
npm run build
  ↓
vite generates hashed files (main-2hrVdgkJ.js)
  ↓
manifest.json maps: index.html → assets/main-2hrVdgkJ.js
  ↓
User visits /play
  ↓
play.py reads manifest.json
  ↓
play.py extracts game_js and game_css paths
  ↓
play.html renders with injected CSS/JS
  ↓
Browser loads React app
  ↓
Game starts
```

---

## 📞 Support

Read: `PRODUCTION_DEPLOYMENT.md` for detailed guide

---

**Status**: ✅ Ready to Deploy
