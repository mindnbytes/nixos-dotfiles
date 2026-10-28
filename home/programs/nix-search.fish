set -l ref github:NixOS/nixpkgs/nixos-unstable
set -l query_args
set -l broad 0
while test (count $argv) -gt 0
    if test "$argv[1]" = --ref
        if test (count $argv) -lt 2; or contains -- "$argv[2]" --ref --all; or test -z "$argv[2]"
            echo 'nix-search: --ref requires a value' >&2
            return 2
        end
        set ref $argv[2]
        set -e argv[1..2]
    else if test "$argv[1]" = --all
        set broad 1
        set -e argv[1]
    else
        set -a query_args $argv[1]
        set -e argv[1]
    end
end
if test (count $query_args) -eq 0
    echo 'usage: nix-search [--all] [--ref <ref>] <query...>' >&2
    return 2
end

set -l regex (string join '|' -- $query_args)
set -l json (nix search --json -- $ref $regex)
set -l nix_status $status
if test $nix_status -ne 0
    return $nix_status
end

set -l color 0
if isatty stdout; and not set -q NO_COLOR
    set color 1
end
set -l out (string join \n -- $json | jq -r --arg color $color --arg broad $broad --arg regex $regex '
    to_entries[] |
    (.key | split(".") | if length > 2 and (.[0] == "packages" or .[0] == "legacyPackages") then .[2:] | join(".") else join(".") end) as $name |
    select($broad == "1" or ($name | test($regex; "i"))) |
    (.value.version // "unknown" | tostring) as $version |
    (.value.description // "" | tostring | if length > 80 then .[0:80] + ".." else . end) as $description |
    if $color == "1" then
        "\u001b[1;32m\($name)\u001b[0m\u001b[1;34m@\($version)\u001b[0m" +
        (if $description == "" then "" else " : \u001b[33m\($description)\u001b[0m" end)
    else
        "\($name)@\($version)" +
        (if $description == "" then "" else " : \($description)" end)
    end
')
set -l jq_status $status
if test $jq_status -ne 0
    return $jq_status
end
if test (count $out) -eq 0
    echo "nix-search: no results for '$regex' in '$ref'"
else
    printf '%s\n' $out
end
