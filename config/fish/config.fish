set fish_greeting
if status is-interactive
    # Commands to run in interactive sessions can go here
    set -U EDITOR nvim
    starship init fish | source
    zoxide init fish | source
end

# uv
fish_add_path "/Users/alex/.local/bin"
