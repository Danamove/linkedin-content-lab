"""Offline parser tests against saved fixtures. Run: python tests/smoke_test.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import parse  # noqa: E402

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _read(name):
    with open(os.path.join(FX, name), encoding="utf-8") as fh:
        return fh.read()


def test_parse_post_counts_and_hook():
    cases = [
        ("phil_post.txt", 139, 65, "I've seen a few posts"),
        ("joveo_post.txt", 57, 23, "Recruitment isn"),
    ]
    for fname, exp_r, exp_c, hook_prefix in cases:
        p = parse.parse_post(_read(fname))
        assert p["reactions"] == exp_r, f"{fname}: reactions {p['reactions']} != {exp_r}"
        assert p["comments"] == exp_c, f"{fname}: comments {p['comments']} != {exp_c}"
        assert p["engagement"] == exp_r + exp_c
        assert p["hook"].startswith(hook_prefix), f"{fname}: hook = {p['hook']!r}"


def test_hook_ignores_consent_boilerplate():
    # consent line is LONGER than the real (short) body — must not become the hook
    md = (
        "Skip to main content\n"
        "My real but shortish post about hiring trends this quarter.\n"
        "By clicking Continue to join or sign in, you agree to LinkedIn's "
        "User Agreement, Privacy Policy, and Cookie Policy.\n"
        "[42](x?trk=foo_social-actions-reactions) "
        "[3 Comments](x?trk=foo_social-actions-comments)\n"
    )
    p = parse.parse_post(md)
    assert "agree to" not in p["hook"].lower(), p["hook"]
    assert p["hook"].startswith("My real but shortish post"), p["hook"]
    assert p["reactions"] == 42 and p["comments"] == 3


def test_hook_ignores_page_title_fence():
    # the leading ```fenced``` page-title must not become the hook on a short post
    md = (
        "```\n   this hits hard: | Charly Wargnier | 58 comments   \n```\n"
        "this hits hard: | Charly Wargnier | 58 comments\n"   # plain repeated heading
        "Skip to main content\n"
        "The real post body is a proper sentence with enough length to qualify here.\n"
        "[1266](x?trk=foo_social-actions-reactions) "
        "[58 Comments](x?trk=foo_social-actions-comments)\n"
    )
    p = parse.parse_post(md)
    assert "| Charly Wargnier |" not in p["hook"], p["hook"]
    assert p["hook"].startswith("The real post body"), p["hook"]
    assert p["reactions"] == 1266


def test_hook_ignores_orphaned_link_fragment():
    md = (
        "](https://www.linkedin.com/login?session_redirect=https%3A%2F%2Fwww.example.com%2Flong)\n"
        "The genuine post text that should be selected as the body of this post.\n"
        "[40](x?trk=foo_social-actions-reactions) "
        "[5 Comments](x?trk=foo_social-actions-comments)\n"
    )
    p = parse.parse_post(md)
    assert not p["hook"].startswith("]") and "http" not in p["hook"], p["hook"]
    assert p["hook"].startswith("The genuine post text"), p["hook"]


def test_hook_ignores_image_link_artifact():
    # empty-text image link is longer than the real body — must not become the hook
    md = (
        "[](https://media.licdn.com/some/very/long/actor-image/url/that/is/over/forty/chars)\n"
        "A short but real take on AI sourcing tools and where they fall short.\n"
        "[88](x?trk=foo_social-actions-reactions) "
        "[9 Comments](x?trk=foo_social-actions-comments)\n"
    )
    p = parse.parse_post(md)
    assert "http" not in p["hook"] and not p["hook"].startswith("["), p["hook"]
    assert p["hook"].startswith("A short but real take"), p["hook"]


def test_extract_own_posts_filters_liked():
    md = _read("glencathey_activity.txt")
    own = parse.extract_own_posts(md, "glencathey")
    ids = sorted(p["activity_id"] for p in own)
    assert ids == ["7470848493218246656", "7471180623559331843"], ids
    # must exclude liked (larsschmidt, masterburnett, alliekmiller) and other handle (hunglee)
    for bad in ("larsschmidt", "hunglee"):
        bad_own = parse.extract_own_posts(md, bad)
        if bad == "hunglee":
            assert len(bad_own) == 1  # the uk.linkedin.com hunglee post is correctly his
        else:
            assert len(bad_own) == 1  # larsschmidt has exactly one post in fixture


def test_activity_id_to_date():
    dt = parse.activity_id_to_dt("7437477906945077249")
    assert dt.year == 2026 and dt.month == 3, dt.isoformat()  # Phil's post: "3mo" before June


def test_extract_articles_filters_by_name():
    md = _read("glencathey_articles.txt")
    arts = parse.extract_articles(md, "Glen Cathey")
    keys = sorted(a["key"] for a in arts)
    assert len(arts) == 2, [a["url"] for a in arts]            # jane-doe excluded
    assert all("glen-cathey" in k for k in keys)
    by_key = {a["key"].split("-")[-1]: a for a in arts}
    assert by_key["xotoe"]["date"] == "2026-06-04T00:00:00+00:00"
    assert by_key["5l8le"]["date"] == "2026-06-02T00:00:00+00:00"


def test_parse_published_date():
    assert parse.parse_published_date("foo\nPublished Jun 9, 2026\nbar") \
        .isoformat() == "2026-06-09T00:00:00+00:00"
    assert parse.parse_published_date("no date here") is None


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"PASS — {len(fns)} tests")
