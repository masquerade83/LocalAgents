# Hermes stack diagrams (SVG for Notion)

Notion’s Mermaid renderer is older and layout-narrow, so these diagrams are exported as **SVG** for consistent visuals in Notion pages.

## Files

| SVG | Mermaid source | Used on Notion page |
|-----|----------------|---------------------|
| `hermes-architecture-with-uris.svg` | `hermes-architecture-with-uris.mmd` | Hermes Agent — Full stack with all access URIs |
| `hermes-system-architecture.svg` | `hermes-system-architecture.mmd` | Hermes Agent — System architecture (legacy) |
| `hermes-routing-before.svg` | `hermes-routing-before.mmd` | Hermes Agent — Architecture Before |
| `hermes-routing-after.svg` | `hermes-routing-after.mmd` | Hermes Agent — Architecture After |
| `stack-modules-e2e.svg` | `stack-modules-e2e.mmd` | Stack Modules — End-to-end flow |
| `stack-modules-before-after.svg` | `stack-modules-before-after.mmd` | Stack Modules — Before vs After |
| `case-litellm-eks.svg` | `case-litellm-eks.mmd` | LLM Routers — Case 1 |
| `case-litellm-componentized.svg` | `case-litellm-componentized.mmd` | LLM Routers — Case 2 |
| `case-envoy-two-tier.svg` | `case-envoy-two-tier.mmd` | LLM Routers — Case 3 |
| `case-helicone.svg` | `case-helicone.mmd` | LLM Routers — Case 4 |
| `case-portkey.svg` | `case-portkey.mmd` | LLM Routers — Case 5 |
| `case-hermes-local.svg` | `case-hermes-local.mmd` | LLM Routers — Case 6 |

## Regenerate SVGs

```bash
cd docs/diagrams
npm install @mermaid-js/mermaid-cli --no-save
for f in *.mmd; do npx mmdc -i "$f" -o "${f%.mmd}.svg" -b transparent -w 1200; done
```

## Notion upload (MCP)

1. Regenerate SVGs (above).
2. Upload via Notion MCP `notion-create-attachment` using `source_url` (public HTTPS) or inline `content` (≤200 KiB).
3. Embed on pages:

```markdown
<callout icon="🖼️" color="blue_bg">SVG diagram — source: clawd/docs/diagrams/NAME.mmd</callout>
<image src="file-upload://UPLOAD_ID"></image>
```

Batch helpers:

```bash
python3 notion_batch_upload.py pending          # stems not yet in upload-manifest.json
python3 notion_batch_upload.py args STEM        # JSON args for MCP create-attachment
python3 notion_batch_upload.py record STEM ID file-upload://ID
```

`upload-manifest.json` records Notion `file-upload://` IDs after upload. `upload-urls.json` lists temporary public URLs used for `source_url` imports (catbox.moe).

Manual fallback: drag the `.svg` onto the Notion page.
