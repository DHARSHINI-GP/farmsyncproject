"""Small read-only probes through the assigned Location identity in Mumbai."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(override=True)
from farmsync.aws import create_client,safe_error

if __name__=='__main__':
    output={'region':'ap-south-1','checks':{}}
    try:
        client=create_client('location')
        if client is None: raise ValueError('Location disabled or identity unavailable')
        snapshot=json.loads(Path('.runtime/aws-build/cloud-snapshot.json').read_text())
        center=snapshot['details']['384']['parcel']['centroid']
        position=[center['longitude'],center['latitude']]
        for name,call in [
            ('geocoding',lambda:client.search_place_index_for_position(IndexName=os.getenv('AMAZON_LOCATION_INDEX','FARMSYNC_PlaceIndex'),Position=position,MaxResults=1)),
            ('routing',lambda:client.calculate_route(CalculatorName=os.getenv('AMAZON_LOCATION_ROUTER','FARMSYNC_RouteCalculator'),DeparturePosition=[77.992336,8.752486],DestinationPosition=position,TravelMode='Car',IncludeLegGeometry=True))]:
            try:
                result=call()
                okay=bool(result.get('Results')) if name=='geocoding' else bool(result.get('Legs') and result.get('Summary',{}).get('Distance') is not None)
                output['checks'][name]={'status':'PASS' if okay else 'FAIL_EMPTY_RESULT'}
            except Exception as exc:output['checks'][name]={'status':'FAIL','error_code':safe_error(exc)}
    except Exception as exc:output['checks']['configuration']={'status':'FAIL','error_code':safe_error(exc)}
    output['all_passed']=len(output['checks'])==2 and all(v['status']=='PASS' for v in output['checks'].values())
    Path('scratch/location-live-check.json').write_text(json.dumps(output,indent=2))
    print(json.dumps(output,indent=2))
    raise SystemExit(0 if output['all_passed'] else 1)
