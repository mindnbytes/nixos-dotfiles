set fish_greeting
if status is-interactive
    # Commands to run in interactive sessions can go here
    set -U EDITOR hx
    starship init fish | source
    zoxide init fish | source
end
