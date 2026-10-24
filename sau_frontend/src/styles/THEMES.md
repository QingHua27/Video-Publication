# Studio themes

Theme metadata is registered in `src/utils/themes.mjs`. Each entry has a stable id, name, description, surface/accent preview colors, preview class, sidebarWidth and optional artwork URL. The navigation picker enumerates this registry, so new entries need no picker rewrite. IDs are persisted in `omnipost.appearance.theme.v1`; unknown IDs safely fall back to Botanical.

Initialize the document theme before Vue mounts in `main.js` to avoid a wrong-theme flash. Theme styles should be scoped with `html[data-theme=THEME_ID]`; this also covers Element Plus overlays teleported to body. Preserve status colors and semantic distinctions between submitted, published and failed.

To add a theme: register metadata; add a scoped stylesheet and import it after base styles; place project assets under public/themes/THEME_ID; verify the picker, reload, navigation collapse, responsive widths, dialogs and publishing interactions. Artwork must be decorative and pointer-events:none. Respect reduced-motion preferences; maintain readable contrast and keyboard focus.

The existing Apple theme remains the visual base. Both themes share reference geometry and equal-width account/platform grids in studio-layout.css. Botanical adds watercolor decoration and its palette. Switching themes must never mutate drafts, account selections, records or publishing jobs.
