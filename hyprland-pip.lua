local pip_class = "mpv"
local pip_title = "YouTube Audio PiP"
local pip_width = 300
local pip_height = 169

o.window(
  { class = "^" .. pip_class .. "$", title = "^" .. pip_title .. "$" },
  {
    float = true,
    pin = true,
    size = { pip_width, pip_height },
    keep_aspect_ratio = true,
    border_size = 0,
    opacity = "1 1",
    move = { "(monitor_w-window_w-40)", "(monitor_h*0.04)" },
  }
)

hl.on("window.open", function(window)
  if window.class ~= pip_class or window.initial_title ~= pip_title then return end
  hl.dispatch(hl.dsp.window.resize({
    window = window,
    x = pip_width,
    y = pip_height,
    relative = false,
  }))
end)
