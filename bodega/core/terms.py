"""An agreement's words: the standard terms a new profile starts with ({owner} becomes the profile's name) and the
closing note. The store gives them to new profiles; documents print them. No Qt here."""

from __future__ import annotations

from bodega.core.model import Business

DEFAULT_TERMS = """Rental period. The rental starts when the gear is picked up and ends when all of it is back with {owner}. Gear returned late is billed at its day rate for every extra day.

Care and use. The renter will use the gear with care, by people who know how to use it, for the production named above. No lending, sub-renting, or taking the gear outside the United States without written permission.

Loss and damage. From pickup until return, the renter is responsible for the gear, including loss, theft and damage, and pays for repairs or the replacement value listed above.

Insurance. Before pickup, the renter sends a certificate of insurance covering the full replacement value, naming {owner} as loss payee and additional insured.

Checking the gear. The renter checks the gear at pickup. Anything missing or not working must be reported within 24 hours, or the gear is taken as complete and working.

Cancellation. Cancelling less than 48 hours before pickup is billed one day's rent.

Payment and deposit. Rent is due at pickup. The security deposit is returned within 7 days of the gear coming back complete and undamaged, less any charges under this agreement.

Agreement. Signing below means the renter has read and accepts these terms."""
DEFAULT_NOTE = "Thanks for renting with us."


def terms_for(b: Business) -> str:
    who = b.name.strip() or "the owner"
    return (b.terms or DEFAULT_TERMS).replace("{owner}", who)
