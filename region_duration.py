from app import REGION_CONFIG

for level, region in REGION_CONFIG.items():
    durations = [challenge["duration"] for challenge in region["challenges"]]
    total_seconds = sum(durations)
    total_minutes = total_seconds / 60
    print(f"Level {level}: {region['name']}")
    print(f"  Tasks: {len(durations)}")
    print(f"  Total duration: {total_seconds} seconds ({total_minutes:.1f} minutes)")
    for challenge in region["challenges"]:
        print(f"    - {challenge['name']}: {challenge['duration']} sec")
    print()
