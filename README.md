# hermes-kagi

A [Kagi](https://kagi.com) web search plugin for [Hermes Agent](https://hermes-agent.nousresearch.com/).

## What it provides

- **Search**: routes the built-in `web_search` tool through Kagi's Search API.
- **Extract**: routes the built-in `web_extract` tool through Kagi's Extract API.
- **`kagi_search` tool**: additional search tool that allows date-range and "lens" filtering.

## Install

### Recommended: `hermes plugins install`

```bash
hermes plugins install hadsie/hermes-kagi --enable
```

This clones the plugin into `~/.hermes/plugins/web-kagi`, enables it, and
prompts you for your `KAGI_API_KEY`. Get a key at https://kagi.com/api/keys.

### Manual

1. Clone into your Hermes plugins directory:

   ```bash
   git clone https://github.com/hadsie/hermes-kagi.git ~/.hermes/plugins/web-kagi
   ```

2. Enable the plugin in `~/.hermes/config.yaml`:

   ```yaml
   plugins:
     enabled:
       - web-kagi
   ```

3. Add your API key to `~/.hermes/.env`:

   ```bash
   KAGI_API_KEY=your-key-here
   ```

### Select Kagi as the web backend

Set the web backend in `~/.hermes/config.yaml`:

```yaml
web:
  backend: kagi
```

Alternatively

```yaml
web:
  search_backend: kagi
  extract_backend: kagi
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `KAGI_API_KEY` | Yes | Kagi v1 API key (bearer token). |
| `KAGI_BASE_URL` | No | Override the API root (default `https://kagi.com/api`). |
| `KAGI_SAFE_SEARCH` | No | Set to `off` to disable safe search (default on). |

## Notes

- At this time he Kagi Search API requires an invite. The API requires paid credits.
- Kagi will need to be explicitly set as the web.backend provider, the default provider preference won't be overridden autoomatically

## Reference

Kagi API documentation: https://kagi.com/api/docs
