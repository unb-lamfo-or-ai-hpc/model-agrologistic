# Legacy localization resources

`en.json` and `pt.json` retain interface translation mappings used by the legacy
`logic/i18n.py` helper. Their keys are runtime identifiers and may be Portuguese.
They are data, not code comments or new research prose.

Do not translate or delete those keys during the English documentation review:
that would change lookup behavior. New scientific documentation, code comments,
captions and manuscript text are English. A separate interface migration would
need compatibility tests and is outside this CLI research demonstrator.
