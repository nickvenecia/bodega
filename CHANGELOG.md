# Changelog

## Unreleased

- Menus, dropdown lists, pickers and suggestions look like the sidebar and Settings: the same rounded rows, spacing
  and soft highlight.

## 1.1.0

- Bodega is blue now: a blue accent across the app and on the paper (new profiles; your profile's paper color is
  in Settings › Profiles), with neutral greys to match.
- A new icon: "b." with a blue full stop.
- Pick your own accent color in Settings › General: blue, purple, pink, orange, yellow, green, turquoise or
  graphite. The whole app follows, in light and dark.

## 1.0.2

- The same app as 1.0.1, released again from a tidied-up history.

## 1.0.1

- Dragging a row to reorder it no longer lets go when you drift back up or a little left of the grip. It only
  hands off to the sidebar's groups once the pointer is over the sidebar.

## 1.0.0

The first Bodega, for gear and rentals.

- Gear with departments, groups, quantities, a serial number per unit, value, replacement value, day rate, link,
  notes and status (Ready, In Repair, Retired).
- Gear that belongs to other gear: attached pieces fold under their main piece and go wherever it goes.
- Import a hand-made .xlsx or .csv gear list through an Import window: fix which column is which, leave out
  departments or single pieces, choose attaching and pricing (departments, groups, quantities, prices, Rent?, the day-rate percent
  and tax from the formulas), with attachments guessed from "… for Sony FX6". Export to .csv.
- Kits priced by discount, a set day rate, or what the gear adds up to.
- Rentals from quote to returned: renters, packages, gear and fees, a discount, sales tax and a security deposit;
  3-day weeks and the Friday-to-Monday weekend; lines with their own dates; double-booking checks.
- Pages: the rental agreement (or quote) with Out / In boxes and signatures, the inventory list, the rate card and
  the kit sheet. Save PDF, print, PNG, copy as text, email the renter.
- Full screen: a sidebar of places (all gear, departments, kits, rentals, a calendar), a big sortable table, and
  the piece you picked on the right, edited in place. Agreements and sheets open in their own window.
- Gear divided by department (by group inside one), with totals; a totals bar with paid, tax, value with tax
  and the day rate, like a gear sheet. Attached gear is linked from its piece instead of listed.
- Light and dark, following the computer (View → Appearance).
- Links on a sheet's cells come in with the gear; Check Price reads a price from the link.
- Groups are how gear is organised (departments are gone from the screen); Tidy Up Groups gives plain names.
  Make, rename, reorder; Move To… for several pieces at once, or drag.
- Every piece has its own row; gear that goes with another says "with …" after its name.
- Prices read as money; with no profile yet, prices use the sheet's rate and tax.
- Cmd+A, Shift and Cmd-click to pick many pieces; Delete deletes them (and what's attached) after a warning.
- Company and Series for every piece (company guessed from the name); divide by company; your own order
  (drag by the grip); choose your columns.
- A calmer inspector: ⋯ for Duplicate and Delete, Rent This… along the bottom, parts added only when needed,
  and one Works With section for gear that goes together.
- A Liquid-Glass look: floating rounded panels on a soft gradient, capsule controls, rounded row highlights.
- The right panel slides in when you pick something and out on Esc; the toolbar's search is centred.
- Import straight from a Google Sheets link (links included, =HYPERLINK formulas too).
- Updates itself from GitHub.
- AI with your own key: Anthropic, OpenAI, Gemini, Kimi, OpenRouter, DeepSeek, Mistral, xAI, Groq or any
  OpenAI-compatible service (a local model too), models listed live. The AI Assistant (✦, ⌘J) updates prices and
  names from links, finds missing links (each one checked), tidies names and answers questions. Every change is
  reviewed first, with a copy of your gear kept.
- Settings (⌘,), a sign-in window ready for accounts, Send Feedback (kept until sending is switched on), Back Up.
- The sidebar folds: groups under All Gear, kits under Kits. The window opens filling the screen, then where you
  left it; double-click the title bar to fill the screen or shrink it, animated.
- One card style for every panel, a flat backdrop, cooler greys, a softer dark look.
- Drag rows by the grip and the others slide apart live to show where it lands.
- The AI can organize groups (making new ones) and move gear on request from the chat.
- Rentals in the sidebar: All Rentals with Out Now and Coming Up under it, then Calendar.
- The calendar is a month you can read: rentals as bars across their days, colored by where they stand, with
  ‹ Today › and a Timeline view for overlaps.
- Your profile and Settings at the bottom of the sidebar; Import & Export together in one toolbar menu.
- The gear dropdowns became one filter icon (violet while a filter is on): divide by, show (in, out, booked,
  in repair, retired, for rent), one company, what's missing (link, price, serial numbers, company), and Clear
  Filters. The search box got the room.
- Menus and dropdown lists open just below their button, with a little air, and never run off the window.
- The AI assistant has its own icon, a round smiling speech bubble, and says hi.
- Photos of each piece: choose a file, drop one on the panel, or take it from the piece's link (File › Get
  Photos from Links does them all). They show in the gear list and on the inventory list and rate card.
- What each piece has earned (and how much of its cost it has paid back), in its panel and an Earned column.
- Check Out / Check In: tick each piece (or scan its label), note its condition, add photos; then mark the rental
  Out or Returned.
- QR labels: a sticker for every piece on Avery 5160 sheets (File › Print Labels…); scanning one opens the piece.
- Send to Cobro: a rental becomes a draft invoice in Cobro, with the same total.
- Add to Calendar: pickups and returns in Apple Calendar (or Google Calendar, from the saved file).
- Maintenance: a log of services and repairs, service reminders, and a Needs Service filter.
- The + beside Inventory makes gear, a group or a kit; the one beside Rentals makes a rental. Kits have a case icon.
- Undo and Redo (⌘Z, ⇧⌘Z) for gear, kits, rentals, renters, profiles and groups; text boxes keep their own.
- Standard keys throughout (Edit menu with Cut, Copy, Paste, Select All, Duplicate, Delete, Find; Window menu;
  Quit), and Help › Keyboard Shortcuts (⌘/) lists them all.
- A new piece, kit or rental you leave empty (Esc) isn't kept.
- Delete asks in a Mac-style alert, and Return confirms.
- Settings is one window with a sidebar of sections (General, Profiles, AI, Account, Keyboard Shortcuts, Your
  Data), each edited in place. Send Feedback has its own window.
- The AI assistant slides in as the right-hand panel and stays while you work.
- One button system: text buttons are capsules, icon buttons are circles; every right-hand panel has a round ✕
  and a round ⋯.
- Security: safe web fetching (https only, public addresses only, size caps), only web links open, CSV exports
  can't carry formulas, oversized sheets refused, updates checked by source, checksum and signature, keys in the
  keychain. Many fixes, among them: deleting gear no longer changes rentals' prices, and a huge number can't stop
  Bodega from opening.
