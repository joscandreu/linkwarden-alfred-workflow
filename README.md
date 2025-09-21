# Linkwarden Alfred Workflow

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Alfred Version](https://img.shields.io/badge/Alfred-5+-blue.svg)](https://www.alfredapp.com/)
[![Linkwarden](https://img.shields.io/badge/Linkwarden-v2.0+-green.svg)](https://linkwarden.app/)

A powerful Alfred workflow for searching, browsing, and saving links to your [Linkwarden](https://linkwarden.app/) instance.

## Features

- **Universal Search (`lw`)** - Search links by content, tags, collections, and URLs
- **Collection Browser (`lwc`)** - Browse and navigate your collections
- **Smart Save (`lws`)** - Save links with automatic tagging and collection assignment
- **Enhanced Syntax** - Use `#tags` and `@collections` for intuitive filtering
- **Auto-completion** - Automatic tag and collection creation

## Installation

1. Download and double-click the `.alfredworkflow` file to import
2. Right-click the workflow in Alfred Preferences → **"Configure Workflow..."**
3. Set your configuration:
   - **Linkwarden URL**: `https://your-linkwarden-instance.com`
   - **API Token**: Get from Linkwarden Settings → Access Tokens

> **Note**: Use the base URL without `/api/v1` or trailing slash

### Cache Configuration (Optional)

The workflow uses intelligent caching to improve performance. You can customize cache behavior:

- **LW_CACHE_COLLECTIONS_TTL**: Collections cache TTL in seconds (default: 600 = 10 minutes)
- **LW_CACHE_TAGS_TTL**: Tags cache TTL in seconds (default: 600 = 10 minutes)
- **LW_CACHE_SEARCH_TTL**: Search results cache TTL in seconds (default: 120 = 2 minutes)

**Recommended Settings:**
- Fast networks: 300s (5 minutes) for collections/tags
- Slow networks: 1800s (30 minutes) for collections/tags
- Active usage: 60-120s for search results

## Usage

### Search Links (`lw`)
```bash
lw javascript tutorial              # Text search
lw #coding @work python            # Tags and collections
lw tag:work collection:dev         # Legacy syntax
```

### Browse Collections (`lwc`)
```bash
lwc                                # Show all collections
lwc work                          # Filter collections
```

### Save Links (`lws`)
```bash
lws example.com                    # Simple save
lws github.com #coding @work       # With tags and collection
lws example.com #tutorial #js @dev # Multiple tags
```

## Syntax

### Search Filters
- `#tagname` - Filter by tag
- `@collection` - Filter by collection
- `tag:name` - Legacy tag syntax
- `collection:name` - Legacy collection syntax

### Save Features
- **Auto HTTPS** - Adds `https://` automatically
- **Smart tags** - Creates missing tags
- **Smart collections** - Creates missing collections
- **Title extraction** - Gets page title automatically

## Troubleshooting

**Configuration Issues:**
- Right-click workflow → "Configure Variables..." to set URL and token
- Use base URL without `/api/v1` or trailing slash
- Get API token from Linkwarden Settings → Access Tokens

**Common Errors:**
- "Invalid API token" - Check token in Linkwarden settings
- "Connection error" - Verify URL and instance accessibility
- "Link already exists" - URL already saved in Linkwarden

**Test Configuration:**
```bash
python3 test_config.py
```

## Requirements

- Alfred 5+ with Powerpack
- Linkwarden v2.0+
- Python 3.7+
- Valid API token with read/write permissions

## Development

**Project Structure:**
- `linkwarden_api.py` - Core API client
- `linkwarden_search.py` - Search functionality
- `linkwarden_collections.py` - Collection browser
- `linkwarden_save.py` - Save interface
- `linkwarden_save_action.py` - Save processor

**Key Implementation:**
- Two-step save process (workaround for API collection bug)
- Enhanced `#tag @collection` syntax parsing
- Automatic tag/collection creation
- Alfred native notifications

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test thoroughly
4. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.