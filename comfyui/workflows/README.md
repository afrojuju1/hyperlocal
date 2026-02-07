# ComfyUI Workflow Templates

Place an exported ComfyUI workflow JSON here, for example:
- `comfyui/workflows/flyer_full.json`

The backend will replace placeholder tokens at runtime. Use tokens without quotes and let the code insert JSON-safe values.

This workflow expects custom nodes:
- `hyperlocal_layout` (class names: `Rectangle Overlay`, `Hyperlocal Text Overlay`)
It uses the system font if available. You can override with `{{FONT_PATH}}`.

Supported placeholders:
- `{{PROMPT}}`, `{{NEGATIVE_PROMPT}}`
- `{{WIDTH}}`, `{{HEIGHT}}`
- `{{HEADLINE}}`, `{{SUBHEAD}}`, `{{BODY}}`, `{{CTA}}`, `{{DISCLAIMER}}`
- `{{BUSINESS_BLOCK}}`, `{{AUDIENCE}}`
- `{{PALETTE}}`, `{{STYLE_KEYWORDS}}`, `{{LAYOUT_GUIDANCE}}`
- `{{BUSINESS_NAME}}`, `{{PRODUCT}}`, `{{OFFER}}`, `{{CONSTRAINTS}}`
- `{{PRIMARY_COLOR}}`, `{{ACCENT_COLOR}}`, `{{TEXT_DARK}}`, `{{TEXT_MUTED}}`, `{{TEXT_LIGHT}}`
- `{{FONT_PATH}}`
