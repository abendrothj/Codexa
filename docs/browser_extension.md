# Browser Extension Design for Codexa

## Overview

A Chrome/Firefox browser extension that allows users to save web documentation, articles, and code snippets directly to their local Codexa knowledge vault from the browser.

## Key Features

### 1. **Save Current Page**
- One-click save of the entire page content
- Automatically extract and clean HTML to markdown
- Preserve code blocks and formatting
- Save page metadata (URL, title, timestamp, tags)

### 2. **Selection Save**
- Highlight text/code on any page and save to Codexa
- Context menu integration: "Save to Codexa"
- Keyboard shortcut for quick save

### 3. **Smart Documentation Detection**
- Auto-detect common documentation sites (MDN, StackOverflow, GitHub, etc.)
- Extract structured content (code examples, API references)
- Parse and preserve syntax highlighting

### 4. **Tagging and Organization**
- Add custom tags when saving
- Auto-suggest tags based on content
- Organize by domain/topic

### 5. **Local Connection**
- Connect to local Codexa API (configurable endpoint)
- No cloud sync - all data stays local
- Offline indicator when API is unavailable

## Architecture

```
┌─────────────────────────────────────────┐
│         Browser Extension               │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Content Scripts                │  │
│  │  - Page scraping                 │  │
│  │  - Selection capture             │  │
│  │  - HTML → Markdown conversion    │  │
│  └──────────────────────────────────┘  │
│                ↓                        │
│  ┌──────────────────────────────────┐  │
│  │   Background Script              │  │
│  │  - API communication             │  │
│  │  - Storage management            │  │
│  │  - Badge/notification control    │  │
│  └──────────────────────────────────┘  │
│                ↓                        │
│  ┌──────────────────────────────────┐  │
│  │   Popup UI                       │  │
│  │  - Quick save interface          │  │
│  │  - Settings                      │  │
│  │  - Status indicator              │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
                 ↓
         HTTP POST/GET
                 ↓
┌─────────────────────────────────────────┐
│      Codexa API (localhost:8000)        │
│                                         │
│  POST /index/web                        │
│  - Index web content                    │
│                                         │
│  GET /search                            │
│  - Search saved content                 │
└─────────────────────────────────────────┘
```

## Implementation Details

### Extension Components

#### 1. **manifest.json** (v3)
```json
{
  "manifest_version": 3,
  "name": "Codexa Web Clipper",
  "version": "1.0.0",
  "description": "Save web documentation to your local Codexa knowledge vault",
  "permissions": [
    "activeTab",
    "storage",
    "contextMenus"
  ],
  "host_permissions": [
    "http://localhost:8000/*"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [{
    "matches": ["<all_urls>"],
    "js": ["content.js"]
  }],
  "action": {
    "default_popup": "popup.html",
    "default_icon": "icon.png"
  }
}
```

#### 2. **Content Script** (content.js)
- Extract page content
- Convert HTML to Markdown (using Turndown.js)
- Detect code blocks and preserve syntax
- Handle selection events
- Send content to background script

#### 3. **Background Script** (background.js)
- Handle API communication with Codexa
- Manage context menu
- Process save requests
- Handle errors and retries
- Badge notifications

#### 4. **Popup UI** (popup.html + popup.js)
- Quick save form
- Tag input
- API connection status
- Settings (API endpoint, auto-tags)
- Recently saved items

### API Extension for Codexa

Add a new endpoint to handle web content:

**POST /index/web**
```json
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "content": "# Markdown content...",
  "tags": ["web", "documentation"],
  "source": "chrome-extension",
  "timestamp": "2024-01-01T00:00:00Z",
  "metadata": {
    "domain": "example.com",
    "author": "John Doe"
  }
}
```

Response:
```json
{
  "document_id": "uuid",
  "status": "indexed",
  "message": "Web content indexed successfully"
}
```

## User Flows

### Flow 1: Save Full Page
1. User browses to documentation page
2. Clicks extension icon
3. Popup shows page title and extracted content preview
4. User adds optional tags
5. Clicks "Save to Codexa"
6. Extension calls `/index/web` endpoint
7. Success notification shown
8. Badge updates to show saved count

### Flow 2: Save Selection
1. User highlights text/code on any page
2. Right-clicks → "Save to Codexa"
3. Content script extracts selection
4. Background script sends to API
5. Notification confirms save

### Flow 3: Search from Browser
1. User types query in extension popup
2. Extension calls `/search` endpoint
3. Results displayed with links to open in Codexa desktop app
4. User can click to view full document

## Technical Considerations

### HTML to Markdown Conversion
- Use **Turndown.js** library
- Preserve code blocks with language tags
- Handle tables, lists, and formatting
- Clean up unnecessary HTML elements

### API Connection
- Configurable endpoint (default: localhost:8000)
- Health check on extension load
- Show connection status in popup
- Graceful handling of offline state
- Option to queue saves when offline

### Privacy & Security
- All communication with local API only
- No external services or analytics
- No data collection or tracking
- User controls what gets saved

### Cross-Browser Support
- Manifest V3 for Chrome
- WebExtensions API for Firefox
- Shared codebase with conditional logic

## Development Phases

### Phase 1: Core Extension (MVP)
- [x] Basic extension structure
- [ ] Content extraction
- [ ] API integration
- [ ] Simple popup UI
- [ ] Context menu "Save to Codexa"

### Phase 2: Enhanced Features
- [ ] Selection save
- [ ] Tag suggestions
- [ ] Multiple page formats
- [ ] Settings page
- [ ] Keyboard shortcuts

### Phase 3: Advanced Capabilities
- [ ] Search from extension
- [ ] Batch save (multiple tabs)
- [ ] Smart content detection
- [ ] Custom selectors for specific sites
- [ ] Reading mode integration

### Phase 4: Polish
- [ ] Better UI/UX
- [ ] Dark mode
- [ ] Onboarding flow
- [ ] Error recovery
- [ ] Performance optimization

## File Structure

```
codexa-extension/
├── manifest.json
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
├── popup/
│   ├── popup.html
│   ├── popup.css
│   └── popup.js
├── content/
│   ├── content.js
│   └── turndown.min.js
├── background/
│   └── background.js
├── options/
│   ├── options.html
│   └── options.js
└── README.md
```

## Testing Strategy

1. **Unit Tests**: Test content extraction, markdown conversion
2. **Integration Tests**: Test API communication
3. **Manual Testing**: Test on various documentation sites
4. **Performance Testing**: Measure conversion speed, memory usage

## Distribution

- Chrome Web Store
- Firefox Add-ons
- Manual installation instructions for development
- GitHub releases for versioning

## Future Enhancements

1. **Smart Sync**: Detect when content updates and offer to re-index
2. **Collections**: Group related documentation by project
3. **Share**: Export collections to share with team
4. **Mobile**: Companion mobile app for on-the-go saving
5. **AI Summaries**: Generate summaries of saved content
6. **Related Content**: Suggest related docs from your vault
