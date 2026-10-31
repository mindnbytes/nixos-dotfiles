# Rex and Tailscale on the mini

The mini runs the Rex login server and a host-level Tailscale daemon. Rex
sessions run as `alex`; the Mac app connects through private Tailscale Serve on
HTTPS port 7297. The NixOS module manages this Serve mapping. The Rex account
policy allows the configured Tailscale identity to connect as `alex`.

## First-time setup

1. Create a Tailscale account, install Tailscale on the Mac, and sign in. Enable
   MFA with the identity provider. In the Tailscale admin console enable
   MagicDNS and HTTPS certificates. HTTPS certificate names appear in public
   certificate transparency logs; Serve itself remains private to the tailnet.
2. On the mini, update this checkout and apply the configuration:

   ```sh
   cd ~/nixos-dotfiles
   sudo nixos-rebuild switch --flake .#nixos-btw
   sudo tailscale up
   tailscale status
   ```

   Follow the sign-in link and approve the mini in the admin console if needed.
   Until enrollment and HTTPS are ready, the Rex Serve unit may retry.
3. Confirm the Tailscale login in the admin console matches the principal in
   `hosts/nixos-btw/rex.nix`. This identity is not a password, but grants
   access to `alex`'s account. Review your tailnet access policy as well.
4. On the mini, check `tailscale status`, `tailscale serve status`, and
   `systemctl status rex-login-server rex-tailscale-serve`. The module owns
   the Serve mapping on port 7297; do not configure another mapping there.
5. Connect Tailscale on the Mac. In Rex for Mac, choose **Add Remote Host…**
   and enter `https://<mini-tailnet-name>:7297`, using the full MagicDNS name
   shown by Tailscale. Create a session and verify `whoami` is `alex` and
   `hostname` is `nixos-btw`. Disconnect and reconnect to test persistence.

The Mac CLI can also connect with `rex -S https://<mini-tailnet-name>:7297 ls`.
CLI host aliases and the Mac app's host list are separate.

## Operations and security

- Access to Rex means the ability to run commands as `alex`. Rex relies on
  Tailscale identity and the account policy, not a separate Rex password.
- Serve is tailnet-only. Do not use Funnel or an anonymous HTTP Rex listener.
- Sessions survive client disconnections and login-server restarts, but not a
  mini reboot or termination of the per-account server. Keep SSH for recovery.
- Check `journalctl -u rex-login-server` and `journalctl -u rex-tailscale-serve`
  for errors. `tailscale status` and `tailscale serve status` show connectivity
  and the mapping. Tailscale enrollment is persistent machine state outside Git.
- Rex is a preview binary pinned by `flake.lock`. Update it deliberately with
  `nix flake update rex`; review the change and test before relying on it.
- Existing `home.arpa` service names do not automatically work remotely. Design
  remote Immich and monitoring access separately, without exposing them publicly.
