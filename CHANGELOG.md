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
- Each rental keeps its history (open History on the rental): when it was made, booked, marked out, returned or
  cancelled, when its number changed, and when it went to Saldo.
- Only a quote can be deleted. A rental that's been booked is marked cancelled instead and kept, with its number,
  prices and history. Gear that's on a rental is retired instead of deleted (with what's attached to it): it can't
  be booked and is left off your inventory, rate card and labels, and you can bring it back.
- Deleting gear keeps a safety copy of everything first, as an import or Tidy Up does (File › Restore… brings it
  back).
- Booking or marking out a rental whose gear is already promised (or in repair) asks first, and says what's short,
  instead of only showing a hint. Go ahead if you're renting more in to cover it.
- Importing a sheet no longer replaces your profile's pricing unless you turn on Use the Sheet's Pricing (it starts
  off once you have a profile). The Import window now says what it filled in where the sheet was blank (a quantity
  of 1, for rent, a company from the name), lets you turn off the company guess, and asks before adding the
  sheet's links to gear you already have (only where it has none).
- SVG logos are kept as their drawing only: a logo can no longer pull a picture from your computer onto your
  agreements. Logos you added before are drawn the same safe way.
- A sheet too big to be a gear list, or one with a cell far too long, now says so in plain words instead of
  failing quietly. A web page that trickles in is given up on after 30 seconds, so Stop never waits on it.
- ⌘⌫ (Ctrl+Backspace on Windows and Linux) while typing in a field deletes a word or the line, as it should,
  instead of asking to delete the piece you have open.
- Screen readers (VoiceOver, Narrator, Orca) now say the name of every round icon button and every place in
  the sidebar, instead of only "button".
- Attaching gear to a piece now gives it the piece's department as well as its group, as it always meant to.
- Settings › Your Data says plainly that your files and backups hold your renters' details, and how to keep
  them private (FileVault or BitLocker). Backing up says so too.
- On Linux, another account on the same computer can no longer stop Bodega from opening.
- A fresh look, measured to Apple's own sizes: buttons and fields are a little more compact, rows in the gear
  list are roomier, titles are larger, and the dark look is deeper, with the panels lifted above it. Every word
  now reads clearly: hints and counts are darker in light and brighter in dark, and the words on blue buttons
  are easier to read. Group bands in the gear list are a quiet grey, so blue means something you can press.
  Money in the lists lines up digit for digit. A switch that's on is green, as on a Mac.
- Buttons, fields, dropdowns and menus follow Apple's own look more closely: fields are soft grey until you
  type in them, dropdowns show the up-down arrows a Mac uses, the next step at the foot of a panel (Rent This,
  Agreement…) is a plain button so only + stands out, menu rows are a touch more compact, and a delete in a
  menu has a red trash icon. The sidebar is slightly wider, so your profile's name fits.
- Bodega follows your computer's accessibility settings: with Reduce Motion the side panel and messages simply
  appear instead of sliding and rising; with Increase Contrast secondary words are darker and every edge is
  drawn strong; with Reduce Transparency the panels are solid.
- Keyboard: Tab now reaches the places in the sidebar (Return opens one, the arrow keys move and fold), Esc
  clears the search before it closes anything, Settings opens with the keyboard on its section, and after
  deleting a piece from the keyboard the next one is ready.
- Screen readers hear each field by its label, whether a card is folded, and every message Bodega shows.
- Bodega keeps safety copies of your gear, kits, rentals, renters and profiles: one each day you open it (the last
  14 days), and one before each import, Tidy Up Groups, AI change or restore (the last 20).
- File › Restore from Backup… (also in Settings › Your Data) puts a Back Up zip or a safety copy back. It shows
  what's in it first, and keeps what you have now as a safety copy, so a restore can be undone the same way.
- Closing a renter, your profile, Send Feedback or Check Out with changes you haven't saved asks first (Discard
  Changes or Keep Editing), instead of dropping them. Save Changes stays off until you've changed something.
- When something can't be saved, printed or downloaded, Bodega says why in plain words (there's no free space,
  Bodega isn't allowed to write to that folder, another app has the file open, no internet) and what to do, instead
  of the computer's own error text. Anything it can't explain comes with a short reference to send with feedback.
- The banner for changes that aren't saved names the real reason too.
- Amounts, percents and billed days take only numbers as you type. Before, a letter was accepted and quietly read
  as nothing.
- Clearer, shorter words across the app: tooltips are a few words each, the Assistant opens with "Ask About Your
  Gear", and sending feedback says "Feedback sent."
- A gear name too long for its column shows in full when you point at it, and screen readers read cut-off names
  and labels in full. Names in the gear picker and the import list are cut at the end, the data folder's path in
  the middle.
- Deleting a profile names it ("Delete Second Unit?") and says Edit › Undo brings it back, which it does.
- Settings no longer shows an Account page while there's nothing to sign in to.
- A search that finds nothing says "No Results" with a Clear Search button (or Clear Filters, when the filters
  hid everything), instead of an empty table.
- Search ignores accents as well as capitals: "cafe" finds "Café".
- The Assistant's button is now last in the bar, after +.
- With a rental open beside the list, Production and then Total step aside so renters' names have room.
- Dates are never cut off: a narrow date box shows "Oct 18, 2026" instead of "Sun, Oct 18, 202".
- Booked rentals show in their own blue, in the tables, the calendar and a piece's panel; the app's accent color
  is kept for things you can press. Out rentals show in amber on the calendar, as they do in the lists.
- Secondary words (retired pieces, cancelled rentals, the calendar's days and numbers) are a little darker, so they
  read clearly on every background.
- Settings and About show which build of Bodega you have.
- The profile card's menu has Keyboard Shortcuts, next to Settings. Adding and editing profiles is in
  Settings › Profiles (and the Bodega menu).
- Going to another place in the sidebar starts with an empty search and no filters, so nothing stays hidden by a
  search you typed somewhere else.
- After midnight Bodega updates on its own: late rentals, Out Now and Coming Up go by the new day, and the day's
  safety copy is made. Switching to another app saves what you were typing at once, and nonstop typing is saved
  every few seconds.
- A piece's Earned figure is marked as an estimate (≈), and pointing at it says how it's worked out.
- Late rentals say "1 late" in the sidebar, not only in red.
- Screen readers now name the pickup and return dates, a line's quantity and rate, a kit's quantities, the
  sidebar's fold arrows, the accent colors and your profile card, which the keyboard can now reach.
- Quitting while your AI is still on a job, or a photo is still coming from a link, asks first (Stop and Quit).
- If something unexpected goes wrong, Bodega says so in the window, with a short reference to send with
  feedback, instead of only writing it to its log.
- AI Review's From column says "AI suggestion" for changes no web page backs up, so you know which to check.
- If your AI provider stops offering the model you chose, AI Settings keeps it and says so, instead of quietly
  switching to another one.
- The sidebar's fold arrows and the small + buttons are a little bigger, easier to hit.
- Screen readers now hear status lines as they change: Checking…, a number another rental has, gear that's short,
  how far a check-out has got.
- A message at the bottom of the window never covers the row you're on: the list scrolls it clear.
- After you pick a renter for a new rental, the keyboard goes on to the pickup date.
- From the search box, ↓ goes on into the list and Return opens the first match. ⌥⌘F finds too.
- A CSV saved by Excel on Windows keeps its accents and dashes ("Café", "–") when it's imported.
- Importing from a Google Sheet and Back Up run in the background, so the window never freezes while they work.
- The totals under the gear list say how many pieces showing have no price ("Paid · 3 not priced"), so the totals
  aren't read as everything.
- Gear can move up and down in its group from the Edit menu (Move Up, Move Down) or a row's right-click menu.
- Edit › Undo and Redo say what they'll change back ("Undo Change to Gear", "Undo Typing").
- A rental sent to Saldo says where its invoice stands, under History: a draft not sent yet, sent, or paid. If a
  send doesn't work, its history says so too.
- Each tick in Check Out and Check In keeps the time it was made (point at a piece to see it).
- Export Gear as CSV exports what the list shows: a group, or what a search or filter left. With nothing narrowing
  it, it's all your gear, as before.
- In the gear list, → and ← open and fold a group from the keyboard, and Bodega remembers it as it does a click.
  ⌥-click a group to fold or open them all.
- In every menu, Home and End go to the first and last choice.
- More of Bodega works from the keyboard: Tab reaches the sidebar's section headings, each line of a rental and
  the gear that goes with a piece, and Return or Space opens or folds them. A switch shows a ring when the keyboard
  is on it.
- Coming Up goes by every line's dates: a rental with gear that goes out later than the rest stays in Coming Up
  until its last line's dates go by.
- Bodega no longer grows in memory as you work: every time Settings, the page window, Search Everything or an alert
  closed, it used to stay in memory until you quit (Settings alone, about a megabyte each time).
- Much faster with a big inventory: with 3,000 pieces and 2,000 rentals, opening Bodega went from about 10 seconds
  to under 2, opening a piece from about 5 seconds to a fraction of one, and deleting 300 pieces at once from
  about 3 seconds to half of one. Undo uses a small fraction of the memory it did, and keeps track twice as fast.
- A right-click on a row offers what the ⋯ in its panel does: Update with AI… on gear; Add to Calendar, Check Out,
  Check In and Send to Saldo on rentals.
- The share button above the gear list opens the page window straight away (Inventory List, Rate Card, Labels).
  Importing a spreadsheet or a Google Sheet is under the + (and in File).
- Statuses in the lists are a small colored dot and the word in the normal text color ("● Booked"), easier to
  read than colored words.
- While a filter hides gear, it shows under the title as a small capsule ("In ✕", "Sony ✕"). Click one to take
  that filter off.
- Move To… on a piece's right-click menu opens a list of your groups you can search, instead of a menu on top of
  the menu: type a few letters, press Return.
- Settings has a search box: type "logo", "tax" or "backup" and only the section that holds it stays; Return opens
  it.
- Importing a sheet with blanks lets you choose what they mean: a blank Rent? can mean for rent or not, and pieces
  with no quantity can come in as 1 or be left out. (The usual choices stay as before.)
- When a sheet has its own Equipment Total row, the Import window checks it against what was read and says whether
  it matches, or by how much it's off.
- A piece you renamed after importing it isn't brought in a second time when you import the same sheet again:
  Bodega remembers the name the sheet gave it.
- On a Mac, the menu bar has a Gear menu (Rent This, Update with AI…, Make It Its Own Piece) and a Rental menu
  (Agreement…, Check Out…, Check In…, Send to Saldo…, Add to Calendar, Mark as Cancelled…) for what's open.
- Asking the Assistant to change every piece from one company or in one group ("put all the Aputure gear in its
  own group") now reaches all of them, even in a big inventory: Bodega finds every match itself, and you review
  them all before anything changes.
- Esc in Settings' search clears what you typed first; a second Esc closes Settings.
- Checking for updates while a check is already running doesn't start a second one.
- Words made consistent across the app: "piece" and "kit" everywhere (never "item" or "package"), "1 piece" and
  "2 pieces", "a day" rather than "/day", Select All, Match System, Add Profile…, All Gear and All Companies in the
  filter, and an ellipsis only where a command asks for more before it acts (Rent This acts at once; Add Gear…
  opens a list). The AI menu says Show Assistant or Hide Assistant.
- Fewer words in the way: shorter tooltips and labels, no line of explanation under Send Feedback's title, and a
  rental's second card is called Dates & Status (not Rental again, under Rental).
- A message about a problem stays up longer than good news; a sentence that ends in a name with its own full stop
  ("Northwind Media Inc.") no longer gets a second one.
- The ways to start on an empty page show their whole names ("Import Spreadsheet…" was cut off at both ends), with
  their icons on their own. A switch's knob is white whether it's on or off, as on a Mac.
- The share button shows once there's gear to print, and File › Print Inventory List…, Print Rate Card… and Print
  Labels… are off until then. A button that's off says why when you point at it (Rent This, Check Price, the
  Assistant's jobs).
- Settings › Your Data has Import & Export: Import Spreadsheet…, Import from Google Sheets… and Export Gear as
  CSV…. These, Back Up… and Restore… close Settings first, so one window never opens on top of another.
- The keyboard's ring is thicker and clearer everywhere: around a button, a field you're typing in, a place in the
  sidebar and the accent colors, so it's easy to see where the keyboard is.
- The Assistant's sign is now a sparkle, the usual sign for AI, and its button stays lit while the Assistant is
  open.
- A piece's panel opens with its head as on a Mac: its photo beside its name (press the photo to change it), then a
  quiet line with a dot and words ("● Out · Northwind Media · back Oct 25", click it to open the rental) and its
  company and group, instead of a colored box at the top.
- The words follow Bodega's own: the inventory list and rate card say Gear where they said Item, the Import button
  counts rows ("Import 12 Rows"), and a few labels are shorter (Choose File…, From Link, Use Sheet Pricing, Gear
  Discount, Own Day Rate, a group of None). In AI Settings, what's sent and what it costs now sit under the form.
- The gear jobs (Update from Links…, Find Missing Links…, Tidy Up Names…, Organize Groups…, and Update with AI… on
  a piece) are written the same way everywhere, each with "…": each ends in Review, and nothing changes until you
  approve.
- The filter button beside the search is the same size as the other round buttons in the bar.
- The calendar works from the keyboard: Tab reaches it, the arrow keys move from rental to rental (the one you're on
  has a ring), Return opens it, and VoiceOver or Narrator says each one ("JLF-2026-001, Northwind Media, Oct 18–25,
  Booked").
- Back Up, Import from Google Sheets and getting photos from links say how far they've got (a bar, or a turning
  ring while Google hasn't said how big the sheet is) and have a Stop button. A backup you stop leaves no half-made
  file behind; photos found before you stopped are kept.
- When the computer can't do something you asked (read a file, use a photo, sign out, check for updates), the
  message stays at the bottom of the window until you click it away, instead of fading before you've read it.
- Check Out and Check In keep each tick, note and photo the moment you make it: closing the window never loses
  them, and Done (where Save and Cancel were) leaves them for later.
- Undo says what it takes back ("Undo Delete Sony FX6", "Undo Change to JLF-2026-001") and shows you the piece,
  kit or rental it brought back.
- File › Export Kits as CSV… and Export Rentals as CSV… (also in Settings › Your Data): each kit with its prices and
  gear, each rental with its renter, dates, status and money, for what the list shows.
- While you're in a group, the Gear menu has Rename Group…, Move Group Up, Move Group Down and Remove Group… (they
  were only in its right-click menu).
- Typing a name in a list jumps to it, as in the Finder, and typing in an open menu jumps to the choice it starts.
  A screen reader hears each place's count in the sidebar.
- With no internet, Get Photos from Links and Update from Links stop after a few tries and say so, instead of
  trying every piece in turn.
- Search Everything (⌘K, Ctrl+K on Windows and Linux, or Search at the top of the sidebar): type a few letters to go
  to a place, open a piece, kit or rental, or run any command in the menus. ↓ ↑ to choose, Return to go. On Windows
  and Linux it's also the way to every command that lives in the menu bar.
- Settings › AI checks your key by itself as you paste it: a ✓ and "Key works · 12 models", or what's wrong in plain
  words (a key that can't be right is said without sending it). There's no Test button. Models show by the names
  your provider gives them, the list is kept for the day, and ↻ asks again. Remove Key is a red row at the foot.
- The Assistant reads like Messages: your words in blue bubbles on the right, its answers as plain words, and
  notes from Bodega in a quiet box. Point at a message for Copy, and on yours Edit and Ask Again. The message field
  grows as you type, Return sends and Shift-Return starts a new line, and Send (Stop while it works) sits inside it.
  While it thinks, "Thinking…" shimmers and the field's edge turns in blue (still, with Reduce Motion on).
- A change you ask the Assistant for waits in a card in the conversation, saying what would change: Decline, or
  Change 3 Items (Review… to pick some of them). While it waits, the field reads Accept or Decline Above and Esc
  leaves the Assistant open; afterwards the card says what happened.
- The Assistant's header has Clear Chat (the trash can) and ⋯ with Copy Conversation and AI Settings…. Before the
  first question it offers a few to try: click one and it's in the field, ready to send.
- Delete… and Remove… in menus are red, words and icon, so they're easy to tell from the rest.
- Anything that's off (a button, a field, a switch, a menu item) is dimmed the same way everywhere, as on a Mac.
- Copying from a saved PDF now gives the right characters: a rental number like JLF-2026-001 and a phone number in
  brackets came out of agreements as odd symbols (and screen readers read them that way).
- A rental's lines, a kit's gear and what goes with a piece are now rows with thin lines between them, instead of
  boxes inside a box.
- New date fields: the date in blue with a calendar sign. Click one (or press ↓) and the month opens under it; the
  arrow keys move a day or a week, Page Up and Page Down a month, Return chooses. Or just type: 10/16, Oct 16 or
  today all work, and a date without a year is taken as the nearest one.
- A piece, kit or rental open on the right has ‹ 2 / 18 › at its foot: step to the one before or after it in the
  list, as the list shows it (your search, filters and sort). ← and → step too, unless you're typing in a field.
- Drag a column's title in the gear list to put the columns in your own order (Name stays first); right-click a
  title for Move Left and Move Right. Bodega keeps the order for next time.
- Switching Month and Timeline (and every other row of choices like it) slides the highlight across, as on a Mac.
  With Reduce Motion on, it moves at once.
- The page window says which page you're looking at ("Page 2 of 5") as you scroll a long list, and its scroll bar
  is always there, so the pages never shift sideways.
- Gear that's attached to another piece says which in its own Goes With column, instead of grey words squeezed in
  after its name, so whole names fit. The column stays away until something is attached.
- Saving a calendar file offers Open Google Calendar, which goes straight to where Google takes the file in, instead
  of a list of menus to find. When the Import window finds no gear, it opens Columns, where you pick the names.
- In the renter and profile forms, Return moves to the next field, and on the last one saves; ⌘Return (Ctrl+Enter
  on Windows and Linux) saves from anywhere. Before, Return saved half-way through.
- With more than 12 renters, groups or profiles to choose from, their dropdown opens as a list you can search:
  type a few letters, then Return.
- On a very wide screen the page stops growing at its widest and sits in the middle, instead of stretching rows
  edge to edge. The Assistant button's tip shows Ctrl+J on Windows and Linux (it said ⌘J everywhere).
- A page's title, the list under it and the calendar now start at one left edge and end at one right edge, lined
  up with the buttons in the top bar.
- A deposit of 0% in your profile now means no deposit (it used to suggest 10%), and a sheet's 0% day rate is kept
  as 0%.
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
