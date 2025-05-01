import json

# Load the pipeline results
with open('pipeline_results.json', 'r') as f:
    data = json.load(f)

# Print a summary of the rankings for each pipeline
print("\nCandidate Rankings by Pipeline:")
for result in data:
    sequence = result['sequence']
    print(f"\n{sequence}:")
    
    # Print ranked candidates
    for i, (candidate_id, ranking) in enumerate(result['ranked_candidates']):
        score = ranking.get('ranking_score', 'N/A')
        print(f"  {i+1}. {candidate_id} (Score: {score})")

# Print an overall summary
print("\nOverall Summary:")
print("=" * 50)

# Calculate average ranking for each candidate across all pipelines
candidate_scores = {}

for result in data:
    for candidate_id, ranking in result['ranked_candidates']:
        score = ranking.get('ranking_score', 0)
        if candidate_id not in candidate_scores:
            candidate_scores[candidate_id] = []
        candidate_scores[candidate_id].append(score)

# Calculate average scores
average_scores = {
    candidate_id: sum(scores) / len(scores) 
    for candidate_id, scores in candidate_scores.items()
}

# Sort candidates by average score
sorted_candidates = sorted(
    average_scores.items(),
    key=lambda x: x[1],
    reverse=True
)

# Print the final ranking
print("\nFinal Ranking (averaged across all pipelines):")
for i, (candidate_id, avg_score) in enumerate(sorted_candidates):
    print(f"  {i+1}. {candidate_id} (Average Score: {avg_score:.2f})")

# Print some statistics
print("\nStatistics:")
for candidate_id, scores in candidate_scores.items():
    min_score = min(scores)
    max_score = max(scores)
    avg_score = sum(scores) / len(scores)
    print(f"  {candidate_id}: Min: {min_score}, Max: {max_score}, Avg: {avg_score:.2f}") 