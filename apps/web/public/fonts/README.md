Self-hosted font files

These woff2 files were downloaded from Google Fonts (fonts.gstatic.com)
on 2026-06-01 and committed locally so that the build does not require
network access at compile time. The Latin subset only is shipped.

Source: https://fonts.google.com/specimen/Chakra+Petch
        https://fonts.google.com/specimen/JetBrains+Mono

Both families are released under the SIL Open Font License 1.1.

Layout.tsx loads them via next/font/local and exposes them as
--font-chakra and --font-jetbrains, which globals.css aliases to the
design-system names --font-display and --font-mono.

File map:

  ChakraPetch-300.woff2   weight 300
  ChakraPetch-400.woff2   weight 400
  ChakraPetch-500.woff2   weight 500
  ChakraPetch-600.woff2   weight 600
  ChakraPetch-700.woff2   weight 700
  JetBrainsMono-400.woff2 weight 400 to 700 (variable, single file)

To refresh these files (e.g. after a font version bump), re-run the
download block documented in the prior agent session and commit the
updated binaries.
