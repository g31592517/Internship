from datetime import date

from opportunity.dates import find_deadline, parse_date
from opportunity.locations import find_counties, match_location, resolve_user_location
from opportunity.normalize import extract_email, extract_requirements, normalize
from opportunity.search import CourseQuery, apply_filters, dedupe, is_internship_like, rank
from scrapers.wordpress import org_from_tags, split_title_org

TODAY = date(2026, 10, 8)


def raw(**kw):
    base = {"title": "Software Developer Intern", "company": "Acme", "location": "", "link": "https://x.test/a",
            "source": "A", "scraped_at": "2026-10-08 10:00:00"}
    base.update(kw)
    return base


# ---- dates
def test_parse_date_formats():
    assert parse_date("Oct 16, 2026") == date(2026, 10, 16)
    assert parse_date("15th October 2026") == date(2026, 10, 15)
    assert parse_date("15/10/2026") == date(2026, 10, 15)
    assert parse_date("2026-10-15") == date(2026, 10, 15)


def test_year_inferred_forward_for_deadlines_and_back_for_posted():
    assert parse_date("5 January", TODAY, future=True) == date(2027, 1, 5)
    assert parse_date("08 October", TODAY, future=False) == date(2026, 10, 8)
    assert parse_date("20 December", TODAY, future=False) == date(2025, 12, 20)


def test_find_deadline_needs_keyword():
    assert find_deadline("Apply before 30th November 2026 to be considered", TODAY) == date(2026, 11, 30)
    assert find_deadline("We started on 3 March 2020", TODAY) is None
    assert find_deadline("Location: Nairobi Deadline: 20260724 The DREEM", TODAY) == date(2026, 7, 24)


# ---- locations
def test_counties_towns_and_user_input():
    assert find_counties("Westlands, Nairobi") == ["Nairobi"]
    assert find_counties("jobs in nakuru") == ["Nakuru"]
    assert resolve_user_location("Thika") == "Kiambu"
    assert resolve_user_location("Nairobi County") == "Nairobi"
    assert resolve_user_location("Atlantis") is None


def test_match_location_rules():
    assert match_location("", "anything", [], False) == "exact"
    assert match_location("Nairobi", "Nairobi", ["Nairobi"], False) == "exact"
    assert match_location("Nairobi", "Mombasa", ["Mombasa"], False) is None
    assert match_location("Nairobi", "Kenya", [], False) == "unspecified"
    assert match_location("Lagos", "Lagos, Nigeria", [], False) == "exact"   # non-Kenyan: plain text


# ---- normalisation
def test_normalize_sparse_record_does_not_crash():
    o = normalize({"title": "Intern", "link": "https://x.test/1", "source": "S"}, TODAY)
    assert o.organization == "" and o.location == "" and o.deadline is None and o.apply_method == "link"


def test_normalize_extracts_email_deadline_requirements_and_expiry():
    desc = ("About the role\nWe need help.\nRequirements:\n- Pursuing a degree in computer science\n- Knowledge of Python\n\n"
            "How to apply: send your CV to jobs@acme.co.ke. Deadline: 1st October 2026")
    o = normalize(raw(description=desc), TODAY)
    assert o.apply_email == "jobs@acme.co.ke" and o.apply_method == "email"
    assert o.deadline == date(2026, 10, 1) and o.expired
    assert o.requirements[:2] == ["Pursuing a degree in computer science", "Knowledge of Python"]
    assert o.field == "ICT & Computing"


def test_job_board_addresses_are_not_application_inboxes():
    assert extract_email("contact services@myjobmag.co.ke or hr@acme.com") == "hr@acme.com"


def test_title_org_splitting_for_wordpress_blogs():
    assert split_title_org("Software Engineering Internship Job Hanmak Technologies") == ("Software Engineering Internship", "Hanmak Technologies")
    assert split_title_org("Intern -Engineering Job Job AfDB") == ("Intern -Engineering", "AfDB")
    assert split_title_org("Microsoft Software Engineering Intern Job") == ("Microsoft Software Engineering Intern", "")
    assert org_from_tags("Electrical Intern Ramco Group", ["ramco group jobs in kenya"]) == ("Electrical Intern", "Ramco Group")


# ---- search
def test_internship_detection_ignores_international():
    assert is_internship_like(normalize(raw(title="ICT Intern"), TODAY))
    assert is_internship_like(normalize(raw(title="Industrial Attachment - Engineering"), TODAY))
    assert not is_internship_like(normalize(raw(title="International Relations Manager"), TODAY))


def test_ranking_is_course_specific_and_unknown_courses_still_work():
    se = normalize(raw(title="Software Engineering Intern", link="https://x.test/1"), TODAY)
    civil = normalize(raw(title="Civil Engineering Intern", link="https://x.test/2"), TODAY)
    nurse = normalize(raw(title="Pharmacy Intern", link="https://x.test/3", description="Dispensing medicines"), TODAY)
    got = [o.title for o, _ in rank([se, civil, nurse], "BSc Software Engineering")]
    assert got == ["Software Engineering Intern"]
    assert [o.title for o, _ in rank([se, civil, nurse], "Pharmacy")] == ["Pharmacy Intern"]
    assert [o.title for o, _ in rank([se, civil, nurse], "Civil Engineering")] == ["Civil Engineering Intern"]


def test_course_query_strips_degree_words():
    assert CourseQuery.parse("Bachelor of Science in Computer Science").phrase == "computer science"
    assert CourseQuery.parse("BSc Information Technology").phrase == "information technology"


def test_dedupe_merges_same_ad_across_sources():
    a = normalize(raw(title="Software Developer Intern", company="Acme Ltd", link="https://a.test/1", source="A"), TODAY)
    b = normalize(raw(title="Software Developer Intern", company="Acme", link="https://b.test/9", source="B",
                      description="x" * 400, deadline="Nov 3, 2026"), TODAY)
    out = dedupe([a, b])
    assert len(out) == 1 and out[0].source == "B" and out[0].also_on[0].source == "A" and out[0].deadline == date(2026, 11, 3)


def test_filters_location_expiry_broken():
    nbi = normalize(raw(link="https://x.test/1", location="Nairobi"), TODAY)
    msa = normalize(raw(link="https://x.test/2", location="Mombasa"), TODAY)
    anywhere = normalize(raw(link="https://x.test/3", location="Kenya"), TODAY)
    old = normalize(raw(link="https://x.test/4", deadline="1 Sep 2026"), TODAY)
    broken = normalize(raw(link="https://x.test/5", link_status="broken"), TODAY)
    ranked = rank([nbi, msa, anywhere, old, broken], "Software Engineering")
    ids = lambda hits: [h.url[-1] for h in hits]
    assert sorted(ids(apply_filters(ranked))) == ["1", "2", "3"]                       # no location filter: nothing hidden by place
    hits = apply_filters(ranked, location="Nairobi")
    assert ids(hits) == ["1", "3"] and hits[1].location_match == "unspecified"          # exact first, nationwide kept
    assert ids(apply_filters(ranked, location="Nairobi", strict_location=True)) == ["1"]
    assert "4" in ids(apply_filters(ranked, include_expired=True))


def test_wordpress_enrich_drops_site_banner_and_reads_application_email():
    from types import SimpleNamespace
    from scrapers.wordpress import WordPressSource
    html = ("<article><div class='entry-content'>"
            "<div>HR Intern Job ARC Ride Choose your goal below: Browse Latest Jobs Post A Free Job Advert</div>"
            "<div><p>Reports To: HR Officer</p><p>Send CV to <a href='mailto:hr@arcride.com'>hr@arcride.com</a></p>"
            "<p>Not Getting Interviews? Fix Your CV</p></div></div></article>").encode()
    src = WordPressSource()
    src.get = lambda url, **kw: SimpleNamespace(content=html)
    raw = src.enrich({"link": "https://x.test/p", "title": "HR Intern"})
    assert "Choose your goal" not in raw["description"] and "Fix Your CV" not in raw["description"]
    assert "Reports To: HR Officer" in raw["description"] and raw["apply_email"] == "hr@arcride.com"
    assert normalize({"title": "x", "link": "u", "source": "s", "description": "Oﬃcer"}, TODAY).description == "Officer"


def test_old_ads_without_deadline_are_treated_as_expired():
    assert normalize(raw(posted="2025-01-10"), TODAY).expired
    assert not normalize(raw(posted="2026-09-20"), TODAY).expired
    assert not normalize(raw(posted="2025-01-10", deadline="2026-12-01"), TODAY).expired


def test_emails_glued_to_the_next_word_are_repaired():
    from opportunity.normalize import clean_email
    assert extract_email("Send your application to: jobs@rvibs.ac.keSubject line: Intern") == "jobs@rvibs.ac.ke"
    assert clean_email("hr@acme.comdeadline") == "hr@acme.com"
    assert clean_email("Careers@GreenCom.co.ke.") == "Careers@greencom.co.ke"
    assert clean_email("intern@company.africa") == "intern@company.africa"
    assert clean_email("not-an-email") == ""
