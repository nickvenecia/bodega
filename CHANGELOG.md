# Changelog

## 1.3.0

- A rental's prices hold once it's booked. A quote still follows your current day rates, kit prices and profile
  pricing; once you book it (and while it's out, returned or cancelled), each line keeps the rate and name it had
  then, so changing a piece's day rate later never rewrites what you agreed with a renter.
- A rental number is never given out twice. Deleting the newest rental used to hand its number to the next one, so
  two renters could end up with agreements carrying the same number; now a number, once given, stays used.
- A quote keeps its number when you move its dates into another year.
- Settings › Profiles › Numbers & Paper has a Next Number, so a series from your old spreadsheet carries on (type 48
  and the next rental is JLF-2026-048). It never goes below a number already given.
- When you type a rental number another rental already has, it says so under the field.
- When Bodega can't save (the disk is full, say), a banner across the top says so and stays until it can, with Try
  Again; your profile card at the bottom of the sidebar says Not Saved. Bodega keeps trying, and tells you when it's
  saved. Quitting while something isn't saved asks first: Try Again, Quit Anyway or Cancel.
- An odd value in one of Bodega's files (a kit whose name is a number, say) no longer stops Bodega from opening.
- If a newer Bodega saved your files and you open them with this one, it says so, and keeps everything the newer
  one added instead of dropping it the next time it saves. A rental status it doesn't know keeps its gear held.
- AI: every answer is capped in length with every provider (only Anthropic's were before), so no answer can run
  up your bill. A job asks your AI at most 150 questions, says how many it may ask before a big one, and stops
  if your AI fails three times in a row (out of credit, say) instead of asking again for every piece. Pages from
  one store are read a second apart.
- AI Settings and the Assistant now say plainly what's sent to your AI provider: the gear you ask about, with
  what you paid for it, never renters or rentals. They also say that your provider bills each question and may
  keep what's sent, and that you can set a spending limit there.
- Send to Cobro is now Send to Saldo, Cobro's new name, and the draft lands in Saldo's own folder (drafts sent
  after the move to Saldo went where Saldo never looks). Sending a rental again updates its draft instead of
  making a second invoice; once Saldo has sent it, a new draft goes beside it. With more than one profile in
  Saldo, Bodega asks once which one each of your profiles sends as. If Saldo is open, it asks you to quit it
  first, so Saldo never gives two invoices the same number.
- Bodega keeps safety copies of your gear, kits, rentals, renters and profiles: one each day you open it (the last
  14 days), and one before each import, Tidy Up Groups, AI change or restore (the last 20).
- File › Restore from Backup… (also in Settings › Your Data) puts a Back Up zip or a safety copy back. It shows
  what's in it first, and keeps what you have now as a safety copy, so a restore can be undone the same way.
- Closing a renter, your profile, Send Feedback or Check Out with changes you haven't saved asks first (Discard
  Changes or Keep Editing), instead of dropping them. Save Changes stays off until you've changed something.
- Fixed a crash when saving your profile. Adding your profile, or saving a change to it, in Settings › Profiles
  could close Bodega, every time on a Mac.
- Fixed a crash when renaming or removing a group from its right-click menu in the sidebar.
- Opening another rental, piece of gear or kit shows it from the top, instead of as far down as you'd scrolled the
  last one.
- Scrolling over a name long enough to take two lines scrolls the panel. Before, it could scroll the name inside its
  box instead, hiding its first line.
- Scrolling past a dropdown or a date no longer moves your cursor into it, so the field you're typing in keeps it.

## 1.2.1

- Check Price is now a small circle arrow beside the link, next to the arrow that opens it, so it no longer takes a
  line of its own. Under the link you see only "Checking B&H…" and then the price it found, with Use It.
- When Check Price can't read a page (B&H turns it away, say), it tells you in a short message at the bottom of the
  window, like the app's other messages, instead of a long note under the link.

## 1.2.0

- Some stores, B&H among them, let only web browsers read their pages, so Bodega can't read their links. Now it says
  so and what to do: Check Price says to open the link and see the price there, and a photo From the Link says how
  to bring it in yourself.
- Paste a photo onto a piece of gear: in your browser, right-click the picture and choose Copy Image, then in Bodega
  choose + Photo › Paste (or press ⌘V while the gear is open). Dragging a picture out of a browser onto the gear works
  too.
- AI › Update from Links works for gear linked to B&H too: when a store won't let Bodega read its page, your AI
  finds another page about that piece (usually the maker's), Bodega checks it's really about it, and you get its price
  and a tidier name to approve. Your B&H link stays as it is. A price in another currency says so in Review.
- Messages are easier to notice. They float over your list, just above the totals, and rise in and fade away: a green
  check when something worked, an amber sign on an amber card when it didn't, and a dark card on the white page in
  the light look. Long ones stay up long enough to read, resting the pointer on one keeps it up, and they never get
  in the way of a click.

## 1.1.7

- What's new in an update is easier to read: Bodega's own type, a small label, a dot before each change and room
  between them, in a soft box only as tall as it needs. It's written in plain words (this changelog), without
  GitHub's links and names.

## 1.1.6

- A new look when there's nothing yet: the ways to start, as tiles. Empty gear offers three (Add Manually, Import
  Spreadsheet…, Google Sheets…), and a spreadsheet dragged onto the window comes in too; empty kits and rentals offer
  New Kit or New Rental the same way. Search and the filter stay hidden until there's something to search.

## 1.1.5

- A sidebar section's + fades in only while the pointer is over that section.

## 1.1.4

- The sidebar's + buttons are the Mac's: a small gray + beside each section's title, shown while the pointer is over the
  sidebar.

## 1.1.3

- Panels have one thin edge and a soft, wide shadow, like the Mac's (no more dark smudge in dark mode).
- Check for Updates… is in the profile menu (and the Bodega menu on the Mac); Settings keeps the automatic switch.
- When a new version is out, Bodega shows it as soon as it opens, every time (Later closes it).
- The profile card is one clean line: your profile's name, with your email under it only once you're signed in.

## 1.1.2

- The side panels are one even tone, like Apple's glass (no more gradient), in light and dark.
- Dark mode uses the Mac's charcoal for the main area, with the panels a step lighter on top.

## 1.1.1

- The light look is the Mac's: a white main area with soft gray side panels and white cards on them.
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
