# VHS tape for the README demo GIF (https://github.com/charmbracelet/vhs).
#
# Regenerate from the repo root:
#   uv sync
#   PATH="$PWD/.venv/bin:$PATH" vhs .github/assets/demo.tape
#
# Requires vhs, ttyd, ffmpeg, and vim.

Output .github/assets/demo.gif

Require eventum
Require vim

Set Shell bash
Set Theme "Catppuccin Mocha"
Set Width 1200
Set Height 540
Set FontSize 18
Set Padding 24
Set WindowBar Colorful
Set Framerate 24
Set TypingSpeed 50ms

# Scratch directory and a minimal vimrc: syntax highlighting on,
# auto-indentation off (lines below are typed with explicit indent),
# .jinja highlighted via the bundled django syntax.
Hide
Type@1ms "cd $(mktemp -d)"
Enter
Type@1ms "cat > .vimrc.demo << 'EOF'"
Enter
Type@1ms "syntax on"
Enter
Type@1ms "set background=dark"
Enter
Type@1ms "filetype plugin off"
Enter
Type@1ms "filetype indent off"
Enter
Type@1ms "set noautoindent nosmartindent"
Enter
Type@1ms "set shortmess+=I"
Enter
Type@1ms "autocmd BufNewFile,BufRead *.jinja setfiletype django"
Enter
Type@1ms "EOF"
Enter
Type@1ms 'export VIMINIT="source $PWD/.vimrc.demo"'
Enter
Type@1ms "clear"
Enter
Show

Sleep 600ms

# Write the generator config.
Type@40ms "vim generator.yml"
Sleep 300ms
Enter
Sleep 700ms
Type "i"
Sleep 300ms
Type@25ms "input:"
Enter
Type@25ms "  - cron:"
Enter
Type@25ms '      expression: "* * * * * *"'
Enter
Type@25ms "      count: 1"
Enter
Enter
Type@25ms "event:"
Enter
Type@25ms "  template:"
Enter
Type@25ms "    mode: all"
Enter
Type@25ms "    templates:"
Enter
Type@25ms "      - my_event:"
Enter
Type@25ms "          template: events.jinja"
Enter
Enter
Type@25ms "output:"
Enter
Type@25ms "  - stdout: {}"
Sleep 500ms
Escape
Sleep 400ms
Type@80ms ":wq"
Sleep 300ms
Enter
Sleep 700ms

# Write the event template.
Type@40ms "vim events.jinja"
Sleep 300ms
Enter
Sleep 700ms
Type "i"
Sleep 300ms
Type@18ms "{{ timestamp }} INFO  user={{ module.faker.locale.en.user_name() }} action=login ip={{ module.faker.locale.en.ipv4() }}"
Sleep 500ms
Escape
Sleep 400ms
Type@80ms ":wq"
Sleep 300ms
Enter
Sleep 700ms

# Run the generator.
Type "eventum generate --path generator.yml --id demo"
Sleep 600ms
Enter
Sleep 15s
