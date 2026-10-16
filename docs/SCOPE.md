# Scope

What Bodega builds, what another system owns, and what's put off, set against what people used before it. Check it
before adding or changing a feature: a feature on the "another system" side goes there, not here.

## What people leave for it

A gear list in a spreadsheet (Excel or Google Sheets: quantity, item, cost, a day rate or a percent of the cost), a
rental agreement typed in a word processor, and a calendar kept by hand. Bodega reads the spreadsheet as it is
(Import Spreadsheet…), so nobody retypes their list.

## Bodega builds

- **Gear**: each piece with its company, series, group, quantity, serial numbers, value, day rate, link, photo,
  service log, and the gear that lives on it; retired gear kept.
- **Kits**: gear sold together, priced by a discount or a fixed rate.
- **Rentals**: quote, booked, out, returned or cancelled; lines with their own dates; fees, discount, tax, deposit;
  availability and shortages; check out and check in with a checklist; each rental's history.
- **Paper**: agreements and quotes, kit sheets, inventory lists, rate cards and labels, as PDF, PNG or print.
- **Keeping it safe**: atomic saves, safety copies and Restore, undo.
- **Help with the list**: an assistant on the person's own AI key that suggests names, groups, links and prices,
  approved one by one.

## Another system owns

- **Invoices, payments and the books**: Saldo. Bodega hands it a draft invoice (Send to Saldo) and never keeps
  payments or balances of its own.
- **Calendars**: the person's calendar app, through an .ics file.
- **Email**: the person's mail app (Email Renter opens it with the agreement's words).
- **Signatures**: the agreement is printed or sent as a PDF and signed outside Bodega.
- **Taxes and depreciation**: the accountant; Bodega gives values, not tax figures.

## Put off

- Live Google Calendar sync (needs a Google Cloud project, sign-in and Google's app review).
- Accounts and sign-in, and with them who booked, checked out and checked in a rental (the standard's D-41).
- A purchase date and depreciation for each piece.
- Signed downloads (an Apple Developer ID and a Windows certificate, when the owner wants them).
- More than one person working on the same gear at once.
