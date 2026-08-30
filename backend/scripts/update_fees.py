"""
Populate each PPR's fee figure from the CMVM register.

taxa_gestao was previously left NULL: the NAV series we seed are already net
of fees, and no machine-readable fee source had been found, so storing a
guessed number would have misstated a real product's costs.

CMVM publishes the Taxa de Encargos Correntes (TEC) -- the ongoing charges
figure -- for each registered fund, which fills that gap from the regulator's
own record.

Note this is the TEC, not a management fee in isolation: it bundles
management, depositary, audit and supervision costs. It is stored for display
and is never applied to returns, since the NAV already reflects it.

Usage:
    python scripts/update_fees.py [--dry-run]
"""
import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal  # noqa: E402
from models.ppr import PPR  # noqa: E402
from services.casa_history import CASA_FUNDS  # noqa: E402
from services.cmvm_reference import (  # noqa: E402
    CMVMDataError,
    fetch_ppr_register,
    match_fund,
    tec_by_fund,
)
from services.investing_history import INVESTING_FUNDS  # noqa: E402


def _verified_identities() -> dict:
    """
    Map our fund name -> CMVM name, for funds the regulator lists under a
    different name.

    Some managers market a fund under a name the register does not use --
    Casa's "Casa Global Value PPR Founders" is registered as "Save & Grow
    PPR/OICVM". Name matching cannot bridge that and correctly refuses to
    guess, so the fetchers record the identity they established by matching
    returns, and it is reused here.
    """
    return {
        fund["nome"]: fund["cmvm_name"]
        for fund in list(CASA_FUNDS) + list(INVESTING_FUNDS)
        if fund.get("cmvm_name")
    }


def update_fees(dry_run: bool = False) -> int:
    """
    Set taxa_gestao from the CMVM TEC. Returns the number of funds updated.

    A fund with no unambiguous CMVM match is left untouched rather than
    guessed at.
    """
    print("Fetching the CMVM register...")
    register = fetch_ppr_register()
    tec = tec_by_fund(register)
    print(f"  {len(register)} funds, {len(tec)} with a published TEC")

    identities = _verified_identities()

    db = SessionLocal()
    updated = unmatched = unchanged = 0

    try:
        for ppr in db.query(PPR).order_by(PPR.nome).all():
            # Prefer an identity already confirmed by return matching; fall
            # back to matching on the name.
            override = identities.get(ppr.nome)
            match = match_fund(override or ppr.nome, tec)
            if match is None:
                print(f"  [SKIP] {ppr.nome}: no unambiguous CMVM match")
                unmatched += 1
                continue

            cmvm_name, value = match
            new_value = Decimal(str(value))
            if ppr.taxa_gestao is not None and Decimal(ppr.taxa_gestao) == new_value:
                unchanged += 1
                continue

            print(
                f"  [SET]  {ppr.nome}: {ppr.taxa_gestao} -> {new_value}%  "
                f"({cmvm_name.split(' - ')[0][:44]})"
            )
            if not dry_run:
                ppr.taxa_gestao = new_value
            updated += 1

        if dry_run:
            db.rollback()
            print(f"\n[DRY RUN] {updated} would be updated, "
                  f"{unchanged} unchanged, {unmatched} unmatched. Nothing written.")
        else:
            db.commit()
            print(f"\n[SUCCESS] {updated} updated, "
                  f"{unchanged} unchanged, {unmatched} unmatched.")
        return updated

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set PPR fees from CMVM")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        update_fees(dry_run=args.dry_run)
    except CMVMDataError as exc:
        print(f"\n[FAILED] Could not read the CMVM register: {exc}", file=sys.stderr)
        sys.exit(1)
