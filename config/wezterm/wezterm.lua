-- Pull in the wezterm API
local wezterm = require("wezterm")
local act = wezterm.action

-- This will hold the configuration.
local config = wezterm.config_builder()

-- This is where you actually apply your config choices

config.window_padding = { left = 0, right = 0, top = 0, bottom = 0 }
config.tiling_desktop_environments = {
	"X11 LG3D",
	"X11 bspwm",
	"X11 i3",
	"X11 dwm",
	"Wayland",
}
-- config.mux_enable_ssh_agent = false
-- For example, changing the color scheme:
config.color_scheme = "Tokyo Night"
-- Fonts with fallback to have symbols/glyphs
config.font = wezterm.font_with_fallback({ "JetBrains Mono", "CaskaydiaCove Nerd Font", "FiraCode Nerd Font" })
config.font_size = 11
-- remove tab bar
config.enable_tab_bar = false
-- set background color (match with starship)
config.background = {
	{
		source = {
			Color = "#1E1E2E",
		},
		opacity = 0.95,
		width = "100%",
		height = "100%",
	},
}
-- Use Powershell if on windows
if wezterm.target_triple == "x86_64-pc-windows-msvc" then
	config.default_prog = { "C:\\Program Files\\PowerShell\\7\\pwsh.exe" }
end
if wezterm.target_triple == "aarch64-apple-darwin" then
	config.font_size = 13
end
-- Key Bindings
config.leader = { key = "Space", mods = "CTRL" }
config.keys = {

	-- CTRL+Space, followed by 'w' will put us in pane
	-- mode until we cancel that mode.
	{
		key = "w",
		mods = "LEADER",
		action = act.ActivateKeyTable({
			name = "pane",
			one_shot = false,
		}),
	},
	{
		key = "9",
		mods = "CTRL",
		action = act.ShowLauncherArgs({ flags = "FUZZY|WORKSPACES" }),
	},
	{ key = "j", mods = "CTRL", action = act.SwitchWorkspaceRelative(1) },
	{ key = "k", mods = "CTRL", action = act.SwitchWorkspaceRelative(-1) },
}
config.key_tables = {
	-- Defines the keys that are active in our pane mode.
	-- Since we're likely to want to make multiple adjustments,
	-- we made the activation one_shot=false. We therefore need
	-- to define a key assignment for getting out of this mode.
	-- 'pane' here corresponds to the name='pane' in
	-- the key assignments above.
	pane = {
		{ key = "<", mods = "SHIFT", action = act.AdjustPaneSize({ "Left", 5 }) },

		{ key = ">", mods = "SHIFT", action = act.AdjustPaneSize({ "Right", 5 }) },

		{ key = "+", mods = "SHIFT", action = act.AdjustPaneSize({ "Up", 5 }) },

		{ key = "-", mods = "SHIFT", action = act.AdjustPaneSize({ "Down", 5 }) },

		{ key = "h", action = act.ActivatePaneDirection("Left") },

		{ key = "l", action = act.ActivatePaneDirection("Right") },

		{ key = "k", action = act.ActivatePaneDirection("Up") },

		{ key = "j", action = act.ActivatePaneDirection("Down") },

		{ key = "v", action = act.SplitHorizontal({}) },

		{ key = "s", action = act.SplitVertical({}) },

		{ key = "q", action = act.CloseCurrentPane({ confirm = true }) },
		-- Cancel the mode by pressing escape
		{ key = "Escape", action = "PopKeyTable" },
	},
}
-- and finally, return the configuration to wezterm
return config
