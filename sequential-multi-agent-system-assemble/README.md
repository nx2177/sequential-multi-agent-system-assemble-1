# Multi-Resume Recruitment Pipeline System

This system demonstrates a multi-agent approach to recruitment by sequentially applying three categories of AI agents to evaluate multiple candidate resumes against a job description.

## How It Works

The system processes multiple resumes through a pipeline of three agent categories:

1. **Keyword Extraction (Category A)**: Extracts key skills, experience, education, and other relevant information from resumes.
2. **Candidate Filtering (Category B)**: Evaluates extracted keywords against a job description, screens out candidates failing hard requirements.
3. **Candidate Ranking (Category C)**: Ranks qualifying candidates based on their filtered profiles and provides a detailed assessment.

Each agent category has multiple implementations with different prompting styles:
- A1 vs A2: Concise vs. Detailed keyword extraction
- B1 vs B2: Analytical vs. Evaluative candidate filtering
- C1 vs C2: Numerical vs. Comprehensive candidate ranking

The system runs all combinations of agents (2×2×2=8 pipelines) and compares their results.

## Key Features

- Process multiple resumes in parallel through the same agent pipelines
- Screen out candidates failing hard requirements
- Independently evaluate qualifying candidates through the A→B→C pipeline
- Generate a ranked list of candidates for each agent combination
- Compare results across different agent pipelines

## Simulation Mode

The system includes a simulation mode that generates 5 types of candidates:
- 1 **strong candidate**: An excellent fit with high alignment to job requirements
- 3 **moderate candidates**: Each good in different ways (skills, education, or experience)
- 1 **mismatch candidate**: Fails at least one hard requirement

These candidates are processed through all agent pipelines without requiring actual API calls.

## Usage

### Installation

```bash
pip install -r requirements.txt
```

### Running with Simulation Mode

```bash
python recruitment_pipeline.py --simulate
```

### Running with Your Own Resumes

```bash
python recruitment_pipeline.py --resumes resume1.txt resume2.txt resume3.txt resume4.txt resume5.txt --job example_job_description.txt
```

### Output Format

The system generates a structured JSON output with the following format for each pipeline:

```json
{
  "sequence": "A1 → B2 → C1",
  "filtered_out": ["candidate_3"],
  "final_ranking": [
    {"id": "candidate_1", "score": 0.91},
    {"id": "candidate_5", "score": 0.84},
    {"id": "candidate_2", "score": 0.72}
  ]
}
```

## Customization

You can modify:
- Agent prompts in the `AgentFactory` class
- Hard requirements in the `CandidateFilteringAgent` class
- Simulated candidate profiles in the `SIMULATED_CANDIDATES` dictionary

## Requirements

- Python 3.8+
- langchain-community
- langchain-core
- OpenAI API key (if not using simulation)
