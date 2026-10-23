import tempfile
from pathlib import Path
from core.profile_library import ProfileLibraryManager, GameRule


def test_profile_library_and_rules():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        mgr = ProfileLibraryManager(base_dir=tmp_path)
        assert mgr.list_profiles() == []
        assert mgr.get_rules() == []

        # Add a test rule
        rule = GameRule(name="Left 4 Dead 2", pattern="steam_app_550", target_slot=5, profile_name="Left 4 Dead 2.json")
        mgr.save_rules([rule])
        rules = mgr.get_rules()
        assert len(rules) == 1
        assert rules[0].pattern == "steam_app_550"
        assert rules[0].target_slot == 5

        # Test creating and saving default profile
        prof_dict = ProfileLibraryManager.create_default_profile_dict("Left 4 Dead 2")
        mgr.save_profile_to_library("Left 4 Dead 2.json", prof_dict)
        assert "Left 4 Dead 2.json" in mgr.list_profiles()
        loaded = mgr.load_profile_from_library("Left 4 Dead 2.json")
        assert loaded is not None
        assert loaded["name"] == "Left 4 Dead 2"
