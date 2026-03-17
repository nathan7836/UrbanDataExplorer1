import json
from pathlib import Path

with open('dashboard/static/data/paris_arrondissements_official.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)

processed_features = []
for i, feature in enumerate(data['features']):
    props = feature.get('properties', {})
    arr_num = None
    
    if 'c_ar' in props:
        arr_num = int(props['c_ar'])
    elif 'c_arinsee' in props:
        code = str(props['c_arinsee'])
        if code.startswith('751') and len(code) == 5:
            arr_num = int(code[3:])
    elif 'arrondissement' in props:
        arr_num = props['arrondissement']
    else:
        arr_num = i + 1
    new_props = {
        'arrondissement': arr_num,
        'nom': props.get('nom', f'{arr_num}e' if arr_num > 1 else '1er'),
        **props
    }
    
    processed_features.append({
        'type': 'Feature',
        'properties': new_props,
        'geometry': feature.get('geometry', {})
    })

output = {
    'type': 'FeatureCollection',
    'features': processed_features
}

output_file = Path('dashboard/static/data/paris_arrondissements_processed.geojson')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n[OK] Fichier traite sauvegarde: {output_file}")
print(f"     {len(processed_features)} arrondissements")

