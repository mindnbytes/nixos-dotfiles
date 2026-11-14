{ ... }:

{
  programs.btop = {
    enable = true;
    settings = {
      color_theme = "flexoki-light";
      theme_background = false;
      vim_keys = true;
      shown_boxes = "mem proc net cpu";
      proc_per_core = false;
      # Home Manager owns the config; persist changes here rather than in btop.
      save_config_on_exit = false;
    };
  };
}
