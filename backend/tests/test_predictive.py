from app.predictive import family_name
def test_family_name_removes_year_and_round():
 assert family_name('Nature Restoration Challenge 2026 Round 2')=='nature restoration'
def test_family_name_stable_across_years():
 assert family_name('EIC Accelerator 2025 Call 1')==family_name('EIC Accelerator 2026 Call 2')
