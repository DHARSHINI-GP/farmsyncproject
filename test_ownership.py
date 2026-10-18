import sys, os
sys.path.insert(0, '.')
from farmsync.orchestrator import FarmSyncOrchestrator

orch = FarmSyncOrchestrator()

tests = [
    ('176',
     'data/FAI_Product_Challange/TASK_2/Land_documents/Survey176/Survey_176_Patta.pdf',
     'output/images/Survey_176_Peroorani_FieldPhoto.jpg'),
    ('384',
     'data/FAI_Product_Challange/TASK_2/Land_documents/Survey384/Survey_384_Patta.pdf',
     'data/FAI_Product_Challange/TASK_4/Images/images/642632_218_58__d8beea21cbeeb9fa-27006-13984678781444-2049_627801_2024_11_12_13_31_14.jpg'),
]

for survey, pdf, img_file in tests:
    img_fname = 'field_photo_survey_' + survey + '.jpg'
    orch.vision.image_registry[img_fname] = {
        'filename': img_fname,
        'filepath': os.path.abspath(img_file),
        'survey_no': survey,
        'latitude': 8.788, 'longitude': 78.022,
        'width': 640, 'height': 480,
        'location_source': 'user supplied; image authenticity not independently verified'
    }

    # Debug: check doc extraction directly
    doc_result = orch.docs.extract_document_claims(
        doc_path=os.path.abspath(pdf), survey_no=survey)
    xcheck = orch.docs.cross_check_registry(survey, doc_result)
    reg_village = orch.docs.revenue_registry.get(str(survey), {}).get('village', 'N/A')
    print('--- Survey', survey, '(pre-orchestrator debug) ---')
    print('  PDF extracted owner:', doc_result.get('extracted_owner'))
    print('  PDF found:', doc_result.get('found'))
    print('  owner_match:', xcheck.get('owner_match'))
    print('  reg_village:', reg_village)
    print('  doc_village:', doc_result.get('document_village'))

    result = orch.execute_request(
        query='Verify Survey ' + survey + ' ownership and crop',
        survey_no=survey,
        document_path=os.path.abspath(pdf),
        image_filename=img_fname
    )
    vobj = result['verified_result_object']
    attrs = vobj['extracted_attributes']
    trust = vobj['trust_metrics']
    print('  [Orchestrator] Status           :', trust['verification_status'])
    print('  [Orchestrator] FTS              :', trust['task_trust_score_fts'])
    print('  [Orchestrator] ownership_verified:', attrs.get('ownership_verified'))
    print('  [Orchestrator] ownership_status :', attrs.get('ownership_status'))
    print('  [Orchestrator] photo_assoc      :', attrs.get('photo_association_verified'))
    print()
