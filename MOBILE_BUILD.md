# DiabCare AI — Android app (no Flutter, Capacitor wrapper)

This wraps the existing `frontend/` (HTML/CSS/JS) into an installable Android app.
AI stays on the Flask backend (Render). The phone just sends photos to the API.

## 1. Deploy backend first (required)

1. Push to GitHub, create Render Web Service from `render.yaml`.
2. Use plan Starter+ (torch needs RAM, Free will OOM).
3. Set `CORS_ORIGINS=https://your-app.onrender.com`
4. Copy the generated `API_TOKEN` value.

## 2. Point the app at your backend

In the app: open **Backend Settings** (sidebar) and set:
- API URL: `https://your-app.onrender.com/api`
- API Key: `<API_TOKEN from Render>`

These are saved in `localStorage` (`diabcare_api_url`, `diabcare_api_key`).
You can also pre-fill by editing `frontend/js/app.js` → `DEFAULT_REMOTE_API`.

## 3. Build the APK (Windows)

```powershell
cd diabcare-ai
npm install
npx cap add android
npx cap sync
npx cap open android
```

In Android Studio:
- Let Gradle sync finish
- `Build > Build Bundle(s)/APK(s) > Build APK(s)`
- APK at `android/app/build/outputs/apk/debug/app-debug.apk`
- Install on phone, open app, set Backend Settings once.

Permissions handled by Capacitor/WebView: Internet + file/camera via
`<input type=file accept=image/*>`. For direct camera capture add
`<input type=file accept=image/* capture=environment>` (already compatible).

## 4. PWA install (no store, alternative)

Any phone browser → open `https://your-app.onrender.com` →
Menu → Add to Home Screen / Install. Works offline for UI
(`sw.js` caches shell, never caches `/api/`).

## Notes / safety

- Still demo-mode until real `best.pt` is placed in `backend/model/`.
- Banners in UI state: screening tool only, not a medical diagnosis.
- Do not publish to Play Store as medical app without privacy policy,
  disclaimer, and clinical validation.
