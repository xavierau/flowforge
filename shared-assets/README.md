# Shared Assets

Centralized location for brand assets used across FlowForge projects.

## 📁 Structure

```
shared-assets/
├── logos/
│   ├── logo.svg              # Primary logo (vector - recommended)
│   ├── logo.png              # Primary logo (raster)
│   ├── logo-dark.svg         # Dark mode variant
│   ├── logo-dark.png         # Dark mode variant (raster)
│   ├── logo-icon.svg         # Icon only (no text)
│   ├── logo-icon.png         # Icon only (raster)
│   └── favicon.png           # Favicon (32x32 or 512x512)
└── brand/
    ├── colors.json           # Brand color palette
    └── guidelines.md         # Brand guidelines
```

## 🔄 Syncing Assets

After adding/updating logos here, run:

```bash
# From project root
./sync-assets.sh
```

This copies logos to:
- `marketing/public/images/` (Astro site)
- `frontend/public/` (React app)

## 🎨 Logo Specifications

### Primary Logo
- **Format:** SVG (preferred) + PNG fallback
- **Dimensions:**
  - PNG: 800x200px (4:1 ratio)
  - SVG: Scalable
- **Background:** Transparent
- **Colors:** Use brand colors

### Favicon
- **Format:** PNG (will be converted to ICO/SVG as needed)
- **Dimensions:** 512x512px (will be downscaled)
- **Background:** Transparent or brand color

### Logo Icon (Square)
- **Format:** SVG + PNG
- **Dimensions:** 512x512px
- **Use:** App icon, favicons, social media avatars

## 📝 Usage in Code

### Marketing Site (Astro)
```astro
<!-- Auto-loaded from config -->
<!-- Configured in: src/config/config.json -->
<img src="/images/logo.png" alt="FlowForge" />
```

### Frontend App (React)
```tsx
<img src="/logo.png" alt="FlowForge" />
```

### Dark Mode Support
```tsx
// React
<img
  src={isDark ? '/logo-dark.png' : '/logo.png'}
  alt="FlowForge"
/>
```

## 🚀 First Time Setup

1. **Add your logo files to `logos/` folder**
2. **Run sync script:**
   ```bash
   ./sync-assets.sh
   ```
3. **Update configuration:**
   - Marketing: `marketing/src/config/config.json`
   - Frontend: Update imports as needed

---

**Last Updated:** 2025-11-03
