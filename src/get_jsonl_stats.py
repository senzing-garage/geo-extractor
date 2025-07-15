import os
import sys
import json
import csv
import glob

from json2attribute import json2attribute
json_parser = json2attribute('sz_default_config.json')


if len(sys.argv) != 2:
    print('\nsyntax:\n\tpython3 get_jsonl_stats <directory>')
    sys.exit(1)


record_types = []
features = []
stat_pack = {}

for file_name in glob.glob(f"{sys.argv[1]}/*.jsonl"):
    stat_pack[file_name] = {
        'record_types': {},
        'features': {}
    }
    with open(file_name,'r') as f:
        line_cnt = 0
        for line in f:
            attr_list = json_parser.parse(line)
            for attr_data in attr_list:
                if not attr_data.get('FTYPE_CODE'):
                    continue
                if attr_data['FTYPE_CODE'] == 'RECORD_TYPE':
                    value_type = 'record_types'
                    value = attr_data['ATTR_VALUE']
                    if value not in record_types:
                        record_types.append(value)
                else:
                    value_type = 'features'
                    value = attr_data['FTYPE_CODE']
                    if value not in features:
                        features.append(value)

                if value not in stat_pack[file_name][value_type]:
                    stat_pack[file_name][value_type][value] = 1
                else:
                    stat_pack[file_name][value_type][value] += 1
            line_cnt += 1
            if line_cnt % 100000 == 0:
                print(f"{line_cnt} rows processed for {file_name}")

    print(f"{line_cnt} rows processed for {file_name}, complete!")


    record_types = sorted(record_types)
    features = sorted(features, key=lambda x: json_parser.feature_lookup[x]['FTYPE_ID'])
    header = ['source', 'geo', 'records']
    header.extend(record_types)
    header.extend(features)

    with open(f"{sys.argv[1]}/file_stats.csv", 'w') as f:
        dw = csv.DictWriter(f, fieldnames=header)
        dw.writeheader()

        rows = []
        for file_name in stat_pack:
            row = {}
            row['source'], row['geo'] = os.path.basename(file_name).replace('.jsonl', '').split('-')
            row['records'] = 0
            for record_type in record_types:
                record_count = stat_pack[file_name]['record_types'].get(record_type,0)
                row[record_type] = record_count
                row['records'] += record_count
            for feature in features:
                record_count = stat_pack[file_name]['features'].get(feature,0)
                row[feature] = record_count

            dw.writerow(row)

sys.exit(0)

