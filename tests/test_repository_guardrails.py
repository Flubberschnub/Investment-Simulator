from pathlib import Path


def test_alpaca_removed_and_thinkscript_present() -> None:
    root = Path(__file__).parents[1]
    source = "\n".join(path.read_text() for path in (root / "src").rglob("*.py"))
    assert "alpaca" not in source.lower()
    script = (root / "thinkscript" / "Aegis_ORB_Strategy.ts").read_text()
    assert "AddOrder" in script
