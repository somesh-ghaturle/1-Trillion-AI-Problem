import os
import json
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from . import views as core_views


def _check_admin_token(request):
    admin_token = os.environ.get('ADMIN_TOKEN')
    if not admin_token:
        return True
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth.split('Bearer ')[1].strip()
        return token == admin_token
    return False


@csrf_exempt
def validate_endpoint(request):
    """POST /api/validate/ - run data quality validation on uploaded CSV or sample data"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    if not _check_admin_token(request):
        return HttpResponseForbidden('Invalid ADMIN_TOKEN')

    try:
        # If a CSV file is uploaded, use it; otherwise use sample data
        if request.FILES and 'csv' in request.FILES:
            import pandas as pd
            csv = request.FILES['csv']
            df = pd.read_csv(csv)
        else:
            # use sample data from example_usage
            from example_usage import create_sample_data
            df, _ = create_sample_data()

        from data_quality_validator import DataQualityValidator

        validator = DataQualityValidator()
        # lightweight default config
        config = request.GET.dict()
        # run validation
        results, score = validator.run_validation_suite(df, {
            'required_columns': ['customer_id', 'revenue', 'order_count', 'customer_segment'],
            'key_columns': ['customer_id'],
            'value_ranges': {'revenue': (0, 100000), 'order_count': (0, 1000)},
            'expected_types': {'customer_id': 'int', 'revenue': 'float', 'order_count': 'int'}
        })

        return JsonResponse({
            'score': score,
            'results': [r.to_dict() for r in results]
        })

    except Exception as e:
        return HttpResponseBadRequest(str(e))


@csrf_exempt
def trust_endpoint(request):
    """POST /api/trust/ - calculate trust score on uploaded CSV or sample data"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    if not _check_admin_token(request):
        return HttpResponseForbidden('Invalid ADMIN_TOKEN')

    try:
        if request.FILES and 'csv' in request.FILES:
            import pandas as pd
            csv = request.FILES['csv']
            df = pd.read_csv(csv)
        else:
            from example_usage import create_sample_data
            df, _ = create_sample_data()

        from trust_scoring import TrustScoringEngine

        engine = TrustScoringEngine()
        trust_score = engine.calculate_trust_score(df, {})

        return JsonResponse({'trust_score': trust_score.to_dict()})

    except Exception as e:
        return HttpResponseBadRequest(str(e))


def governance_endpoint(request):
    """GET /api/governance/ - return governance configuration JSON"""
    if request.method != 'GET':
        return JsonResponse({'error': 'GET required'}, status=405)

    try:
        # if export exists, read it; otherwise generate
        export_path = os.path.join(os.getcwd(), 'governance_export.json')
        if os.path.exists(export_path):
            with open(export_path, 'r') as f:
                data = json.load(f)
            return JsonResponse(data)

        # generate on the fly
        from data_governance import GovernanceFramework
        framework = GovernanceFramework()
        framework.register_standard_metrics()
        out = framework.export_governance_config
        # export_governance_config writes a file; reuse export then read
        framework.export_governance_config(export_path)
        with open(export_path, 'r') as f:
            data = json.load(f)
        return JsonResponse(data)

    except Exception as e:
        return HttpResponseBadRequest(str(e))
