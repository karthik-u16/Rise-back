from app import REGION_CONFIG

all_names = []
for level, region in REGION_CONFIG.items():
    print(f"Level {level} {region['name']}:")
    for challenge in region['challenges']:
        print(f"  - {challenge['name']}")
        all_names.append(challenge['name'])
    print()
print(f"Unique challenge count: {len(set(all_names))}")
print("Unique challenge names:")
for name in sorted(set(all_names)):
    print(f"  - {name}")
