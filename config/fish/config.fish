set fish_greeting

# Nix user profile
if test -d $HOME/.nix-profile/bin
    fish_add_path --global $HOME/.nix-profile/bin
end

# System Nix profile
if test -d /nix/var/nix/profiles/default/bin
    fish_add_path --global /nix/var/nix/profiles/default/bin
end

# Homebrew on macOS
if test -x /opt/homebrew/bin/brew
    fish_add_path /opt/homebrew/bin /opt/homebrew/sbin
else if test -x /usr/local/bin/brew
    fish_add_path /usr/local/bin /usr/local/sbin
end

if status is-interactive
    # Commands to run in interactive sessions can go here
    set -U EDITOR hx
    set -gx COLORTERM truecolor
    starship init fish | source
    zoxide init fish | source
end
