-- Retain browser-compatible PNG previews and use vector figures in LaTeX.
function Image(image)
  if FORMAT:match("latex") then
    local source = image.src:gsub("solver%-comparison%.png$", "runtime_memory_comparison.pdf")
    source = source:gsub("%.png$", ".pdf")
    local handle = io.open(source, "rb")
    if handle then
      handle:close()
      image.src = source
    end
  end
  return image
end
