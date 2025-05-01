import json

# Load the pipeline results
with open('pipeline_results.json', 'r') as f:
    data = json.load(f)

# Print the results in the requested format
print("\nRecruitment Pipeline Results (Updated Format):")
print("=" * 50)

for result in data:
    sequence = result['sequence']
    filtered_out = result.get('filtered_out', [])
    final_ranking = result.get('final_ranking', [])
    
    print(f"\n{sequence}:")
    
    # Format as JSON
    formatted_result = {
        "sequence": sequence,
        "filtered_out": filtered_out,
        "final_ranking": final_ranking
    }
    
    print(json.dumps(formatted_result, indent=2))
    
# Print a summary of rankings across pipelines
print("\nCandidate Ranking Summary:")
print("=" * 50)

# Calculate average ranking position for each candidate
candidate_positions = {}

for result in data:
    # Get candidates that weren't filtered out
    filtered_out = set(result.get('filtered_out', []))
    
    # Record ranking positions
    for pos, candidate in enumerate(result.get('final_ranking', []), 1):
        candidate_id = candidate['id']
        
        if candidate_id not in candidate_positions:
            candidate_positions[candidate_id] = []
            
        candidate_positions[candidate_id].append(pos)

# Calculate average position and filter status
summary = []
for candidate_id, positions in candidate_positions.items():
    avg_position = sum(positions) / len(positions)
    filtered_count = sum(1 for result in data if candidate_id in result.get('filtered_out', []))
    
    summary.append({
        "candidate_id": candidate_id,
        "avg_position": avg_position,
        "filtered_out_count": filtered_count,
        "total_pipelines": len(data)
    })

# Sort by average position (lower is better)
summary.sort(key=lambda x: x["avg_position"])

# Print summary
for entry in summary:
    print(f"{entry['candidate_id']}:")
    print(f"  Average Rank: {entry['avg_position']:.2f}")
    if entry['filtered_out_count'] > 0:
        print(f"  Filtered out in {entry['filtered_out_count']} of {entry['total_pipelines']} pipelines")
    else:
        print("  Never filtered out")
    print() 