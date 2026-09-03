"""Split function contract and loader.

Split functions live in the `splits/` directory, one per .py file. To add a
new one, drop a file in there (any filename not starting with `_`) that
defines a function named `split`. The file's name (minus .py) becomes the
function's name in reports. See `splits/_template.py` for a skeleton.

Each split function receives ONLY (id, stated_wtp) pairs -- never true_wtp --
and must decide:
  1. whether the group makes the purchase, and
  2. how much each negotiator (by id) pays.

Signature:
    split(offers: list[tuple[int, int]]) -> tuple[bool, dict[int, float]]

`offers` is a list of (id, stated_wtp). The fixed cost of the purchase is COST.

Contract (checked by `validate_split_result` on every simulated round):
  - payments must have exactly one entry per offered id
  - payments must be non-negative
  - if purchase is True, payments must total at least COST (over-collection
    is allowed -- e.g. Clarke pivot taxes -- and is reported as budget surplus)
  - if purchase is False, payments are usually all zero, but taxes are
    allowed (Clarke charges agents who pivot the decision to "don't buy")
"""
import importlib.util
from pathlib import Path

COST = 500

_TOL = 1e-6

SPLITS_DIR = Path(__file__).parent / "splits"


def load_split_functions(directory: Path = SPLITS_DIR) -> dict:
    """Discover split functions: every non-underscore .py file in `directory`
    must define a `split(offers)` function, registered under the file's stem."""
    functions = {}
    for path in sorted(Path(directory).glob("*.py")):
        if path.name.startswith("_"):
            continue
        name = path.stem
        spec = importlib.util.spec_from_file_location(f"splits.{name}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, "split", None)
        if not callable(fn):
            raise ValueError(
                f"{path} does not define a `split(offers)` function; "
                "see splits/_template.py for the expected shape"
            )
        functions[name] = fn
    if not functions:
        raise ValueError(f"no split functions found in {directory}")
    return functions


def validate_split_result(
    offers: list[tuple[int, int]], purchase: bool, payments: dict[int, float]
) -> None:
    """Raise ValueError if a split function's output violates the contract."""
    ids = {id_ for id_, _ in offers}
    if set(payments) != ids:
        raise ValueError(f"payment ids {sorted(payments)} != offer ids {sorted(ids)}")
    for id_, p in payments.items():
        if p < -_TOL:
            raise ValueError(f"negative payment {p} for id {id_}")
    if purchase and sum(payments.values()) < COST - _TOL:
        raise ValueError(
            f"purchase made but payments total {sum(payments.values()):.4f} < cost {COST}"
        )
