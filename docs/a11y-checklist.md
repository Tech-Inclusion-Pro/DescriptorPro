# Manual accessibility checklist (run each phase before calling it done)

Automated axe checks run in `npm test`. This manual pass is the part automation
cannot do (spec §12). macOS: VoiceOver (Cmd+F5). Windows, later phases: NVDA.

## Keyboard

- [ ] Tab from the top: first stop is the "Skip to main content" link; it works.
- [ ] Every control is reachable by Tab in a sensible order; nothing traps focus.
- [ ] Focus is always visible (3px outline) in all four palettes.
- [ ] Step tabs: Left/Right/Up/Down move and select; Home/End jump; only the
      selected tab is in the Tab order.
- [ ] Mode buttons (Recorded / Live / Standards) toggle with Enter and Space.
- [ ] Display settings: button opens the panel and focus moves to Close; Escape
      closes and returns focus; the grip moves the panel with arrow keys
      (Shift for bigger steps); Reset works.

## VoiceOver

- [ ] The app name, tagline, and "Local only" chip are announced on load.
- [ ] Each step tab announces its name, position (1 of 5), state, and selection.
- [ ] Pane headings are reachable with VO heading navigation.
- [ ] The segment findings table (Need check) is announced as a table with its
      caption; the scroll region is focusable and labeled.
- [ ] Running the test job announces status changes politely, without flooding.
- [ ] Display settings choices announce their effect ("Large text", "High
      contrast", and so on).
- [ ] The decorative icons are not announced.

## Display settings

- [ ] Each palette keeps every verdict/status readable (text + icon, never color
      alone).
- [ ] Largest text size at a narrow window (320 px wide) causes no horizontal
      page scroll; the findings table scrolls inside its own region instead.
- [ ] Widest text spacing breaks no layout.
- [ ] OpenDyslexic renders (check the fab label and a pane heading).
- [ ] Stop animation: step-tab hover transitions stop; cursor trail still works
      only if explicitly on.
- [ ] Choices persist after quitting and reopening the app.

## Zero network

- [ ] With `nettop` or Little Snitch open, run a full session (open app, run the
      test job, change settings, quit): every connection is 127.0.0.1/localhost.
