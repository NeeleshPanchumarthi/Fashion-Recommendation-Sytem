import json

from app.domain.product import select_display_images


def _img(variant):
    return {"variant": variant, "thumb": f"thumb-{variant}", "large": f"large-{variant}", "hi_res": f"hires-{variant}"}


def _raw(*variants):
    return json.dumps([_img(v) for v in variants])


def test_only_main_returns_main():
    assert select_display_images(_raw("MAIN")) == ["large-MAIN"]


def test_pt01_returns_main_and_pt01_only():
    assert select_display_images(_raw("MAIN", "PT01", "PT02", "PT03")) == ["large-MAIN", "large-PT01"]


def test_angle_shots_are_added_after_pt01():
    raw = _raw("MAIN", "PT01", "PT02", "BOTT", "FRNT", "TOPP", "BACK")
    assert select_display_images(raw) == [
        "large-MAIN", "large-PT01", "large-FRNT", "large-BACK", "large-TOPP", "large-BOTT",
    ]


def test_spelled_out_angle_variants():
    assert select_display_images(_raw("MAIN", "front", "Left")) == ["large-MAIN", "large-front", "large-Left"]


def test_accepts_parsed_list_and_missing_values():
    assert select_display_images([_img("MAIN")]) == ["large-MAIN"]
    assert select_display_images(None) == []
    assert select_display_images("") == []
