# Nix completion in Helix and Zed

Both editors share defaults from `home/programs/nixd-settings.nix`. Package completion uses the stable Nixpkgs input of `~/nixos-dotfiles`; NixOS options come from the mini configuration, and Home Manager options come from the current host's profile. The checkout path is absolute, so launching the editor elsewhere does not change these defaults.

These settings only affect editor assistance. A project's `nix develop` or build still uses its own inputs and lock file.

## Projects with different inputs

Add an override in the project when its Nixpkgs differs. Replace `/absolute/path/to/project` below with the actual checkout path as seen by the language server. These examples assume the project's input is named `nixpkgs` and use the language server's current system.

For Helix, create `.helix/languages.toml`:

```toml
[language-server.nixd.config.nixd.nixpkgs]
expr = 'import (builtins.getFlake "/absolute/path/to/project").inputs.nixpkgs { system = builtins.currentSystem; }'

[language-server.nixd.config.nixd.options.nixos]
expr = '{}'

[language-server.nixd.config.nixd.options.home-manager]
expr = '{}'
```

For Zed, create `.zed/settings.json`:

```json
{
  "lsp": {
    "nixd": {
      "settings": {
        "nixd": {
          "nixpkgs": {
            "expr": "import (builtins.getFlake \"/absolute/path/to/project\").inputs.nixpkgs { system = builtins.currentSystem; }"
          },
          "options": {
            "nixos": { "expr": "{}" },
            "home-manager": { "expr": "{}" }
          }
        }
      }
    }
  }
}
```

The empty option expressions avoid importing dotfiles-specific options into a development-shell project. For a project that defines NixOS or Home Manager configurations, replace them with expressions selecting that project's option sets. Restart the language server after changing these settings.

Absolute paths may differ between machines; keep these overrides local when needed. See the [Helix language configuration](https://docs.helix-editor.com/languages.html) and [Zed language-server configuration](https://zed.dev/docs/configuring-languages) documentation.
