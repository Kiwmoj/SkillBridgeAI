from apps.backend.services.skills.matching import match_descriptors, match_tools

NAMES = {name.casefold(): name for name in (
    "Active Listening", "Speaking", "Writing", "Oral Expression", "Critical Thinking", "Programming",
    "Computers and Electronics", "Cooperation", "Coordination", "Communications and Media", "Mathematics")}


def keys(*displayed):
    return {name.casefold() for name in displayed}


def test_exact_and_wrapped_names_match():
    assert match_descriptors("critical thinking", NAMES) == keys("Critical Thinking")
    assert match_descriptors("I have good critical thinking skills", NAMES) == keys("Critical Thinking")
    assert match_descriptors("communications", NAMES) == keys("Communications and Media")


def test_everyday_wording_maps_to_official_descriptors():
    assert {"speaking", "writing", "active listening"} <= match_descriptors("communication", NAMES)
    assert {"programming", "computers and electronics"} <= match_descriptors("Python", NAMES)
    assert match_descriptors("teamwork", NAMES) >= keys("Cooperation", "Coordination")


def test_unrelated_text_and_substrings_do_not_match():
    assert match_descriptors("i like pizza", NAMES) == set()
    assert match_descriptors("", NAMES) == set()
    assert match_descriptors("javascript frameworks", {"programming": "Programming"}) == {"programming"}
    assert match_descriptors("rewriting", NAMES) == set()


def test_tools_match_whole_words_only():
    assert match_tools("python", ["Python", "Microsoft Excel"]) == ["Python"]
    assert match_tools("excel", ["Microsoft Excel"]) == ["Microsoft Excel"]
    assert match_tools("go", ["Google Docs"]) == []
