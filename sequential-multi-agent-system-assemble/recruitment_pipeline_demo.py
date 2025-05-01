import os
import json
import random
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import itertools

# Simulate API responses instead of making real calls
SIMULATE_API_CALLS = True

@dataclass
class AgentPrompt:
    """Represents a prompt configuration for an agent"""
    name: str
    style: str
    template: str

@dataclass
class AgentResult:
    """Stores the result from an agent"""
    agent_name: str
    output: Any

@dataclass
class CandidateResult:
    """Stores the results for a single candidate"""
    resume_id: str
    a_result: AgentResult
    b_result: AgentResult
    c_result: AgentResult
    final_rank: Any

@dataclass
class PipelineResult:
    """Stores the results from a full pipeline run with multiple candidates"""
    sequence: str
    candidate_results: List[CandidateResult]
    ranked_candidates: List[Tuple[str, Any]]

class RecruitmentAgent:
    """Base class for all recruitment agents"""
    
    def __init__(self, prompt: AgentPrompt):
        self.prompt = prompt
    
    def run(self, inputs: Dict[str, Any]) -> Any:
        """Run the agent with the given inputs"""
        # In a real implementation, this would call an LLM API
        # Here we'll just simulate a response
        print(f"  Simulating {self.__class__.__name__} with prompt {self.prompt.name}")
        return {"simulation": "This is a simulated response"}

class KeywordExtractionAgent(RecruitmentAgent):
    """Agent for extracting keywords from resume (Category A)"""
    
    def run(self, resume: str) -> Dict[str, List[str]]:
        """Extract keywords from resume"""
        if SIMULATE_API_CALLS:
            # Extract some basic keywords based on the resume content
            resume_lower = resume.lower()
            
            # Look for keywords in the resume
            technical_skills = []
            if "python" in resume_lower:
                technical_skills.append("Python")
            if "machine learning" in resume_lower or "ml" in resume_lower:
                technical_skills.append("Machine Learning")
            if "tensorflow" in resume_lower:
                technical_skills.append("TensorFlow")
            if "docker" in resume_lower:
                technical_skills.append("Docker")
            if "aws" in resume_lower:
                technical_skills.append("AWS")
            
            soft_skills = []
            if "lead" in resume_lower or "leadership" in resume_lower:
                soft_skills.append("Leadership")
            if "communication" in resume_lower:
                soft_skills.append("Communication")
            if "team" in resume_lower:
                soft_skills.append("Teamwork")
            
            education = []
            if "master" in resume_lower:
                education.append("Master's Degree")
            if "bachelor" in resume_lower:
                education.append("Bachelor's Degree")
            if "computer science" in resume_lower:
                education.append("Computer Science")
            
            experience = []
            if "senior" in resume_lower:
                experience.append("Senior-level experience")
            if "machine learning engineer" in resume_lower:
                experience.append("Machine Learning Engineer")
            if "software engineer" in resume_lower:
                experience.append("Software Engineer")
            
            return {
                "technical_skills": technical_skills,
                "soft_skills": soft_skills,
                "education": education,
                "experience": experience
            }
        else:
            result = super().run({"resume": resume})
            try:
                return json.loads(result)
            except:
                return {"extracted_text": result}

class CandidateFilteringAgent(RecruitmentAgent):
    """Agent for filtering candidates (Category B)"""
    
    def run(self, keywords: Dict[str, List[str]], job_description: str) -> Dict[str, Any]:
        """Filter candidate based on keywords and job description"""
        if SIMULATE_API_CALLS:
            # Simulate filtering by checking for ML and Python skills
            match_score = 0
            strengths = []
            gaps = []
            
            # Check for key requirements
            if "Machine Learning" in keywords.get("technical_skills", []):
                match_score += 40
                strengths.append("Machine Learning experience")
            else:
                gaps.append("No Machine Learning experience")
                
            if "Python" in keywords.get("technical_skills", []):
                match_score += 20
                strengths.append("Python skills")
            else:
                gaps.append("No Python skills")
                
            if "AWS" in keywords.get("technical_skills", []) or "GCP" in keywords.get("technical_skills", []):
                match_score += 15
                strengths.append("Cloud platform experience")
            else:
                gaps.append("No cloud platform experience")
                
            if "Docker" in keywords.get("technical_skills", []):
                match_score += 10
                strengths.append("Docker experience")
                
            if "Leadership" in keywords.get("soft_skills", []):
                match_score += 10
                strengths.append("Leadership skills")
            
            # Determine if candidate meets requirements
            meets_requirements = match_score >= 60
            
            return {
                "meets_requirements": meets_requirements,
                "match_score": match_score,
                "strengths": strengths,
                "gaps": gaps,
                "overall_assessment": "Suitable candidate" if meets_requirements else "Does not meet minimum requirements"
            }
        else:
            result = super().run({
                "keywords": json.dumps(keywords),
                "job_description": job_description
            })
            try:
                return json.loads(result)
            except:
                return {"filtered_result": result}

class CandidateRankingAgent(RecruitmentAgent):
    """Agent for ranking candidates (Category C)"""
    
    def run(self, filtered_profile: Dict[str, Any], job_description: str) -> Dict[str, Any]:
        """Rank candidate based on filtered profile and job description"""
        if SIMULATE_API_CALLS:
            # Rank candidate based on match score
            match_score = filtered_profile.get("match_score", 0)
            ranking_score = min(match_score / 10, 10)  # Convert to 0-10 scale
            
            return {
                "ranking_score": ranking_score,
                "justification": f"Candidate has a match score of {match_score} with {len(filtered_profile.get('strengths', []))} strengths and {len(filtered_profile.get('gaps', []))} gaps"
            }
        else:
            result = super().run({
                "filtered_profile": json.dumps(filtered_profile),
                "job_description": job_description
            })
            try:
                return json.loads(result)
            except:
                return {"ranking_result": result}
    
    def rank_candidates(self, filtered_profiles: List[Dict[str, Any]], job_description: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Rank multiple candidates based on their filtered profiles"""
        # Rank each candidate individually
        ranked_results = []
        
        for profile in filtered_profiles:
            result = self.run(profile.get("filtered_data", {}), job_description)
            rank_score = 0
            
            if isinstance(result, dict):
                rank_score = result.get("ranking_score", 0)
            
            ranked_results.append((profile.get("resume_id", "unknown"), rank_score, result))
            
        # Sort by rank score (higher is better)
        sorted_results = sorted(ranked_results, key=lambda x: x[1], reverse=True)
        
        # Return as (candidate_id, full_ranking_result)
        return [(cand_id, result) for cand_id, _, result in sorted_results]

class AgentFactory:
    """Factory for creating agents with different prompting styles"""
    
    @staticmethod
    def create_keyword_extraction_agents() -> List[KeywordExtractionAgent]:
        """Create two different keyword extraction agents"""
        prompts = [
            AgentPrompt(
                name="A1",
                style="Concise and direct",
                template="Extract the most important skills from the resume"
            ),
            AgentPrompt(
                name="A2",
                style="Detailed and conversational",
                template="Carefully analyze this resume and extract comprehensive information"
            )
        ]
        
        return [KeywordExtractionAgent(prompt) for prompt in prompts]
    
    @staticmethod
    def create_candidate_filtering_agents() -> List[CandidateFilteringAgent]:
        """Create two different candidate filtering agents"""
        prompts = [
            AgentPrompt(
                name="B1",
                style="Analytical and structured",
                template="Analyze the candidate's keywords against the job description"
            ),
            AgentPrompt(
                name="B2",
                style="Evaluative and detailed",
                template="Evaluate this candidate for the position"
            )
        ]
        
        return [CandidateFilteringAgent(prompt) for prompt in prompts]
    
    @staticmethod
    def create_candidate_ranking_agents() -> List[CandidateRankingAgent]:
        """Create two different candidate ranking agents"""
        prompts = [
            AgentPrompt(
                name="C1",
                style="Numerical and objective",
                template="Assign a numerical ranking to the candidate"
            ),
            AgentPrompt(
                name="C2",
                style="Comprehensive and contextual",
                template="Evaluate this candidate with multiple dimensions"
            )
        ]
        
        return [CandidateRankingAgent(prompt) for prompt in prompts]

class RecruitmentPipeline:
    """Main pipeline for running the recruitment process"""
    
    def __init__(self):
        # Create all agents
        self.a_agents = AgentFactory.create_keyword_extraction_agents()
        self.b_agents = AgentFactory.create_candidate_filtering_agents()
        self.c_agents = AgentFactory.create_candidate_ranking_agents()
        
    def run_all_pipelines(self, resumes: Dict[str, str], job_description: str) -> List[PipelineResult]:
        """Run all possible combinations of agents on multiple resumes"""
        results = []
        
        # Generate all possible combinations (2x2x2=8)
        for a_agent, b_agent, c_agent in itertools.product(self.a_agents, self.b_agents, self.c_agents):
            sequence = f"{a_agent.prompt.name}->{b_agent.prompt.name}->{c_agent.prompt.name}"
            print(f"Running sequence: {sequence}")
            
            # Process each resume through the pipeline
            candidate_results = []
            all_filtered_profiles = []
            
            for resume_id, resume_text in resumes.items():
                print(f"  Processing resume: {resume_id}")
                
                # Stage A: Extract keywords
                a_output = a_agent.run(resume_text)
                a_result = AgentResult(a_agent.prompt.name, a_output)
                
                # Stage B: Filter candidate
                b_output = b_agent.run(a_output, job_description)
                b_result = AgentResult(b_agent.prompt.name, b_output)
                
                # Stage C: Rank individual candidate
                c_output = c_agent.run(b_output, job_description)
                c_result = AgentResult(c_agent.prompt.name, c_output)
                
                # Extract the final rank for this candidate
                if isinstance(c_output, dict):
                    final_rank = c_output.get("ranking_score")
                else:
                    final_rank = None
                
                # Store the candidate result
                candidate_result = CandidateResult(
                    resume_id=resume_id,
                    a_result=a_result,
                    b_result=b_result,
                    c_result=c_result,
                    final_rank=final_rank
                )
                candidate_results.append(candidate_result)
                
                # Store the filtered profile for final ranking
                enhanced_profile = {
                    "resume_id": resume_id,
                    "keywords": a_output,
                    "filtered_data": b_output,
                    "individual_ranking": c_output
                }
                all_filtered_profiles.append(enhanced_profile)
                
            # Rank all candidates against each other
            ranked_candidates = c_agent.rank_candidates(all_filtered_profiles, job_description)
            
            # Create the pipeline result
            pipeline_result = PipelineResult(
                sequence=sequence,
                candidate_results=candidate_results,
                ranked_candidates=ranked_candidates
            )
            
            results.append(pipeline_result)
            
        return results
    
    def evaluate_results(self, results: List[PipelineResult]) -> Dict[str, List[Tuple[str, Any]]]:
        """Evaluate results across all pipelines"""
        # For each pipeline, get the ranked list of candidates
        pipeline_rankings = {}
        
        for r in results:
            pipeline_rankings[r.sequence] = [(cand_id, rank) for cand_id, rank in r.ranked_candidates]
            
        return pipeline_rankings

def load_resumes(resume_paths: List[str]) -> Dict[str, str]:
    """Load multiple resumes from files"""
    resumes = {}
    
    for path in resume_paths:
        with open(path, 'r', encoding='utf-8') as f:
            # Use filename without extension as resume_id
            resume_id = os.path.basename(path).split('.')[0]
            resumes[resume_id] = f.read()
    
    return resumes

def main(resume_paths: List[str], job_description_path: str):
    """Main function to run the recruitment pipeline"""
    # Load resumes and job description
    resumes = load_resumes(resume_paths)
    
    with open(job_description_path, 'r', encoding='utf-8') as f:
        job_description = f.read()
    
    # Initialize pipeline
    pipeline = RecruitmentPipeline()
    
    # Run all pipelines
    results = pipeline.run_all_pipelines(resumes, job_description)
    
    # Evaluate results
    pipeline_rankings = pipeline.evaluate_results(results)
    
    # Print rankings for each pipeline
    print("\nCandidate Rankings by Pipeline:")
    for sequence, rankings in pipeline_rankings.items():
        print(f"\n{sequence}:")
        for rank, (cand_id, score) in enumerate(rankings, 1):
            print(f"  {rank}. {cand_id} (Score: {score.get('ranking_score', 'N/A')})")
    
    # Save detailed results to file
    with open('pipeline_results.json', 'w') as f:
        json.dump(
            [{
                "sequence": r.sequence,
                "candidates": [{
                    "resume_id": cr.resume_id,
                    "a_output": cr.a_result.output,
                    "b_output": cr.b_result.output,
                    "c_output": cr.c_result.output,
                    "individual_rank": cr.final_rank
                } for cr in r.candidate_results],
                "ranked_candidates": [(cand_id, result) for cand_id, result in r.ranked_candidates]
            } for r in results],
            f,
            indent=2,
            default=lambda o: repr(o) if not isinstance(o, (dict, list, str, int, float, bool, type(None))) else o
        )
    
    print(f"\nDetailed results saved to pipeline_results.json")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the recruitment pipeline")
    parser.add_argument("resumes", nargs='+', help="Paths to resume files")
    parser.add_argument("--job", "-j", dest="job_description", required=True, 
                       help="Path to the job description file")
    
    args = parser.parse_args()
    
    main(args.resumes, args.job_description) 