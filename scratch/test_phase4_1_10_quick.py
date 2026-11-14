import sys, tempfile, os, shutil

tmp = tempfile.mkdtemp(prefix='biowriter_test_')
os.environ['BIOWRITER_DATA_DIR'] = tmp
sys.path.insert(0, os.path.abspath('upload'))

try:
    # 1. Test Repair A: dispatch_faculty_feedback
    from core.draft_store import save_student_draft, get_student_draft, dispatch_faculty_feedback
    res1 = save_student_draft('STU_001', {'title': 'My Proposal', 'abstract': 'Initial abstract'})
    assert res1.get('success'), 'Failed to save initial draft'
    v1 = res1.get('version', 1)
    
    fb = {'evaluator': 'Dr. Smith', 'score': 95, 'comments': 'Excellent proposal.'}
    disp_res = dispatch_faculty_feedback('STU_001', fb)
    assert disp_res.get('success'), f'Dispatch failed: {disp_res}'
    assert disp_res.get('version') == v1 + 1, f"Version not incremented: {disp_res.get('version')}"
    
    loaded = get_student_draft('STU_001')
    assert loaded.get('title') == 'My Proposal', 'Proposal title lost!'
    assert loaded.get('faculty_review', {}).get('score') == 95, 'Faculty review not preserved!'
    assert loaded.get('faculty_review', {}).get('dispatched_at') is not None, 'Dispatched timestamp missing!'
    assert loaded.get('version') == v1 + 1, 'Draft version mismatch!'
    print('Repair A verification: PASSED!')

    # 2. Test Repair B: CitationStatusCache.copy()
    from core.reference_service import CitationStatusCache
    cache = CitationStatusCache(max_size=10, ttl=60.0)
    cache['10.1000/1'] = {'success': True, 'title': 'Original Paper'}
    cache_copy = cache.copy()
    assert isinstance(cache_copy, CitationStatusCache), 'Copy is not CitationStatusCache!'
    cache_copy['10.1000/1']['title'] = 'Mutated Title'
    assert cache['10.1000/1']['title'] == 'Original Paper', 'Original cache was mutated by copy mutation!'
    assert cache.get('10.1000/1')['title'] == 'Original Paper', 'Original cache get() was mutated!'
    print('Repair B verification: PASSED!')

    # 3. Test Repair C: analyze_animal_model_context
    from core.paper_analyst_llm import analyze_animal_model_context
    r1 = analyze_animal_model_context('Animal models are interesting.')
    assert r1.get('status') == 'ambiguous', f'Expected ambiguous, got: {r1}'
    r2 = analyze_animal_model_context('Earlier studies evaluated cell culture, whereas we tested the formulation in mice.')
    assert r2.get('status') == 'performed', f'Expected performed, got: {r2}'
    print('Repair C verification: PASSED!')

finally:
    shutil.rmtree(tmp, ignore_errors=True)
