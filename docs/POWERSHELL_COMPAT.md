# PowerShell 5.1 Compatibility Rule

EarthForge's Windows helper scripts must remain safe for Windows PowerShell 5.1.

Rules:

- `.ps1` files should be ASCII-only unless they are deliberately written with a
  PowerShell-5.1-safe BOM encoding.
- Avoid typographic quotes, en dashes, em dashes, arrows, or other Unicode
  punctuation in `.ps1` source.
- Pass switch parameters to child `powershell.exe` processes only when the
  switch is actually enabled. Do not serialize `SwitchParameter` values as
  `-Switch:$value` through an argument string.
- Prefer explicit, simple syntax that works in Windows PowerShell 5.1.
- Keep human-facing Unicode documentation in Markdown rather than executable
  PowerShell source.

This rule exists because Windows PowerShell 5.1 may interpret UTF-8-without-BOM
scripts using the legacy system code page.
